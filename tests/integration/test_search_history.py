"""
Tests for search history tracking functionality.
"""

import logging
import sys
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import unittest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.messaging.search_history import SearchHistory
from src.messaging.message_reader import MessageReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSearchHistory(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary file for search history
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.temp_dir, "test_search_history.json")
        self.history = SearchHistory(self.history_file)
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary files
        if os.path.exists(self.history_file):
            os.remove(self.history_file)
        os.rmdir(self.temp_dir)
        
    def test_01_add_search(self):
        """Test adding a search to history."""
        # Add a test search
        self.history.add_search(
            content="test message",
            sender="+19174998893",
            result_count=5
        )
        
        # Verify it was added
        recent = self.history.get_recent_searches(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['criteria']['content'], "test message")
        self.assertEqual(recent[0]['criteria']['sender'], "+19174998893")
        self.assertEqual(recent[0]['result_count'], 5)
        
    def test_02_history_limit(self):
        """Test that history is limited to 100 entries."""
        # Add more than 100 searches
        for i in range(110):
            self.history.add_search(
                content=f"test {i}",
                result_count=i
            )
            
        # Verify only 100 are kept
        all_searches = self.history.get_recent_searches(limit=200)
        self.assertEqual(len(all_searches), 100)
        
        # Verify they're in reverse chronological order
        self.assertEqual(all_searches[0]['criteria']['content'], "test 109")
        
    def test_03_popular_searches(self):
        """Test getting popular searches."""
        # Add searches with different result counts
        searches = [
            ("popular search", 100),
            ("less popular", 50),
            ("rare search", 10)
        ]
        
        for content, count in searches:
            self.history.add_search(content=content, result_count=count)
            
        # Get popular searches
        popular = self.history.get_popular_searches(limit=3)
        self.assertEqual(popular[0]['criteria']['content'], "popular search")
        self.assertEqual(popular[0]['result_count'], 100)
        
    def test_04_clear_history(self):
        """Test clearing search history."""
        # Add some searches
        self.history.add_search(content="test", result_count=5)
        self.history.add_search(content="another test", result_count=10)
        
        # Clear history
        self.history.clear_history()
        
        # Verify it's empty
        recent = self.history.get_recent_searches()
        self.assertEqual(len(recent), 0)
        
    def test_05_integration_with_message_reader(self):
        """Test search history integration with MessageReader."""
        # Create a MessageReader with our test history file
        reader = MessageReader()
        reader.search_history = SearchHistory(self.history_file)
        
        # Perform a search
        reader.search_messages(
            content="test",
            sender="+19174998893",
            start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        # Verify search was recorded
        recent = reader.search_history.get_recent_searches(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['criteria']['content'], "test")
        self.assertEqual(recent[0]['criteria']['sender'], "+19174998893")

def run_tests(test_names=None):
    """Run tests, optionally filtering to specific test names."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSearchHistory)
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
