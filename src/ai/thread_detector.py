"""
Thread Detector module for grouping related messages into logical conversation threads.
Handles multi-day conversations and topic continuity.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

class ThreadDetector:
    """Groups messages into logical conversation threads based on time and content."""
    
    def __init__(self, time_gap_hours: int = 4, similarity_threshold: float = 0.3):
        """
        Initialize the thread detector.
        
        Args:
            time_gap_hours: Maximum hours between messages to consider same thread
            similarity_threshold: Minimum similarity score to group messages
        """
        self.time_gap_hours = time_gap_hours
        self.similarity_threshold = similarity_threshold
        self.logger = logger
        
    def detect_threads(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group messages into conversation threads.
        
        Args:
            messages: List of message dictionaries with 'text', 'date', 'is_from_me' fields
            
        Returns:
            List of thread dictionaries containing:
                - thread_id: Unique identifier for the thread
                - messages: List of messages in the thread
                - start_time: Thread start timestamp
                - end_time: Thread end timestamp
                - duration: Thread duration in minutes
                - message_count: Number of messages
                - participants: List of participants
                - topic_summary: Brief summary of thread topic
        """
        if not messages:
            return []
        
        # Sort messages by date
        sorted_messages = sorted(messages, key=lambda m: m.get('date', ''))
        
        threads = []
        current_thread = []
        thread_id = 0
        
        for i, message in enumerate(sorted_messages):
            if not current_thread:
                current_thread.append(message)
            else:
                # Check if message belongs to current thread
                if self._belongs_to_thread(message, current_thread):
                    current_thread.append(message)
                else:
                    # Finalize current thread and start new one
                    threads.append(self._create_thread_object(current_thread, thread_id))
                    thread_id += 1
                    current_thread = [message]
        
        # Don't forget the last thread
        if current_thread:
            threads.append(self._create_thread_object(current_thread, thread_id))
        
        return threads
    
    def find_related_threads(self, threads: List[Dict[str, Any]], max_days_apart: int = 7) -> List[List[int]]:
        """
        Find threads that are related to each other.
        
        Args:
            threads: List of thread dictionaries from detect_threads
            max_days_apart: Maximum days between threads to consider related
            
        Returns:
            List of related thread groups (list of thread IDs)
        """
        related_groups = []
        processed = set()
        
        for i, thread in enumerate(threads):
            if i in processed:
                continue
                
            # Find all threads related to this one
            group = [i]
            processed.add(i)
            
            for j, other_thread in enumerate(threads[i+1:], start=i+1):
                if j in processed:
                    continue
                    
                if self._are_threads_related(thread, other_thread, max_days_apart):
                    group.append(j)
                    processed.add(j)
            
            if len(group) > 1:
                related_groups.append(group)
        
        return related_groups
    
    def merge_threads(self, threads: List[Dict[str, Any]], thread_ids: List[int]) -> Dict[str, Any]:
        """
        Merge multiple threads into a single conversation.
        
        Args:
            threads: List of all threads
            thread_ids: IDs of threads to merge
            
        Returns:
            Merged thread dictionary
        """
        if not thread_ids:
            return {}
        
        # Collect all messages from specified threads
        all_messages = []
        for thread_id in thread_ids:
            if 0 <= thread_id < len(threads):
                all_messages.extend(threads[thread_id]['messages'])
        
        # Sort by date
        all_messages.sort(key=lambda m: m.get('date', ''))
        
        return self._create_thread_object(all_messages, thread_ids[0])
    
    def _belongs_to_thread(self, message: Dict[str, Any], thread: List[Dict[str, Any]]) -> bool:
        """Check if a message belongs to the current thread."""
        if not thread:
            return False
        
        # Check time gap
        last_message = thread[-1]
        time_gap = self._calculate_time_gap(last_message, message)
        
        if time_gap > self.time_gap_hours:
            return False
        
        # Check content similarity for edge cases
        if time_gap > self.time_gap_hours / 2:
            # For larger gaps, check if content is related
            similarity = self._calculate_content_similarity(message, thread)
            return similarity >= self.similarity_threshold
        
        return True
    
    def _calculate_time_gap(self, msg1: Dict[str, Any], msg2: Dict[str, Any]) -> float:
        """Calculate time gap between messages in hours."""
        try:
            date1 = datetime.fromisoformat(msg1.get('date', ''))
            date2 = datetime.fromisoformat(msg2.get('date', ''))
            gap = abs((date2 - date1).total_seconds() / 3600)
            return gap
        except:
            return float('inf')
    
    def _calculate_content_similarity(self, message: Dict[str, Any], thread: List[Dict[str, Any]]) -> float:
        """
        Calculate content similarity between message and thread.
        Simple implementation - can be enhanced with better NLP.
        """
        message_text = message.get('text', '')
        if not message_text:
            return 0.0
        message_text = message_text.lower()
        
        # Extract keywords from message
        message_words = set(re.findall(r'\b\w+\b', message_text))
        
        # Extract keywords from recent thread messages
        thread_words = set()
        for msg in thread[-5:]:  # Look at last 5 messages
            text = msg.get('text', '').lower()
            thread_words.update(re.findall(r'\b\w+\b', text))
        
        # Calculate Jaccard similarity
        if not thread_words:
            return 0.0
        
        intersection = len(message_words & thread_words)
        union = len(message_words | thread_words)
        
        return intersection / union if union > 0 else 0.0
    
    def _create_thread_object(self, messages: List[Dict[str, Any]], thread_id: int) -> Dict[str, Any]:
        """Create a thread object from a list of messages."""
        if not messages:
            return {}
        
        start_time = messages[0].get('date', '')
        end_time = messages[-1].get('date', '')
        
        # Calculate duration
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
        except:
            duration_minutes = 0
        
        # Identify participants
        participants = set()
        for msg in messages:
            if msg.get('is_from_me'):
                participants.add('Me')
            else:
                participants.add('Contact')
        
        # Generate topic summary (simple version - first non-trivial message)
        topic_summary = "No content"
        for msg in messages:
            text = msg.get('text', '')
            if text:
                text = text.strip()
                if len(text) > 10:
                    topic_summary = text[:100] + ('...' if len(text) > 100 else '')
                    break
        
        return {
            'thread_id': thread_id,
            'messages': messages,
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': round(duration_minutes, 1),
            'message_count': len(messages),
            'participants': list(participants),
            'topic_summary': topic_summary
        }
    
    def _are_threads_related(self, thread1: Dict[str, Any], thread2: Dict[str, Any], max_days_apart: int) -> bool:
        """Check if two threads are related based on time and content."""
        # Check time proximity
        try:
            end1 = datetime.fromisoformat(thread1['end_time'])
            start2 = datetime.fromisoformat(thread2['start_time'])
            days_apart = abs((start2 - end1).days)
            
            if days_apart > max_days_apart:
                return False
        except:
            return False
        
        # Check content similarity
        # Extract text from both threads
        text1 = ' '.join([m.get('text', '') for m in thread1['messages'][-3:]])
        text2 = ' '.join([m.get('text', '') for m in thread2['messages'][:3]])
        
        # Simple keyword overlap check
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                       'i', 'you', 'we', 'they', 'it', 'is', 'are', 'was', 'were', 'been',
                       'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                       'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        words1 -= common_words
        words2 -= common_words
        
        if not words1 or not words2:
            return False
        
        # Check overlap
        overlap = len(words1 & words2)
        min_size = min(len(words1), len(words2))
        
        return overlap / min_size >= 0.3  # 30% overlap threshold