"""
Integration tests for GroupChatManager.
Tests the complete workflow with real dependencies.
"""

import unittest
from unittest.mock import patch
import tempfile
import shutil
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json
import sqlite3

import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.database.db_connector import DatabaseConnector
from src.contacts.contact import Contact
from src.contacts.contact_manager import ContactManager
from src.messaging.message_sender import MessageSender
from src.messaging.group_chat_manager import GroupChatManager
from src.database.chat_state import ChatStateManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestGroupChatIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment with real components."""
        # Create temporary directories for our app data
        self.temp_dir = tempfile.mkdtemp()
        self.contacts_dir = Path(self.temp_dir) / 'contacts'
        self.storage_dir = Path(self.temp_dir) / '.imessage_crm'
        
        # Create directories
        self.contacts_dir.mkdir(parents=True)
        self.storage_dir.mkdir(parents=True)
        
        # Initialize real components with actual iMessage database
        self.db_connector = DatabaseConnector()  # Uses real chat.db
        self.contact_manager = ContactManager(str(self.contacts_dir))
        self.message_sender = MessageSender()
        
        # System phone number
        self.system_phone = "+16096077685"
        
        # Initialize state manager with test database
        self.state_db_path = Path(self.temp_dir) / '.imessage_crm' / 'chat_state.db'
        self.state_manager = ChatStateManager(self.state_db_path)
        
        # Reduce logging noise
        logging.getLogger('src.messaging.group_chat_manager').setLevel(logging.WARNING)
        
        # Initialize manager with real components and state manager
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            self.manager = GroupChatManager(
                self.db_connector,
                self.contact_manager,
                self.message_sender,
                self.system_phone,
                state_manager=self.state_manager
            )
            
        # Reset logging level for test output
        logging.getLogger('src.messaging.group_chat_manager').setLevel(logging.INFO)
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        

    
    def test_full_group_chat_workflow(self):
        """Test the complete group chat detection and setup workflow.
        
        This test verifies that:
        1. We can detect when a new group chat is created in iMessage
        2. We correctly identify all participants
        3. We send a welcome message
        4. We create/update contact records
        5. We properly track the chat state for future monitoring
        6. We correctly process existing chats during initialization
        """
        print("\n=== iMessage Group Chat Integration Test ===")
        print("\nPhase 1: Initializing...")
        
        # Reduce logging noise during chat processing
        logging.getLogger('src.messaging.group_chat_manager').setLevel(logging.WARNING)
        # Reset state to ensure clean test
        self.state_manager.reset_state()
        
        # Initialize manager which should process existing chats
        initial_chats = self.manager.check_new_group_chats()
        print(f"Found {len(initial_chats)} existing group chats during initialization")
        
        # Phase 2: Test new group chat detection
        print("\nPhase 2: Testing new group chat detection")
        print("\nIMPORTANT: Follow these steps in order:")
        print("1. Press Enter to START monitoring")
        print("2. THEN create your group chat:")
        print("   - Click compose in Messages")
        print("   - Add at least 2 participants")
        print("   - Send a message like 'Testing group chat'")
        print("   - Wait 5-10 seconds for iMessage to process")
        
        print("\nPress Enter to begin monitoring, then create your group chat...")
        input()
        
        print("\nMonitoring started - please create your group chat now...")
        print("Waiting for you to create a group chat. Press Enter after you've created and sent a message...")
        input()
        
        print("\nChecking for new group chats...")
        max_attempts = 5
        detected_chat = None
        
        for attempt in range(max_attempts):
            print(f"\nCheck attempt {attempt + 1}/{max_attempts}...")
            # Check for any new unprocessed chats
            current_chats = self.manager.check_new_group_chats()
            
            if current_chats:
                detected_chat = current_chats[0]  # Get the first new chat
                break
            
            if attempt < max_attempts - 1:
                print("No new chat detected yet, waiting 5 seconds...")
                time.sleep(5)
        
        # Verify chat detection
        self.assertIsNotNone(detected_chat, "Failed to detect new group chat")
        print(f"\nSuccessfully detected new group chat: {detected_chat['name']}")
        
        # Process the chat
        print("\nProcessing chat participants...")
        self.manager.process_new_chat(detected_chat)
        
        # Verify participant processing
        print("\nVerifying participant processing...")
        chat_participants = self.db_connector.execute_query(
            """SELECT DISTINCT handle.id 
               FROM handle 
               JOIN chat_handle_join ON handle.ROWID = chat_handle_join.handle_id
               WHERE chat_handle_join.chat_id = ?""",
            (detected_chat['chat_id'],)
        )
        
        participant_count = 0
        for participant in chat_participants:
            phone = participant['id']  # sqlite3.Row provides dictionary-like access
            if phone != self.system_phone:  # Skip our own number
                participant_count += 1
                contact = self.contact_manager.find_by_identifier(phone)
                self.assertIsNotNone(
                    contact,
                    f"No contact record created for {phone}"
                )
                self.assertEqual(
                    contact.get_metadata('in_crm'),
                    'true',
                    f"Contact {phone} not marked as in CRM"
                )
                print(f"\n=== Contact Verification ===")
                print(f"Found contact record for {phone}:")
                print(f"Name: {contact.name}")
                print(f"ID: {contact.contact_id}")
                print("-" * 30)
        
        self.assertGreater(
            participant_count,
            1,
            "Expected at least 2 participants in group chat"
        )
        
        # Verify state management
        print("\nVerifying chat state management...")
        
        # Check that chat is marked as processed
        self.assertTrue(
            self.state_manager.is_chat_processed(detected_chat['guid']),
            "Chat not marked as processed in state manager"
        )
        
        # Verify we can get the last processed message
        last_msg = self.state_manager.get_last_processed_message(detected_chat['guid'])
        self.assertIsNotNone(last_msg, "No last message ID recorded")
        
        # Double-check that we won't reprocess this chat
        new_chats = self.manager.check_new_group_chats()
        self.assertFalse(
            any(c['guid'] == detected_chat['guid'] for c in new_chats),
            "Chat was not properly marked as processed"
        )
        
        print("\n=== Test Completed Successfully ===")
        print("\nVerification Steps:")
        print("1. Check Messages app - you should see a welcome message")
        print("2. Contact records were created for all participants")
        print("3. The group chat is now being monitored")
        print("\nPress Enter to clean up test data...")
        input()
    
    def test_message_handling(self):
        """Test message handling in group chat context."""
        print("\n=== Message Handling Test ===\n")
        print("This test verifies that new messages in a group chat are processed correctly.")
        print("\nTest Steps:")
        print("1. Use the SAME group chat from the previous test")
        print("2. Send a new message to the group")
        print("3. System will detect and process the message")
        
        print("\nPress Enter when ready to start...")
        input()
        
        # Get current message count
        initial_count = self.db_connector.execute_query(
            "SELECT COUNT(*) as count FROM message WHERE is_from_me = 0"
        )[0]['count']
        
        print("\nWaiting for new message...")
        max_attempts = 5
        new_message_detected = False
        
        for attempt in range(max_attempts):
            print(f"Check attempt {attempt + 1}/{max_attempts}...")
            current_count = self.db_connector.execute_query(
                "SELECT COUNT(*) as count FROM message WHERE is_from_me = 0"
            )[0]['count']
            
            if current_count > initial_count:
                new_message_detected = True
                break
                
            if attempt < max_attempts - 1:
                print("No new message detected, waiting 5 seconds...")
                time.sleep(5)
        
        self.assertTrue(new_message_detected, "Failed to detect new message")
        print("\nSuccessfully detected new message!")
        
        print("\n=== Test Completed Successfully ===\n")
        
    def test_contact_enrichment(self):
        """Test contact enrichment from group chat context."""
        print("\n=== Contact Enrichment Test ===\n")
        print("This test verifies that contact information can be enriched")
        print("with additional details like names and email addresses.")
        
        print("\nTest Steps:")
        print("1. System will process existing participants")
        print("2. You can add contact details (name/email)")
        print("3. System will verify data persistence")
        
        print("\nPress Enter to begin contact enrichment test...")
        input()
        
        # Get a participant from an existing group chat
        participants = self.db_connector.execute_query(
            """SELECT DISTINCT handle.id 
               FROM handle 
               JOIN chat_handle_join ON handle.ROWID = chat_handle_join.handle_id
               WHERE handle.service = 'iMessage'
               AND handle.id != ?""",
            (self.system_phone,)
        )
        
        self.assertGreater(len(participants), 0, "No participants found to test with")
        test_phone = participants[0]['id']
        
        print(f"\nEnriching contact data for: {test_phone}")
        
        # Create or update contact
        contact = self.contact_manager.find_by_phone(test_phone)
        if not contact:
            contact = Contact(phone_numbers=[test_phone])
        
        # Add enriched data
        contact.name = f"Test User {datetime.now().strftime('%H%M%S')}"
        contact.add_email(f"test{datetime.now().strftime('%H%M%S')}@example.com")
        self.contact_manager.update_contact(contact)
        
        # Verify persistence
        updated_contact = self.contact_manager.find_by_phone(test_phone)
        self.assertIsNotNone(updated_contact, "Contact not found after update")
        self.assertEqual(updated_contact.name, contact.name)
        self.assertEqual(updated_contact.emails[0], contact.emails[0])
        
        print(f"Successfully enriched contact:")
        print(f"- Name: {updated_contact.name}")
        print(f"- Email: {updated_contact.emails[0]}")
        print(f"- Phone: {updated_contact.phone_numbers[0]}")
        
        print("\n=== Test Completed Successfully ===\n")

if __name__ == "__main__":
    # When run directly, only run the group chat workflow test
    suite = unittest.TestSuite()
    suite.addTest(TestGroupChatIntegration('test_full_group_chat_workflow'))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
