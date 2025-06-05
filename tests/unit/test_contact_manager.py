"""
Unit tests for ContactManager class.
"""

import unittest
import tempfile
import shutil
import json
from datetime import datetime
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.contacts.contact import Contact
from src.contacts.contact_manager import (
    ContactManager,
    ContactManagerError,
    ContactNotFoundError
)

class TestContactManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for contact storage
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ContactManager(self.temp_dir)
        
        # Create some test contacts
        self.contact1 = Contact(
            name="John Doe",
            phone_numbers=["+11234567890"],
            emails=["john@example.com"]
        )
        self.contact2 = Contact(
            name="Jane Smith",
            phone_numbers=["+19876543210"],
            emails=["jane@example.com"]
        )
        
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        
    def test_add_contact(self):
        """Test adding contacts."""
        self.manager.add_contact(self.contact1)
        self.assertEqual(len(self.manager.contacts), 1)
        
        # Verify contact was saved to disk
        file_path = Path(self.temp_dir) / f"{self.contact1.contact_id}.json"
        self.assertTrue(file_path.exists())
        
        # Try adding same contact again
        with self.assertRaises(ContactManagerError):
            self.manager.add_contact(self.contact1)
            
    def test_get_contact(self):
        """Test retrieving contacts."""
        self.manager.add_contact(self.contact1)
        
        # Get existing contact
        contact = self.manager.get_contact(self.contact1.contact_id)
        self.assertEqual(contact.name, "John Doe")
        
        # Try getting non-existent contact
        with self.assertRaises(ContactNotFoundError):
            self.manager.get_contact("nonexistent")
            
    def test_update_contact(self):
        """Test updating contacts."""
        self.manager.add_contact(self.contact1)
        
        # Update contact
        self.contact1.name = "John Smith"
        self.manager.update_contact(self.contact1)
        
        # Verify update
        contact = self.manager.get_contact(self.contact1.contact_id)
        self.assertEqual(contact.name, "John Smith")
        
        # Try updating non-existent contact
        with self.assertRaises(ContactNotFoundError):
            self.manager.update_contact(self.contact2)
            
    def test_delete_contact(self):
        """Test deleting contacts."""
        self.manager.add_contact(self.contact1)
        
        # Delete contact
        self.manager.delete_contact(self.contact1.contact_id)
        self.assertEqual(len(self.manager.contacts), 0)
        
        # Verify file was deleted
        file_path = Path(self.temp_dir) / f"{self.contact1.contact_id}.json"
        self.assertFalse(file_path.exists())
        
        # Try deleting non-existent contact
        with self.assertRaises(ContactNotFoundError):
            self.manager.delete_contact("nonexistent")
            
    def test_find_by_identifier(self):
        """Test finding contacts by identifier."""
        self.manager.add_contact(self.contact1)
        
        # Find by phone
        contact = self.manager.find_by_identifier("1234567890")
        self.assertEqual(contact.name, "John Doe")
        
        # Find by email
        contact = self.manager.find_by_identifier("john@example.com")
        self.assertEqual(contact.name, "John Doe")
        
        # Try finding non-existent contact
        contact = self.manager.find_by_identifier("nonexistent")
        self.assertIsNone(contact)
        
    def test_search_contacts(self):
        """Test searching contacts."""
        self.manager.add_contact(self.contact1)
        self.manager.add_contact(self.contact2)
        
        # Search by name
        results = self.manager.search_contacts(query="john")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "John Doe")
        
        # Search by phone
        results = self.manager.search_contacts(query="987")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Jane Smith")
        
        # Search with unread filter
        self.contact1.update_message_stats(unread_delta=1)
        self.manager.update_contact(self.contact1)
        
        results = self.manager.search_contacts(has_unread=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "John Doe")
        
        # Search with metadata filter
        self.contact1.set_metadata("category", "client")
        self.contact2.set_metadata("category", "vendor")
        self.manager.update_contact(self.contact1)
        self.manager.update_contact(self.contact2)
        
        results = self.manager.search_contacts(
            metadata_filters={"category": "client"}
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "John Doe")
        
    def test_bulk_update_metadata(self):
        """Test bulk metadata updates."""
        self.manager.add_contact(self.contact1)
        self.manager.add_contact(self.contact2)
        
        # Update metadata for both contacts
        self.manager.bulk_update_metadata(
            contact_ids=[
                self.contact1.contact_id,
                self.contact2.contact_id
            ],
            metadata_updates={
                "status": "active",
                "priority": "high"
            }
        )
        
        # Verify updates
        for contact_id in [self.contact1.contact_id, self.contact2.contact_id]:
            contact = self.manager.get_contact(contact_id)
            self.assertEqual(contact.get_metadata("status"), "active")
            self.assertEqual(contact.get_metadata("priority"), "high")
            
    def test_update_message_stats(self):
        """Test updating message statistics."""
        self.manager.add_contact(self.contact1)
        
        # Update stats
        now = datetime.now().isoformat()
        self.manager.update_message_stats(
            identifier="1234567890",
            total_delta=5,
            unread_delta=3,
            last_message_time=now
        )
        
        # Verify updates
        contact = self.manager.get_contact(self.contact1.contact_id)
        self.assertEqual(contact.total_messages, 5)
        self.assertEqual(contact.unread_messages, 3)
        self.assertEqual(contact.last_message_at, now)
        
        # Try updating non-existent contact
        with self.assertRaises(ContactNotFoundError):
            self.manager.update_message_stats(
                identifier="nonexistent",
                total_delta=1
            )
            
    def test_persistence(self):
        """Test contact persistence across manager instances."""
        # Add contacts
        self.manager.add_contact(self.contact1)
        self.manager.add_contact(self.contact2)
        
        # Create new manager instance
        new_manager = ContactManager(self.temp_dir)
        
        # Verify contacts were loaded
        self.assertEqual(len(new_manager.contacts), 2)
        self.assertIn(self.contact1.contact_id, new_manager.contacts)
        self.assertIn(self.contact2.contact_id, new_manager.contacts)

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == "__main__":
    run_tests()
