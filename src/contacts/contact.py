"""
Contact class for managing contact information and message history.
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Contact:
    """Represents a contact in the iMessage CRM system."""
    
    def __init__(
        self,
        name: str,
        phone_numbers: Optional[List[str]] = None,
        emails: Optional[List[str]] = None,
        contact_id: Optional[str] = None
    ):
        """
        Initialize a contact.
        
        Args:
            name: Contact's name
            phone_numbers: List of phone numbers
            emails: List of email addresses
            contact_id: Unique identifier for the contact
        """
        self.name = name
        self.phone_numbers = [self._normalize_phone_number(p) for p in (phone_numbers or [])]
        self.emails = emails or []
        self.contact_id = contact_id or self._generate_contact_id()
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.last_message_at = None
        self.total_messages = 0
        self.unread_messages = 0
        self.metadata = {}
        
    def _generate_contact_id(self) -> str:
        """Generate a unique contact ID based on name and timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"contact_{self.name.lower().replace(' ', '_')}_{timestamp}"
        
    def add_phone_number(self, phone: str) -> None:
        """
        Add a phone number to the contact.
        Normalizes the phone number format.
        """
        normalized = self._normalize_phone_number(phone)
        if normalized not in self.phone_numbers:
            self.phone_numbers.append(normalized)
            self._update_timestamp()
            
    def add_email(self, email: str) -> None:
        """Add an email address to the contact."""
        if email.lower() not in [e.lower() for e in self.emails]:
            self.emails.append(email)
            self._update_timestamp()
            
    def update_message_stats(
        self,
        total_delta: int = 0,
        unread_delta: int = 0,
        last_message_time: Optional[str] = None
    ) -> None:
        """
        Update message statistics for the contact.
        
        Args:
            total_delta: Change in total message count
            unread_delta: Change in unread message count
            last_message_time: ISO format timestamp of last message
        """
        self.total_messages += total_delta
        self.unread_messages += unread_delta
        if last_message_time:
            self.last_message_at = last_message_time
        self._update_timestamp()
        
    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value for the contact."""
        self.metadata[key] = value
        self._update_timestamp()
        
    def get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value for the contact."""
        return self.metadata.get(key)
        
    def matches_identifier(self, identifier: str) -> bool:
        """
        Check if an identifier (phone/email) belongs to this contact.
        
        Args:
            identifier: Phone number or email to check
            
        Returns:
            True if identifier matches any of contact's phone numbers or emails
        """
        if '@' in identifier:
            # Handle email comparison
            return identifier.lower() in [email.lower() for email in self.emails]
        else:
            # Handle phone comparison
            normalized_input = self._normalize_phone_number(identifier)
            normalized_numbers = [self._normalize_phone_number(p) for p in self.phone_numbers]
            return any(
                self._compare_phone_numbers(normalized_input, number)
                for number in normalized_numbers
            )
            
    def _compare_phone_numbers(self, a: str, b: str) -> bool:
        """
        Compare two phone numbers, handling different formats.
        """
        # If either is empty
        if not a or not b:
            return False
            
        # If they're exactly the same
        if a == b:
            return True
            
        # Strip any leading '+' and '1' (US country code)
        a_stripped = a.lstrip('+1')
        b_stripped = b.lstrip('+1')
        
        # Compare the stripped versions
        return a_stripped == b_stripped
        
    def to_dict(self) -> Dict:
        """Convert contact to dictionary for serialization."""
        return {
            'contact_id': self.contact_id,
            'name': self.name,
            'phone_numbers': self.phone_numbers,
            'emails': self.emails,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_message_at': self.last_message_at,
            'total_messages': self.total_messages,
            'unread_messages': self.unread_messages,
            'metadata': self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Contact':
        """Create a contact instance from a dictionary."""
        contact = cls(
            name=data['name'],
            phone_numbers=data['phone_numbers'],
            emails=data['emails'],
            contact_id=data['contact_id']
        )
        contact.created_at = data['created_at']
        contact.updated_at = data['updated_at']
        contact.last_message_at = data['last_message_at']
        contact.total_messages = data['total_messages']
        contact.unread_messages = data['unread_messages']
        contact.metadata = data['metadata']
        return contact
        
    def _update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now().isoformat()
        
    @staticmethod
    def _normalize_phone_number(phone: str) -> str:
        """
        Normalize a phone number to E.164 format.
        Assumes US numbers if no country code provided.
        """
        # Handle empty input
        if not phone:
            return phone
            
        # If already in E.164 format, return as is
        if phone.startswith('+') and len(phone) > 1:
            return phone
            
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Handle different formats
        if len(digits) == 10:
            # Add US country code
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            # Add + for E.164 format
            return f"+{digits}"
        elif len(digits) > 11 and digits.startswith('1'):
            # Already includes country code
            return f"+{digits}"
        else:
            # Return normalized digits if we can't determine format
            return digits
            
    def __str__(self) -> str:
        """String representation of the contact."""
        return (
            f"Contact: {self.name}\n"
            f"ID: {self.contact_id}\n"
            f"Phone: {', '.join(self.phone_numbers)}\n"
            f"Email: {', '.join(self.emails)}\n"
            f"Messages: {self.total_messages} ({self.unread_messages} unread)"
        )
