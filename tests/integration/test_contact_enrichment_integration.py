"""Integration tests for contact enrichment system."""
import os
import unittest
from datetime import datetime
from typing import Dict, List

from openai import OpenAI

from src.contacts.contact_enrichment import ContactEnrichmentManager
from src.contacts.contact_manager import ContactManager
from src.messaging import MessageSender
from src.database.chat_state import ChatStateManager
from config.openai_config import OpenAIConfig

class TestContactEnrichmentIntegration(unittest.TestCase):
    """Integration tests for contact enrichment."""
    
    # Test configuration
    SYSTEM_PHONE = "+1234567890"
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that can be reused across tests."""
        # Initialize real components
        cls.contact_manager = ContactManager()
        cls.message_sender = MessageSender()
        cls.state_manager = ChatStateManager()
        
        # Initialize OpenAI with test API key from environment
        test_api_key = os.getenv('OPENAI_API_KEY', 'test-key-placeholder')
        cls.openai_client = OpenAIConfig.get_client(test_api_key)
        
        # Create enrichment manager
        cls.enrichment_manager = ContactEnrichmentManager(
            contact_manager=cls.contact_manager,
            message_sender=cls.message_sender,
            state_manager=cls.state_manager,
            system_phone=cls.SYSTEM_PHONE,
            openai_client=cls.openai_client
        )
        
        # Initialize message reader to get chats
        from src.messaging.message_reader import MessageReader
        cls.message_reader = MessageReader()
        
        # Get recent group chats
        cls.group_chats = [chat for chat in cls.message_reader.get_recent_chats(limit=10)
                          if chat['is_group']]
        
        if not cls.group_chats:
            raise unittest.SkipTest(
                "No group chats found for testing. "
                "Please create a group chat first."
            )
            
        # Set test chat to first group chat
        cls.test_chat = cls.group_chats[0]
        
    def setUp(self):
        """Set up test-specific data."""
        self.chat_guid = self.test_chat['guid']
        chat_info = self.state_manager.get_chat_info(self.chat_guid)
        
        # Get participants who need enrichment
        all_participants = chat_info['participants']
        self.participants = {}
        
        # Find participants missing contact info
        for phone in all_participants:
            if phone != self.system_phone:  # Skip our system number
                contact = self.contact_manager.get_contact(phone)
                missing_fields = []
                
                if not contact.get('name'):
                    missing_fields.append('name')
                if not contact.get('email'):
                    missing_fields.append('email')
                if not contact.get('company'):
                    missing_fields.append('company')
                    
                if missing_fields:  # Only include if they're missing info
                    self.participants[phone] = missing_fields
                    
        if not self.participants:
            self.skipTest("No participants found needing enrichment")
        
    def tearDown(self):
        """Clean up after each test."""
        # No cleanup needed since we're using existing chats
        pass
        
    def test_end_to_end_enrichment_flow(self):
        """Test the complete enrichment flow with real components."""
        try:
            # Step 1: Generate enrichment request
            message = self.enrichment_manager.generate_enrichment_request(
                self.chat_guid,
                self.participants
            )
            
            # Verify message content
            self.assertIsInstance(message, str)
            self.assertGreater(len(message), 0)
            
            # Verify it contains relevant context
            self.assertIn("Integration Test Project", message.lower())
            
            # Step 2: Verify state tracking
            enrichment_state = self.state_manager.get_enrichment_state(self.chat_guid)
            
            # Check each participant's state
            for phone, fields in self.participants.items():
                participant_state = enrichment_state.get(phone)
                self.assertIsNotNone(participant_state)
                self.assertEqual(participant_state["requested_fields"], fields)
                self.assertEqual(participant_state["status"], "pending")
                
            # Step 3: Simulate responses and verify updates
            for phone, fields in self.participants.items():
                # Simulate user response with contact info
                contact_info = {
                    "name": "Test User",
                    "email": "test@example.com",
                    "company": "Test Corp"
                }
                
                # Update contact info
                self.contact_manager.update_contact(
                    phone_number=phone,
                    contact_info=contact_info
                )
                
                # Mark enrichment as complete
                self.state_manager.update_enrichment_status(
                    chat_guid=self.chat_guid,
                    phone_number=phone,
                    status="completed",
                    timestamp=datetime.now().isoformat()
                )
            
            # Verify final state
            final_state = self.state_manager.get_enrichment_state(self.chat_guid)
            for phone in self.participants:
                self.assertEqual(
                    final_state[phone]["status"],
                    "completed"
                )
                
        except Exception as e:
            self.fail(f"Integration test failed: {e}")
            
    def test_enrichment_with_large_group(self):
        """Test enrichment with a larger group of participants."""
        # Get chat info
        chat_info = self.state_manager.get_chat_info(self.chat_guid)
        
        # Skip if not enough participants
        if len(chat_info['participants']) < 5:
            self.skipTest(f"Test group '{self.TEST_GROUP_NAME}' needs at least 5 participants")
            
        # Get participants needing enrichment
        large_participants = {}
        
        for phone in chat_info['participants']:
            if phone != self.system_phone:
                contact = self.contact_manager.get_contact(phone)
                if not all(contact.get(f) for f in ['name', 'email', 'company']):
                    large_participants[phone] = [
                        f for f in ['name', 'email', 'company']
                        if not contact.get(f)
                    ]
                    
        if not large_participants:
            self.skipTest("No participants found needing enrichment in large group")
            
        # Generate request
        message = self.enrichment_manager.generate_enrichment_request(
            large_chat['chat_guid'],
            large_participants
        )
        
        # Verify message handles large group appropriately
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)
        
        # Verify state tracking for large group
        enrichment_state = self.state_manager.get_enrichment_state(large_chat['chat_guid'])
        self.assertEqual(
            len(enrichment_state),
            len(large_participants)
        )
            
    def test_enrichment_with_minimal_fields(self):
        """Test enrichment with minimal required fields."""
        # Get chat info
        chat_info = self.state_manager.get_chat_info(self.chat_guid)
        
        # Find a participant missing only their name
        minimal_participants = {}
        for phone in chat_info['participants']:
            if phone != self.system_phone:
                contact = self.contact_manager.get_contact(phone)
                if not contact.get('name') and contact.get('email'):
                    minimal_participants[phone] = ['name']
                    break
                    
        if not minimal_participants:
            self.skipTest("No participants found missing only name")
            
        # Generate request
        message = self.enrichment_manager.generate_enrichment_request(
            chat['chat_guid'],
            minimal_participants
        )
        
        # Verify message is appropriate for minimal request
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)
        self.assertIn("name", message.lower())
        
        # Verify state tracking
        enrichment_state = self.state_manager.get_enrichment_state(chat['chat_guid'])
        participant_state = enrichment_state.get(list(minimal_participants.keys())[0])
        self.assertEqual(
            participant_state["requested_fields"],
            ["name"]
        )
            
if __name__ == '__main__':
    unittest.main()
