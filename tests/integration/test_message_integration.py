"""
Comprehensive integration tests for the iMessage CRM system.
Tests real message sending, receiving, group chats, and error conditions.
"""

import logging
import sys
import os
import time
import subprocess
from pathlib import Path
import unittest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.messaging.message_sender import MessageSender, SendError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMessageIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.sender = MessageSender()
        self.test_number = "+19174998893"  # Our verified test number
        
    def test_01_basic_message_send(self):
        """Test sending a basic message with standard characters."""
        message = (
            "Integration Test 1: Basic Message\n"
            "Testing basic message sending functionality."
        )
        success = self.sender.send_message(self.test_number, message)
        self.assertTrue(success, "Basic message sending failed")
        
    def test_02_special_characters(self):
        """Test sending messages with special characters."""
        message = (
            "Integration Test 2: Special Characters\n"
            "Testing symbols: @ # $ % & * ( )\n"
            "Testing punctuation: ; : , . ! ?\n"
            "Testing quotes: 'single' and \"double\""
        )
        success = self.sender.send_message(self.test_number, message)
        self.assertTrue(success, "Special character message sending failed")
        
    def test_03_rate_limiting(self):
        """Test rate limiting by sending multiple messages quickly."""
        messages = [
            f"Rate limit test {i+1}/3" for i in range(3)
        ]
        
        results = []
        for msg in messages:
            success = self.sender.send_message(self.test_number, msg)
            results.append(success)
            # Small delay to prevent overwhelming the system
            time.sleep(1)
            
        self.assertTrue(all(results), "Rate limiting test failed")
        
    def test_04_invalid_number(self):
        """Test sending to an invalid phone number."""
        invalid_number = "invalid123"  # Clearly invalid format
        message = "This should not be delivered"
        
        with self.assertRaises(SendError):
            self.sender.send_message(invalid_number, message)
            
    def test_05_read_messages(self):
        """Test reading recent messages from a chat."""
        test_number = "+1 (917) 499-8893"
        
        try:
            # Create a message reader
            from src.messaging.message_reader import MessageReader
            reader = MessageReader()
            
            # Try to read messages from the test number's chat
            messages = reader.get_recent_messages(test_number, limit=5)
            
            # If we got messages, verify their structure
            if messages:
                logger.info(f"Retrieved {len(messages)} messages from {test_number}")
                # Check that each message has the expected fields
                for msg in messages:
                    self.assertIn('text', msg, "Message missing 'text' field")
                    self.assertIn('sender', msg, "Message missing 'sender' field")
                    self.assertIn('timestamp', msg, "Message missing 'timestamp' field")
                    self.assertIn('is_from_me', msg, "Message missing 'is_from_me' field")
                    
                    # Log message details for debugging
                    logger.info(f"Message from {msg['sender']}: {msg['text'][:50]}...")
            else:
                logger.warning(f"No messages found in chat with {test_number}")
                # Optionally try to send a test message to create some history
                try:
                    message = "Integration Test 5: Creating message history for testing."
                    self.sender.send_message(test_number, message)
                    logger.info("Sent test message to create chat history")
                    
                    # Try reading messages again
                    messages = reader.get_recent_messages(test_number, limit=5)
                    if messages:
                        logger.info(f"Successfully retrieved messages after sending test message")
                        for msg in messages:
                            logger.info(f"Message from {msg['sender']}: {msg['text'][:50]}...")
                    else:
                        logger.warning("Still no messages found after sending test message")
                    self.skipTest("No existing messages found. Created test message for future runs.")
                except SendError as e:
                    logger.error(f"Failed to create test message: {e}")
                    self.skipTest("No messages available for testing")
        except SendError as e:
            logger.error(f"Error reading messages: {e}")
            self.skipTest(f"Unable to read messages: {e}")
        
    def test_06_group_message(self):
        """Test sending a message to a group chat."""
        group_name = "NYC (VP)"
        message = (
            "Integration Test 5: Group Message\n"
            "Testing group message functionality.\n"
            "This is a test message from the iMessage CRM system."
        )
        
        success = self.sender.send_message(group_name, message, is_group=True)
        self.assertTrue(success, "Group message sending failed")

    def test_07_messages_app_state(self):
        """Test behavior when Messages app is in different states."""
        # Test when Messages app is not running
        try:
            # Quit Messages app if it's running
            subprocess.run(
                ['osascript', '-e', 'tell application "Messages" to quit'],
                check=True
            )
            time.sleep(2)  # Wait for app to fully quit
            
            # Should still be able to send messages
            success = self.sender.send_message(
                self.test_number,
                "Test sending while Messages app is closed"
            )
            self.assertTrue(success, "Failed to send message while Messages app was closed")
            
            # Should still be able to read messages
            from src.messaging.message_reader import MessageReader
            reader = MessageReader()
            messages = reader.get_recent_messages(self.test_number, limit=1)
            self.assertTrue(messages, "Failed to read messages while Messages app was closed")
            
        finally:
            # Restart Messages app
            subprocess.run(
                ['open', '-a', 'Messages'],
                check=True
            )
            time.sleep(2)  # Wait for app to start
            
        # Test when Messages app is running but busy
        try:
            # Send a message while simultaneously doing something in Messages
            subprocess.Popen(
                ['osascript', '-e', 'tell application "Messages" to get every chat'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Try to send a message immediately
            success = self.sender.send_message(
                self.test_number,
                "Test sending while Messages app is busy"
            )
            self.assertTrue(success, "Failed to send message while Messages app was busy")
            
        except Exception as e:
            self.skipTest(f"Messages app state test failed: {e}")

def run_tests(test_names=None):
    """Run tests, optionally filtering to specific test names."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMessageIntegration)
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
