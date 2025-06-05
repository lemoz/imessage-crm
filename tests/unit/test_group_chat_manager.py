"""
Unit tests for the GroupChatManager class.
Tests individual components with mocked dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)
import json
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from src.messaging.group_chat_manager import GroupChatManager
from src.database.db_connector import DatabaseConnector
from src.contacts.contact import Contact
from src.contacts.contact_manager import ContactManager
from src.messaging import MessageSender

class TestGroupChatManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / '.imessage_crm'
        
        # Mock dependencies
        self.db_connector = Mock(spec=DatabaseConnector)
        self.db_connector.execute_query = Mock(return_value=[])
        
        self.contact_manager = Mock(spec=ContactManager)
        self.contact_manager.find_by_phone = Mock(return_value=None)
        self.contact_manager.add_contact = Mock()
        self.contact_manager.update_contact = Mock()
        
        self.message_sender = Mock(spec=MessageSender)
        self.message_sender.send_message = Mock()
        
        # System phone number for testing
        self.system_phone = "+16096077685"
        
        # Create storage directory
        self.storage_path.mkdir(parents=True)
        
        # Initialize manager with mocked dependencies
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            self.manager = GroupChatManager(
                self.db_connector,
                self.contact_manager,
                self.message_sender,
                self.system_phone
            )
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_check_new_group_chats_empty(self):
        """Test checking for new chats when none exist."""
        # Mock empty database response
        self.db_connector.execute_query.return_value = []
        
        # Check for new chats
        result = self.manager.check_new_group_chats()
        
        # Verify results
        self.assertEqual(len(result), 0)
        self.db_connector.execute_query.assert_called_once()
    
    def test_check_new_group_chats_found(self):
        """Test finding new group chats."""
        # Mock database response with a new chat
        mock_chat = {
            'chat_id': 123,
            'guid': 'chat123',
            'display_name': 'Test Group',
            'participant_numbers': f'{self.system_phone},+19995551234,+19995555678'
        }
        self.db_connector.execute_query.return_value = [mock_chat]
        
        # Check for new chats
        result = self.manager.check_new_group_chats()
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['chat_id'], 123)
        self.assertEqual(len(result[0]['participants']), 3)
        self.assertIn(self.system_phone, result[0]['participants'])
    
    def test_process_new_chat(self):
        """Test processing a new group chat."""
        # Test chat data
        chat_info = {
            'chat_id': 123,
            'guid': 'chat123',
            'name': 'Test Group',
            'participants': [self.system_phone, '+19995551234', '+19995555678']
        }
        
        # Mock contact manager response
        self.contact_manager.find_by_phone.return_value = None
        
        # Process the chat
        self.manager.process_new_chat(chat_info)
        
        # Verify contact creation
        self.assertEqual(
            self.contact_manager.add_contact.call_count,
            len(chat_info['participants']) - 1  # Exclude system number
        )
        
        # Verify welcome message
        self.message_sender.send_message.assert_called_once()
    
    def test_process_participant_new(self):
        """Test processing a new participant."""
        # Test data
        phone = "+19995551234"
        chat_info = {'guid': 'chat123'}
        
        # Mock no existing contact
        self.contact_manager.find_by_phone.return_value = None
        
        # Process participant
        self.manager._process_participant(phone, chat_info)
        
        # Verify new contact creation
        self.contact_manager.add_contact.assert_called_once()
        
        # Get the created contact
        created_contact = self.contact_manager.add_contact.call_args[0][0]
        
        # Verify contact data
        self.assertEqual(created_contact.phone_numbers[0], phone)
        self.assertEqual(created_contact.get_metadata('in_crm'), 'true')
        self.assertEqual(created_contact.get_metadata('source_chat'), 'chat123')
    
    def test_process_participant_existing(self):
        """Test processing an existing participant."""
        # Test data
        phone = "+19995551234"
        chat_info = {'guid': 'chat123'}
        
        # Mock existing contact
        existing_contact = Contact("Test User", [phone])
        self.contact_manager.find_by_phone.return_value = existing_contact
        
        # Process participant
        self.manager._process_participant(phone, chat_info)
        
        # Verify contact was updated not created
        self.contact_manager.add_contact.assert_not_called()
        self.contact_manager.update_contact.assert_called_once()
        
        # Verify metadata was updated
        self.assertEqual(existing_contact.get_metadata('in_crm'), 'true')
        self.assertEqual(existing_contact.get_metadata('source_chat'), 'chat123')
    
    def test_send_welcome_message(self):
        """Test sending welcome message."""
        chat_info = {'guid': 'chat123'}
        
        # Send welcome message
        self.manager._send_welcome_message(chat_info)
        
        # Verify message was sent
        self.message_sender.send_message.assert_called_once()
        
        # Verify message content
        sent_message = self.message_sender.send_message.call_args[0][0]
        self.assertIn("👋 Hello!", sent_message)
        self.assertIn("help manage", sent_message)
    
    def test_save_monitoring_data(self):
        """Test saving chat monitoring data."""
        # Test data
        chat_guid = 'chat123'
        monitoring_data = {
            'chat_id': 123,
            'guid': chat_guid,
            'name': 'Test Group',
            'active': True
        }
        
        # Save monitoring data
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            self.manager._save_monitoring_data(chat_guid, monitoring_data)
        
        # Verify file was created
        storage_file = self.storage_path / 'chats' / f"{chat_guid}.json"
        self.assertTrue(storage_file.exists())
        
        # Verify content
        with open(storage_file, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, monitoring_data)
    
    def test_error_handling(self):
        """Test error handling in main functions."""
        # Mock database error
        self.db_connector.execute_query.side_effect = Exception("Database error")
        
        # Verify graceful handling
        result = self.manager.check_new_group_chats()
        self.assertEqual(result, [])
