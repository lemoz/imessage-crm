"""
Integration tests for message filtering functionality.
Tests filtering by type, status, service, and combinations.
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import unittest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.messaging.message_reader import (
    MessageReader, MessageType, MessageService, MessageReadError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMessageFiltering(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.reader = MessageReader()
        self.test_number = "+19174998893"  # Our verified test number
        
    def test_01_filter_by_type(self):
        """Test filtering messages by type (text vs attachment)."""
        # Get only text messages
        text_results = self.reader.search_messages(
            message_types=[MessageType.TEXT]
        )
        self.assertGreater(text_results.total_count, 0)
        for msg in text_results.messages:
            self.assertFalse(msg['has_attachment'])
            
        # Get only messages with attachments
        attachment_results = self.reader.search_messages(
            message_types=[MessageType.ATTACHMENT]
        )
        for msg in attachment_results.messages:
            self.assertTrue(msg['has_attachment'])
            self.assertIsNotNone(msg['attachment'])
            
        logger.info(
            f"Found {text_results.total_count} text messages and "
            f"{attachment_results.total_count} messages with attachments"
        )
        
    def test_02_filter_by_service(self):
        """Test filtering messages by service (iMessage vs SMS)."""
        # Get only iMessages
        imessage_results = self.reader.search_messages(
            services=[MessageService.IMESSAGE]
        )
        for msg in imessage_results.messages:
            self.assertEqual(msg['service'], MessageService.IMESSAGE)
            
        # Get only SMS messages
        sms_results = self.reader.search_messages(
            services=[MessageService.SMS]
        )
        for msg in sms_results.messages:
            self.assertEqual(msg['service'], MessageService.SMS)
            
        logger.info(
            f"Found {imessage_results.total_count} iMessages and "
            f"{sms_results.total_count} SMS messages"
        )
        
    def test_03_filter_by_read_status(self):
        """Test filtering messages by read status."""
        # Get unread messages
        unread_results = self.reader.search_messages(read_status=False)
        for msg in unread_results.messages:
            self.assertFalse(msg['is_read'])
            
        # Get read messages
        read_results = self.reader.search_messages(read_status=True)
        for msg in read_results.messages:
            self.assertTrue(msg['is_read'])
            
        logger.info(
            f"Found {unread_results.total_count} unread messages and "
            f"{read_results.total_count} read messages"
        )
        
    def test_04_combined_filters(self):
        """Test combining multiple filters."""
        # Get unread iMessages with attachments from last week
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        results = self.reader.search_messages(
            start_date=start_date,
            end_date=end_date,
            message_types=[MessageType.ATTACHMENT],
            services=[MessageService.IMESSAGE],
            read_status=False
        )
        
        for msg in results.messages:
            self.assertTrue(msg['has_attachment'])
            self.assertEqual(msg['service'], MessageService.IMESSAGE)
            self.assertFalse(msg['is_read'])
            msg_date = datetime.strptime(msg['timestamp'].split()[0], "%Y-%m-%d")
            self.assertGreaterEqual(msg_date, datetime.strptime(start_date, "%Y-%m-%d"))
            self.assertLessEqual(msg_date, datetime.strptime(end_date, "%Y-%m-%d"))
            
        logger.info(
            f"Found {results.total_count} unread iMessage attachments "
            f"from the last week"
        )
        
    def test_05_invalid_filters(self):
        """Test handling of invalid filter values."""
        # Test with invalid message type
        results = self.reader.search_messages(
            message_types=['invalid_type']
        )
        self.assertIsNotNone(results)  # Should not raise error, just ignore invalid type
        
        # Test with invalid service
        results = self.reader.search_messages(
            services=['invalid_service']
        )
        self.assertIsNotNone(results)  # Should not raise error, just ignore invalid service
        
        # Test with mixed valid/invalid values
        results = self.reader.search_messages(
            message_types=[MessageType.TEXT, 'invalid_type'],
            services=[MessageService.IMESSAGE, 'invalid_service']
        )
        self.assertIsNotNone(results)
        # Should still apply valid filters
        for msg in results.messages:
            self.assertFalse(msg['has_attachment'])  # TEXT type
            self.assertEqual(msg['service'], MessageService.IMESSAGE)

def run_tests(test_names=None):
    """Run tests, optionally filtering to specific test names."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageFiltering)
    if test_names:
        # Filter to only the specified tests
        suite._tests = [
            suite._tests[0].__class__(name) for name in test_names
        ]
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

if __name__ == "__main__":
    # If specific test names are provided as arguments, run only those
    test_names = sys.argv[1:] if len(sys.argv) > 1 else None
    run_tests(test_names)
