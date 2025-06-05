"""
ContactManager for managing contacts in the iMessage CRM system.
Handles storage, retrieval, and operations on Contact objects.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
from .contact import Contact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContactManagerError(Exception):
    """Base exception for contact management errors."""
    pass

class ContactNotFoundError(ContactManagerError):
    """Raised when a contact cannot be found."""
    pass

class ContactManager:
    """Manages contacts and their storage."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the contact manager.
        
        Args:
            storage_dir: Directory to store contact data.
                       If None, uses ~/.imessage_crm/contacts/
        """
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.imessage_crm/contacts")
            
        self.storage_dir = Path(storage_dir)
        self.contacts: Dict[str, Contact] = {}
        self._ensure_storage_exists()
        self._load_contacts()
        
    def _ensure_storage_exists(self) -> None:
        """Ensure the storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_contacts(self) -> None:
        """Load all contacts from storage."""
        logger.info(f"Loading contacts from {self.storage_dir}")
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                contact = Contact.from_dict(data)
                self.contacts[contact.contact_id] = contact
            except Exception as e:
                logger.error(f"Error loading contact from {file_path}: {e}")
        logger.info(f"Loaded {len(self.contacts)} contacts")
        
    def _save_contact(self, contact: Contact) -> None:
        """Save a contact to storage."""
        file_path = self.storage_dir / f"{contact.contact_id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(contact.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving contact {contact.contact_id}: {e}")
            raise ContactManagerError(f"Failed to save contact: {e}")
            
    def add_contact(self, contact: Contact) -> None:
        """
        Add a new contact.
        
        Args:
            contact: Contact to add
            
        Raises:
            ContactManagerError: If contact already exists
        """
        if contact.contact_id in self.contacts:
            raise ContactManagerError(f"Contact {contact.contact_id} already exists")
            
        self.contacts[contact.contact_id] = contact
        self._save_contact(contact)
        logger.info(f"Added contact: {contact.name} ({contact.contact_id})")
        
    def update_contact(self, contact: Contact) -> None:
        """
        Update an existing contact.
        
        Args:
            contact: Contact to update
            
        Raises:
            ContactNotFoundError: If contact doesn't exist
        """
        if contact.contact_id not in self.contacts:
            raise ContactNotFoundError(f"Contact {contact.contact_id} not found")
            
        self.contacts[contact.contact_id] = contact
        self._save_contact(contact)
        logger.info(f"Updated contact: {contact.name} ({contact.contact_id})")
        
    def get_contact(self, contact_id: str) -> Contact:
        """
        Get a contact by ID.
        
        Args:
            contact_id: ID of contact to get
            
        Returns:
            Contact object
            
        Raises:
            ContactNotFoundError: If contact doesn't exist
        """
        if contact_id not in self.contacts:
            raise ContactNotFoundError(f"Contact {contact_id} not found")
        return self.contacts[contact_id]
        
    def delete_contact(self, contact_id: str) -> None:
        """
        Delete a contact.
        
        Args:
            contact_id: ID of contact to delete
            
        Raises:
            ContactNotFoundError: If contact doesn't exist
        """
        if contact_id not in self.contacts:
            raise ContactNotFoundError(f"Contact {contact_id} not found")
            
        contact = self.contacts.pop(contact_id)
        file_path = self.storage_dir / f"{contact_id}.json"
        try:
            file_path.unlink()
            logger.info(f"Deleted contact: {contact.name} ({contact_id})")
        except Exception as e:
            logger.error(f"Error deleting contact file {file_path}: {e}")
            # Add contact back to memory since file deletion failed
            self.contacts[contact_id] = contact
            raise ContactManagerError(f"Failed to delete contact: {e}")
            
    def find_by_identifier(self, identifier: str) -> Optional[Contact]:
        """
        Find a contact by phone number or email.
        
        Args:
            identifier: Phone number or email to search for
            
        Returns:
            Matching contact or None if not found
        """
        for contact in self.contacts.values():
            if contact.matches_identifier(identifier):
                return contact
        return None
        
    def search_contacts(
        self,
        query: Optional[str] = None,
        has_unread: Optional[bool] = None,
        last_message_after: Optional[str] = None,
        metadata_filters: Optional[Dict[str, str]] = None
    ) -> List[Contact]:
        """
        Search contacts with various filters.
        
        Args:
            query: Search string to match against name/phone/email
            has_unread: Filter to contacts with/without unread messages
            last_message_after: ISO format date to filter by last message
            metadata_filters: Dict of metadata key-value pairs to match
            
        Returns:
            List of matching contacts
        """
        results = []
        
        for contact in self.contacts.values():
            # Apply query filter
            if query and not self._matches_query(contact, query):
                continue
                
            # Apply unread filter
            if has_unread is not None:
                if has_unread and contact.unread_messages == 0:
                    continue
                if not has_unread and contact.unread_messages > 0:
                    continue
                    
            # Apply last message filter
            if last_message_after and contact.last_message_at:
                if contact.last_message_at < last_message_after:
                    continue
                    
            # Apply metadata filters
            if metadata_filters:
                match = True
                for key, value in metadata_filters.items():
                    if contact.get_metadata(key) != value:
                        match = False
                        break
                if not match:
                    continue
                    
            results.append(contact)
            
        return results
        
    def bulk_update_metadata(
        self,
        contact_ids: List[str],
        metadata_updates: Dict[str, str]
    ) -> None:
        """
        Update metadata for multiple contacts.
        
        Args:
            contact_ids: List of contact IDs to update
            metadata_updates: Dict of metadata key-value pairs to set
            
        Raises:
            ContactNotFoundError: If any contact doesn't exist
        """
        # Verify all contacts exist first
        for contact_id in contact_ids:
            if contact_id not in self.contacts:
                raise ContactNotFoundError(f"Contact {contact_id} not found")
                
        # Update all contacts
        for contact_id in contact_ids:
            contact = self.contacts[contact_id]
            for key, value in metadata_updates.items():
                contact.set_metadata(key, value)
            self._save_contact(contact)
            
        logger.info(f"Updated metadata for {len(contact_ids)} contacts")
        
    def update_message_stats(
        self,
        identifier: str,
        total_delta: int = 0,
        unread_delta: int = 0,
        last_message_time: Optional[str] = None
    ) -> None:
        """
        Update message statistics for a contact.
        
        Args:
            identifier: Phone number or email of contact
            total_delta: Change in total message count
            unread_delta: Change in unread message count
            last_message_time: ISO format timestamp of last message
            
        Raises:
            ContactNotFoundError: If contact not found
        """
        contact = self.find_by_identifier(identifier)
        if not contact:
            raise ContactNotFoundError(f"No contact found for {identifier}")
            
        contact.update_message_stats(
            total_delta=total_delta,
            unread_delta=unread_delta,
            last_message_time=last_message_time
        )
        self._save_contact(contact)
        
    def _matches_query(self, contact: Contact, query: str) -> bool:
        """Check if a contact matches a search query."""
        query = query.lower()
        
        # Check name
        if query in contact.name.lower():
            return True
            
        # Check phone numbers
        for phone in contact.phone_numbers:
            if query in phone:
                return True
                
        # Check emails
        for email in contact.emails:
            if query in email.lower():
                return True
                
        return False
