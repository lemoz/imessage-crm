-- Contacts Database Schema

-- Core contacts table
CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_message_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    unread_messages INTEGER DEFAULT 0
);

-- Contact identifiers (phone numbers, emails)
CREATE TABLE IF NOT EXISTS contact_identifiers (
    identifier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT REFERENCES contacts(contact_id),
    identifier_type TEXT CHECK (identifier_type IN ('phone', 'email')) NOT NULL,
    identifier_value TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(identifier_type, identifier_value)
);

-- Contact attributes (name, role, etc)
CREATE TABLE IF NOT EXISTS contact_attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT REFERENCES contacts(contact_id),
    attribute_type TEXT NOT NULL,  -- e.g., 'name', 'role', 'company', etc.
    attribute_value TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    source TEXT NOT NULL,  -- e.g., 'user_provided', 'extracted', 'ai_generated'
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Contact categories
CREATE TABLE IF NOT EXISTS contact_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT REFERENCES contacts(contact_id),
    category_name TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Data collection attempts
CREATE TABLE IF NOT EXISTS collection_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT REFERENCES contacts(contact_id),
    chat_guid TEXT,
    attempt_type TEXT NOT NULL,  -- e.g., 'name_extraction', 'email_request', etc.
    status TEXT CHECK (status IN ('pending', 'successful', 'failed')) NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    details TEXT  -- JSON string with attempt details
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contact_identifiers_contact 
ON contact_identifiers(contact_id);

CREATE INDEX IF NOT EXISTS idx_contact_attributes_contact 
ON contact_attributes(contact_id);

CREATE INDEX IF NOT EXISTS idx_contact_categories_contact 
ON contact_categories(contact_id);

CREATE INDEX IF NOT EXISTS idx_collection_attempts_contact 
ON collection_attempts(contact_id);

CREATE INDEX IF NOT EXISTS idx_contact_identifiers_value 
ON contact_identifiers(identifier_value);

CREATE INDEX IF NOT EXISTS idx_contact_attributes_type_value 
ON contact_attributes(attribute_type, attribute_value);
