"""
Unit tests for Contact class.
"""

import unittest
from datetime import datetime
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.contacts.contact import Contact

class TestContact(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.contact = Contact(
            name="John Doe",
            phone_numbers=["+1234567890"],
            emails=["john@example.com"]
        )
        
    def test_contact_creation(self):
        """Test basic contact creation."""
        self.assertEqual(self.contact.name, "John Doe")
        self.assertEqual(self.contact.phone_numbers, ["+1234567890"])
        self.assertEqual(self.contact.emails, ["john@example.com"])
        self.assertTrue(self.contact.contact_id.startswith("contact_john_doe_"))
        
    def test_phone_number_normalization(self):
        """Test phone number normalization."""
        test_cases = [
            ("1234567890", "+11234567890"),
            ("11234567890", "+11234567890"),
            ("+11234567890", "+11234567890"),
            ("(123) 456-7890", "+11234567890"),
            ("123-456-7890", "+11234567890"),
            ("123.456.7890", "+11234567890")
        ]
        
        for input_number, expected in test_cases:
            contact = Contact("Test", phone_numbers=[input_number])
            self.assertEqual(
                contact.phone_numbers[0],
                expected,
                f"Failed to normalize {input_number}"
            )
            
    def test_add_phone_number(self):
        """Test adding phone numbers."""
        self.contact.add_phone_number("9876543210")
        self.assertEqual(len(self.contact.phone_numbers), 2)
        self.assertIn("+19876543210", self.contact.phone_numbers)
        
        # Test duplicate prevention
        self.contact.add_phone_number("+19876543210")
        self.assertEqual(len(self.contact.phone_numbers), 2)
        
    def test_add_email(self):
        """Test adding email addresses."""
        self.contact.add_email("john.doe@example.com")
        self.assertEqual(len(self.contact.emails), 2)
        self.assertIn("john.doe@example.com", self.contact.emails)
        
        # Test duplicate prevention (case-insensitive)
        self.contact.add_email("JOHN.DOE@EXAMPLE.COM")
        self.assertEqual(len(self.contact.emails), 2)
        
    def test_message_stats(self):
        """Test message statistics updates."""
        self.contact.update_message_stats(
            total_delta=5,
            unread_delta=3,
            last_message_time=datetime.now().isoformat()
        )
        
        self.assertEqual(self.contact.total_messages, 5)
        self.assertEqual(self.contact.unread_messages, 3)
        self.assertIsNotNone(self.contact.last_message_at)
        
    def test_metadata(self):
        """Test metadata operations."""
        self.contact.set_metadata("category", "client")
        self.contact.set_metadata("priority", "high")
        
        self.assertEqual(self.contact.get_metadata("category"), "client")
        self.assertEqual(self.contact.get_metadata("priority"), "high")
        self.assertIsNone(self.contact.get_metadata("nonexistent"))
        
    def test_matches_identifier(self):
        """Test identifier matching."""
        # Should match phone number in different formats
        self.assertTrue(self.contact.matches_identifier("1234567890"))
        self.assertTrue(self.contact.matches_identifier("+11234567890"))
        self.assertTrue(self.contact.matches_identifier("(123) 456-7890"))
        
        # Should match email case-insensitively
        self.assertTrue(self.contact.matches_identifier("john@example.com"))
        self.assertTrue(self.contact.matches_identifier("JOHN@EXAMPLE.COM"))
        
        # Should not match non-existent identifiers
        self.assertFalse(self.contact.matches_identifier("9999999999"))
        self.assertFalse(self.contact.matches_identifier("other@example.com"))
        
    def test_serialization(self):
        """Test contact serialization and deserialization."""
        # Update some fields
        self.contact.update_message_stats(
            total_delta=10,
            unread_delta=5,
            last_message_time=datetime.now().isoformat()
        )
        self.contact.set_metadata("note", "Important client")
        
        # Convert to dict and back
        contact_dict = self.contact.to_dict()
        new_contact = Contact.from_dict(contact_dict)
        
        # Verify all fields match
        self.assertEqual(new_contact.name, self.contact.name)
        self.assertEqual(new_contact.phone_numbers, self.contact.phone_numbers)
        self.assertEqual(new_contact.emails, self.contact.emails)
        self.assertEqual(new_contact.contact_id, self.contact.contact_id)
        self.assertEqual(new_contact.total_messages, self.contact.total_messages)
        self.assertEqual(new_contact.unread_messages, self.contact.unread_messages)
        self.assertEqual(new_contact.metadata, self.contact.metadata)
        
    def test_string_representation(self):
        """Test string representation of contact."""
        expected = (
            "Contact: John Doe\n"
            f"ID: {self.contact.contact_id}\n"
            "Phone: +1234567890\n"
            "Email: john@example.com\n"
            "Messages: 0 (0 unread)"
        )
        self.assertEqual(str(self.contact), expected)

def run_tests():
    """Run the test suite."""
    unittest.main()

if __name__ == "__main__":
    run_tests()
