# iMessage CRM MVP

## Overview

The iMessage CRM MVP is a proof-of-concept project aimed at connecting to macOS iMessage, ingesting all conversation data from the Messages app, and organizing it by contact. The goal is to build a lightweight CRM that not only stores conversation histories but also lays the foundation for future enhancements like AI-powered insights, automated response generation, and intelligent follow-ups.

### Initial Phase Focus
- **iMessage Integration**: Connecting to the Messages app using AppleScript and reading data directly from the iMessage SQLite database (chat.db)
- **Conversation Ingestion**: Extracting and organizing conversation history by contact
- **Basic CRM Functionality**: Providing a structure to log, search, and manage conversations for each contact
- **Security and Permissions**: Ensuring proper macOS permissions (Full Disk Access, Automation)

### Future Phases
- **Automated Follow-Ups**: Rules to schedule and send follow-up messages
- **AI-Powered Insights**: Analyzing conversation context, generating reply suggestions, and categorizing topics

## Architecture and Approach

### iMessage Integration

#### AppleScript for Sending Messages
```applescript
tell application "Messages"
    set targetBuddy to "[email protected]" -- Replace with the recipient's Apple ID or phone number
    set targetService to id of 1st service whose service type = iMessage
    send "Hello from automation!" to buddy targetBuddy of service id targetService
end tell
```

Python's subprocess module or libraries like py-applescript can be used to run this script.

#### Reading Conversation Data via chat.db
- **Database Location**: `~/Library/Messages/chat.db`
- **Access Method**: Python's built-in sqlite3 module

Sample Python Polling Code:
```python
import sqlite3, time

conn = sqlite3.connect("/Users/YourUser/Library/Messages/chat.db")
cursor = conn.cursor()
last_id = None

while True:
    cursor.execute("SELECT rowid, text, is_from_me, handle_id, date FROM message ORDER BY rowid DESC LIMIT 1;")
    row = cursor.fetchone()
    if row:
        msg_id, text, is_from_me, handle, date = row
        if not is_from_me:  # Process incoming message
            if last_id is None or msg_id > last_id:
                print("New message from contact ID", handle, "text:", text)
                # Additional processing here (e.g., logging, AI integration)
            last_id = msg_id
    time.sleep(5)  # Poll every 5 seconds
```

**Security Note**: Accessing chat.db requires Full Disk Access permissions.

### CRM and Data Organization
- Contact Mapping: Extract sender information from handle table
- Conversation Logging: Local SQLite database or JSON files
- State Tracking: Log conversation metadata

### Future Modules (Planned)
- **AI Module**:
  - Contextual Reply Generation using GPT-4
  - Topic Detection using NLP models
- **Automated Follow-Up Scheduler**:
  - Queue management with APScheduler
  - Dynamic timing based on context

## Prerequisites
- macOS Environment with active iMessage
- Required Permissions:
  - Full Disk Access
  - AppleScript Automation
- Python 3.8+
- Dependencies in requirements.txt

## Installation

1. Clone the Repository:
```bash
git clone https://github.com/lemoz/imessage-crm.git
cd imessage-crm
```

2. Install Dependencies:
```bash
pip install -r requirements.txt
```

3. Set Up Environment:
```bash
cp .env.example .env
# Edit .env with your configuration (optional)
```

4. Configure Permissions:
   - Add terminal/IDE to Full Disk Access in System Preferences
   - Authorize Python interpreter for Messages control

5. Test Installation:
```bash
python src/main.py --stats
```

## Usage

### Command Line Interface

1. **View Database Statistics:**
```bash
python src/main.py --stats
```

2. **List Recent Contacts:**
```bash
python src/main.py --list-contacts --limit 20
```

3. **Send a Test Message:**
```bash
python src/main.py --send "+1234567890" "Hello from iMessage CRM!"
```

### Python API

```python
from src.database.db_connector import DatabaseConnector
from src.messaging.message_sender import MessageSender
from src.contacts.contact_manager import ContactManager

# Connect to iMessage database
db = DatabaseConnector()

# Get recent messages
messages = db.get_recent_messages(limit=10)

# Send a message
sender = MessageSender()
sender.send_message("+1234567890", "Hello!")

# Manage contacts
cm = ContactManager(db)
contacts = cm.get_all_contacts()
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest tests/unit/
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=src
```

## Roadmap

### Phase 1 (MVP)
- Establish iMessage connection
- Ingest and parse conversations
- Organize by contact

### Phase 2
- Build basic CRM features

### Phase 3
- Develop automated follow-ups
- Integrate AI module

### Phase 4
- Refine user interface
- Add external integrations

## Security and Compliance
- Proper permissions management
- Secure data handling
- Rate limiting
- Audit logging

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for macOS iMessage integration
- Uses AppleScript for message sending
- SQLite for message database access
- OpenAI integration for future AI features

## Disclaimer

This software is provided as-is for educational and personal use. Please respect privacy and obtain proper consent when accessing message data. The authors are not responsible for any misuse of this software.

## Open Questions & Iteration Points
- Project naming considerations
- Data storage format selection
- UI approach (CLI vs GUI)
- AI module implementation strategy
- Follow-up logic specifics
