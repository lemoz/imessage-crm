# iMessage Database Integration Design

## Overview
This document outlines the design for integrating with the macOS Messages app's chat.db database.

## Database Schema

### Key Tables

1. `handle`
   - Primary key: ROWID
   - Fields:
     - id (phone number/email)
     - country
     - service (iMessage/SMS)
     - uncanonicalized_id

2. `message`
   - Primary key: ROWID
   - Fields:
     - text (message content)
     - handle_id (foreign key to handle)
     - date (message timestamp)
     - is_from_me (boolean)
     - cache_has_attachments
     - service (iMessage/SMS)

3. `chat`
   - Contains group chat information
   - Links to handles through chat_handle_join

4. `chat_message_join`
   - Links messages to specific chats
   - Handles group message organization

5. `message_attachment_join`
   - Links messages to attachments
   - Handles media content

## State Management

### ChatStateManager Database

1. `group_chats` Table
   - Primary key: chat_guid
   - Fields:
     - chat_id (iMessage chat ID)
     - display_name
     - created_at
     - last_active
     - last_processed_message_id
     - status (active/archived/left)

2. `participants` Table
   - Composite key: (chat_guid, phone_number)
   - Fields:
     - joined_at
     - left_at
     - is_admin

3. Technical Details:
   - SQLite-based persistent storage
   - Located at ~/.imessage_crm/chat_state.db
   - Handles chat processing state
   - Prevents duplicate processing
   - Tracks participant history

## Technical Considerations

### Security
1. Full Disk Access
   - Required for accessing ~/Library/Messages/chat.db
   - Must handle permission errors gracefully
   - Need to implement secure credential storage

2. Data Privacy
   - Implement encryption for stored messages
   - Secure handling of phone numbers and emails
   - Proper cleanup of sensitive data in memory

### Performance
1. Database Access
   - Implement connection pooling
   - Use prepared statements for frequent queries
   - Cache frequently accessed data (contacts, recent messages)

2. Message Polling
   - Efficient polling strategy with configurable intervals
   - Track last processed message ID
   - Handle database locks gracefully

### Error Handling
1. Database Errors
   - Handle database locks (Messages app access)
   - Recover from corruption
   - Handle schema changes across macOS versions

2. Permission Errors
   - Clear error messages for missing permissions
   - Guidance for enabling required permissions
   - Graceful degradation when permissions are revoked

## Implementation Strategy

### Phase 1: Basic Integration
1. Create DatabaseConnector class
   - Implement connection management
   - Basic error handling
   - Permission checking

2. Implement MessageReader class
   - Read recent messages
   - Map handles to contacts
   - Basic message formatting

### Phase 2: Enhanced Features
1. Add caching layer
2. Implement attachment handling
3. Add group chat support
4. Enhanced error recovery

### Phase 3: Performance Optimization
1. Connection pooling
2. Query optimization
3. Bulk operations support

## Testing Strategy
1. Unit tests for each component
2. Integration tests with sample database
3. Performance benchmarks
4. Error condition testing
