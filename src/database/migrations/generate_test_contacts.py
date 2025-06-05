"""
Generate test contacts for development and testing.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from src.contacts.contact import Contact

def generate_test_contacts() -> List[Contact]:
    """Generate a list of test contacts."""
    contacts = [
        Contact(
            name="John Smith",
            phone_numbers=["+14155551234"],
            emails=["john.smith@example.com"]
        ),
        Contact(
            name="Alice Johnson",
            phone_numbers=["+14155555678", "+14155555679"],
            emails=["alice@example.com", "alice.j@work.com"]
        ),
        Contact(
            name="Bob Wilson",
            phone_numbers=["+14155559012"],
            emails=["bob.wilson@example.com"]
        )
    ]
    
    # Add some metadata
    contacts[0].set_metadata("company", "Acme Corp")
    contacts[0].set_metadata("role", "Sales Manager")
    
    contacts[1].set_metadata("company", "Tech Solutions")
    contacts[1].set_metadata("role", "Software Engineer")
    contacts[1].set_metadata("timezone", "PST")
    
    contacts[2].set_metadata("company", "Global Industries")
    contacts[2].set_metadata("department", "Marketing")
    
    return contacts

def save_contacts(contacts: List[Contact]) -> Dict[str, int]:
    """
    Save contacts to JSON files.
    
    Returns:
        Dictionary with operation statistics
    """
    stats = {
        'total': len(contacts),
        'saved': 0,
        'failed': 0
    }
    
    # Ensure directory exists
    contact_dir = Path.home() / '.imessage_crm' / 'contacts'
    contact_dir.mkdir(parents=True, exist_ok=True)
    
    # Save each contact
    for contact in contacts:
        try:
            file_path = contact_dir / f"{contact.contact_id}.json"
            with open(file_path, 'w') as f:
                json.dump(contact.to_dict(), f, indent=2)
            stats['saved'] += 1
        except Exception as e:
            print(f"Failed to save contact {contact.name}: {e}")
            stats['failed'] += 1
            
    return stats

def main():
    """Generate and save test contacts."""
    print("Generating test contacts...")
    contacts = generate_test_contacts()
    
    print("Saving contacts...")
    stats = save_contacts(contacts)
    
    print("\nOperation complete:")
    print(f"Total contacts: {stats['total']}")
    print(f"Successfully saved: {stats['saved']}")
    print(f"Failed to save: {stats['failed']}")

if __name__ == '__main__':
    main()
