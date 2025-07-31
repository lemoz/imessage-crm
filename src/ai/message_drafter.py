"""
Message Drafter module for generating context-aware follow-up messages.
Uses conversation history and analysis to create appropriate responses.
"""

import logging
from typing import List, Dict, Optional, Any
import json
import openai
from config.openai_config import get_openai_client
from src.ai.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class MessageDrafter:
    """Generates draft messages for follow-ups based on conversation context."""
    
    def __init__(self, conversation_memory: Optional[ConversationMemory] = None):
        """Initialize the message drafter with OpenAI client and conversation memory.
        
        Args:
            conversation_memory: Optional ConversationMemory instance for accessing deep insights
        """
        self.client = get_openai_client()
        self.model = "o3"  # Use O3 for better contextual understanding
        self.memory = conversation_memory or ConversationMemory()
        
    def draft_message(self,
                     conversation_context: Dict[str, Any],
                     user_intent: str,
                     contact_id: str,
                     follow_up_type: str = 'general',
                     tone: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Generate context-aware message drafts using deep insights from memory.
        
        Args:
            conversation_context: Dictionary containing messages, analysis, and contact info
            user_intent: User's specific intent for the message (e.g., "check in on their health", "follow up on project")
            contact_id: Contact identifier for memory lookup
            follow_up_type: Type of follow-up (general/action_item/check_in/reminder/thanks)
            tone: Desired tone (professional/friendly/casual/empathetic)
            
        Returns:
            List of draft dictionaries with enhanced metadata
        """
        try:
            # Use analysis tone if not specified
            analysis = conversation_context.get('analysis', {})
            if not tone:
                tone = analysis.get('suggested_response_tone', 'professional')
            
            # Build the enhanced context-aware prompt
            prompt = self._build_drafting_prompt(
                conversation_context,
                user_intent,
                follow_up_type,
                tone,
                contact_id
            )
            
            # Generate drafts with O3, emphasizing voice adoption
            system_prompt = """You are a relationship assistant specializing in crafting thoughtful, empathetic, and contextually relevant messages.

CRITICAL INSTRUCTION: You MUST write in the exact voice and style of the user whose voice profile is provided. This is not optional - the authenticity of the user's voice is paramount. Study their tone, vocabulary, emoji usage, sentence structure, and distinctive phrases, then embody that style completely in your message drafts."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=1.0,  # O3 requires temperature=1
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            drafts = result.get('drafts', [])
            
            # Add metadata to each draft
            for draft in drafts:
                draft['tone'] = tone
                draft['type'] = follow_up_type
                draft['contact_id'] = contact_id
                draft['user_intent'] = user_intent
                
            logger.info(f"Generated {len(drafts)} context-aware draft messages")
            return drafts
            
        except Exception as e:
            logger.error(f"Error generating context-aware message drafts: {e}")
            return [self._get_fallback_draft(follow_up_type, tone)]
    
    def draft_follow_up(self, 
                       conversation_context: Dict[str, Any],
                       follow_up_type: str = 'general',
                       tone: Optional[str] = None,
                       specific_points: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Generate follow-up message drafts based on conversation context.
        
        Args:
            conversation_context: Dictionary containing:
                - messages: Recent conversation messages
                - analysis: Conversation analysis results
                - contact_info: Contact information
            follow_up_type: Type of follow-up (general/action_item/check_in/reminder/thanks)
            tone: Desired tone (professional/friendly/casual/empathetic)
            specific_points: Specific points to address in the message
            
        Returns:
            List of draft dictionaries containing:
                - draft: The message text
                - tone: Tone used
                - type: Type of message
                - confidence: Confidence score (0-1)
        """
        try:
            # Extract context
            messages = conversation_context.get('messages', [])
            analysis = conversation_context.get('analysis', {})
            contact_info = conversation_context.get('contact_info', {})
            
            # Use analysis tone if not specified
            if not tone:
                tone = analysis.get('suggested_response_tone', 'professional')
            
            # Create the drafting prompt
            prompt = self._create_drafting_prompt(
                messages, analysis, contact_info, follow_up_type, tone, specific_points
            )
            
            # Generate drafts
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at drafting thoughtful, contextually appropriate messages. Generate multiple draft options for the user to choose from."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1.0 if self.model == "o3" else 0.7,  # O3 only supports temperature=1
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            drafts = result.get('drafts', [])
            
            # Add metadata to each draft
            for draft in drafts:
                draft['tone'] = tone
                draft['type'] = follow_up_type
                
            logger.info(f"Generated {len(drafts)} draft messages")
            return drafts
            
        except Exception as e:
            logger.error(f"Error generating message drafts: {e}")
            return [self._get_fallback_draft(follow_up_type, tone)]
    
    def draft_action_item_follow_up(self, 
                                   action_items: List[Dict[str, Any]],
                                   conversation_context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate drafts specifically for following up on action items.
        
        Args:
            action_items: List of action items to follow up on
            conversation_context: Recent conversation context
            
        Returns:
            List of draft messages addressing the action items
        """
        if not action_items:
            return []
        
        # Prepare action item summary
        action_summary = []
        for item in action_items[:5]:  # Limit to 5 most important
            desc = item.get('description', '')
            status = item.get('status', 'pending')
            if status == 'pending' and desc:
                action_summary.append(desc)
        
        return self.draft_follow_up(
            conversation_context,
            follow_up_type='action_item',
            specific_points=action_summary
        )
    
    def draft_check_in(self, 
                      days_since_last: int,
                      relationship_health: Dict[str, Any],
                      conversation_context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate check-in messages based on relationship status.
        
        Args:
            days_since_last: Days since last conversation
            relationship_health: Relationship health metrics
            conversation_context: Historical conversation context
            
        Returns:
            List of appropriate check-in message drafts
        """
        # Determine check-in style based on relationship health
        health_score = relationship_health.get('health_score', 50)
        
        if health_score >= 75:
            tone = 'friendly'
            style = 'warm'
        elif health_score >= 50:
            tone = 'professional'
            style = 'standard'
        else:
            tone = 'empathetic'
            style = 'reconnecting'
        
        # Add context about time gap
        specific_points = []
        if days_since_last > 30:
            specific_points.append(f"It's been {days_since_last} days since we last spoke")
        elif days_since_last > 14:
            specific_points.append("It's been a couple of weeks")
        
        return self.draft_follow_up(
            conversation_context,
            follow_up_type='check_in',
            tone=tone,
            specific_points=specific_points
        )
    
    def draft_response(self,
                      incoming_message: str,
                      conversation_context: Dict[str, Any],
                      response_type: str = 'direct') -> List[Dict[str, str]]:
        """
        Generate response drafts to a specific incoming message.
        
        Args:
            incoming_message: The message to respond to
            conversation_context: Recent conversation context
            response_type: Type of response (direct/clarifying/acknowledging)
            
        Returns:
            List of response drafts
        """
        # Add the incoming message to context
        enhanced_context = conversation_context.copy()
        enhanced_context['incoming_message'] = incoming_message
        enhanced_context['response_type'] = response_type
        
        return self.draft_follow_up(
            enhanced_context,
            follow_up_type='response',
            specific_points=[f"Responding to: {incoming_message[:100]}"]
        )
    
    def _build_drafting_prompt(self,
                             conversation_context: Dict[str, Any],
                             user_intent: str,
                             follow_up_type: str,
                             tone: str,
                             contact_id: str) -> str:
        """Build a sophisticated context-aware prompt using deep insights from memory.
        
        Args:
            conversation_context: Current conversation context with messages and analysis
            user_intent: User's specific intent for the message
            follow_up_type: Type of follow-up message
            tone: Desired tone
            contact_id: Contact identifier for memory lookup
            
        Returns:
            Enhanced prompt incorporating deep insights and memory
        """
        # Get deep insights from memory
        memory_context = self.memory.get_conversation_context(contact_id)
        
        # Extract components from memory
        current_state = memory_context.get('current_state', {})
        learned_preferences = memory_context.get('learned_preferences', {})
        recent_successes = memory_context.get('recent_successes', [])
        conversation_patterns = memory_context.get('conversation_patterns', {})
        
        # Format recent successful messages
        success_examples = ""
        if recent_successes:
            success_examples = "\n\nSuccessful past messages:\n"
            for success in recent_successes[:3]:
                success_examples += f"- {success.get('message', '')}\n"
        
        # Build relationship dynamics section
        relationship_context = ""
        if current_state:
            relationship_context = f"""
Relationship Dynamics:
- Communication style: {current_state.get('communication_profile', {}).get('their_style', {}).get('formality', 'unknown')}
- Response pattern: {current_state.get('communication_profile', {}).get('their_style', {}).get('response_length', 'unknown')}
- Emotional temperature: {current_state.get('relationship_dynamics', {}).get('emotional_temperature', 'unknown')}
- Trust level: {current_state.get('relationship_dynamics', {}).get('trust_level', 'unknown')}
- Shared interests: {', '.join(current_state.get('relationship_dynamics', {}).get('shared_interests', [])[:3])}
"""
        
        # Build unresolved items section
        unresolved_section = ""
        unresolved_items = current_state.get('unresolved_items', [])
        if unresolved_items:
            unresolved_section = "\n\nUnresolved items to potentially address:\n"
            for item in unresolved_items[:3]:
                unresolved_section += f"- {item.get('topic', '')}: {item.get('context', '')} (Priority: {item.get('priority', 'unknown')})\n"
        
        # Build guidance section from current state
        guidance_section = ""
        msg_guidance = current_state.get('message_generation_guidance', {})
        if msg_guidance:
            guidance_section = f"""
Message Generation Guidance:
- Optimal message types: {', '.join([t.get('type', '') for t in msg_guidance.get('optimal_message_types', [])])}
- Recommended tone: {msg_guidance.get('tone_recommendation', tone)}
- Timing suggestion: {msg_guidance.get('timing_suggestion', 'flexible')}
- Message length: {msg_guidance.get('message_length', 'moderate')}
- Call to action style: {msg_guidance.get('call_to_action', 'open-ended')}
"""
        
        # Get recent messages for immediate context
        messages = conversation_context.get('messages', [])
        recent_messages = self._format_recent_messages(messages[-10:])
        
        # Contact info
        contact_info = conversation_context.get('contact_info', {})
        contact_name = contact_info.get('name', 'the recipient')
        
        # Get voice profile for authenticity
        voice_profile = self.memory.get_voice_profile()
        voice_summary = self.memory.get_voice_profile_summary()
        
        # Build the comprehensive prompt with voice profile
        prompt = f"""You are a relationship assistant specializing in crafting thoughtful, empathetic, and contextually relevant messages.

CRITICAL: YOU MUST ADOPT THE USER'S AUTHENTIC VOICE AND WRITING STYLE. The following voice profile is based on analysis of the user's actual messages:

USER VOICE PROFILE:
{voice_summary}

DETAILED VOICE CHARACTERISTICS:
{json.dumps(voice_profile, indent=2) if voice_profile else "No detailed voice profile available"}

YOU MUST embody this exact writing style in all drafts you generate. Match their tone, formality level, vocabulary, emoji usage, punctuation style, and distinctive phrases.

OBJECTIVE: Generate message drafts that feel authentic and strengthen the relationship while addressing the user's specific intent.

USER INTENT: {user_intent}

DEEP RELATIONSHIP CONTEXT:
Contact: {contact_name}
{relationship_context}

CONVERSATION STATE:
- Last topic: {current_state.get('conversation_state', {}).get('last_topic', 'unknown')}
- Momentum: {current_state.get('conversation_state', {}).get('conversation_momentum', 'unknown')}
- Phase: {current_state.get('conversation_state', {}).get('conversation_phase', 'unknown')}
{unresolved_section}

LEARNED PREFERENCES:
{json.dumps(learned_preferences, indent=2) if learned_preferences else "No preferences learned yet"}

COMMUNICATION PATTERNS:
- Engagement triggers: {', '.join(conversation_patterns.get('their_engagement_triggers', [])[:3])}
- Successful exchanges: {', '.join(conversation_patterns.get('successful_exchanges', [])[:3])}
- Conversation flow: {conversation_patterns.get('natural_conversation_flow', 'unknown')}
{success_examples}

{guidance_section}

RECENT CONVERSATION:
{recent_messages}

TASK: Generate 3 different message drafts for a {follow_up_type} message with {tone} tone.

Return in JSON format:
{{
    "drafts": [
        {{
            "draft": "The complete message text",
            "approach": "Brief description of the approach used",
            "confidence": 0.0-1.0,
            "addresses_unresolved": true/false,
            "leverages_insights": ["specific insights used"]
        }}
    ]
}}

Guidelines:
- Use deep insights to craft messages that resonate with their communication style
- Reference shared interests or inside jokes when appropriate
- Consider the current emotional temperature and trust level
- Address unresolved items naturally if relevant to the user's intent
- Match their preferred communication patterns (length, formality, emoji usage)
- Each draft should take a distinctly different approach while maintaining authenticity"""
        
        return prompt
    
    def _create_drafting_prompt(self,
                               messages: List[Dict[str, Any]],
                               analysis: Dict[str, Any],
                               contact_info: Dict[str, Any],
                               follow_up_type: str,
                               tone: str,
                               specific_points: Optional[List[str]] = None) -> str:
        """Create the prompt for message drafting (legacy method for backward compatibility)."""
        # Format recent conversation
        recent_messages = self._format_recent_messages(messages[-10:])  # Last 10 messages
        
        # Extract relevant analysis
        sentiment = analysis.get('sentiment_label', 'neutral')
        topics = ', '.join(analysis.get('topics', [])[:3])
        relationship = analysis.get('relationship_context', 'professional contact')
        
        # Format specific points
        points_section = ""
        if specific_points:
            points_list = '\n'.join([f"- {point}" for point in specific_points])
            points_section = f"\nSpecific points to address:\n{points_list}"
        
        # Contact context
        contact_name = contact_info.get('name', 'the recipient')
        
        prompt = f"""Generate 3 different message drafts for a {follow_up_type} message.

Context:
- Recipient: {contact_name}
- Relationship: {relationship}
- Recent conversation sentiment: {sentiment}
- Recent topics: {topics}
- Desired tone: {tone}
{points_section}

Recent conversation:
{recent_messages}

Please generate 3 drafts with slightly different approaches. Return in JSON format:
{{
    "drafts": [
        {{
            "draft": "The complete message text",
            "approach": "Brief description of the approach used",
            "confidence": 0.0-1.0
        }}
    ]
}}

Guidelines:
- Keep messages concise and natural
- Match the specified tone
- Reference recent conversation naturally
- For {follow_up_type} messages, focus on the appropriate purpose
- Make each draft distinctly different in approach"""
        
        return prompt
    
    def _format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format recent messages for context."""
        if not messages:
            return "No recent messages"
        
        formatted = []
        for msg in messages:
            sender = "Me" if msg.get('is_from_me') else "Contact"
            text = msg.get('text', '[No text]')[:200]
            formatted.append(f"{sender}: {text}")
        
        return '\n'.join(formatted)
    
    def _get_fallback_draft(self, follow_up_type: str, tone: str) -> Dict[str, str]:
        """Generate a fallback draft when API fails."""
        fallback_messages = {
            'general': {
                'professional': "Hi, I wanted to follow up on our recent conversation. Please let me know if you have any questions or if there's anything I can help with.",
                'friendly': "Hey! Just wanted to check in and see how things are going. Let me know if you need anything!",
                'casual': "Hey, following up on our chat. What's up?"
            },
            'action_item': {
                'professional': "Hi, I'm following up on the action items from our last discussion. Could you please provide an update on the status?",
                'friendly': "Hey! Just checking in on those items we discussed. How's it going?",
                'casual': "Hey, any update on what we talked about?"
            },
            'check_in': {
                'professional': "Hi, I hope this message finds you well. It's been a while since we last spoke, and I wanted to check in.",
                'friendly': "Hey! It's been a while - hope you're doing well! How have you been?",
                'casual': "Hey, long time no talk! How's it going?"
            }
        }
        
        message_type = follow_up_type if follow_up_type in fallback_messages else 'general'
        tone_type = tone if tone in fallback_messages[message_type] else 'professional'
        
        return {
            'draft': fallback_messages[message_type][tone_type],
            'approach': 'Standard template (fallback)',
            'confidence': 0.5,
            'tone': tone,
            'type': follow_up_type
        }
    
    def load_analysis_to_memory(self, contact_id: str, analysis_file: str) -> None:
        """
        Load analysis from JSON file into conversation memory.
        
        Args:
            contact_id: Contact identifier
            analysis_file: Path to the analysis JSON file
        """
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            # Extract relevant insights from the analysis
            analysis_results = analysis_data.get('analysis_results', {})
            statistics = analysis_data.get('statistics', {})
            
            # Create a state object from the analysis
            state = {
                'conversation_state': {
                    'last_topic': analysis_results.get('topics', ['unknown'])[0] if analysis_results.get('topics') else 'unknown',
                    'conversation_momentum': 'active' if statistics.get('avg_response_time', 0) < 60 else 'moderate',
                    'last_speaker': 'unknown',
                    'time_since_last_message': 'unknown',
                    'conversation_phase': 'ongoing'
                },
                'unresolved_items': [
                    {'topic': item, 'context': 'From conversation analysis', 'priority': 'medium'}
                    for item in analysis_results.get('action_items', [])
                ],
                'relationship_dynamics': {
                    'relationship_stage': 'established',
                    'emotional_temperature': analysis_results.get('sentiment_label', 'neutral'),
                    'trust_level': 'high' if analysis_results.get('sentiment', 0) > 0.5 else 'moderate',
                    'conflict_areas': [],
                    'bonding_topics': analysis_results.get('topics', []),
                    'shared_interests': [],
                    'inside_jokes_references': []
                },
                'communication_profile': {
                    'their_style': {
                        'formality': 'casual',
                        'response_length': 'moderate',
                        'emoji_usage': 'occasional',
                        'preferred_topics': analysis_results.get('topics', []),
                        'communication_pace': 'moderate' if statistics.get('avg_response_time', 0) > 30 else 'rapid',
                        'best_times': 'flexible'
                    },
                    'my_style': {
                        'typical_approach': 'friendly and supportive',
                        'successful_patterns': 'thoughtful responses',
                        'areas_to_adjust': 'response timing'
                    },
                    'style_compatibility': 'good match'
                },
                'message_generation_guidance': {
                    'optimal_message_types': [
                        {'type': 'check-in', 'reasoning': 'maintain connection'},
                        {'type': 'affection', 'reasoning': 'strengthen bond'}
                    ],
                    'topics_to_address': analysis_results.get('next_steps', []),
                    'topics_to_avoid': [],
                    'tone_recommendation': analysis_results.get('suggested_response_tone', 'friendly'),
                    'timing_suggestion': 'flexible',
                    'message_length': 'moderate',
                    'call_to_action': 'open-ended'
                }
            }
            
            # Save to memory
            self.memory.save_conversation_state(contact_id, state)
            
            # Update learned preferences
            preferences = {
                'response_time_preference': f"{statistics.get('avg_response_time', 0):.0f} minutes",
                'message_balance': f"You: {statistics.get('from_you', 0)}, Them: {statistics.get('from_yao', 0)}",
                'conversation_type': analysis_results.get('conversation_type', 'personal'),
                'urgency_level': analysis_results.get('urgency_level', 'low')
            }
            self.memory.update_learned_preferences(contact_id, preferences)
            
            logger.info(f"Loaded analysis for {contact_id} into memory")
            
        except Exception as e:
            logger.error(f"Error loading analysis to memory: {e}")