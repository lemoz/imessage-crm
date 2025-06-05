"""
Database connector for iMessage chat.db.
Handles connection management, permissions, and basic querying functionality.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass

class PermissionError(DatabaseError):
    """Raised when database access is denied."""
    pass

class DatabaseConnector:
    """Manages connections and queries to the iMessage chat.db database."""
    
    DEFAULT_DB_PATH = str(Path.home() / "Library" / "Messages" / "chat.db")
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connector.
        
        Args:
            db_path: Optional path to chat.db. If None, uses default location.
        
        Raises:
            PermissionError: If database access is denied
            DatabaseError: If database cannot be accessed for other reasons
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._validate_database_access()
        
    def _validate_database_access(self) -> None:
        """
        Validate that we can access the database.
        
        Raises:
            PermissionError: If database access is denied
            DatabaseError: If database cannot be accessed for other reasons
        """
        if not os.path.exists(self.db_path):
            raise DatabaseError(f"Database not found at {self.db_path}")
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                raise PermissionError(
                    "Unable to access chat.db. Ensure Full Disk Access permission "
                    "is granted in System Preferences > Security & Privacy > Privacy."
                ) from e
            raise DatabaseError(f"Database error: {e}") from e
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Raises:
            DatabaseError: If connection fails
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
            yield conn
        except sqlite3.Error as e:
            raise DatabaseError(f"Database connection error: {e}") from e
        finally:
            if conn:
                conn.close()
                
    def get_recent_messages(self, limit: int = 100) -> List[Dict]:
        """
        Get recent messages from the database.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries containing:
                - text: Message content
                - date: Message timestamp
                - is_from_me: Boolean indicating if message was sent by user
                - service: Service type (iMessage/SMS)
                - handle_id: ID of the contact
        """
        query = """
            SELECT 
                message.ROWID,
                message.text,
                message.date,
                message.is_from_me,
                message.service,
                message.handle_id,
                handle.id as contact_id
            FROM message 
            LEFT JOIN handle ON message.handle_id = handle.ROWID
            WHERE message.text IS NOT NULL
            ORDER BY message.date DESC
            LIMIT ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                messages = [dict(row) for row in cursor.fetchall()]
                return messages
        except sqlite3.Error as e:
            raise DatabaseError(f"Error fetching messages: {e}") from e
            
    def get_contact_info(self, handle_id: int) -> Optional[Dict]:
        """
        Get contact information for a handle ID.
        
        Args:
            handle_id: The handle ID to look up
            
        Returns:
            Dictionary containing contact information or None if not found
        """
        query = """
            SELECT 
                ROWID,
                id,
                country,
                service,
                uncanonicalized_id
            FROM handle 
            WHERE ROWID = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (handle_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"Error fetching contact info: {e}") from e
            
    def get_message_count(self) -> int:
        """
        Get total count of messages in the database.
        
        Returns:
            Integer count of messages
        """
        query = "SELECT COUNT(*) as count FROM message WHERE text IS NOT NULL"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchone()['count']
        except sqlite3.Error as e:
            raise DatabaseError(f"Error counting messages: {e}") from e
            
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                # Handle both direct SELECT queries and CTEs (WITH ... SELECT)
                query_upper = query.strip().upper()
                if query_upper.startswith('SELECT') or query_upper.startswith('WITH'):
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    conn.commit()
                    return [{'lastrowid': cursor.lastrowid}]
        except sqlite3.Error as e:
            raise DatabaseError(f"Error executing query: {e}") from e
            
    def get_all_contacts(self) -> List[Dict]:
        """
        Get all contacts from the Messages database.
        
        Returns:
            List of contact dictionaries containing:
                - handle_id: Internal handle ID
                - contact_id: Contact identifier (phone/email)
                - service: Service type (iMessage/SMS)
                - country: Country code if available
                - uncanonical_id: Original format of the identifier
                - last_message_date: Timestamp of last message
                - message_count: Total number of messages
        """
        query = """
        WITH contact_stats AS (
            SELECT 
                handle_id,
                MAX(date) as last_message_date,
                COUNT(*) as message_count
            FROM message
            WHERE handle_id IS NOT NULL
            GROUP BY handle_id
        )
        SELECT 
            h.ROWID as handle_id,
            h.id as contact_id,
            h.service,
            h.country,
            h.uncanonicalized_id,
            cs.last_message_date,
            cs.message_count
        FROM handle h
        LEFT JOIN contact_stats cs ON h.ROWID = cs.handle_id
        ORDER BY cs.last_message_date DESC
        """
        
        try:
            return self.execute_query(query)
        except sqlite3.Error as e:
            raise DatabaseError(f"Error fetching contacts: {e}") from e
            
    def get_contact_messages(self, handle_id: int, limit: int = 100) -> List[Dict]:
        """
        Get messages for a specific contact.
        
        Args:
            handle_id: Handle ID of the contact
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries containing:
                - message_id: Message ID
                - text: Message content
                - date: Message timestamp
                - is_from_me: Whether message was sent by user
                - service: Service type
        """
        query = """
        SELECT 
            m.ROWID as message_id,
            m.text,
            m.date,
            m.is_from_me,
            m.service,
            m.cache_has_attachments,
            CASE 
                WHEN m.associated_message_type = 1 THEN 'reply'
                WHEN m.associated_message_type = 2 THEN 'reaction'
                ELSE NULL
            END as message_type
        FROM message m
        WHERE m.handle_id = ?
        AND m.text IS NOT NULL
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        try:
            return self.execute_query(query, (handle_id, limit))
        except sqlite3.Error as e:
            raise DatabaseError(f"Error fetching contact messages: {e}") from e
            
    def get_contact_chats(self, handle_id: int) -> List[Dict]:
        """
        Get all chats that a contact participates in.
        
        Args:
            handle_id: Handle ID of the contact
            
        Returns:
            List of chat dictionaries containing:
                - chat_id: Chat ID
                - guid: Chat GUID
                - chat_name: Display name of chat
                - is_group: Whether it's a group chat
                - participant_count: Number of participants
        """
        query = """
        SELECT 
            c.ROWID as chat_id,
            c.guid,
            c.display_name as chat_name,
            CASE 
                WHEN c.style = 43 THEN 1
                ELSE 0
            END as is_group,
            (SELECT COUNT(*) 
             FROM chat_handle_join 
             WHERE chat_id = c.ROWID) as participant_count
        FROM chat c
        JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
        WHERE chj.handle_id = ?
        ORDER BY c.last_addressed_handle DESC
        """
        
        try:
            return self.execute_query(query, (handle_id,))
        except sqlite3.Error as e:
            raise DatabaseError(f"Error fetching contact chats: {e}") from e
