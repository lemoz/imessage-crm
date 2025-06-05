#!/usr/bin/env python3
"""
Main entry point for iMessage CRM application.
Provides a simple CLI interface for basic functionality.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.db_connector import DatabaseConnector, DatabaseError, PermissionError
from messaging.message_sender import MessageSender, SendError
from contacts.contact_manager import ContactManager
from messaging.search_history import SearchHistory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database() -> Optional[DatabaseConnector]:
    """Initialize database connection with proper error handling."""
    try:
        db = DatabaseConnector()
        logger.info("Successfully connected to iMessage database")
        return db
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        logger.error("Please ensure Full Disk Access is granted to your terminal/IDE")
        logger.error("Go to System Preferences > Security & Privacy > Privacy > Full Disk Access")
        return None
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return None


def list_contacts(db: DatabaseConnector, limit: int = 10):
    """List recent contacts from the database."""
    try:
        contacts = db.get_all_contacts()
        print(f"\n📱 Recent Contacts (showing first {limit}):")
        print("-" * 50)
        
        for i, contact in enumerate(contacts[:limit]):
            contact_id = contact.get('contact_id', 'Unknown')
            message_count = contact.get('message_count', 0)
            last_date = contact.get('last_message_date', 'Never')
            
            print(f"{i+1:2d}. {contact_id}")
            print(f"    Messages: {message_count}, Last: {last_date}")
            print()
            
    except Exception as e:
        logger.error(f"Error listing contacts: {e}")


def send_test_message(recipient: str, message: str):
    """Send a test message using the MessageSender."""
    try:
        sender = MessageSender()
        success = sender.send_message(recipient, message)
        
        if success:
            print(f"✅ Message sent successfully to {recipient}")
        else:
            print(f"❌ Failed to send message to {recipient}")
            
    except SendError as e:
        logger.error(f"Send error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def show_stats(db: DatabaseConnector):
    """Display basic statistics about the iMessage database."""
    try:
        message_count = db.get_message_count()
        contacts = db.get_all_contacts()
        active_contacts = len([c for c in contacts if c.get('message_count', 0) > 0])
        
        print("\n📊 iMessage Database Statistics:")
        print("-" * 40)
        print(f"Total Messages: {message_count:,}")
        print(f"Total Contacts: {len(contacts)}")
        print(f"Active Contacts: {active_contacts}")
        print()
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="iMessage CRM - Manage your iMessage conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-contacts          # List recent contacts
  %(prog)s --stats                  # Show database statistics
  %(prog)s --send "+1234567890" "Hello!"  # Send a test message
  
For more information, visit: https://github.com/yourusername/imessage-crm
        """
    )
    
    parser.add_argument(
        '--list-contacts', 
        action='store_true',
        help='List recent contacts from iMessage database'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show database statistics'
    )
    
    parser.add_argument(
        '--send', 
        nargs=2, 
        metavar=('RECIPIENT', 'MESSAGE'),
        help='Send a test message (recipient, message)'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=10,
        help='Limit number of contacts to display (default: 10)'
    )
    
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show welcome message
    print("🍎 iMessage CRM v0.1.0")
    print("=" * 30)
    
    # Handle send message command (doesn't require database)
    if args.send:
        recipient, message = args.send
        send_test_message(recipient, message)
        return
    
    # For other commands, we need database access
    db = setup_database()
    if not db:
        print("❌ Could not connect to iMessage database. Exiting.")
        sys.exit(1)
    
    # Handle commands
    if args.list_contacts:
        list_contacts(db, args.limit)
    elif args.stats:
        show_stats(db)
    else:
        # Default: show basic info
        print("✅ Successfully connected to iMessage database")
        show_stats(db)
        print("\nUse --help for available commands")


if __name__ == "__main__":
    main()