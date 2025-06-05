"""
Migration script to move contacts from JSON files to SQLite database.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from src.database.contacts_db import ContactsDatabaseConnector
from src.contacts.contact import Contact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContactMigrator:
    """Handles migration of contacts from JSON to SQLite."""
    
    def __init__(self):
        """Initialize migrator with source and destination."""
        self.json_dir = Path.home() / '.imessage_crm' / 'contacts'
        self.db = ContactsDatabaseConnector()
        
    def migrate_all_contacts(self) -> Dict[str, int]:
        """
        Migrate all contacts from JSON to SQLite.
        
        Returns:
            Dictionary with migration statistics
        """
        stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        logger.info(f"Starting migration from {self.json_dir}")
        
        # Ensure source directory exists
        if not self.json_dir.exists():
            logger.warning(f"Source directory {self.json_dir} does not exist")
            return stats
            
        # Process each JSON file
        for file_path in self.json_dir.glob("*.json"):
            stats['total_files'] += 1
            try:
                # Read JSON file
                with open(file_path, 'r') as f:
                    contact_data = json.load(f)
                    
                # Convert to Contact object
                contact = Contact.from_dict(contact_data)
                
                # Migrate to database
                self._migrate_contact(contact)
                
                stats['successful'] += 1
                logger.info(f"Successfully migrated contact: {contact.name}")
                
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"Failed to migrate {file_path}: {e}")
                
        logger.info(f"Migration complete. Stats: {stats}")
        return stats
        
    def _migrate_contact(self, contact: Contact) -> None:
        """
        Migrate a single contact to the database.
        
        Args:
            contact: Contact object to migrate
        """
        # Create core contact record
        self.db.create_contact(contact.contact_id)
        
        # Add phone numbers
        for phone in contact.phone_numbers:
            self.db.add_identifier(
                contact_id=contact.contact_id,
                id_type='phone',
                value=phone,
                confidence=1.0,  # Assuming existing data is verified
                verified=True
            )
            
        # Add emails
        for email in contact.emails:
            self.db.add_identifier(
                contact_id=contact.contact_id,
                id_type='email',
                value=email,
                confidence=1.0,
                verified=True
            )
            
        # Add name as attribute
        self.db.add_attribute(
            contact_id=contact.contact_id,
            attr_type='name',
            value=contact.name,
            confidence=1.0,
            source='json_migration'
        )
        
        # Migrate metadata as attributes
        for key, value in contact.metadata.items():
            self.db.add_attribute(
                contact_id=contact.contact_id,
                attr_type=key,
                value=str(value),  # Ensure string format
                confidence=1.0,
                source='json_migration'
            )
            
def run_migration():
    """Run the migration process."""
    try:
        migrator = ContactMigrator()
        stats = migrator.migrate_all_contacts()
        
        # Log results
        logger.info("Migration Results:")
        logger.info(f"Total files processed: {stats['total_files']}")
        logger.info(f"Successfully migrated: {stats['successful']}")
        logger.info(f"Failed to migrate: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == '__main__':
    run_migration()
