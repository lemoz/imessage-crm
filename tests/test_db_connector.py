"""
Tests for the DatabaseConnector class.
"""

import os
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.database.db_connector import DatabaseConnector, DatabaseError, PermissionError

# Test data
MOCK_MESSAGES = [
    {
        'ROWID': 1,
        'text': 'Test message 1',
        'date': 1234567890,
        'is_from_me': 0,
        'service': 'iMessage',
        'handle_id': 1,
        'contact_id': '+1234567890'
    },
    {
        'ROWID': 2,
        'text': 'Test message 2',
        'date': 1234567891,
        'is_from_me': 1,
        'service': 'SMS',
        'handle_id': 2,
        'contact_id': 'test@example.com'
    }
]

MOCK_CONTACT = {
    'ROWID': 1,
    'id': '+1234567890',
    'country': 'US',
    'service': 'iMessage',
    'uncanonicalized_id': '+1 (234) 567-890'
}

@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_chat.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create test tables
    conn.execute("""
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY,
            text TEXT,
            date INTEGER,
            is_from_me INTEGER,
            service TEXT,
            handle_id INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY,
            id TEXT,
            country TEXT,
            service TEXT,
            uncanonicalized_id TEXT
        )
    """)
    
    # Insert test data
    conn.execute("""
        INSERT INTO message (text, date, is_from_me, service, handle_id)
        VALUES (?, ?, ?, ?, ?)
    """, (
        MOCK_MESSAGES[0]['text'],
        MOCK_MESSAGES[0]['date'],
        MOCK_MESSAGES[0]['is_from_me'],
        MOCK_MESSAGES[0]['service'],
        MOCK_MESSAGES[0]['handle_id']
    ))
    
    conn.execute("""
        INSERT INTO handle (id, country, service, uncanonicalized_id)
        VALUES (?, ?, ?, ?)
    """, (
        MOCK_CONTACT['id'],
        MOCK_CONTACT['country'],
        MOCK_CONTACT['service'],
        MOCK_CONTACT['uncanonicalized_id']
    ))
    
    conn.commit()
    conn.close()
    
    return str(db_path)

def test_init_with_invalid_path():
    """Test initialization with invalid database path."""
    with pytest.raises(DatabaseError):
        DatabaseConnector("/nonexistent/path/chat.db")

def test_init_with_permission_error():
    """Test initialization with permission error."""
    with patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.OperationalError(
            "unable to open database file"
        )
        with pytest.raises(PermissionError):
            DatabaseConnector()

def test_get_recent_messages(mock_db_path):
    """Test retrieving recent messages."""
    db = DatabaseConnector(mock_db_path)
    messages = db.get_recent_messages(limit=1)
    
    assert len(messages) == 1
    assert messages[0]['text'] == MOCK_MESSAGES[0]['text']
    assert messages[0]['is_from_me'] == MOCK_MESSAGES[0]['is_from_me']
    assert messages[0]['service'] == MOCK_MESSAGES[0]['service']

def test_get_contact_info(mock_db_path):
    """Test retrieving contact information."""
    db = DatabaseConnector(mock_db_path)
    contact = db.get_contact_info(1)
    
    assert contact is not None
    assert contact['id'] == MOCK_CONTACT['id']
    assert contact['country'] == MOCK_CONTACT['country']
    assert contact['service'] == MOCK_CONTACT['service']

def test_get_message_count(mock_db_path):
    """Test getting message count."""
    db = DatabaseConnector(mock_db_path)
    count = db.get_message_count()
    
    assert count == 1

def test_connection_error_handling():
    """Test handling of connection errors."""
    with pytest.raises(DatabaseError) as exc_info:
        DatabaseConnector("/nonexistent/path/chat.db")
    assert "Database not found" in str(exc_info.value)

def test_get_connection_context_manager(mock_db_path):
    """Test the connection context manager."""
    db = DatabaseConnector(mock_db_path)
    
    with db.get_connection() as conn:
        assert isinstance(conn, sqlite3.Connection)
        # Connection should be open
        conn.cursor().execute("SELECT 1")
    
    # Connection should be closed
    with pytest.raises(sqlite3.ProgrammingError):
        conn.cursor().execute("SELECT 1")
