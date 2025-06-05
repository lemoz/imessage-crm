"""
Manages state for group chats and participant tracking.
"""
import sqlite3
from pathlib import Path
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ChatStateManager:
    def __init__(self, db_path=None):
        """Initialize chat state manager with SQLite database."""
        if db_path is None:
            db_path = Path.home() / '.imessage_crm' / 'chat_state.db'
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Track all group chats we're managing
                CREATE TABLE IF NOT EXISTS group_chats (
                    chat_guid TEXT PRIMARY KEY,
                    chat_id INTEGER,
                    display_name TEXT,
                    created_at TIMESTAMP NOT NULL,
                    last_active TIMESTAMP NOT NULL,
                    last_processed_message_id INTEGER,
                    status TEXT CHECK (status IN ('active', 'archived', 'left')) NOT NULL
                );

                -- Track all participants in group chats
                CREATE TABLE IF NOT EXISTS participants (
                    chat_guid TEXT REFERENCES group_chats(chat_guid),
                    phone_number TEXT NOT NULL,
                    joined_at TIMESTAMP NOT NULL,
                    left_at TIMESTAMP,
                    is_admin BOOLEAN DEFAULT false,
                    PRIMARY KEY (chat_guid, phone_number)
                );

                -- Track processed messages to avoid duplicates
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id INTEGER PRIMARY KEY,
                    chat_guid TEXT REFERENCES group_chats(chat_guid),
                    processed_at TIMESTAMP NOT NULL
                );
            """)

    def is_chat_processed(self, chat_guid):
        """Check if we've already processed this chat."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM group_chats WHERE chat_guid = ?",
                (chat_guid,)
            )
            return cursor.fetchone() is not None

    def record_new_chat(self, chat_info):
        """Record a new group chat and its participants."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert chat
            conn.execute("""
                INSERT INTO group_chats (
                    chat_guid, chat_id, display_name, created_at, 
                    last_active, status
                ) VALUES (?, ?, ?, ?, ?, 'active')
            """, (
                chat_info['guid'],
                chat_info['chat_id'],
                chat_info.get('name', ''),
                now,
                now
            ))

            # Insert participants
            for phone in chat_info['participants']:
                conn.execute("""
                    INSERT INTO participants (
                        chat_guid, phone_number, joined_at
                    ) VALUES (?, ?, ?)
                """, (chat_info['guid'], phone, now))

    def update_last_processed_message(self, chat_guid, message_id):
        """Update the last processed message ID for a chat."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE group_chats 
                SET last_processed_message_id = ?,
                    last_active = ?
                WHERE chat_guid = ?
            """, (message_id, datetime.now().isoformat(), chat_guid))

    def get_last_processed_message(self, chat_guid):
        """Get the last processed message ID for a chat."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT last_processed_message_id FROM group_chats WHERE chat_guid = ?",
                (chat_guid,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def mark_message_processed(self, message_id, chat_guid):
        """Mark a message as processed to avoid duplicates."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO processed_messages (
                    message_id, chat_guid, processed_at
                ) VALUES (?, ?, ?)
            """, (message_id, chat_guid, datetime.now().isoformat()))
            
    def reset_state(self):
        """Reset all state - useful for testing."""
        logger.info("Resetting chat state database...")
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                DELETE FROM processed_messages;
                DELETE FROM participants;
                DELETE FROM group_chats;
            """)
        logger.info("Chat state database reset complete")

    def get_unprocessed_messages(self, chat_guid):
        """Get list of message IDs we haven't processed yet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT last_processed_message_id 
                FROM group_chats 
                WHERE chat_guid = ?
            """, (chat_guid,))
            result = cursor.fetchone()
            return result[0] if result else 0
