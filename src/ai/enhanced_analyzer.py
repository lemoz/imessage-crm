"""
Enhanced Conversation Analyzer with improved context extraction for message generation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from config.openai_config import get_openai_client

class EnhancedConversationAnalyzer:
    """Enhanced analyzer that extracts rich context for message generation."""
    
    def __init__(self):
        self.client = get_openai_client()
        self.model = "o3"
    
    def analyze_for_message_generation(self, messages: List[Dict[str, Any]], 
                                     contact_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze conversation specifically to extract context for generating next messages.
        
        Returns enhanced context including:
        - Current conversation state
        - Unresolved topics
        - Communication style profile
        - Relationship dynamics
        - Optimal messaging strategies
        """
        
        # Get recent messages for immediate context
        recent_messages = messages[-50:] if len(messages) > 50 else messages
        
        # Create specialized prompt for message generation context
        prompt = self._create_message_generation_prompt(messages, recent_messages, contact_info)
        
        # Call O3 for deep analysis
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": """You are an expert at analyzing conversations to understand relationship dynamics, 
                    communication patterns, and context needed for generating appropriate follow-up messages. 
                    Focus on extracting actionable insights that will help craft personalized, contextually-appropriate messages."""
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _create_message_generation_prompt(self, all_messages: List[Dict], 
                                        recent_messages: List[Dict], 
                                        contact_info: Dict) -> str:
        """Create a comprehensive prompt for message generation context."""
        
        # Format recent conversation
        recent_convo = self._format_messages(recent_messages)
        
        # Calculate conversation statistics
        stats = self._calculate_conversation_stats(all_messages)
        
        return f"""Analyze this conversation to extract context for generating appropriate follow-up messages.

Contact: {contact_info.get('name', 'Unknown')} ({contact_info.get('phone', 'Unknown')})

CONVERSATION STATISTICS:
- Total messages analyzed: {len(all_messages)}
- Message ratio: Me {stats['my_ratio']:.1%}, {contact_info.get('name', 'Them')} {stats['their_ratio']:.1%}
- Average response time: {stats['avg_response_time']} minutes
- Conversation span: {stats['date_range']}

RECENT CONVERSATION (Last 50 messages):
{recent_convo}

Please analyze and provide the following in JSON format:

{{
    "conversation_state": {{
        "last_topic": "What was being discussed most recently",
        "conversation_momentum": "active/slowing/stalled",
        "last_speaker": "who sent the last message",
        "time_since_last_message": "how long ago",
        "conversation_phase": "opening/mid/closing/dormant"
    }},
    
    "unresolved_items": [
        {{
            "topic": "What needs resolution",
            "context": "Brief context",
            "priority": "high/medium/low",
            "suggested_approach": "How to address it"
        }}
    ],
    
    "communication_profile": {{
        "their_style": {{
            "formality": "casual/moderate/formal",
            "response_length": "brief/moderate/detailed",
            "emoji_usage": "none/occasional/frequent",
            "preferred_topics": ["list of topics they engage with most"],
            "communication_pace": "rapid/moderate/slow",
            "best_times": "when they're most responsive"
        }},
        "my_style": {{
            "typical_approach": "how I usually communicate",
            "successful_patterns": "what works well",
            "areas_to_adjust": "what could improve"
        }},
        "style_compatibility": "How well our styles match and suggestions"
    }},
    
    "relationship_dynamics": {{
        "relationship_stage": "early/developing/established/long-term",
        "emotional_temperature": "warm/neutral/cool/variable",
        "trust_level": "building/moderate/high",
        "conflict_areas": ["recurring friction points"],
        "bonding_topics": ["what brings us closer"],
        "shared_interests": ["common ground topics"],
        "inside_jokes_references": ["shared humor or references"]
    }},
    
    "current_context": {{
        "their_current_situation": "What they might be dealing with based on recent messages",
        "my_current_situation": "What I've shared about my situation",
        "upcoming_events": ["mentioned future plans or events"],
        "ongoing_projects": ["things we're working on together"],
        "recent_emotions": "emotional state from recent exchanges"
    }},
    
    "message_generation_guidance": {{
        "optimal_message_types": [
            {{
                "type": "check-in/planning/affection/humor/practical",
                "reasoning": "why this type would work now",
                "example_opener": "suggested way to start"
            }}
        ],
        "topics_to_address": ["priority topics for next message"],
        "topics_to_avoid": ["sensitive areas to skip for now"],
        "tone_recommendation": "warm/playful/supportive/neutral/professional",
        "timing_suggestion": "immediate/wait_few_hours/tomorrow/give_space",
        "message_length": "brief/moderate/detailed",
        "call_to_action": "question/suggestion/statement/open-ended"
    }},
    
    "conversation_patterns": {{
        "successful_exchanges": ["what patterns lead to good conversations"],
        "conversation_killers": ["what tends to end conversations"],
        "their_engagement_triggers": ["what gets them talking"],
        "natural_conversation_flow": "how conversations typically progress"
    }},
    
    "contextual_cues": {{
        "time_patterns": "when they're most active",
        "response_indicators": "signs they're engaged vs busy",
        "mood_indicators": "how to read their emotional state",
        "conversation_energy": "current energy level of exchange"
    }}
}}

Focus on actionable insights that will help generate messages that feel natural, 
timely, and appropriate for this specific relationship and current moment."""
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """Format messages for analysis."""
        formatted = []
        for msg in messages:
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')
            date = msg.get('date', '')
            formatted.append(f"[{date}] {sender}: {text}")
        return "\n".join(formatted)
    
    def _calculate_conversation_stats(self, messages: List[Dict]) -> Dict:
        """Calculate conversation statistics."""
        my_count = sum(1 for m in messages if m.get('is_from_me', False))
        their_count = len(messages) - my_count
        
        # Calculate average response time
        response_times = []
        for i in range(1, len(messages)):
            if messages[i]['is_from_me'] != messages[i-1]['is_from_me']:
                try:
                    t1 = datetime.strptime(messages[i-1]['date'], '%Y-%m-%d %H:%M:%S')
                    t2 = datetime.strptime(messages[i]['date'], '%Y-%m-%d %H:%M:%S')
                    diff = (t2 - t1).total_seconds() / 60
                    if 0 < diff < 1440:  # Less than 24 hours
                        response_times.append(diff)
                except:
                    pass
        
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        # Date range
        if messages:
            first_date = messages[0].get('date', 'Unknown')
            last_date = messages[-1].get('date', 'Unknown')
            date_range = f"{first_date} to {last_date}"
        else:
            date_range = "No messages"
        
        return {
            'my_ratio': my_count / len(messages) if messages else 0,
            'their_ratio': their_count / len(messages) if messages else 0,
            'avg_response_time': round(avg_response, 1),
            'date_range': date_range
        }