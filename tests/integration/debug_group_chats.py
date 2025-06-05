"""
Debug script to check group chat detection.
"""
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.database.db_connector import DatabaseConnector
from src.contacts.contact_manager import ContactManager
from src.messaging.message_sender import MessageSender
from src.messaging.group_chat_manager import GroupChatManager
from src.database.chat_state import ChatStateManager

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Run group chat detection with debug logging."""
    try:
        # Initialize components
        db = DatabaseConnector()
        contact_manager = ContactManager()
        message_sender = MessageSender()
        system_phone = "+16096077685"  # Your number
        
        # Initialize and reset state manager
        state_manager = ChatStateManager()
        logger.info("Resetting chat state...")
        state_manager.reset_state()
        
        logger.info("\n=== Phase 1: Initial Setup ===")
        logger.info("Initializing GroupChatManager...")
        manager = GroupChatManager(
            db,
            contact_manager,
            message_sender,
            system_phone,
            state_manager=state_manager
        )
        
        logger.info("\n=== Phase 2: Waiting for New Group Chat ===")
        logger.info("Instructions:")
        logger.info("1. Create a new group chat now")
        logger.info("2. Send a test message")
        logger.info("3. Press Enter when done")
        input()
        
        logger.info("\n=== Phase 3: New Chat Detection ===")
        logger.info("Checking for new group chats...")
        
        # Check for new chats multiple times with a delay
        import time
        max_attempts = 3
        for attempt in range(max_attempts):
            logger.info(f"\nAttempt {attempt + 1}/{max_attempts}:")
            chats = manager.check_new_group_chats()
            
            if chats:
                logger.info(f"Found {len(chats)} new group chats!")
                for chat in chats:
                    logger.info("\nChat Details:")
                    logger.info(f"  GUID: {chat['guid']}")
                    logger.info(f"  Name: {chat['name']}")
                    logger.info(f"  Participants: {chat['participants']}")
                    logger.info(f"  Last Message: {chat.get('last_message_text', 'None')}")
                    logger.info(f"  Last Message Date: {chat.get('last_message_date', 'None')}")
                break
            else:
                logger.info("No new chats found yet, waiting 2 seconds...")
                if attempt < max_attempts - 1:  # Don't wait after last attempt
                    time.sleep(2)
        
        if not chats:
            logger.info("\nNo new group chats were detected")
            logger.info("Make sure you:")
            logger.info("1. Created a new group chat")
            logger.info("2. Sent at least one message")
            logger.info("3. The message was sent from your number")
            
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)

if __name__ == "__main__":
    main()
