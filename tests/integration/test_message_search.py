"""
Integration tests for message search functionality.
Tests search by content, sender, date range, and pagination.
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

from src.messaging.message_reader import MessageReader, MessageReadError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMessageSearch(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.reader = MessageReader()
        self.test_number = "+19174998893"  # Our verified test number
        
    def test_01_search_by_content(self):
        """Test searching messages by content."""
        # Search for a common word that should exist
        search_term = "test"
        results = self.reader.search_messages(content=search_term)
        
        self.assertIsNotNone(results)
        self.assertGreater(results.total_count, 0, f"No messages found containing '{search_term}'")
        
        # Verify each message contains the search term
        for msg in results.messages:
            self.assertIn(search_term.lower(), msg['text'].lower())
            
        logger.info(f"Found {results.total_count} messages containing '{search_term}'")
        
    def test_02_search_by_sender(self):
        """Test searching messages by sender."""
        results = self.reader.search_messages(sender=self.test_number)
        
        self.assertIsNotNone(results)
        self.assertGreater(results.total_count, 0, f"No messages found from {self.test_number}")
        
        # Verify sender in results
        for msg in results.messages:
            self.assertTrue(
                msg['is_from_me'] or self.test_number in msg['sender'],
                f"Message from unexpected sender: {msg['sender']}"
            )
            
        logger.info(f"Found {results.total_count} messages from {self.test_number}")
        
    def test_03_search_by_date_range(self):
        """Test searching messages within a date range."""
        # Search for messages from the last 7 days
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        results = self.reader.search_messages(
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertIsNotNone(results)
        logger.info(f"Found {results.total_count} messages between {start_date} and {end_date}")
        
        # Verify message dates are within range
        for msg in results.messages:
            msg_date = datetime.strptime(msg['timestamp'].split()[0], "%Y-%m-%d")
            self.assertGreaterEqual(msg_date, datetime.strptime(start_date, "%Y-%m-%d"))
            self.assertLessEqual(msg_date, datetime.strptime(end_date, "%Y-%m-%d"))
            
    def test_04_pagination(self):
        """Test message search pagination."""
        page_size = 5
        
        # Get first page
        page1 = self.reader.search_messages(page=1, page_size=page_size)
        self.assertEqual(len(page1.messages), min(page_size, page1.total_count))
        
        if page1.has_next_page():
            # Get second page
            page2 = self.reader.search_messages(page=2, page_size=page_size)
            self.assertNotEqual(
                page1.messages[0]['timestamp'],
                page2.messages[0]['timestamp'],
                "First message of second page should differ from first page"
            )
            
        logger.info(
            f"Pagination test: {page1.total_count} total messages, "
            f"{page1.total_pages} pages with {page_size} messages per page"
        )
        
    def test_05_combined_search(self):
        """Test searching with multiple criteria."""
        # Search for test messages from our test number in the last 30 days
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        results = self.reader.search_messages(
            content="test",
            sender=self.test_number,
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertIsNotNone(results)
        logger.info(
            f"Found {results.total_count} test messages from {self.test_number} "
            f"between {start_date} and {end_date}"
        )
        
        # Verify results match all criteria
        for msg in results.messages:
            self.assertIn("test", msg['text'].lower())
            self.assertTrue(
                msg['is_from_me'] or self.test_number in msg['sender'],
                f"Message from unexpected sender: {msg['sender']}"
            )
            msg_date = datetime.strptime(msg['timestamp'].split()[0], "%Y-%m-%d")
            self.assertGreaterEqual(msg_date, datetime.strptime(start_date, "%Y-%m-%d"))
            self.assertLessEqual(msg_date, datetime.strptime(end_date, "%Y-%m-%d"))

def run_tests(test_names=None):
    """Run tests, optionally filtering to specific test names."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageSearch)
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
