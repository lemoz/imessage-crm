"""
VoiceAnalyzer service for analyzing the user's unique writing voice and style.
Creates a detailed voice profile based on analyzing sent messages across conversations.
"""

import logging
from typing import Dict, List, Any, Optional
import json
import asyncio
from datetime import datetime
from config.openai_config import get_openai_client
from src.messaging.message_reader import MessageReader

logger = logging.getLogger(__name__)

class VoiceAnalyzer:
    """Analyzes user's message patterns to create a unique voice profile."""
    
    def __init__(self, message_reader: Optional[MessageReader] = None):
        """
        Initialize the VoiceAnalyzer.
        
        Args:
            message_reader: MessageReader instance for accessing message data
        """
        self.client = get_openai_client()
        self.model = "o3"  # Use O3 for deep linguistic analysis
        self.message_reader = message_reader or MessageReader()
        
    async def analyze_user_voice(self, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Analyze the user's unique voice and writing style from their sent messages.
        
        Args:
            sample_size: Number of recent sent messages to analyze
            
        Returns:
            Dictionary containing detailed voice profile analysis
        """
        try:
            logger.info(f"Starting voice analysis for {sample_size} messages...")
            
            # Get a diverse sample of user's messages
            user_messages = await self._get_user_message_sample(sample_size)
            
            if not user_messages:
                logger.warning("No user messages found for voice analysis")
                return self._get_default_voice_profile()
            
            logger.info(f"Analyzing {len(user_messages)} user messages for voice patterns")
            
            # Create specialized linguistic analysis prompt
            voice_analysis_prompt = self._create_voice_analysis_prompt(user_messages)
            
            # Call O3 for deep linguistic analysis
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert linguistic analyst specializing in identifying unique writing voice patterns and communication styles. Your task is to analyze a corpus of messages and extract a detailed voice profile."""
                    },
                    {
                        "role": "user", 
                        "content": voice_analysis_prompt
                    }
                ],
                temperature=1.0,  # O3 requires temperature=1
                response_format={"type": "json_object"}
            )
            
            # Parse the voice profile
            voice_profile = json.loads(response.choices[0].message.content)
            
            # Add metadata
            voice_profile['analysis_metadata'] = {
                'analyzed_at': datetime.now().isoformat(),
                'messages_analyzed': len(user_messages),
                'sample_size_requested': sample_size,
                'model_used': self.model
            }
            
            logger.info("Voice analysis completed successfully")
            return voice_profile
            
        except Exception as e:
            logger.error(f"Error during voice analysis: {e}")
            return self._get_default_voice_profile()
    
    async def _get_user_message_sample(self, sample_size: int) -> List[Dict[str, Any]]:
        """
        Get a diverse sample of user's sent messages from various conversations.
        
        Args:
            sample_size: Number of messages to retrieve
            
        Returns:
            List of user messages with metadata
        """
        try:
            # Get all chats to ensure diverse sample
            all_chats = self.message_reader.list_all_chats()
            
            user_messages = []
            messages_per_chat = max(1, sample_size // len(all_chats)) if all_chats else sample_size
            
            # Collect messages from various conversations for diversity
            for chat in all_chats:
                if len(user_messages) >= sample_size:
                    break
                    
                try:
                    chat_id = chat.get('chat_id')
                    if not chat_id:
                        continue
                    
                    # Get messages from this chat
                    if chat.get('is_group', False):
                        chat_messages = self.message_reader.get_group_chat_messages(
                            chat_id, limit=messages_per_chat * 3  # Get more to filter for user messages
                        )
                    else:
                        # For direct chats, get the contact ID
                        contact_id = chat.get('contact_id')
                        if contact_id:
                            chat_messages = self.message_reader.get_direct_conversation(
                                contact_id, limit=messages_per_chat * 3
                            )
                        else:
                            continue
                    
                    # Filter for user messages only
                    chat_user_messages = [
                        msg for msg in chat_messages.get('messages', [])
                        if msg.get('is_from_me', False) and msg.get('text', '').strip()
                    ]
                    
                    # Add chat context to messages
                    for msg in chat_user_messages[:messages_per_chat]:
                        msg['chat_context'] = {
                            'chat_id': chat_id,
                            'is_group': chat.get('is_group', False),
                            'participants': chat.get('participants', [])
                        }
                        user_messages.append(msg)
                        
                except Exception as e:
                    logger.warning(f"Error processing chat {chat.get('chat_id', 'unknown')}: {e}")
                    continue
            
            # Sort by date to get most recent messages
            user_messages.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Return requested sample size
            return user_messages[:sample_size]
            
        except Exception as e:
            logger.error(f"Error retrieving user message sample: {e}")
            return []
    
    def _create_voice_analysis_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """
        Create a specialized prompt for analyzing the user's voice and writing style.
        
        Args:
            messages: List of user messages to analyze
            
        Returns:
            Comprehensive prompt for voice analysis
        """
        # Format messages for analysis
        message_corpus = self._format_messages_for_analysis(messages)
        
        # Calculate basic statistics
        total_chars = sum(len(msg.get('text', '')) for msg in messages)
        avg_message_length = total_chars / len(messages) if messages else 0
        
        return f"""Analyze the following corpus of messages to create a detailed voice profile. These are all messages sent by the same person across different conversations.

CORPUS STATISTICS:
- Total messages: {len(messages)}
- Average message length: {avg_message_length:.1f} characters
- Date range: {messages[-1].get('date', 'unknown') if messages else 'none'} to {messages[0].get('date', 'unknown') if messages else 'none'}

MESSAGE CORPUS:
{message_corpus}

Please analyze this corpus and provide a comprehensive voice profile in the following JSON format:

{{
    "tone": {{
        "primary_tone": "Overall dominant tone (e.g., casual, warm, professional)",
        "secondary_tones": ["List of other frequent tones"],
        "tone_description": "Detailed description of how tone varies and when",
        "emotional_range": "Description of emotional expression patterns"
    }},
    
    "formality": {{
        "level": "formal/semi-formal/informal/very-informal",
        "formality_description": "Detailed description of formality patterns",
        "greeting_style": "How this person typically starts conversations",
        "closing_style": "How this person typically ends conversations",
        "title_usage": "How they address others (names, titles, etc.)"
    }},
    
    "vocabulary_and_phrasing": {{
        "common_phrases": ["List of frequently used phrases or expressions"],
        "filler_words": ["Common filler words or transitions used"],
        "vocabulary_level": "simple/moderate/complex/mixed",
        "vocabulary_description": "Description of word choice patterns",
        "unique_expressions": ["Distinctive phrases or expressions unique to this person"],
        "slang_usage": "Description of slang, abbreviations, or internet language usage"
    }},
    
    "sentence_structure": {{
        "typical_length": "short/medium/long/varied",
        "complexity": "simple/compound/complex/mixed",
        "structure_description": "Detailed description of sentence patterns",
        "question_style": "How this person asks questions",
        "statement_style": "How this person makes statements",
        "paragraph_organization": "How they organize longer messages"
    }},
    
    "emoji_and_symbols": {{
        "usage_frequency": "never/rare/occasional/frequent/very-frequent",
        "common_emojis": ["List of most frequently used emojis"],
        "emoji_placement": "Where emojis typically appear (beginning/middle/end)",
        "emoji_function": "How emojis are used (emphasis, emotion, decoration)",
        "symbol_usage": "Use of other symbols like !, ?, ..., etc.",
        "emoticon_usage": "Use of text-based emoticons like :) or :P"
    }},
    
    "punctuation_style": {{
        "exclamation_usage": "How frequently and in what context exclamation points are used",
        "question_mark_style": "Question mark usage patterns",
        "comma_usage": "Comma usage patterns (heavy/light/standard)",
        "period_usage": "Period usage in messages",
        "ellipsis_usage": "Use of ... or .. for pauses/trailing off",
        "capitalization": "Capitalization patterns and consistency",
        "other_punctuation": "Use of dashes, parentheses, quotes, etc."
    }},
    
    "communication_patterns": {{
        "message_timing": "Patterns in when/how quickly they respond",
        "conversation_initiation": "How they start conversations",
        "topic_transitions": "How they change subjects or topics",
        "agreement_expression": "How they show agreement or approval",
        "disagreement_expression": "How they express disagreement or concerns",
        "enthusiasm_markers": "How they show excitement or enthusiasm",
        "support_expression": "How they offer support or encouragement"
    }},
    
    "contextual_adaptation": {{
        "group_vs_individual": "Differences between group and one-on-one communication",
        "relationship_variation": "How style varies with different relationships",
        "topic_sensitivity": "How communication changes with serious vs casual topics",
        "time_awareness": "How communication adapts to time of day or urgency"
    }},
    
    "distinctive_markers": {{
        "signature_phrases": ["Phrases that are uniquely characteristic of this person"],
        "humor_style": "Type and frequency of humor used",
        "personality_indicators": "Key personality traits evident in communication",
        "communication_quirks": ["Unique habits or patterns in their messaging"],
        "authenticity_markers": ["Elements that make their voice most recognizable"]
    }}
}}

Focus on identifying the unique, distinctive elements that make this person's communication style recognizable and authentic. Pay special attention to patterns that occur consistently across different types of conversations and relationships."""
    
    def _format_messages_for_analysis(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for linguistic analysis.
        
        Args:
            messages: List of messages to format
            
        Returns:
            Formatted message corpus string
        """
        formatted_messages = []
        
        for i, msg in enumerate(messages, 1):
            text = msg.get('text', '').strip()
            if not text:
                continue
                
            date = msg.get('date', 'unknown')
            chat_context = msg.get('chat_context', {})
            is_group = chat_context.get('is_group', False)
            
            context_info = f"[{date}] {'Group' if is_group else 'Direct'}"
            formatted_messages.append(f"{context_info}: {text}")
            
            # Limit to prevent overwhelming the context
            if i >= 800:  # Keep some buffer for the rest of the prompt
                break
        
        return '\n'.join(formatted_messages)
    
    def _get_default_voice_profile(self) -> Dict[str, Any]:
        """
        Return a default voice profile when analysis fails.
        
        Returns:
            Default voice profile structure
        """
        return {
            "tone": {
                "primary_tone": "casual and friendly",
                "secondary_tones": ["supportive", "warm"],
                "tone_description": "Generally casual and approachable communication style",
                "emotional_range": "Moderate emotional expression"
            },
            "formality": {
                "level": "informal",
                "formality_description": "Relaxed, conversational approach",
                "greeting_style": "Simple greetings",
                "closing_style": "Casual endings",
                "title_usage": "First names preferred"
            },
            "vocabulary_and_phrasing": {
                "common_phrases": ["sounds good", "no problem", "thanks"],
                "filler_words": ["um", "like", "so"],
                "vocabulary_level": "moderate",
                "vocabulary_description": "Clear, straightforward language",
                "unique_expressions": [],
                "slang_usage": "Occasional modern slang"
            },
            "sentence_structure": {
                "typical_length": "medium",
                "complexity": "mixed",
                "structure_description": "Mix of simple and compound sentences",
                "question_style": "Direct questions",
                "statement_style": "Clear statements",
                "paragraph_organization": "Short paragraphs"
            },
            "emoji_and_symbols": {
                "usage_frequency": "occasional",
                "common_emojis": ["😊", "👍", "❤️"],
                "emoji_placement": "end",
                "emoji_function": "emotional emphasis",
                "symbol_usage": "Standard punctuation",
                "emoticon_usage": "rare"
            },
            "punctuation_style": {
                "exclamation_usage": "moderate",
                "question_mark_style": "standard",
                "comma_usage": "standard",
                "period_usage": "consistent",
                "ellipsis_usage": "occasional",
                "capitalization": "standard",
                "other_punctuation": "minimal"
            },
            "communication_patterns": {
                "message_timing": "responsive",
                "conversation_initiation": "friendly",
                "topic_transitions": "smooth",
                "agreement_expression": "positive",
                "disagreement_expression": "diplomatic",
                "enthusiasm_markers": "exclamation points",
                "support_expression": "encouraging"
            },
            "contextual_adaptation": {
                "group_vs_individual": "consistent style",
                "relationship_variation": "slightly more formal with new contacts",
                "topic_sensitivity": "adapts tone appropriately",
                "time_awareness": "considerate of timing"
            },
            "distinctive_markers": {
                "signature_phrases": [],
                "humor_style": "light and friendly",
                "personality_indicators": ["helpful", "considerate"],
                "communication_quirks": [],
                "authenticity_markers": ["consistent tone", "clear communication"]
            },
            "analysis_metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "messages_analyzed": 0,
                "sample_size_requested": 0,
                "model_used": self.model,
                "error": "Failed to analyze - using default profile"
            }
        }
    
    async def save_voice_profile(self, profile: Dict[str, Any], filepath: str) -> None:
        """
        Save voice profile to a JSON file.
        
        Args:
            profile: Voice profile dictionary
            filepath: Path to save the profile
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(profile, f, indent=2)
            logger.info(f"Voice profile saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving voice profile: {e}")
    
    def load_voice_profile(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load voice profile from a JSON file.
        
        Args:
            filepath: Path to the profile file
            
        Returns:
            Voice profile dictionary or None if failed
        """
        try:
            with open(filepath, 'r') as f:
                profile = json.load(f)
            logger.info(f"Voice profile loaded from {filepath}")
            return profile
        except Exception as e:
            logger.error(f"Error loading voice profile: {e}")
            return None