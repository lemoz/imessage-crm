"""
Integration test for sending real messages through iMessage.
This script will attempt to send an actual message through the Messages app.
"""

import logging
import sys
import os
from pathlib import Path

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

def test_send_message(recipient: str):
    """
    Test sending a real message to the specified recipient.
    
    Args:
        recipient: Phone number or email to send the message to
    """
    sender = MessageSender()
    test_message = (
        "This is an automated test message from the iMessage CRM system. "
        "If you receive this, the integration is working correctly. "
        f"Sent at: {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, None, None, None), None)}"
    )
    
    logger.info(f"Attempting to send test message to {recipient}")
    try:
        success = sender.send_message(recipient, test_message)
        if success:
            logger.info("✅ Message sent successfully!")
        else:
            logger.error("❌ Message sending failed without raising an exception")
    except SendError as e:
        logger.error(f"❌ Failed to send message: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_real_message.py <recipient_phone_or_email>")
        print("Example: python test_real_message.py +1234567890")
        sys.exit(1)
        
    recipient = sys.argv[1]
    test_send_message(recipient)
