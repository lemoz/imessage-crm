"""
Group chat management module for automated CRM functionality.
Handles detection and setup of new group chats.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

from src.database import DatabaseConnector
from src.contacts.contact import Contact
from src.contacts.contact_manager import ContactManager
from src.messaging.message_sender import MessageSender

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroupChatManager:
    """Manages automated group chat detection and setup."""
    
    def __init__(
            self,
            db_connector: DatabaseConnector,
            contact_manager: ContactManager,
            message_sender: MessageSender,
            system_phone: str,
            state_manager=None
        ):
        """
        Initialize the group chat manager.
        
        Args:
            db_connector: Database connection for chat.db
            contact_manager: Contact management system
            message_sender: Message sending system
            system_phone: Phone number of the system
            state_manager: Optional ChatStateManager instance
        """
        self.db = db_connector
        self.contact_manager = contact_manager
        self.message_sender = message_sender
        self.system_phone = system_phone
        
        # Initialize state manager
        if state_manager is None:
            from ..database.chat_state import ChatStateManager
            state_manager = ChatStateManager()
        self.state = state_manager
        
        # Process existing chats during initialization
        logger.info("Processing existing chats during initialization...")
        self._process_existing_chats()
        
        # Initialize with current time
        self.last_check_time = int(datetime.now().timestamp() * 1e9)  # Current time in nanoseconds
        self._save_last_check_time(self.last_check_time)
        logger.info(f"Initialized last_check_time to: {self.last_check_time}")
        
    def _process_existing_chats(self):
        """Process all existing group chats during initialization."""
        try:
            # Use the same query but without time filter
            existing_chats = self.check_new_group_chats(process_all=True)
            logger.info(f"Found {len(existing_chats)} existing chats to process")
            
            # Process each chat
            for chat in existing_chats:
                logger.info(f"Auto-processing existing chat: {chat['guid']}")
                self.state.record_new_chat(chat)
                
        except Exception as e:
            logger.error(f"Error processing existing chats: {e}", exc_info=True)
    
    def check_new_group_chats(self, since_time: Optional[int] = None, process_all: bool = False) -> List[Dict]:
        """
        Check for new group chats that include our system number.
        Detects both chats we create and chats others add us to.
        
        Args:
            since_time: Optional timestamp to check from (in Messages epoch nanoseconds)
                       If not provided, will check all unprocessed chats
        
        Returns:
            List of new or active group chats with their participants
        """
        query = """
        WITH potential_chats AS (
            -- Find all group chats where we're involved
            SELECT DISTINCT
                c.ROWID as chat_id,
                c.guid,
                c.display_name,
                c.style
            FROM chat c
            WHERE c.style = 43  -- Group chats
            AND (
                -- Either we're a participant
                EXISTS (
                    SELECT 1 FROM chat_handle_join chj
                    JOIN handle h ON chj.handle_id = h.ROWID
                    WHERE chj.chat_id = c.ROWID
                    AND h.id IN (?, ?)
                )
                -- Or we've sent messages to this chat
                OR EXISTS (
                    SELECT 1 FROM message m
                    JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                    WHERE cmj.chat_id = c.ROWID
                    AND m.is_from_me = 1
                )
            )
        ),
        group_chats AS (
            -- Get participant info for these chats
            SELECT 
                pc.*,
                GROUP_CONCAT(DISTINCT h.id) as participant_numbers,
                COUNT(DISTINCT h.ROWID) as participant_count
            FROM potential_chats pc
            JOIN chat_handle_join chj ON pc.chat_id = chj.chat_id
            JOIN handle h ON chj.handle_id = h.ROWID
            GROUP BY pc.chat_id
            -- Include chats with 2 or more participants
            HAVING participant_count >= 2
        )
        SELECT 
            gc.*,
            m.ROWID as last_message_id,
            m.date as last_message_date,
            m.text as last_message_text,
            m.is_from_me as last_message_is_from_me,
            CASE 
                WHEN gc.participant_numbers LIKE ? THEN 1
                ELSE 0
            END as is_participant
        FROM group_chats gc
        LEFT JOIN (
            -- Get latest message for each chat
            SELECT 
                cmj.chat_id,
                m.ROWID,
                m.date,
                m.text,
                m.is_from_me
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN (
                SELECT chat_id, MAX(message_id) as last_mid
                FROM chat_message_join
                GROUP BY chat_id
            ) latest ON cmj.chat_id = latest.chat_id 
            AND cmj.message_id = latest.last_mid
        ) m ON gc.chat_id = m.chat_id
        ORDER BY m.date DESC
        """
        
        try:
            # Execute query with our phone number (try both with and without +1)
            phone_no_prefix = self.system_phone.lstrip('+1')
            phone_with_prefix = f'+1{phone_no_prefix}'
            logger.info(f"Checking for group chats with numbers: {phone_with_prefix} and {phone_no_prefix}")
            
            # Pass phone numbers twice - once for each format in EXISTS clause,
            # and once more for the LIKE check
            chats = self.db.execute_query(
                query, 
                (phone_with_prefix, phone_no_prefix, f'%{phone_no_prefix}%')
            )
            logger.info(f"Found {len(chats)} total group chats")
            
            # Debug log raw results
            for idx, chat in enumerate(chats):
                logger.info(f"Raw chat {idx}: {chat}")
            
            # Filter for unprocessed chats
            new_chats = []
            for chat in chats:
                try:
                    chat_info = {
                        'chat_id': chat['chat_id'],
                        'guid': chat['guid'],
                        'name': chat['display_name'] or 'Group Chat',
                        'participants': [p.strip() for p in chat['participant_numbers'].split(',')],
                        'last_message_id': chat['last_message_id'],
                        'last_message_date': chat['last_message_date'],
                        'last_message_text': chat['last_message_text'],
                        'last_message_is_from_me': bool(chat['last_message_is_from_me'])
                    }
                    
                    logger.info(f"Processing chat: {chat_info['guid']}")
                    logger.info(f"Participants: {chat_info['participants']}")
                    
                    # Consider chat as ours if we've sent messages to it
                    is_our_chat = chat_info['last_message_is_from_me']
                    logger.info(f"Chat {chat_info['guid']} is_our_chat: {is_our_chat}")
                    
                    if is_our_chat:
                        # For regular checks (not initialization)
                        if not process_all:
                            # Only include chats with messages after last_check_time
                            if since_time and chat_info['last_message_date'] <= since_time:
                                logger.info(f"Skipping chat {chat_info['guid']} - no new messages")
                                continue
                        
                        # Check if chat is already processed
                        is_processed = self.state.is_chat_processed(chat_info['guid'])
                        logger.info(f"Chat {chat_info['guid']} processed status: {is_processed}")
                        
                        if not is_processed:
                            logger.info(f"Found new unprocessed chat that we own: {chat_info}")
                            new_chats.append(chat_info)
                        else:
                            logger.info(f"Skipping already processed chat: {chat_info['guid']}")
                    else:
                        logger.info(f"Skipping chat we don't own: {chat_info['guid']}")
                        
                except Exception as e:
                    logger.error(f"Error processing chat result: {e}", exc_info=True)
                    logger.error(f"Problematic chat data: {chat}")
                    continue
                    
            logger.info(f"Found {len(new_chats)} new unprocessed chats")
            return new_chats
            
        except Exception as e:
            logger.error(f"Error checking for new group chats: {e}", exc_info=True)
            return []
            logger.error(f"Error checking for new group chats: {e}")
            logger.exception(e)
            
        return new_chats
    
    def process_new_chat(self, chat_info: Dict) -> None:
        """
        Process a newly detected group chat.
        
        Args:
            chat_info: Dictionary containing chat details
        """
        try:
            logger.info(f"Processing new chat: {chat_info}")
            
            # Record the chat in the state manager
            self.state.record_new_chat(chat_info)
            
            # Process each participant
            for phone in chat_info['participants']:
                if phone != self.system_phone:
                    self._process_participant(phone, chat_info)
                    
            # Send welcome message
            self._send_welcome_message(chat_info)
            
            # Update last processed message, if available
            if chat_info.get('last_message_id'):
                self.state.update_last_processed_message(chat_info['guid'], chat_info['last_message_id'])
                
            logger.info(f"Successfully processed new group chat: {chat_info['guid']}")
            
        except Exception as e:
            logger.error(f"Error processing chat {chat_info['guid']}: {e}", exc_info=True)
            raise
    
    def _process_participant(self, phone: str, chat_info: Dict) -> None:
        """
        Process a participant in a group chat.
        
        Args:
            phone: Participant's phone number
            chat_info: Chat information
        """
        # Check if contact exists
        contact = self.contact_manager.find_by_identifier(phone)
        
        if not contact:
            # Create new contact
            contact = Contact(
                name=f"Unknown ({phone})",  # Will be updated when we get more info
                phone_numbers=[phone]
            )
            self.contact_manager.add_contact(contact)
        
        # Add chat metadata
        contact.set_metadata('in_crm', 'true')
        contact.set_metadata('join_date', datetime.now().isoformat())
        contact.set_metadata('source_chat', chat_info['guid'])
        
        # Save updates
        self.contact_manager.update_contact(contact)
    
    def _send_welcome_message(self, chat_info: Dict) -> None:
        """
        Send welcome message to new group chat.
        
        Args:
            chat_info: Chat information
        """
        welcome_msg = (
            "👋 Hello! I'm here to help manage our conversation. "
            "I'll be tracking messages and helping with follow-ups. "
            "Feel free to continue chatting as normal!"
        )
        
        try:
            self.message_sender.send_message(
                recipient=chat_info['guid'],
                message=welcome_msg,
                is_group=True
            )
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")
    
    def _setup_monitoring(self, chat_info: Dict) -> None:
        """
        Setup monitoring for the new chat.
        
        Args:
            chat_info: Chat information
        """
        # Save chat info for monitoring
        monitoring_data = {
            'chat_id': chat_info['chat_id'],
            'guid': chat_info['guid'],
            'name': chat_info['name'],
            'start_date': datetime.now().isoformat(),
            'participants': chat_info['participants'],
            'active': True
        }
        
        self._save_monitoring_data(chat_info['guid'], monitoring_data)
    
    def _get_last_check_time(self) -> int:
        """Get timestamp of last check from persistent storage.
        
        Returns:
            Timestamp in Messages epoch format (nanoseconds since 2001-01-01)
        """
        try:
            storage_file = Path.home() / '.imessage_crm' / 'last_check.json'
            if storage_file.exists():
                with open(storage_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_check_time', 0)
        except Exception as e:
            logger.error(f"Error reading last check time: {e}")
        
        # Default to current time - 1 hour
        # Convert to Messages epoch (ns since 2001-01-01)
        # First get seconds since Unix epoch
        unix_ts = datetime.now().timestamp() - 3600  # Look back 1 hour
        # Convert to Messages epoch by adding seconds between 2001 and 1970
        messages_ts = unix_ts + 978307200  # Seconds between 1970-01-01 and 2001-01-01
        # Convert to nanoseconds
        return int(messages_ts * 1e9)
    
    def _save_last_check_time(self, timestamp: int) -> None:
        """Save last check timestamp to persistent storage.
        
        Args:
            timestamp: Timestamp in Messages epoch format
        """
        try:
            storage_file = Path.home() / '.imessage_crm' / 'last_check.json'
            storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(storage_file, 'w') as f:
                json.dump({'last_check_time': timestamp}, f)
                
        except Exception as e:
            logger.error(f"Error saving last check time: {e}")
    
    def _save_monitoring_data(self, chat_guid: str, data: Dict) -> None:
        """
        Save chat monitoring data.
        
        Args:
            chat_guid: Chat GUID
            data: Monitoring data to save
        """
        try:
            storage_dir = Path.home() / '.imessage_crm' / 'chats'
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            storage_file = storage_dir / f"{chat_guid}.json"
            with open(storage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
