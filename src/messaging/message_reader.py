"""
MessageReader module for reading messages from the macOS Messages app.
Uses SQLite to access the Messages database with proper error handling.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from .search_history import SearchHistory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageReadError(Exception):
    """Base exception for message reading errors."""
    pass

class DatabaseAccessError(MessageReadError):
    """Raised when unable to access the Messages database."""
    pass

class MessageType:
    """Enum-like class for message types."""
    TEXT = 'text'
    ATTACHMENT = 'attachment'
    
    @classmethod
    def all_types(cls) -> List[str]:
        return [cls.TEXT, cls.ATTACHMENT]

class MessageService:
    """Enum-like class for message services."""
    IMESSAGE = 'iMessage'
    SMS = 'SMS'
    
    @classmethod
    def all_services(cls) -> List[str]:
        return [cls.IMESSAGE, cls.SMS]

class SearchResult:
    """Represents a paginated search result."""
    def __init__(self, messages: List[Dict], total_count: int, page: int, page_size: int):
        self.messages = messages
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.total_pages = (total_count + page_size - 1) // page_size

    def has_next_page(self) -> bool:
        return self.page < self.total_pages

    def has_previous_page(self) -> bool:
        return self.page > 1

class MessageReader:
    """Handles reading messages from the macOS Messages app database."""
    
    def __init__(self):
        """Initialize the message reader."""
        self.db_path = os.path.expanduser("~/Library/Messages/chat.db")
        logger.info(f"Initializing MessageReader with database at {self.db_path}")
        self._verify_database_access()
        self.search_history = SearchHistory()
    
    def _verify_database_access(self):
        """
        Verify that we can access the Messages database.
        Raises DatabaseAccessError if access is denied.
        """
        if not os.path.exists(self.db_path):
            raise DatabaseAccessError(
                f"Messages database not found at {self.db_path}\n"
                "This could mean:\n"
                "1. Messages app is not set up\n"
                "2. No messages have been sent/received yet\n"
                "3. The database path is incorrect"
            )
            
        # Check file permissions
        if not os.access(self.db_path, os.R_OK):
            raise DatabaseAccessError(
                "Permission denied accessing Messages database.\n"
                "To fix this:\n"
                "1. Open System Settings\n"
                "2. Go to Privacy & Security > Full Disk Access\n"
                "3. Click the + button\n"
                "4. Add Terminal (if running from command line)\n"
                "   or your Python IDE (if running from an IDE)"
            )
            
        try:
            # Try to read from the database
            self._execute_query("SELECT 1")
            logger.info("Successfully verified database access")
        except sqlite3.Error as e:
            # Check if database is locked
            if 'database is locked' in str(e).lower():
                raise DatabaseAccessError(
                    "Messages database is locked. This usually means:\n"
                    "1. Messages app is currently running\n"
                    "2. Another process is accessing the database\n"
                    "Try closing Messages app and any other scripts"
                )
            else:
                raise DatabaseAccessError(
                    f"Unable to access Messages database: {e}\n"
                    "You may need to grant Full Disk Access to Terminal "
                    "or your Python environment."
                )
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """
        Execute a SQLite query on the Messages database.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of query results
            
        Raises:
            DatabaseAccessError: If unable to execute the query
        """
        try:
            logger.debug(f"Executing query: {query} with params: {params}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                logger.debug(f"Query returned {len(results)} results")
                return results
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {e}")
            raise DatabaseAccessError(f"Database query failed: {e}")
    
    def get_recent_messages(
        self,
        chat_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get recent messages from a chat.
        
        Args:
            chat_id: Phone number or email to get messages from.
                    If None, gets messages from all chats.
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries containing:
            - text: Message content
            - sender: Sender's handle (phone/email)
            - timestamp: Message timestamp
            - is_from_me: Whether the message was sent by the user
            
        Raises:
            MessageReadError: If unable to retrieve messages
        """
        try:
            logger.info(f"Retrieving up to {limit} messages" + 
                       (f" from {chat_id}" if chat_id else " from all chats"))
            
            # Base query to get messages with sender info
            query = """
                SELECT 
                    message.text,
                    handle.id as sender,
                    datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
                    message.is_from_me,
                    message.service
                FROM message 
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                WHERE message.text IS NOT NULL
            """
            
            params = []
            
            # Add chat_id filter if specified
            if chat_id:
                query += " AND handle.id = ?"
                # Normalize phone number format
                normalized_id = ''.join(filter(str.isdigit, chat_id))
                if len(normalized_id) == 10:
                    normalized_id = '+1' + normalized_id
                elif len(normalized_id) == 11 and normalized_id.startswith('1'):
                    normalized_id = '+' + normalized_id
                params.append(normalized_id)
                
            # Add ordering and limit
            query += " ORDER BY message.date DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            results = self._execute_query(query, tuple(params))
            
            # Format results
            messages = []
            for row in results:
                text, sender, date, is_from_me, service = row
                
                messages.append({
                    'text': text,
                    'sender': 'me' if is_from_me else (sender or 'unknown'),
                    'timestamp': date,
                    'is_from_me': bool(is_from_me),
                    'service': service
                })
            
            logger.info(f"Retrieved {len(messages)} messages successfully")
            return messages
            
        except DatabaseAccessError as e:
            logger.error(f"Failed to get messages: {e}")
            raise MessageReadError(f"Failed to get messages: {e}")
            
    def search_messages(
        self,
        content: Optional[str] = None,
        sender: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        message_types: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        read_status: Optional[bool] = None,
        has_attachments: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SearchResult:
        """
        Search messages with various filters and pagination.
        
        Args:
            content: Text to search for in message content
            sender: Sender's phone number or email
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            page: Page number (1-based)
            page_size: Number of results per page
            
        Returns:
            SearchResult object containing paginated messages and metadata
            
        Raises:
            MessageReadError: If unable to search messages
        """
        try:
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            
            # Base query with common table expression for filtering
            query = """
                WITH RECURSIVE
                filtered_messages AS (
                    SELECT 
                        message.text,
                        handle.id as sender,
                        datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 
                                'unixepoch', 'localtime') as date,
                        message.is_from_me,
                        message.service,
                        message.date as raw_date,
                        message.is_read,
                        message.cache_has_attachments as has_attachment,
                        attachment.filename as attachment_name,
                        attachment.mime_type as attachment_type
                    FROM message 
                    LEFT JOIN handle ON message.handle_id = handle.ROWID
                    LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                    LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                    LEFT JOIN message_attachment_join ON message.ROWID = message_attachment_join.message_id
                    LEFT JOIN attachment ON message_attachment_join.attachment_id = attachment.ROWID
                    WHERE message.service IN ('SMS', 'iMessage')
            """
            
            params = []
            
            # Add content search
            if content:
                query += " AND message.text LIKE ? "
                params.append(f"%{content}%")
                
            # Add message type filter
            if message_types:
                valid_types = [t for t in message_types if t in MessageType.all_types()]
                if MessageType.ATTACHMENT in valid_types:
                    if MessageType.TEXT in valid_types:
                        pass  # No filter needed for both types
                    else:
                        query += " AND message.cache_has_attachments = 1"
                elif MessageType.TEXT in valid_types:
                    query += " AND message.cache_has_attachments = 0"
                    
            # Add service filter
            if services:
                valid_services = [s for s in services if s in MessageService.all_services()]
                if valid_services:
                    placeholders = ','.join(['?'] * len(valid_services))
                    query += f" AND message.service IN ({placeholders})"
                    params.extend(valid_services)
                    
            # Add read status filter
            if read_status is not None:
                query += " AND message.is_read = ?"
                params.append(1 if read_status else 0)
                
            # Add attachment filter
            if has_attachments is not None:
                query += " AND message.cache_has_attachments = ?"
                params.append(1 if has_attachments else 0)
            
            # Add sender filter
            if sender:
                query += " AND (handle.id = ? OR (message.is_from_me = 1 AND handle.id = ?)) "
                params.extend([sender, sender])
                logger.info(f"Searching for sender (both sent and received): {sender}")
            
            # Add date range filters
            if start_date:
                query += (
                    " AND date(datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), "
                    "'unixepoch', 'localtime')) >= date(?) "
                )
                params.append(start_date)
            if end_date:
                query += (
                    " AND date(datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), "
                    "'unixepoch', 'localtime')) <= date(?) "
                )
                params.append(end_date)
            query += """
                )
                SELECT * FROM filtered_messages
                ORDER BY raw_date DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])
            
            # Log the query and params
            logger.info(f"Executing query: {query}")
            logger.info(f"With parameters: {params}")
            
            # Execute query for paginated results
            results = self._execute_query(query, tuple(params))
            
            # Get total count for pagination
            count_query = """
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM message 
                    LEFT JOIN handle ON message.handle_id = handle.ROWID
                    LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                    LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                    LEFT JOIN message_attachment_join ON message.ROWID = message_attachment_join.message_id
                    LEFT JOIN attachment ON message_attachment_join.attachment_id = attachment.ROWID
                    WHERE (message.text IS NOT NULL OR message.cache_has_attachments = 1)
                    AND message.service IN ('SMS', 'iMessage')
                    AND (
                        length(message.text) > 0
                        OR message.cache_has_attachments = 1
                    )
            """
            
            # Add the same filters to count query
            count_params = []
            if content:
                count_query += " AND message.text LIKE ? "
                count_params.append(f"%{content}%")
            if message_types:
                valid_types = [t for t in message_types if t in MessageType.all_types()]
                if MessageType.ATTACHMENT in valid_types:
                    if MessageType.TEXT in valid_types:
                        pass  # No filter needed for both types
                    else:
                        count_query += " AND message.cache_has_attachments = 1"
                elif MessageType.TEXT in valid_types:
                    count_query += " AND message.cache_has_attachments = 0"
            if services:
                valid_services = [s for s in services if s in MessageService.all_services()]
                if valid_services:
                    placeholders = ','.join(['?'] * len(valid_services))
                    count_query += f" AND message.service IN ({placeholders})"
                    count_params.extend(valid_services)
            if read_status is not None:
                count_query += " AND message.is_read = ?"
                count_params.append(1 if read_status else 0)
            if has_attachments is not None:
                count_query += " AND message.cache_has_attachments = ?"
                count_params.append(1 if has_attachments else 0)
            if sender:
                count_query += " AND (handle.id = ? OR (message.is_from_me = 1 AND ? IN ('me', 'self'))) "
                normalized_sender = ''.join(filter(str.isdigit, sender))
                if len(normalized_sender) == 10:
                    normalized_sender = '+1' + normalized_sender
                elif len(normalized_sender) == 11 and normalized_sender.startswith('1'):
                    normalized_sender = '+' + normalized_sender
                count_params.extend([normalized_sender, sender.lower()])
            if start_date:
                count_query += (
                    " AND date(datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), "
                    "'unixepoch', 'localtime')) >= date(?) "
                )
                count_params.append(start_date)
            if end_date:
                count_query += (
                    " AND date(datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), "
                    "'unixepoch', 'localtime')) <= date(?) "
                )
                count_params.append(end_date)
            count_query += ")"
            
            # Use the same parameters for count query
            total_count = self._execute_query(count_query, tuple(count_params))[0][0]
            
            # Format results
            messages = []
            for row in results:
                text, sender, date, is_from_me, service, _, is_read, has_attachment, attachment_name, attachment_type = row
                
                # Get attachment info if present
                attachment_info = None
                if has_attachment:
                    attachment_info = {
                        'filename': attachment_name,
                        'mime_type': attachment_type
                    }
                
                messages.append({
                    'text': text,
                    'sender': 'me' if is_from_me else (sender or 'unknown'),
                    'timestamp': date,
                    'is_from_me': bool(is_from_me),
                    'service': service,
                    'is_read': bool(is_read),
                    'has_attachment': bool(has_attachment),
                    'attachment': attachment_info
                })
            
            logger.info(f"Found {total_count} messages, returning page {page} ({len(messages)} messages)")
            
            # Track search in history
            self.search_history.add_search(
                content=content,
                sender=sender,
                start_date=start_date,
                end_date=end_date,
                result_count=total_count
            )
            
            return SearchResult(messages, total_count, page, page_size)
            
        except DatabaseAccessError as e:
            logger.error(f"Failed to search messages: {e}")
            raise MessageReadError(f"Failed to search messages: {e}")
    
    def get_recent_chats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most recent chats ordered by last message date.
        
        Args:
            limit: Maximum number of chats to return
            
        Returns:
            List of chat dictionaries containing:
            - id: Chat ROWID
            - guid: Unique identifier
            - service: iMessage or SMS
            - participants: List of participant identifiers
            - message_count: Total messages in chat
            - unread_count: Number of unread messages
            - last_message: Most recent message details
        """
        try:
            query = """
                WITH LastMessages AS (
                    SELECT 
                        chat_id,
                        message_id,
                        message_date,
                        ROW_NUMBER() OVER (PARTITION BY chat_id ORDER BY message_date DESC) as rn
                    FROM chat_message_join
                )
                SELECT 
                    chat.ROWID as chat_id,
                    chat.guid,
                    chat.service_name,
                    chat.display_name,
                    chat.room_name,
                    GROUP_CONCAT(DISTINCT handle.id) as participants,
                    COUNT(DISTINCT message.ROWID) as message_count,
                    SUM(CASE WHEN message.is_read = 0 THEN 1 ELSE 0 END) as unread_count,
                    MAX(message.date) as last_message_date,
                    last_msg.text as last_message_text,
                    last_msg.is_from_me as last_message_is_from_me
                FROM chat
                LEFT JOIN chat_handle_join ON chat.ROWID = chat_handle_join.chat_id
                LEFT JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                LEFT JOIN chat_message_join ON chat.ROWID = chat_message_join.chat_id
                LEFT JOIN message ON chat_message_join.message_id = message.ROWID
                LEFT JOIN LastMessages lm ON lm.chat_id = chat.ROWID AND lm.rn = 1
                LEFT JOIN message as last_msg ON last_msg.ROWID = lm.message_id
                GROUP BY chat.ROWID
                ORDER BY last_message_date DESC
                LIMIT ?
            """
            
            results = self._execute_query(query, (limit,))
            chats = []
            
            # Get column names from cursor description
            columns = ['chat_id', 'guid', 'service_name', 'display_name', 'room_name',
                      'participants', 'message_count', 'unread_count', 'last_message_date',
                      'last_message_text', 'last_message_is_from_me']
            
            for row in results:
                # Convert row tuple to dict
                row_dict = dict(zip(columns, row))
                
                # Convert last message date
                last_message_date = None
                if row_dict['last_message_date']:
                    epoch_2001 = datetime(2001, 1, 1).timestamp()
                    timestamp = int(row_dict['last_message_date'] / 1_000_000_000 + epoch_2001)
                    last_message_date = datetime.fromtimestamp(timestamp).isoformat()
                
                # Get participants list
                participants = []
                if row_dict['participants']:
                    participants = row_dict['participants'].split(',')
                
                chats.append({
                    'id': str(row_dict['chat_id']),
                    'guid': row_dict['guid'],
                    'service': row_dict['service_name'],
                    'display_name': row_dict['display_name'],
                    'room_name': row_dict['room_name'],
                    'is_group': bool(row_dict['room_name']),
                    'participants': participants,
                    'message_count': row_dict['message_count'] or 0,
                    'unread_count': row_dict['unread_count'] or 0,
                    'last_message_date': last_message_date,
                    'last_message': {
                        'text': row_dict['last_message_text'],
                        'is_from_me': bool(row_dict['last_message_is_from_me'])
                    } if row_dict['last_message_text'] else None
                })
                
            logger.info(f"Retrieved {len(chats)} recent chats")
            return chats
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent chats: {e}")
            return []
    
    def find_chat_by_id(self, chat_id: str) -> Optional[Dict[str, str]]:
        """
        Find a chat by phone number, email, or group chat ID.
        
        Args:
            chat_id: Phone number, email, or group chat ID to find
            
        Returns:
            Chat information dictionary or None if not found
            
        Raises:
            MessageReadError: If unable to search for chat
        """
        try:
            logger.info(f"Looking up chat for ID: {chat_id}")
            
            # Normalize phone number if it looks like one
            if any(char.isdigit() for char in chat_id):
                normalized_id = ''.join(filter(str.isdigit, chat_id))
                if len(normalized_id) == 10:
                    normalized_id = '+1' + normalized_id
                elif len(normalized_id) == 11 and normalized_id.startswith('1'):
                    normalized_id = '+' + normalized_id
                chat_id = normalized_id
            
            query = """
                SELECT 
                    chat.ROWID,
                    chat.guid,
                    chat.service_name,
                    GROUP_CONCAT(handle.id) as participants
                FROM chat
                LEFT JOIN chat_handle_join ON chat.ROWID = chat_handle_join.chat_id
                LEFT JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                WHERE handle.id = ?
                GROUP BY chat.ROWID
            """
            
            results = self._execute_query(query, (chat_id,))
            
            if not results:
                logger.info(f"No chat found for ID: {chat_id}")
                return None
                
            row_id, guid, service, participants = results[0]
            chat_info = {
                'id': row_id,
                'guid': guid,
                'service': service,
                'participants': participants.split(',') if participants else []
            }
            
            logger.info(f"Found chat: {chat_info}")
            return chat_info
            
        except DatabaseAccessError as e:
            logger.error(f"Failed to find chat: {e}")
            raise MessageReadError(f"Failed to find chat: {e}")
    
    def get_direct_conversation(self, contact_id: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get all messages from a direct 1-on-1 conversation with a contact.
        
        Args:
            contact_id: Phone number or email of the contact
            limit: Maximum number of messages to retrieve
            
        Returns:
            Dictionary containing:
                - chat_info: Information about the chat
                - messages: List of all messages in chronological order
                - message_count: Total number of messages
        """
        try:
            logger.info(f"Getting direct conversation with {contact_id}")
            
            # First, find the direct chat with this contact
            # Use both style 45 (direct) and check for non-group chats
            query = """
                WITH direct_chats AS (
                    SELECT 
                        c.ROWID as chat_id,
                        c.guid,
                        c.display_name,
                        COUNT(DISTINCT chj.handle_id) as participant_count
                    FROM chat c
                    JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
                    JOIN handle h ON chj.handle_id = h.ROWID
                    WHERE (c.style = 45 OR c.style != 43)  -- Direct messages or not group
                    AND EXISTS (
                        SELECT 1 FROM chat_handle_join chj2
                        JOIN handle h2 ON chj2.handle_id = h2.ROWID
                        WHERE chj2.chat_id = c.ROWID
                        AND h2.id = ?
                    )
                    GROUP BY c.ROWID, c.guid, c.display_name
                    HAVING COUNT(DISTINCT chj.handle_id) <= 1  -- Only 1 other participant
                )
                SELECT 
                    dc.chat_id,
                    dc.guid,
                    dc.display_name,
                    (SELECT COUNT(*) FROM chat_message_join cmj WHERE cmj.chat_id = dc.chat_id) as message_count
                FROM direct_chats dc
                ORDER BY message_count DESC, dc.chat_id DESC
                LIMIT 1
            """
            
            results = self._execute_query(query, (contact_id,))
            
            if not results:
                logger.warning(f"No direct chat found with {contact_id}")
                return {
                    'chat_info': None,
                    'messages': [],
                    'message_count': 0
                }
            
            chat_id = results[0][0]
            chat_guid = results[0][1]
            
            # Now get all messages from this chat
            messages_query = """
                SELECT 
                    m.text,
                    m.attributedBody,
                    CASE 
                        WHEN m.is_from_me = 1 THEN 'Me'
                        ELSE COALESCE(h.id, ?)
                    END as sender,
                    datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 
                            'unixepoch', 'localtime') as date,
                    m.is_from_me,
                    m.service,
                    m.date as raw_date,
                    m.is_read,
                    m.cache_has_attachments as has_attachment,
                    a.filename as attachment_name,
                    a.mime_type as attachment_type,
                    m.associated_message_type
                FROM message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN message_attachment_join maj ON m.ROWID = maj.message_id
                LEFT JOIN attachment a ON maj.attachment_id = a.ROWID
                WHERE cmj.chat_id = ?
                ORDER BY m.date DESC
                LIMIT ?
            """
            
            messages = self._execute_query(messages_query, (contact_id, chat_id, limit))
            
            # Convert to list of dictionaries
            message_list = []
            for msg in messages:
                # Extract text from either text field or attributedBody
                text = msg[0]
                if not text and msg[1]:  # attributedBody
                    text = self._extract_text_from_attributed_body(msg[1])
                
                message_dict = {
                    'text': text,
                    'sender': msg[2],
                    'date': msg[3],
                    'is_from_me': bool(msg[4]),
                    'service': msg[5],
                    'raw_date': msg[6],
                    'is_read': bool(msg[7]),
                    'has_attachment': bool(msg[8]),
                    'attachment_name': msg[9],
                    'attachment_type': msg[10],
                    'message_type': msg[11]
                }
                message_list.append(message_dict)
            
            logger.info(f"Retrieved {len(message_list)} messages from direct chat with {contact_id}")
            
            return {
                'chat_info': {
                    'chat_id': chat_id,
                    'guid': chat_guid,
                    'contact_id': contact_id,
                    'is_group': False
                },
                'messages': message_list,
                'message_count': len(message_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting direct conversation: {e}")
            raise MessageReadError(f"Failed to get direct conversation: {e}")
    
    def get_group_chat_messages(self, chat_id: int, limit: int = 1000) -> Dict[str, Any]:
        """
        Get all messages from a specific group chat with all participants.
        
        Args:
            chat_id: The chat ID of the group chat
            limit: Maximum number of messages to retrieve
            
        Returns:
            Dictionary containing:
                - chat_info: Information about the group chat
                - participants: List of participants
                - messages: List of all messages with participant info
                - message_count: Total number of messages
        """
        try:
            logger.info(f"Getting messages from group chat {chat_id}")
            
            # First get chat info and participants
            chat_info_query = """
                SELECT 
                    c.ROWID,
                    c.guid,
                    c.display_name,
                    c.room_name,
                    GROUP_CONCAT(h.id, ',') as participants
                FROM chat c
                LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
                LEFT JOIN handle h ON chj.handle_id = h.ROWID
                WHERE c.ROWID = ?
                AND c.style = 43  -- Group chat
                GROUP BY c.ROWID
            """
            
            chat_results = self._execute_query(chat_info_query, (chat_id,))
            
            if not chat_results:
                logger.warning(f"No group chat found with ID {chat_id}")
                return {
                    'chat_info': None,
                    'participants': [],
                    'messages': [],
                    'message_count': 0
                }
            
            chat_row = chat_results[0]
            participants = chat_row[4].split(',') if chat_row[4] else []
            
            # Get all messages from this group chat
            messages_query = """
                SELECT 
                    m.text,
                    m.attributedBody,
                    CASE 
                        WHEN m.is_from_me = 1 THEN 'Me'
                        ELSE COALESCE(h.id, 'Unknown')
                    END as sender,
                    datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 
                            'unixepoch', 'localtime') as date,
                    m.is_from_me,
                    m.service,
                    m.date as raw_date,
                    m.is_read,
                    m.cache_has_attachments as has_attachment,
                    a.filename as attachment_name,
                    a.mime_type as attachment_type,
                    h.id as sender_id
                FROM message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN message_attachment_join maj ON m.ROWID = maj.message_id
                LEFT JOIN attachment a ON maj.attachment_id = a.ROWID
                WHERE cmj.chat_id = ?
                ORDER BY m.date ASC
                LIMIT ?
            """
            
            messages = self._execute_query(messages_query, (chat_id, limit))
            
            # Convert to list of dictionaries
            message_list = []
            for msg in messages:
                # Extract text from either text field or attributedBody
                text = msg[0]
                if not text and msg[1]:  # attributedBody
                    text = self._extract_text_from_attributed_body(msg[1])
                
                message_dict = {
                    'text': text,
                    'sender': msg[2],
                    'sender_id': msg[11],
                    'date': msg[3],
                    'is_from_me': bool(msg[4]),
                    'service': msg[5],
                    'raw_date': msg[6],
                    'is_read': bool(msg[7]),
                    'has_attachment': bool(msg[8]),
                    'attachment_name': msg[9],
                    'attachment_type': msg[10]
                }
                message_list.append(message_dict)
            
            logger.info(f"Retrieved {len(message_list)} messages from group chat")
            
            return {
                'chat_info': {
                    'chat_id': chat_row[0],
                    'guid': chat_row[1],
                    'display_name': chat_row[2] or chat_row[3] or 'Group Chat',
                    'is_group': True
                },
                'participants': participants,
                'messages': message_list,
                'message_count': len(message_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting group chat messages: {e}")
            raise MessageReadError(f"Failed to get group chat messages: {e}")
    
    def _extract_text_from_attributed_body(self, data: bytes) -> Optional[str]:
        """Extract readable text from attributedBody binary data."""
        if not data:
            return None
        
        try:
            import plistlib
            
            # Try to parse as NSKeyedArchiver plist
            plist = plistlib.loads(data)
            if isinstance(plist, dict) and '$objects' in plist:
                objects = plist['$objects']
                
                # Look for NSAttributedString or NSMutableAttributedString
                for i, obj in enumerate(objects):
                    if isinstance(obj, dict):
                        # Check if this is a string object
                        if '$class' in obj and 'NS.string' in obj:
                            string_ref = obj['NS.string']
                            if isinstance(string_ref, dict) and 'CF$UID' in string_ref:
                                string_index = string_ref['CF$UID']
                                if string_index < len(objects):
                                    text = objects[string_index]
                                    if isinstance(text, str) and len(text.strip()) > 0:
                                        return text.strip()
                        
                        # Check for direct string content in NSString objects
                        if 'NS.string' in obj:
                            content = obj['NS.string']
                            if isinstance(content, str) and len(content.strip()) > 0:
                                return content.strip()
                
                # Look for any string that looks like message content
                potential_messages = []
                for obj in objects:
                    if isinstance(obj, str) and len(obj.strip()) > 2:
                        # Filter out system/framework strings
                        if (not obj.startswith('NS') and 
                            not obj.startswith('__') and
                            not obj.startswith('CF') and
                            not obj in ['X$versionY$archiverT$topX$objects', 'streamtyped'] and
                            '$' not in obj and
                            'AttributeName' not in obj and
                            'NSColor' not in obj and
                            'NSFont' not in obj):
                            potential_messages.append(obj.strip())
                
                # Return the longest potential message
                if potential_messages:
                    return max(potential_messages, key=len)
                    
        except Exception as e:
            logger.debug(f"Plist parsing failed: {e}")
        
        # Enhanced fallback: extract readable text from binary data
        try:
            # First try UTF-8 decoding
            text = data.decode('utf-8', errors='replace')
            
            # Look for patterns that indicate message content
            import re
            
            # Extract sequences of printable characters
            readable_sequences = re.findall(r'[^\x00-\x1f\x7f-\x9f]{3,}', text)
            
            message_candidates = []
            for seq in readable_sequences:
                # Clean up the sequence
                cleaned = seq.strip()
                
                # Skip system/framework strings
                if (len(cleaned) > 2 and
                    not cleaned.startswith('NS') and
                    not cleaned.startswith('__') and
                    not cleaned.startswith('CF') and
                    not cleaned.startswith('$') and
                    'streamtyped' not in cleaned.lower() and
                    'archiver' not in cleaned.lower() and
                    'attributed' not in cleaned.lower() and
                    'X$version' not in cleaned and
                    '$objects' not in cleaned and
                    '$class' not in cleaned):
                    
                    # Look for natural language patterns
                    if (any(c.isalpha() for c in cleaned) and
                        len([c for c in cleaned if c.isalnum() or c.isspace()]) / len(cleaned) > 0.7):
                        message_candidates.append(cleaned)
            
            # Return the most likely message content
            if message_candidates:
                # Prefer longer, more natural-looking text
                return max(message_candidates, key=lambda x: len(x) + (10 if ' ' in x else 0))
                
        except Exception as e:
            logger.debug(f"Fallback text extraction failed: {e}")
        
        # Last resort: try to find printable ASCII sequences
        try:
            ascii_text = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in data)
            words = [word.strip() for word in ascii_text.split() if len(word.strip()) > 2]
            
            # Filter system strings and join meaningful words
            message_words = [word for word in words if not word.startswith(('NS', '__', 'CF', '$'))]
            
            if message_words:
                # If we have multiple words, join them; otherwise return the longest
                if len(message_words) > 1:
                    return ' '.join(message_words)
                else:
                    return message_words[0]
                    
        except Exception as e:
            logger.debug(f"ASCII extraction failed: {e}")
        
        return None
    
    def list_all_chats(self, contact_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all chats, optionally filtered by a specific contact.
        
        Args:
            contact_id: Optional phone number or email to filter chats
            
        Returns:
            List of chat dictionaries with info about each chat
        """
        try:
            query = """
                SELECT 
                    c.ROWID as chat_id,
                    c.guid,
                    c.display_name,
                    c.room_name,
                    CASE 
                        WHEN c.style = 43 THEN 1
                        ELSE 0
                    END as is_group,
                    COUNT(DISTINCT chj.handle_id) as participant_count,
                    GROUP_CONCAT(h.id, ',') as participants,
                    MAX(m.date) as last_message_date,
                    COUNT(m.ROWID) as message_count
                FROM chat c
                LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
                LEFT JOIN handle h ON chj.handle_id = h.ROWID
                LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
                LEFT JOIN message m ON cmj.message_id = m.ROWID
            """
            
            params = []
            if contact_id:
                query += """
                    WHERE EXISTS (
                        SELECT 1 FROM chat_handle_join chj2
                        JOIN handle h2 ON chj2.handle_id = h2.ROWID
                        WHERE chj2.chat_id = c.ROWID
                        AND h2.id = ?
                    )
                """
                params.append(contact_id)
            
            query += """
                GROUP BY c.ROWID
                ORDER BY last_message_date DESC
            """
            
            results = self._execute_query(query, tuple(params))
            
            chats = []
            for row in results:
                chat = {
                    'chat_id': row[0],
                    'guid': row[1],
                    'display_name': row[2] or row[3] or 'Unnamed Chat',
                    'is_group': bool(row[4]),
                    'participant_count': row[5],
                    'participants': row[6].split(',') if row[6] else [],
                    'last_message_date': datetime.fromtimestamp(row[7] / 1e9 + 978307200) if row[7] else None,
                    'message_count': row[8]
                }
                chats.append(chat)
            
            logger.info(f"Found {len(chats)} chats")
            return chats
            
        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            raise MessageReadError(f"Failed to list chats: {e}")
