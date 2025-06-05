"""Unit tests for contact enrichment manager."""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from src.contacts.contact_enrichment import ContactEnrichmentManager
from src.contacts.contact_manager import ContactManager
from src.messaging import MessageSender
from src.database.chat_state import ChatStateManager
from config.openai_config import OpenAIConfig

class TestContactEnrichmentManager(unittest.TestCase):
    """Test cases for ContactEnrichmentManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.contact_manager = Mock(spec=ContactManager)
        self.message_sender = Mock(spec=MessageSender)
        self.state_manager = Mock()
        self.state_manager.get_chat_info = Mock()
        self.state_manager.record_enrichment_request = Mock()
        self.openai_client = Mock()
        
        # Mock the OpenAI response
        self.mock_completion = ChatCompletion(
            id="test_completion",
            model="gpt-4",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="Welcome! Could you please share your name and email?",
                        role="assistant"
                    )
                )
            ]
        )
        
        self.openai_client.chat.completions.create.return_value = self.mock_completion
        
        self.enrichment_manager = ContactEnrichmentManager(
            contact_manager=self.contact_manager,
            message_sender=self.message_sender,
            state_manager=self.state_manager,
            system_phone="+1234567890",
            openai_client=self.openai_client
        )
        
        # Test data
        self.chat_guid = "test_chat_123"
        self.participants = {
            "+1987654321": ["name", "email"],
            "+1555555555": ["name"]
        }
        self.chat_info = {
            "display_name": "Test Project Team",
            "participants": ["+1234567890", "+1987654321", "+1555555555"],
            "created_at": datetime.now().isoformat()
        }
        
        # Setup state manager mock
        self.state_manager.get_chat_info.return_value = self.chat_info
        
    def test_generate_enrichment_request_success(self):
        """Test successful generation of enrichment request."""
        # Call the method
        message = self.enrichment_manager.generate_enrichment_request(
            self.chat_guid,
            self.participants
        )
        
        # Verify OpenAI was called correctly
        self.openai_client.chat.completions.create.assert_called_once()
        call_args = self.openai_client.chat.completions.create.call_args[1]
        
        # Check OpenAI parameters
        self.assertEqual(call_args["model"], OpenAIConfig.DEFAULT_MODEL)
        self.assertEqual(call_args["temperature"], OpenAIConfig.DEFAULT_TEMPERATURE)
        
        # Verify messages format
        messages = call_args["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Verify response
        self.assertEqual(message, "Welcome! Could you please share your name and email?")
        
        # Verify state tracking
        self.state_manager.record_enrichment_request.assert_called()
        
    def test_generate_enrichment_request_openai_error(self):
        """Test handling of OpenAI API errors."""
        # Make OpenAI call fail
        self.openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Verify error is propagated
        with self.assertRaises(Exception):
            self.enrichment_manager.generate_enrichment_request(
                self.chat_guid,
                self.participants
            )
            
    def test_generate_enrichment_request_state_error(self):
        """Test handling of state manager errors."""
        # Make state manager fail
        self.state_manager.get_chat_info.side_effect = Exception("State Error")
        
        # Verify error is propagated
        with self.assertRaises(Exception):
            self.enrichment_manager.generate_enrichment_request(
                self.chat_guid,
                self.participants
            )
            
    def test_track_enrichment_request(self):
        """Test enrichment request tracking."""
        # Generate request
        self.enrichment_manager.generate_enrichment_request(
            self.chat_guid,
            self.participants
        )
        
        # Verify tracking calls
        expected_calls = len(self.participants)
        self.assertEqual(
            self.state_manager.record_enrichment_request.call_count,
            expected_calls
        )
        
        # Verify tracking data
        for phone, fields in self.participants.items():
            self.state_manager.record_enrichment_request.assert_any_call(
                chat_guid=self.chat_guid,
                phone_number=phone,
                requested_fields=fields,
                timestamp=unittest.mock.ANY  # We can't predict the exact timestamp
            )
            
if __name__ == '__main__':
    unittest.main()
