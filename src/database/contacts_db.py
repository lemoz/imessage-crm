"""
Database connector for the contacts database.
Handles all contact-related database operations.
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ContactsDatabaseError(Exception):
    """Base exception for contacts database errors."""
    pass

class ContactsDatabaseConnector:
    """Manages connections and operations for the contacts database."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the contacts database connector.
        
        Args:
            db_path: Optional path to contacts.db. If None, uses default location.
        """
        if db_path is None:
            db_path = str(Path.home() / '.imessage_crm' / 'contacts.db')
            
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize database with schema."""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # Read and execute schema
        schema_path = Path(__file__).parent / 'schema' / 'contacts.sql'
        with open(schema_path) as f:
            schema = f.read()
            
        with self._get_connection() as conn:
            conn.executescript(schema)
            
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            raise ContactsDatabaseError(f"Database error: {e}")
        finally:
            if conn:
                conn.close()
                
    def create_contact(self, contact_id: str) -> None:
        """
        Create a new contact record.
        
        Args:
            contact_id: Unique identifier for the contact
        """
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO contacts (
                    contact_id, created_at, updated_at
                ) VALUES (?, ?, ?)
            """, (contact_id, now, now))
                
    def add_identifier(self, contact_id: str, id_type: str, 
                      value: str, confidence: float = 1.0,
                      verified: bool = False) -> None:
        """
        Add a phone number or email identifier for a contact.
        
        Args:
            contact_id: Contact's unique ID
            id_type: Type of identifier ('phone' or 'email')
            value: The identifier value
            confidence: Confidence score (0-1)
            verified: Whether this identifier is verified
        """
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO contact_identifiers (
                    contact_id, identifier_type, identifier_value,
                    confidence_score, verified, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, id_type, value, confidence, verified, now, now))
                
    def add_attribute(self, contact_id: str, attr_type: str,
                     value: str, confidence: float = 1.0,
                     source: str = 'user_provided') -> None:
        """
        Add or update an attribute for a contact.
        
        Args:
            contact_id: Contact's unique ID
            attr_type: Type of attribute (e.g., 'name', 'role')
            value: The attribute value
            confidence: Confidence score (0-1)
            source: Source of the attribute
        """
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO contact_attributes (
                    contact_id, attribute_type, attribute_value,
                    confidence_score, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, attr_type, value, confidence, source, now, now))
                
    def record_collection_attempt(self, contact_id: str, 
                                attempt_type: str,
                                chat_guid: Optional[str] = None,
                                details: Optional[Dict] = None) -> int:
        """
        Record a data collection attempt.
        
        Args:
            contact_id: Contact's unique ID
            attempt_type: Type of collection attempt
            chat_guid: Optional chat GUID where attempt was made
            details: Optional details about the attempt
            
        Returns:
            ID of the recorded attempt
        """
        now = datetime.now().isoformat()
        details_json = json.dumps(details) if details else None
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO collection_attempts (
                    contact_id, chat_guid, attempt_type,
                    status, requested_at, details
                ) VALUES (?, ?, ?, 'pending', ?, ?)
            """, (contact_id, chat_guid, attempt_type, now, details_json))
            
            return cursor.lastrowid
            
    def update_collection_attempt(self, attempt_id: int,
                                status: str,
                                details: Optional[Dict] = None) -> None:
        """
        Update status of a collection attempt.
        
        Args:
            attempt_id: ID of the attempt to update
            status: New status ('successful' or 'failed')
            details: Optional updated details
        """
        now = datetime.now().isoformat()
        details_json = json.dumps(details) if details else None
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE collection_attempts
                SET status = ?,
                    completed_at = ?,
                    details = COALESCE(?, details)
                WHERE attempt_id = ?
            """, (status, now, details_json, attempt_id))
            
    def get_contact_data(self, contact_id: str) -> Dict:
        """
        Get all data for a contact.
        
        Args:
            contact_id: Contact's unique ID
            
        Returns:
            Dictionary with all contact data
        """
        with self._get_connection() as conn:
            # Get core contact data
            contact = dict(conn.execute("""
                SELECT * FROM contacts WHERE contact_id = ?
            """, (contact_id,)).fetchone())
            
            # Get identifiers
            contact['identifiers'] = [
                dict(row) for row in conn.execute("""
                    SELECT * FROM contact_identifiers
                    WHERE contact_id = ?
                """, (contact_id,)).fetchall()
            ]
            
            # Get attributes
            contact['attributes'] = [
                dict(row) for row in conn.execute("""
                    SELECT * FROM contact_attributes
                    WHERE contact_id = ?
                """, (contact_id,)).fetchall()
            ]
            
            # Get categories
            contact['categories'] = [
                dict(row) for row in conn.execute("""
                    SELECT * FROM contact_categories
                    WHERE contact_id = ?
                """, (contact_id,)).fetchall()
            ]
            
            return contact
            
    def find_by_identifier(self, id_type: str, value: str) -> Optional[str]:
        """
        Find a contact by identifier.
        
        Args:
            id_type: Type of identifier ('phone' or 'email')
            value: Value to search for
            
        Returns:
            Contact ID if found, None otherwise
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT contact_id FROM contact_identifiers
                WHERE identifier_type = ? AND identifier_value = ?
            """, (id_type, value)).fetchone()
            
            return result['contact_id'] if result else None
