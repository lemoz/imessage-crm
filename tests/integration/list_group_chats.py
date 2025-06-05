"""
Script to list available group chats in Messages app.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.messaging.message_sender import MessageSender

def main():
    sender = MessageSender()
    try:
        chats = sender.list_group_chats()
        print("\nAvailable group chats:")
        for i, chat in enumerate(chats, 1):
            print(f"{i}. {chat}")
    except Exception as e:
        print(f"Error listing group chats: {e}")

if __name__ == "__main__":
    main()
