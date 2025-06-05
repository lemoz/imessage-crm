"""
Integration tests for different message search scenarios.
Tests various search filters and criteria without using real contact data.
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

class TestMessageSearchScenarios(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for contact storage
        self.temp_dir = tempfile.mkdtemp()
        self.contact_manager = ContactManager(self.temp_dir)
        self.message_reader = MessageReader()
        
        # Create test contact with our test number
        self.contact = Contact(
            name="Test User",
            phone_numbers=["+19516357669"],  # Test number
            emails=["test@example.com"]
        )
        
        # Add contact to manager
        self.contact_manager.add_contact(self.contact)
        
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        
    def test_message_search_with_date_range(self):
        """Test searching messages within a date range."""
        # Search messages from last week
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            start_date=last_week,
            end_date=today,
            page=1,
            page_size=100
        ).messages
        
        # Verify all messages are within date range
        for msg in messages:
            msg_date = datetime.strptime(msg['timestamp'].split()[0], "%Y-%m-%d")
            self.assertGreaterEqual(msg_date, datetime.strptime(last_week, "%Y-%m-%d"))
            self.assertLessEqual(msg_date, datetime.strptime(today, "%Y-%m-%d"))
            
    def test_message_search_with_read_status(self):
        """Test searching messages by read status."""
        # Get all messages
        all_messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            page=1,
            page_size=100
        ).messages
        
        if not all_messages:
            self.skipTest("No messages found for test contact")
            
        # Count read and unread messages
        read_count = sum(1 for m in all_messages if m['is_read'])
        unread_count = sum(1 for m in all_messages if not m['is_read'])
        
        # Search specifically for unread messages
        unread_messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            read_status=False,
            page=1,
            page_size=100
        ).messages
        
        # Verify counts match
        self.assertEqual(len(unread_messages), unread_count)
        
    def test_message_search_with_service_type(self):
        """Test searching messages by service type (SMS vs iMessage)."""
        # Search for SMS messages
        sms_messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            services=['SMS'],
            page=1,
            page_size=100
        ).messages
        
        # Search for iMessage messages
        imessage_messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            services=['iMessage'],
            page=1,
            page_size=100
        ).messages
        
        # Verify service types
        for msg in sms_messages:
            self.assertEqual(msg['service'], 'SMS')
            
        for msg in imessage_messages:
            self.assertEqual(msg['service'], 'iMessage')
            
    def test_message_search_with_attachments(self):
        """Test searching messages with attachments."""
        # Search for messages with attachments
        messages = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            has_attachments=True,
            page=1,
            page_size=100
        ).messages
        
        # Verify all messages have attachments
        for msg in messages:
            self.assertTrue(msg['has_attachment'])
            self.assertIsNotNone(msg['attachment'])
            
    def test_message_search_pagination(self):
        """Test message search pagination."""
        # Get total message count
        first_page = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            page=1,
            page_size=10
        )
        
        if first_page.total_count == 0:
            self.skipTest("No messages found for test contact")
            
        # Get second page
        second_page = self.message_reader.search_messages(
            sender=self.contact.phone_numbers[0],
            page=2,
            page_size=10
        )
        
        # Verify pagination
        self.assertEqual(len(first_page.messages), min(10, first_page.total_count))
        if first_page.total_count > 10:
            self.assertEqual(len(second_page.messages), min(10, first_page.total_count - 10))
            
            # Verify messages are different
            first_page_ids = set(m['timestamp'] for m in first_page.messages)
            second_page_ids = set(m['timestamp'] for m in second_page.messages)
            self.assertEqual(len(first_page_ids.intersection(second_page_ids)), 0)

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == "__main__":
    run_tests()
