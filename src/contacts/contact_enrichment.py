"""Contact enrichment system using OpenAI."""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from openai.types.chat import ChatCompletion

from src.database.contacts_db import ContactsDatabaseConnector
from src.database.chat_state import ChatStateManager
from src.messaging import MessageSender
from config.openai_config import OpenAIConfig

logger = logging.getLogger(__name__)

class ContactEnrichmentManager:
    """Manages contact enrichment using OpenAI."""
    
    def __init__(self,
                 contacts_db: ContactsDatabaseConnector,
                 message_sender: MessageSender,
                 state_manager: ChatStateManager,
                 system_phone: str,
                 openai_client: Optional[OpenAI] = None):
        """
        Initialize contact enrichment manager.
        
        Args:
            contacts_db: Contacts database connector
            message_sender: Message sending system
            state_manager: Chat state management system
            system_phone: System's phone number
            openai_client: Optional OpenAI client. If not provided, will create one.
        """
        self.contacts_db = contacts_db
        self.message_sender = message_sender
        self.state_manager = state_manager
        self.system_phone = system_phone
        self.openai_client = openai_client or OpenAIConfig.get_client()
        
    def generate_enrichment_request(self, chat_guid: str, 
                                  participants: Dict[str, List[str]]) -> Tuple[str, List[int]]:
        """
        Generate an enrichment request message for participants.
        
        Args:
            chat_guid: Chat GUID
            participants: Dict mapping phone numbers to list of missing fields
            
        Returns:
            Tuple of (generated message text, list of attempt IDs)
            
        Raises:
            OpenAIError: If message generation fails
        """
        try:
            chat_info = self.state_manager.get_chat_info(chat_guid)
            
            # Build context for OpenAI
            context = {
                "chat_name": chat_info["display_name"],
                "total_participants": len(chat_info["participants"]),
                "existing_participants": [p for p in chat_info["participants"] 
                                       if p != self.system_phone],
                "new_participants": participants
            }
            
            logger.info(f"Generating enrichment request for chat {chat_guid}")
            message = self._generate_message_with_openai(context)
            
            # Track the requests in the database
            attempt_ids = self._track_enrichment_request(chat_guid, participants)
            
            return message, attempt_ids
            
        except Exception as e:
            logger.error(f"Failed to generate enrichment request: {e}")
            raise
    
    def _generate_message_with_openai(self, context: Dict) -> str:
        """
        Generate message using OpenAI.
        
        Args:
            context: Context dictionary containing chat info
            
        Returns:
            Generated message text
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a professional business assistant helping to gather "
                        "contact information in a group chat setting. Generate a message "
                        "that is friendly but professional, clearly explaining what "
                        "information is needed and why it's helpful."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                    Generate a message for a business group chat:
                    
                    Chat Name: {context['chat_name']}
                    Total Participants: {context['total_participants']}
                    New Participants: {context['new_participants']}
                    
                    Request the missing information politely and professionally.
                    Explain why having complete contact information helps everyone
                    in the group chat communicate effectively.
                    """
                }
            ]
            
            logger.debug(f"Sending request to OpenAI with context: {context}")
            response: ChatCompletion = self.openai_client.chat.completions.create(
                model=OpenAIConfig.DEFAULT_MODEL,
                messages=messages,
                temperature=OpenAIConfig.DEFAULT_TEMPERATURE
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise
            
    def _track_enrichment_request(self, chat_guid: str, 
                                participants: Dict[str, List[str]]) -> List[int]:
        """
        Track enrichment request in contacts database.
        
        Args:
            chat_guid: Chat GUID
            participants: Dict of participants and their missing fields
            
        Returns:
            List of attempt IDs
        """
        attempt_ids = []
        
        try:
            for phone, missing_fields in participants.items():
                # Get or create contact ID
                contact_id = self.contacts_db.find_by_identifier('phone', phone)
                if not contact_id:
                    # Create new contact if not found
                    contact_id = f"contact_{datetime.now().strftime('%Y%m%d%H%M%S')}_{phone[-4:]}"
                    self.contacts_db.create_contact(contact_id)
                    self.contacts_db.add_identifier(
                        contact_id=contact_id,
                        id_type='phone',
                        value=phone,
                        confidence=1.0,  # Phone from iMessage is verified
                        verified=True
                    )
                
                # Record collection attempt for each missing field
                for field in missing_fields:
                    attempt_id = self.contacts_db.record_collection_attempt(
                        contact_id=contact_id,
                        attempt_type=f"{field}_collection",
                        chat_guid=chat_guid,
                        details={
                            'field': field,
                            'method': 'direct_request',
                            'context': 'group_chat'
                        }
                    )
                    attempt_ids.append(attempt_id)
                
        except Exception as e:
            logger.error(f"Failed to track enrichment request: {e}")
            # Don't raise - this shouldn't block the main flow
            
        return attempt_ids
