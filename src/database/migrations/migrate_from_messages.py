"""
Migration script to populate contacts database from Messages.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

from src.database.db_connector import DatabaseConnector
from src.database.contacts_db import ContactsDatabaseConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MessagesMigrator:
    """Handles migration of contacts from Messages to our database."""
    
    def __init__(self):
        """Initialize migrator with source and destination databases."""
        self.messages_db = DatabaseConnector()
        self.contacts_db = ContactsDatabaseConnector()
        
    def migrate_all_contacts(self) -> Dict[str, int]:
        """
        Migrate all contacts from Messages to our database.
        
        Returns:
            Dictionary with migration statistics
        """
        stats = {
            'total_contacts': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Get all contacts from Messages
            logger.info("Fetching contacts from Messages database...")
            contacts = self.messages_db.get_all_contacts()
            stats['total_contacts'] = len(contacts)
            
            # Process each contact
            for contact in contacts:
                try:
                    self._migrate_contact(contact)
                    stats['successful'] += 1
                    
                    # Log progress every 50 contacts
                    if stats['successful'] % 50 == 0:
                        logger.info(
                            f"Processed {stats['successful']}/{stats['total_contacts']} contacts"
                        )
                        
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(
                        f"Failed to migrate contact {contact.get('contact_id')}: {e}"
                    )
                    
            logger.info("Migration complete. Stats: %s", stats)
            return stats
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
            
    def _migrate_contact(self, contact: Dict) -> None:
        """
        Migrate a single contact to our database.
        
        Args:
            contact: Contact data from Messages database
        """
        contact_id = f"contact_{datetime.now().strftime('%Y%m%d%H%M%S')}_{contact['handle_id']}"
        
        try:
            # Create core contact record
            self.contacts_db.create_contact(contact_id)
            
            # Add identifier (phone/email)
            identifier_type = 'email' if '@' in contact['contact_id'] else 'phone'
            self.contacts_db.add_identifier(
                contact_id=contact_id,
                id_type=identifier_type,
                value=contact['contact_id'],
                confidence=1.0,  # From Messages, so we trust it
                verified=True
            )
            
            # Get additional contact data
            messages = self.messages_db.get_contact_messages(
                contact['handle_id'],
                limit=100  # Recent messages for analysis
            )
            chats = self.messages_db.get_contact_chats(contact['handle_id'])
            
            # Add metadata
            metadata = {
                'service': contact['service'],
                'country': contact['country'],
                'original_id': contact['uncanonicalized_id'],
                'last_message_date': contact['last_message_date'],
                'message_count': contact['message_count'],
                'group_chat_count': sum(1 for c in chats if c['is_group']),
                'direct_chat_count': sum(1 for c in chats if not c['is_group'])
            }
            
            # Store metadata as attributes
            for key, value in metadata.items():
                if value is not None:  # Skip None values
                    self.contacts_db.add_attribute(
                        contact_id=contact_id,
                        attr_type=key,
                        value=str(value),
                        confidence=1.0,
                        source='messages_migration'
                    )
                    
            # Record migration attempt
            self.contacts_db.record_collection_attempt(
                contact_id=contact_id,
                attempt_type='messages_migration',
                details={
                    'source': 'messages_db',
                    'handle_id': contact['handle_id'],
                    'metadata': metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Error migrating contact {contact['contact_id']}: {e}")
            raise

def run_migration():
    """Run the migration process."""
    try:
        migrator = MessagesMigrator()
        stats = migrator.migrate_all_contacts()
        
        # Log results
        logger.info("Migration Results:")
        logger.info(f"Total contacts found: {stats['total_contacts']}")
        logger.info(f"Successfully migrated: {stats['successful']}")
        logger.info(f"Failed to migrate: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == '__main__':
    run_migration()
