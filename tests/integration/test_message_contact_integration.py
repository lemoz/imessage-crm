"""
Integration tests for MessageReader and ContactManager interaction.
Tests the combined functionality of message reading and contact management.
"""

import unittest
import tempfile
import shutil
import os
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.messaging.message_reader import MessageReader
from src.contacts.contact_manager import ContactManager
from src.contacts.contact import Contact

class TestMessageContactIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for contact storage
        self.temp_dir = tempfile.mkdtemp()
        self.contact_manager = ContactManager(self.temp_dir)
        self.message_reader = MessageReader()
        
        # Create test contact with real phone number
        self.contact = Contact(
            name="Test User",
            phone_numbers=["+19516357669"],  # Real number with correct format
            emails=["test@example.com"]
        )
        
        # Add contact to manager
        self.contact_manager.add_contact(self.contact)
        
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        
    def test_message_search_with_contacts(self):
        """Test searching messages and linking them to contacts."""
        # Search for recent messages
        messages = self.message_reader.search_messages(
            page=1,
            page_size=50
        ).messages
        
        # Track messages belonging to our test contact
        contact_messages = []
        
        for msg in messages:
            sender = msg['sender']
            # Try to find contact by sender identifier
            contact = self.contact_manager.find_by_identifier(sender)
            if contact and contact.contact_id == self.contact.contact_id:
                contact_messages.append(msg)
                    
        # Update message stats for contact
        if contact_messages:
            self.contact_manager.update_message_stats(
                identifier=self.contact.phone_numbers[0],
                total_delta=len(contact_messages),
                unread_delta=sum(1 for m in contact_messages if not m['is_read']),
                last_message_time=max(m['timestamp'] for m in contact_messages)
            )
            
            # Verify contact message stats were updated
            updated_contact = self.contact_manager.get_contact(self.contact.contact_id)
            self.assertEqual(updated_contact.total_messages, len(contact_messages))
            
    def test_filtered_message_search_with_contacts(self):
        """Test searching messages with filters and linking to contacts."""
        # Get messages from the last week
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        messages = self.message_reader.search_messages(
            start_date=start_date,
            end_date=end_date,
            message_types=["text"],
            read_status=False,
            page=1,
            page_size=50
        ).messages
        
        # Track unread messages per contact
        contact_unread = {}
        
        for msg in messages:
            sender = msg['sender']
            contact = self.contact_manager.find_by_identifier(sender)
            if contact:
                if contact.contact_id not in contact_unread:
                    contact_unread[contact.contact_id] = []
                contact_unread[contact.contact_id].append(msg)
                
        # Update contact metadata for unread messages
        for contact_id, unread_messages in contact_unread.items():
            contact = self.contact_manager.get_contact(contact_id)
            self.contact_manager.update_message_stats(
                identifier=contact.phone_numbers[0],
                unread_delta=len(unread_messages),
                last_message_time=max(m['timestamp'] for m in unread_messages)
            )
            
            # Add metadata about unread message content
            topics = set()
            for msg in unread_messages:
                # Simple topic extraction (just first few words)
                text = msg['text']
                if text:
                    topic = ' '.join(text.split()[:3])
                    topics.add(topic)
            
            if topics:
                contact.set_metadata('unread_topics', '; '.join(topics))
                self.contact_manager.update_contact(contact)
                
    def test_contact_message_history(self):
        """Test retrieving full message history for contacts."""
        # Search all messages for this contact
        messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            page=1,
            page_size=100
        ).messages
        
        if messages:
            # Update contact with message history stats
            self.contact_manager.update_message_stats(
                identifier=self.contact.phone_numbers[0],
                total_delta=len(messages),
                unread_delta=sum(1 for m in messages if not m['is_read']),
                last_message_time=max(m['timestamp'] for m in messages)
            )
            
            # Calculate and store engagement metrics
            contact = self.contact_manager.get_contact(self.contact.contact_id)
            
            # Track conversation dates
            conversation_dates = set(m['timestamp'].split('T')[0] for m in messages)
            contact.set_metadata('conversation_days', str(len(conversation_dates)))
            
            # Track message types
            has_attachments = sum(1 for m in messages if m.get('has_attachment'))
            if has_attachments:
                contact.set_metadata('uses_attachments', 'true')
                
            # Track response patterns
            sent_messages = [m for m in messages if m['is_from_me']]
            received_messages = [m for m in messages if not m['is_from_me']]
            
            if sent_messages and received_messages:
                response_ratio = len(sent_messages) / len(received_messages)
                contact.set_metadata('response_ratio', f"{response_ratio:.2f}")
                
            self.contact_manager.update_contact(contact)
                
    def test_search_contacts_by_message_criteria(self):
        """Test searching contacts based on message-related criteria."""
        # First, get message history for the contact
        logger.info(f"Searching for messages from {self.contact.phone_numbers[0]}")
        search_result = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            page=1,
            page_size=100
        )
        messages = search_result.messages
        logger.info(f"Found {search_result.total_count} total messages")
        if messages:
            logger.info(f"First message: {messages[0]}")
        
        if not messages:
            self.skipTest("No messages found for test contact")
            
        # Update contact with message data
        self.contact_manager.update_message_stats(
            identifier=self.contact.phone_numbers[0],
            total_delta=len(messages),
            unread_delta=sum(1 for m in messages if not m['is_read']),
            last_message_time=max(m['timestamp'] for m in messages)
        )
        
        # Update metadata
        contact = self.contact_manager.get_contact(self.contact.contact_id)
        has_attachments = any(m.get('has_attachment') for m in messages)
        if has_attachments:
            contact.set_metadata('uses_attachments', 'true')
            self.contact_manager.update_contact(contact)
        
        # Test search functionality
        if contact.unread_messages > 0:
            # Search for contacts with unread messages
            unread_results = self.contact_manager.search_contacts(has_unread=True)
            self.assertIn(contact.contact_id, [c.contact_id for c in unread_results])
        
        if contact.last_message_at:
            # Search for recently active contacts
            last_week = (datetime.now() - timedelta(days=7)).isoformat()
            recent_results = self.contact_manager.search_contacts(
                last_message_after=last_week
            )
            self.assertIn(contact.contact_id, [c.contact_id for c in recent_results])
        
        if has_attachments:
            # Search for contacts who use attachments
            attachment_results = self.contact_manager.search_contacts(
                metadata_filters={'uses_attachments': 'true'}
            )
            self.assertIn(contact.contact_id, [c.contact_id for c in attachment_results])

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == "__main__":
    run_tests()
