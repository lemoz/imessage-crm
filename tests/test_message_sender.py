"""
Tests for the MessageSender class.
"""

import subprocess
import pytest
import time
from unittest.mock import patch, MagicMock
from src.messaging.message_sender import (
    MessageSender,
    RateLimit,
    SendError
)

@pytest.fixture
def sender():
    """Create a MessageSender instance with test rate limits."""
    return MessageSender(RateLimit(messages_per_minute=60, minimum_delay=0.1))

def test_create_applescript():
    """Test AppleScript command generation."""
    sender = MessageSender()
    script = sender._create_applescript("+1234567890", "Hello, world!")
    
    assert "tell application \"Messages\"" in script
    assert "set targetBuddy to \"+1234567890\"" in script
    assert "send \"Hello, world!\"" in script
    
def test_message_escaping():
    """Test message content escaping."""
    sender = MessageSender()
    script = sender._create_applescript(
        "+1234567890",
        'Message with "quotes" and other "special" characters'
    )
    
    assert 'send "Message with \\"quotes\\" and other \\"special\\" characters"' in script

def test_rate_limiting():
    """Test rate limiting functionality."""
    sender = MessageSender(RateLimit(messages_per_minute=60, minimum_delay=0.1))
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        start_time = time.time()
        
        # Send three messages
        for _ in range(3):
            sender.send_message("+1234567890", "Test message")
            
        end_time = time.time()
        
        # Should take at least 0.2 seconds (2 delays of 0.1s between 3 messages)
        assert end_time - start_time >= 0.2
        assert mock_run.call_count == 3

def test_successful_send():
    """Test successful message sending."""
    sender = MessageSender()
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = sender.send_message("+1234567890", "Test message")
        
        assert result is True
        mock_run.assert_called_once()
        
def test_failed_send():
    """Test failed message sending."""
    sender = MessageSender()
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'cmd', stderr="Failed to send"
        )
        
        with pytest.raises(SendError) as exc_info:
            sender.send_message("+1234567890", "Test message")
            
        assert "Failed to send message" in str(exc_info.value)
        
def test_bulk_send_success():
    """Test successful bulk message sending."""
    sender = MessageSender()
    recipients = ["+1234567890", "+0987654321"]
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        results = sender.send_bulk_messages(recipients, "Test message")
        
        assert all(results.values())
        assert mock_run.call_count == len(recipients)
        
def test_bulk_send_partial_failure():
    """Test bulk sending with some failures."""
    sender = MessageSender()
    recipients = ["+1234567890", "+0987654321", "+1112223333"]
    
    with patch('subprocess.run') as mock_run:
        # Make every other send fail
        mock_run.side_effect = [
            MagicMock(returncode=0),
            subprocess.CalledProcessError(1, 'cmd', stderr="Failed to send"),
            MagicMock(returncode=0)
        ]
        
        results = sender.send_bulk_messages(
            recipients,
            "Test message",
            continue_on_error=True
        )
        
        assert results[recipients[0]] is True
        assert results[recipients[1]] is False
        assert results[recipients[2]] is True
        
def test_bulk_send_stop_on_error():
    """Test bulk sending stopping on first error."""
    sender = MessageSender()
    recipients = ["+1234567890", "+0987654321", "+1112223333"]
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'cmd', stderr="Failed to send"
        )
        
        with pytest.raises(SendError):
            sender.send_bulk_messages(recipients, "Test message")
