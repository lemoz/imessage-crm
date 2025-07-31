"""
Conversation Analyzer module for processing conversations through LLM.
Extracts insights, topics, sentiment, and action items from message threads.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json
import openai
from config.openai_config import get_openai_client

logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """Analyzes conversations using LLM to extract insights and metadata."""
    
    def __init__(self):
        """Initialize the conversation analyzer with OpenAI client."""
        self.client = get_openai_client()
        # Use O3 for deep reasoning and complex relationship analysis
        # O3 provides advanced reasoning capabilities for nuanced understanding
        self.model = "o3"
        
    def analyze_conversation(self, messages: List[Dict[str, Any]], contact_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze a conversation to extract insights, topics, and action items.
        
        Args:
            messages: List of message dictionaries with 'text', 'is_from_me', 'date' fields
            contact_info: Optional contact information dictionary
            
        Returns:
            Dictionary containing:
                - summary: Brief conversation summary
                - topics: List of main topics discussed
                - sentiment: Overall sentiment score (-1 to 1)
                - sentiment_label: Sentiment label (positive/neutral/negative)
                - action_items: List of action items extracted
                - key_points: Important points from the conversation
                - conversation_type: Type of conversation (business/personal/support/etc)
                - urgency_level: low/medium/high
                - follow_up_needed: Boolean indicating if follow-up is needed
                - suggested_response_tone: Recommended tone for responses
        """
        try:
            # Format messages for analysis
            conversation_text = self._format_conversation(messages)
            
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(conversation_text, contact_info)
            
            # Call OpenAI API
            # O3 model requires temperature=1 (default)
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert conversation analyst. Analyze conversations to extract insights, topics, sentiment, and actionable information."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            # O3 doesn't support custom temperature
            if self.model != "o3":
                api_params["temperature"] = 0.3
                
            response = self.client.chat.completions.create(**api_params)
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            analysis['analyzed_at'] = datetime.now().isoformat()
            analysis['message_count'] = len(messages)
            
            logger.info(f"Successfully analyzed conversation with {len(messages)} messages")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return self._get_default_analysis()
    
    def analyze_batch(self, conversations: List[Tuple[str, List[Dict]]]) -> List[Dict[str, Any]]:
        """
        Analyze multiple conversations in batch.
        
        Args:
            conversations: List of tuples (conversation_id, messages)
            
        Returns:
            List of analysis results with conversation_id included
        """
        results = []
        for conversation_id, messages in conversations:
            try:
                analysis = self.analyze_conversation(messages)
                analysis['conversation_id'] = conversation_id
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing conversation {conversation_id}: {e}")
                analysis = self._get_default_analysis()
                analysis['conversation_id'] = conversation_id
                results.append(analysis)
        
        return results
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable conversation format including attachments."""
        formatted_lines = []
        
        for msg in messages:
            # Handle different sender formats
            if 'sender' in msg:
                # New format with explicit sender info (from direct/group chat methods)
                sender = msg['sender']
            else:
                # Legacy format
                sender = "Me" if msg.get('is_from_me') else "Contact"
            
            timestamp = msg.get('date', '')
            
            # Build message content
            content_parts = []
            
            # Add text content if present
            text = msg.get('text', '').strip()
            if text:
                content_parts.append(text)
            
            # Add attachment information if present
            if msg.get('has_attachment') or msg.get('attachment_name') or msg.get('attachment_type'):
                attachment_desc = self._format_attachment_for_analysis(msg)
                if attachment_desc:
                    content_parts.append(attachment_desc)
            
            # Only include the message if it has some content
            if content_parts:
                full_content = " ".join(content_parts)
                formatted_lines.append(f"[{timestamp}] {sender}: {full_content}")
        
        return "\n".join(formatted_lines)
    
    def _format_attachment_for_analysis(self, msg: Dict[str, Any]) -> str:
        """Format attachment information for LLM analysis."""
        filename = msg.get('attachment_name')
        mime_type = msg.get('attachment_type')  # This is actually mime_type from DB
        
        # Determine attachment type from mime type or filename
        attachment_type = 'file'
        if mime_type:
            if mime_type.startswith('image/'):
                attachment_type = 'image'
            elif mime_type.startswith('video/'):
                attachment_type = 'video'
            elif mime_type.startswith('audio/'):
                attachment_type = 'audio'
            elif mime_type in ['application/pdf', 'text/plain']:
                attachment_type = 'document'
        elif filename:
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            if extension in ['jpg', 'jpeg', 'png', 'gif', 'heic']:
                attachment_type = 'image'
            elif extension in ['mp4', 'mov', 'avi']:
                attachment_type = 'video'
            elif extension in ['mp3', 'wav', 'm4a']:
                attachment_type = 'audio'
            elif extension in ['pdf', 'doc', 'docx']:
                attachment_type = 'document'
        
        # Create descriptive text for LLM
        if filename and len(filename) < 50:
            return f"[shared {attachment_type}: {filename}]"
        elif mime_type:
            return f"[shared {attachment_type} ({mime_type})]"
        else:
            return f"[shared {attachment_type}]"
    
    def _create_analysis_prompt(self, conversation_text: str, contact_info: Optional[Dict] = None) -> str:
        """Create the analysis prompt for the LLM."""
        contact_context = ""
        if contact_info:
            contact_context = f"\nContact Information: {contact_info.get('name', 'Unknown')} ({contact_info.get('phone', 'Unknown')})"
        
        return f"""Analyze the following conversation and provide insights in JSON format.{contact_context}

Conversation:
{conversation_text}

Please provide the following analysis in JSON format:
{{
    "summary": "Brief 2-3 sentence summary of the conversation",
    "topics": ["topic1", "topic2", ...],
    "sentiment": 0.0,  // -1 (very negative) to 1 (very positive)
    "sentiment_label": "positive/neutral/negative",
    "action_items": ["action1", "action2", ...],
    "key_points": ["point1", "point2", ...],
    "conversation_type": "business/personal/support/sales/other",
    "urgency_level": "low/medium/high",
    "follow_up_needed": true/false,
    "suggested_response_tone": "professional/friendly/empathetic/casual",
    "relationship_context": "Brief description of the apparent relationship",
    "next_steps": ["suggested next step 1", "suggested next step 2", ...]
}}"""
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis structure when analysis fails."""
        return {
            "summary": "Unable to analyze conversation",
            "topics": [],
            "sentiment": 0.0,
            "sentiment_label": "neutral",
            "action_items": [],
            "key_points": [],
            "conversation_type": "unknown",
            "urgency_level": "low",
            "follow_up_needed": False,
            "suggested_response_tone": "professional",
            "relationship_context": "Unknown",
            "next_steps": [],
            "analyzed_at": datetime.now().isoformat(),
            "error": True
        }
    
    def extract_action_items(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract specific action items from a conversation.
        
        Returns:
            List of action items with details:
                - description: What needs to be done
                - assigned_to: Who should do it (me/contact/unclear)
                - due_date: Extracted due date if mentioned
                - priority: high/medium/low
                - status: pending/mentioned/completed
        """
        conversation_text = self._format_conversation(messages)
        
        prompt = f"""Extract all action items from this conversation. Include tasks, commitments, and follow-ups.

Conversation:
{conversation_text}

Return a JSON array of action items:
[
    {{
        "description": "Clear description of the action",
        "assigned_to": "me/contact/unclear",
        "due_date": "YYYY-MM-DD or null",
        "priority": "high/medium/low",
        "status": "pending/mentioned/completed",
        "context": "Brief context about why this is needed"
    }}
]"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting action items from conversations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('action_items', [])
            
        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return []
    
    def analyze_chat_conversation(self, messages: List[Dict[str, Any]], chat_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a conversation with full chat context.
        
        Args:
            messages: List of messages from get_direct_conversation or get_group_chat_messages
            chat_info: Chat information including is_group, participants, etc.
            
        Returns:
            Enhanced analysis with chat-specific insights
        """
        try:
            # Format messages for analysis
            conversation_text = self._format_conversation(messages)
            
            # Determine chat type and create appropriate prompt
            is_group = chat_info.get('is_group', False)
            
            if is_group:
                participants = chat_info.get('participants', [])
                participant_context = f"Group chat with {len(participants)} participants: {', '.join(participants[:5])}"
                if len(participants) > 5:
                    participant_context += f" and {len(participants) - 5} others"
                
                system_prompt = """You are an expert at analyzing group chat conversations. 
                Pay attention to group dynamics, who participates most, topic changes, and the overall group atmosphere."""
                
                analysis_prompt = f"""Analyze this group chat conversation.
{participant_context}

{self._create_analysis_prompt(conversation_text)}

Additionally, provide these group-specific insights in your JSON response:
{{
    "most_active_participants": ["participant1", "participant2", ...],
    "group_dynamics": "Description of how the group interacts",
    "dominant_voices": ["participants who lead conversations"],
    "quiet_participants": ["participants who rarely speak"],
    "group_cohesion": "low/medium/high",
    "conflict_level": "none/low/medium/high"
}}"""
            else:
                # Direct conversation
                contact_id = chat_info.get('contact_id', 'Unknown')
                system_prompt = """You are an expert at analyzing one-on-one conversations. 
                Focus on the relationship dynamics, communication patterns, and the back-and-forth nature of the dialogue."""
                
                analysis_prompt = f"""Analyze this direct conversation with {contact_id}.

{self._create_analysis_prompt(conversation_text)}

Additionally, provide these direct conversation insights in your JSON response:
{{
    "response_pattern": "Description of how quickly and thoroughly each person responds",
    "conversation_balance": "Who initiates more, who responds more",
    "communication_style_match": "How well the communication styles align",
    "emotional_connection": "low/medium/high",
    "conversation_depth": "surface/moderate/deep"
}}"""
            
            # Call OpenAI API
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            # O3 doesn't support custom temperature
            if self.model != "o3":
                api_params["temperature"] = 0.3
                
            response = self.client.chat.completions.create(**api_params)
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata
            analysis['analyzed_at'] = datetime.now().isoformat()
            analysis['message_count'] = len(messages)
            analysis['chat_type'] = 'group' if is_group else 'direct'
            analysis['chat_info'] = chat_info
            
            logger.info(f"Successfully analyzed {'group' if is_group else 'direct'} conversation with {len(messages)} messages")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing chat conversation: {e}")
            return self._get_default_analysis()