"""
Conversation Memory System for maintaining context across analyses.
Now includes voice profile management for authentic message generation.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Maintains conversation history and context for better message generation."""
    
    def __init__(self, storage_path: str = "~/.imessage_crm/conversation_memory"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Voice profile storage
        self.voice_profile_path = self.storage_path / "voice_profile.json"
        self._cached_voice_profile = None
    
    def save_conversation_state(self, contact_id: str, state: Dict[str, Any]) -> None:
        """Save the current conversation state for a contact."""
        file_path = self.storage_path / f"{contact_id.replace('+', '')}.json"
        
        # Load existing memory
        memory = self.load_conversation_memory(contact_id)
        
        # Update with new state
        memory['last_updated'] = datetime.now().isoformat()
        memory['current_state'] = state
        
        # Add to history
        if 'state_history' not in memory:
            memory['state_history'] = []
        
        memory['state_history'].append({
            'timestamp': datetime.now().isoformat(),
            'state': state
        })
        
        # Keep only last 10 states
        memory['state_history'] = memory['state_history'][-10:]
        
        # Save
        with open(file_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def load_conversation_memory(self, contact_id: str) -> Dict[str, Any]:
        """Load conversation memory for a contact."""
        file_path = self.storage_path / f"{contact_id.replace('+', '')}.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        
        return {
            'contact_id': contact_id,
            'created': datetime.now().isoformat(),
            'current_state': {},
            'state_history': [],
            'learned_preferences': {},
            'successful_messages': [],
            'conversation_patterns': {}
        }
    
    def add_successful_message(self, contact_id: str, message: str, 
                             context: Dict[str, Any], response: Optional[str] = None) -> None:
        """Record a successful message exchange for learning."""
        memory = self.load_conversation_memory(contact_id)
        
        success_record = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'context': context,
            'response': response,
            'response_time': None  # Can be calculated later
        }
        
        if 'successful_messages' not in memory:
            memory['successful_messages'] = []
        
        memory['successful_messages'].append(success_record)
        
        # Keep only last 50 successful exchanges
        memory['successful_messages'] = memory['successful_messages'][-50:]
        
        # Save
        file_path = self.storage_path / f"{contact_id.replace('+', '')}.json"
        with open(file_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def update_learned_preferences(self, contact_id: str, preferences: Dict[str, Any]) -> None:
        """Update learned preferences about a contact."""
        memory = self.load_conversation_memory(contact_id)
        
        if 'learned_preferences' not in memory:
            memory['learned_preferences'] = {}
        
        # Merge preferences
        memory['learned_preferences'].update(preferences)
        memory['last_updated'] = datetime.now().isoformat()
        
        # Save
        file_path = self.storage_path / f"{contact_id.replace('+', '')}.json"
        with open(file_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def get_conversation_context(self, contact_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation context for message generation."""
        memory = self.load_conversation_memory(contact_id)
        
        return {
            'current_state': memory.get('current_state', {}),
            'learned_preferences': memory.get('learned_preferences', {}),
            'recent_successes': memory.get('successful_messages', [])[-5:],
            'conversation_patterns': memory.get('conversation_patterns', {}),
            'state_history': memory.get('state_history', [])[-3:]
        }
    
    def save_voice_profile(self, voice_profile: Dict[str, Any]) -> None:
        """
        Save the user's voice profile to persistent storage.
        
        Args:
            voice_profile: Complete voice analysis profile
        """
        try:
            with open(self.voice_profile_path, 'w') as f:
                json.dump(voice_profile, f, indent=2)
            
            # Cache the profile
            self._cached_voice_profile = voice_profile
            
            logger.info(f"Voice profile saved to {self.voice_profile_path}")
            
        except Exception as e:
            logger.error(f"Error saving voice profile: {e}")
    
    def load_voice_profile(self, filepath: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the user's voice profile from storage.
        
        Args:
            filepath: Optional custom filepath, defaults to standard location
            
        Returns:
            Voice profile dictionary or empty dict if not found
        """
        try:
            # Use custom filepath or default
            profile_path = Path(filepath) if filepath else self.voice_profile_path
            
            # Return cached profile if available and using default path
            if not filepath and self._cached_voice_profile:
                return self._cached_voice_profile
            
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    voice_profile = json.load(f)
                
                # Cache if using default path
                if not filepath:
                    self._cached_voice_profile = voice_profile
                
                logger.info(f"Voice profile loaded from {profile_path}")
                return voice_profile
            else:
                logger.warning(f"Voice profile not found at {profile_path}")
                return {}
                
        except Exception as e:
            logger.error(f"Error loading voice profile: {e}")
            return {}
    
    def get_voice_profile(self) -> Dict[str, Any]:
        """
        Get the current voice profile, loading from disk if needed.
        
        Returns:
            Voice profile dictionary
        """
        return self.load_voice_profile()
    
    def has_voice_profile(self) -> bool:
        """
        Check if a voice profile exists.
        
        Returns:
            True if voice profile exists, False otherwise
        """
        return self.voice_profile_path.exists()
    
    def get_voice_profile_summary(self) -> str:
        """
        Get a formatted summary of the voice profile for use in prompts.
        
        Returns:
            Formatted string summarizing the user's voice characteristics
        """
        voice_profile = self.get_voice_profile()
        
        if not voice_profile:
            return "No voice profile available."
        
        # Extract key characteristics for prompt
        tone = voice_profile.get('tone', {})
        formality = voice_profile.get('formality', {})
        vocab = voice_profile.get('vocabulary_and_phrasing', {})
        emoji = voice_profile.get('emoji_and_symbols', {})
        patterns = voice_profile.get('communication_patterns', {})
        distinctive = voice_profile.get('distinctive_markers', {})
        
        summary_parts = []
        
        # Tone and style
        if tone.get('primary_tone'):
            summary_parts.append(f"Tone: {tone['primary_tone']}")
        
        # Formality
        if formality.get('level'):
            summary_parts.append(f"Formality: {formality['level']}")
        
        # Common phrases
        common_phrases = vocab.get('common_phrases', [])
        if common_phrases:
            summary_parts.append(f"Common phrases: {', '.join(common_phrases[:3])}")
        
        # Emoji usage
        if emoji.get('usage_frequency'):
            emoji_info = f"Emoji usage: {emoji['usage_frequency']}"
            common_emojis = emoji.get('common_emojis', [])
            if common_emojis:
                emoji_info += f" (common: {', '.join(common_emojis[:3])})"
            summary_parts.append(emoji_info)
        
        # Signature phrases
        signature_phrases = distinctive.get('signature_phrases', [])
        if signature_phrases:
            summary_parts.append(f"Signature phrases: {', '.join(signature_phrases[:2])}")
        
        # Humor style
        humor = distinctive.get('humor_style')
        if humor:
            summary_parts.append(f"Humor: {humor}")
        
        return "; ".join(summary_parts) if summary_parts else "Voice profile incomplete."