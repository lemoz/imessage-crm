"""
ConversationSimulator - Advanced multi-turn conversation simulation.
Uses authentic user voice profile and relationship dynamics to simulate strategic conversations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import asyncio
from datetime import datetime
from config.openai_config import get_openai_client
from src.ai.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class ConversationSimulator:
    """Simulates multi-turn conversations using authentic voice profiles and relationship context."""
    
    def __init__(self, conversation_memory: ConversationMemory):
        """
        Initialize the ConversationSimulator.
        
        Args:
            conversation_memory: ConversationMemory instance containing voice profile and relationship data
        """
        self.memory = conversation_memory
        self.client = get_openai_client()
        self.model = "o3"  # Use O3 for sophisticated conversation simulation
        
    async def simulate_conversations(self, 
                                   topic: str,
                                   opening_message: str,
                                   contact_id: str,
                                   num_turns: int = 3,
                                   num_variations: int = 3) -> List[Dict[str, Any]]:
        """
        Simulate multiple conversation variations for strategic planning.
        
        Args:
            topic: The conversation topic/goal (e.g., "budget discussion")
            opening_message: The initial message to start the conversation
            contact_id: Contact identifier for relationship context
            num_turns: Number of back-and-forth exchanges per conversation
            num_variations: Number of different conversation scenarios to generate
            
        Returns:
            List of simulated conversation variations with metadata
        """
        try:
            logger.info(f"Starting conversation simulation: {topic} ({num_variations} variations, {num_turns} turns each)")
            
            # Load context data
            relationship_context = self.memory.get_conversation_context(contact_id)
            voice_profile = self.memory.get_voice_profile()
            
            if not voice_profile:
                logger.warning("No voice profile found - simulations may be less authentic")
            
            # Generate multiple conversation variations
            simulated_conversations = []
            
            for variation in range(num_variations):
                try:
                    logger.info(f"Generating conversation variation {variation + 1}/{num_variations}")
                    
                    conversation = await self._simulate_single_conversation(
                        topic=topic,
                        opening_message=opening_message,
                        relationship_context=relationship_context,
                        voice_profile=voice_profile,
                        num_turns=num_turns,
                        variation_id=variation + 1
                    )
                    
                    simulated_conversations.append(conversation)
                    
                except Exception as e:
                    logger.error(f"Error generating conversation variation {variation + 1}: {e}")
                    continue
            
            logger.info(f"Completed conversation simulation: {len(simulated_conversations)} variations generated")
            return simulated_conversations
            
        except Exception as e:
            logger.error(f"Error in conversation simulation: {e}")
            return []
    
    async def _simulate_single_conversation(self,
                                          topic: str,
                                          opening_message: str,
                                          relationship_context: Dict[str, Any],
                                          voice_profile: Dict[str, Any],
                                          num_turns: int,
                                          variation_id: int) -> Dict[str, Any]:
        """
        Simulate a single conversation variation.
        
        Returns:
            Dictionary containing the complete simulated conversation with metadata
        """
        conversation = {
            'variation_id': variation_id,
            'topic': topic,
            'opening_message': opening_message,
            'exchanges': [],
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'num_turns': num_turns,
                'model_used': self.model
            }
        }
        
        # Start with the opening message
        conversation_history = [
            {'sender': 'user', 'message': opening_message, 'turn': 0}
        ]
        
        # Simulate the alternating turns
        for turn in range(1, num_turns + 1):
            try:
                # Yao's response
                yao_response = await self._generate_yao_response(
                    conversation_history=conversation_history,
                    relationship_context=relationship_context,
                    topic=topic,
                    turn=turn
                )
                
                conversation_history.append({
                    'sender': 'contact',
                    'message': yao_response,
                    'turn': turn
                })
                
                # User's response (if not the last turn)
                if turn < num_turns:
                    user_response = await self._generate_user_response(
                        conversation_history=conversation_history,
                        voice_profile=voice_profile,
                        topic=topic,
                        turn=turn
                    )
                    
                    conversation_history.append({
                        'sender': 'user',
                        'message': user_response,
                        'turn': turn
                    })
                
            except Exception as e:
                logger.error(f"Error generating turn {turn} for variation {variation_id}: {e}")
                break
        
        # Store the complete conversation
        conversation['exchanges'] = conversation_history
        
        # Add conversation analysis
        conversation['analysis'] = self._analyze_conversation_outcome(conversation_history, topic)
        
        return conversation
    
    async def _generate_yao_response(self,
                                   conversation_history: List[Dict],
                                   relationship_context: Dict[str, Any],
                                   topic: str,
                                   turn: int) -> str:
        """
        Generate Yao's response using relationship context and communication patterns.
        
        Returns:
            Simulated response from Yao
        """
        try:
            # Create Yao's persona prompt
            yao_prompt = self._create_yao_persona_prompt(
                conversation_history=conversation_history,
                relationship_context=relationship_context,
                topic=topic,
                turn=turn
            )
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are simulating Yao's responses in a conversation. You must stay completely in character based on the relationship dynamics and communication patterns provided."
                    },
                    {
                        "role": "user",
                        "content": yao_prompt
                    }
                ],
                temperature=1.0  # O3 requires temperature=1
            )
            
            # Extract the response
            yao_response = response.choices[0].message.content.strip()
            
            # Remove any quotes or formatting
            if yao_response.startswith('"') and yao_response.endswith('"'):
                yao_response = yao_response[1:-1]
            
            return yao_response
            
        except Exception as e:
            logger.error(f"Error generating Yao's response: {e}")
            return "I'm not sure how to respond to that right now."
    
    async def _generate_user_response(self,
                                    conversation_history: List[Dict],
                                    voice_profile: Dict[str, Any],
                                    topic: str,
                                    turn: int) -> str:
        """
        Generate user's response using authentic voice profile.
        
        Returns:
            Simulated response from the user in their authentic voice
        """
        try:
            # Create user's persona prompt
            user_prompt = self._create_user_persona_prompt(
                conversation_history=conversation_history,
                voice_profile=voice_profile,
                topic=topic,
                turn=turn
            )
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are simulating the USER's responses. You MUST write in their exact voice and style as defined in the voice profile. This is critical for authenticity."
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=1.0  # O3 requires temperature=1
            )
            
            # Extract the response
            user_response = response.choices[0].message.content.strip()
            
            # Remove any quotes or formatting
            if user_response.startswith('"') and user_response.endswith('"'):
                user_response = user_response[1:-1]
            
            return user_response
            
        except Exception as e:
            logger.error(f"Error generating user's response: {e}")
            return "Let me think about that..."
    
    def _create_yao_persona_prompt(self,
                                 conversation_history: List[Dict],
                                 relationship_context: Dict[str, Any],
                                 topic: str,
                                 turn: int) -> str:
        """
        Create the prompt for generating Yao's response based on relationship dynamics.
        """
        # Format conversation history
        history_text = self._format_conversation_history(conversation_history)
        
        # Extract relationship insights
        current_state = relationship_context.get('current_state', {})
        relationship_dynamics = current_state.get('relationship_dynamics', {})
        communication_profile = current_state.get('communication_profile', {})
        
        prompt = f"""You are simulating Yao's response in a conversation about: {topic}

RELATIONSHIP CONTEXT:
- Relationship Stage: {relationship_dynamics.get('relationship_stage', 'long-term partners')}
- Emotional Temperature: {relationship_dynamics.get('emotional_temperature', 'warm')}
- Trust Level: {relationship_dynamics.get('trust_level', 'high')}
- Communication Style: {communication_profile.get('their_style', {}).get('formality', 'casual and warm')}

YAO'S COMMUNICATION PATTERNS:
- Response Length: {communication_profile.get('their_style', {}).get('response_length', 'moderate')}
- Emoji Usage: {communication_profile.get('their_style', {}).get('emoji_usage', 'occasional')}
- Communication Pace: {communication_profile.get('their_style', {}).get('communication_pace', 'moderate')}
- Preferred Topics: {', '.join(communication_profile.get('their_style', {}).get('preferred_topics', ['daily life']))}

CURRENT CONVERSATION CONTEXT:
- Topic Sensitivity: Budget/financial discussions can be sensitive
- Emotional State: Generally positive but may feel some stress about finances
- Relationship Dynamics: Collaborative approach preferred, values teamwork

CONVERSATION HISTORY:
{history_text}

INSTRUCTIONS:
Generate Yao's next response (Turn {turn}). She should:
1. Respond naturally based on her communication patterns
2. Consider the relationship dynamics and trust level
3. Show appropriate engagement with the topic
4. Maintain emotional consistency with the conversation flow
5. Use her typical communication style (emoji usage, response length, etc.)

Generate only Yao's direct response - no quotation marks or explanations."""
        
        return prompt
    
    def _create_user_persona_prompt(self,
                                  conversation_history: List[Dict],
                                  voice_profile: Dict[str, Any],
                                  topic: str,
                                  turn: int) -> str:
        """
        Create the prompt for generating the user's response using their authentic voice.
        """
        # Format conversation history
        history_text = self._format_conversation_history(conversation_history)
        
        # Get voice profile summary
        voice_summary = self.memory.get_voice_profile_summary()
        
        prompt = f"""You are simulating the USER's response in a conversation about: {topic}

CRITICAL: You MUST write in the user's exact voice and style. This is based on analysis of their actual messages.

USER VOICE PROFILE SUMMARY:
{voice_summary}

DETAILED VOICE CHARACTERISTICS:
{json.dumps(voice_profile, indent=2) if voice_profile else "No detailed profile available"}

CONVERSATION GOAL:
The user wants to have a gentle, collaborative discussion about {topic}. They aim to:
- Maintain a warm, supportive tone
- Frame challenges as team goals
- Show empathy and understanding
- Use their natural communication patterns

CONVERSATION HISTORY:
{history_text}

INSTRUCTIONS:
Generate the USER's next response (Turn {turn}). You MUST:
1. Write in their exact voice using their vocabulary, phrases, and style
2. Match their emoji usage patterns and placement
3. Use their typical sentence structure and length
4. Include their signature phrases when appropriate
5. Maintain their tone and formality level
6. Show their collaborative communication approach
7. Advance the conversation goal strategically but authentically

Generate only the user's direct response - no quotation marks or explanations."""
        
        return prompt
    
    def _format_conversation_history(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for prompts."""
        formatted_lines = []
        
        for exchange in conversation_history:
            sender_name = "You" if exchange['sender'] == 'user' else "Yao"
            message = exchange['message']
            turn = exchange['turn']
            
            formatted_lines.append(f"Turn {turn}, {sender_name}: {message}")
        
        return '\n'.join(formatted_lines)
    
    def _analyze_conversation_outcome(self, conversation_history: List[Dict], topic: str) -> Dict[str, Any]:
        """
        Analyze the simulated conversation outcome.
        
        Returns:
            Analysis of conversation effectiveness and dynamics
        """
        analysis = {
            'total_exchanges': len(conversation_history),
            'conversation_length': sum(len(ex['message']) for ex in conversation_history),
            'topic': topic,
            'engagement_level': 'moderate',  # Could be enhanced with sentiment analysis
            'outcome_prediction': 'positive',  # Simplified for now
            'key_themes': [],
            'potential_issues': [],
            'strengths': []
        }
        
        # Basic analysis based on conversation length and structure
        if analysis['total_exchanges'] >= 5:
            analysis['engagement_level'] = 'high'
        elif analysis['total_exchanges'] <= 2:
            analysis['engagement_level'] = 'low'
        
        return analysis
    
    def get_conversation_summary(self, simulated_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary across all conversation variations.
        
        Args:
            simulated_conversations: List of simulated conversation variations
            
        Returns:
            Summary analysis across all variations
        """
        if not simulated_conversations:
            return {'error': 'No conversations to analyze'}
        
        summary = {
            'total_variations': len(simulated_conversations),
            'topic': simulated_conversations[0]['topic'],
            'generated_at': datetime.now().isoformat(),
            'average_exchanges': 0,
            'common_themes': [],
            'predicted_outcomes': [],
            'strategic_insights': []
        }
        
        # Calculate averages
        total_exchanges = sum(len(conv['exchanges']) for conv in simulated_conversations)
        summary['average_exchanges'] = total_exchanges / len(simulated_conversations)
        
        # Collect outcomes
        for conv in simulated_conversations:
            analysis = conv.get('analysis', {})
            summary['predicted_outcomes'].append(analysis.get('outcome_prediction', 'unknown'))
        
        # Strategic insights
        summary['strategic_insights'] = [
            "Multiple conversation paths simulated for strategic planning",
            f"Average conversation length: {summary['average_exchanges']:.1f} exchanges",
            "Voice-authentic user responses generated",
            "Relationship-aware contact responses simulated"
        ]
        
        return summary