"""
MessageSender module for sending iMessages through AppleScript.
Handles message sending, rate limiting, and error handling.
"""

import subprocess
import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limiting configuration."""
    messages_per_minute: int = 10
    minimum_delay: float = 1.0  # seconds between messages

class MessageError(Exception):
    """Base exception for message-related errors."""
    pass

class SendError(MessageError):
    """Raised when a message fails to send."""
    pass

class MessageSender:
    """Handles sending messages through the macOS Messages app."""
    
    def __init__(self, rate_limit: Optional[RateLimit] = None):
        """
        Initialize the message sender.
        
        Args:
            rate_limit: Optional rate limiting configuration
        """
        self.rate_limit = rate_limit or RateLimit()
        self._last_send_time = 0
        
    def _validate_phone_number(self, phone: str) -> bool:
        """
        Validate phone number format.
        Basic validation for US/Canada numbers in various formats.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if phone number appears valid
        """
        # Remove all non-numeric characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Check if it's a valid length (10 digits for US/Canada, or 11 with country code)
        if len(digits) == 10 or (len(digits) == 11 and digits.startswith('1')):
            return True
            
        return False
        
    def _create_applescript(self, recipient: str, message: str, is_group: bool = False) -> str:
        """
        Create the AppleScript command for sending a message.
        
        Args:
            recipient: Phone number, email, or group chat name
            message: Message content to send
            is_group: Whether this is a group chat message
            
        Returns:
            AppleScript command string
        """
        # Escape any double quotes in the message and recipient
        message = message.replace('"', '\\"')
        recipient = recipient.replace('"', '\\"')
        
        if is_group:
            return f'''
                tell application "Messages"
                    set targetChat to first chat where id is "{recipient}"
                    send "{message}" to targetChat
                end tell
            '''
        else:
            return f'''
                tell application "Messages"
                    set targetBuddy to "{recipient}"
                    set targetService to id of 1st service whose service type = iMessage
                    send "{message}" to buddy targetBuddy of service id targetService
                end tell
            '''
        
    def _enforce_rate_limit(self):
        """
        Enforce rate limiting by waiting if necessary.
        """
        current_time = time.time()
        time_since_last = current_time - self._last_send_time
        
        if time_since_last < self.rate_limit.minimum_delay:
            sleep_time = self.rate_limit.minimum_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        self._last_send_time = time.time()
        
    def send_message(self, recipient: str, message: str, is_group: bool = False) -> bool:
        """
        Send a message to a recipient or group chat.
        
        Args:
            recipient: Phone number, email, or group chat ID
            message: Message content to send
            is_group: Whether this is a group chat message
            
        Returns:
            True if message was sent successfully
            
        Raises:
            SendError: If the message fails to send or recipient is invalid
        """
        # Only validate phone number if it's not a group chat
        if not is_group and not self._validate_phone_number(recipient):
            error_msg = f"Invalid phone number format: {recipient}"
            logger.error(error_msg)
            raise SendError(error_msg)
            
        self._enforce_rate_limit()
        
        script = self._create_applescript(recipient, message, is_group)
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode == 0:
                logger.info(f"Message sent successfully to {recipient}")
                return True
            else:
                raise SendError(f"Message send failed: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to send message to {recipient}: {e.stderr}"
            logger.error(error_msg)
            raise SendError(error_msg) from e
            
    def get_recent_messages(self, chat_id: str = None, limit: int = 10, is_group: bool = False) -> List[Dict[str, str]]:
        """
        Get recent messages from a chat.
        
        Args:
            chat_id: Phone number, email, or group chat name. If None, gets messages from all chats.
            limit: Maximum number of messages to retrieve
            is_group: Whether this is a group chat
            
        Returns:
            List of message dictionaries containing:
            - text: Message content
            - sender: Sender's name or number
            - timestamp: Message timestamp
            - is_from_me: Whether the message was sent by the user
            
        Raises:
            SendError: If unable to retrieve messages
        """
        # First get the chat ID for the target chat
        find_chat_script = f'''
            tell application "Messages"
                try
                    set targetChat to null
                    repeat with c in chats
                        if not is_group then
                            if (exists participants of c) and (count of participants of c) is 1 then
                                set p to first participant of c
                                if (get handle of p) is "{chat_id}" then
                                    set targetChat to c
                                    exit repeat
                                end if
                            end if
                        else
                            if (exists name of c) and (name of c is "{chat_id}") then
                                set targetChat to c
                                exit repeat
                            end if
                        end if
                    end repeat
                    
                    if targetChat is null then
                        return "Chat not found"
                    end if
                    
                    -- Get messages from the chat
                    set messageList to {{}}
                    set msgs to messages of targetChat
                    set msgCount to (count msgs)
                    
                    if msgCount > 0 then
                        set startIdx to (msgCount - {limit} + 1)
                        if startIdx < 1 then
                            set startIdx to 1
                        end if
                        
                        repeat with i from startIdx to msgCount
                            set msg to item i of msgs
                            set msgInfo to {{}}
                            
                            -- Get message content
                            set end of msgInfo to (get content of msg)
                            
                            -- Get sender info
                            if exists sender of msg then
                                if is from me of msg then
                                    set end of msgInfo to "me"
                                else
                                    set end of msgInfo to (get name of sender of msg)
                                end if
                            else
                                set end of msgInfo to "unknown"
                            end if
                            
                            -- Get timestamp and is_from_me
                            set end of msgInfo to ((get date received of msg) as string)
                            set end of msgInfo to (get is from me of msg)
                            
                            set end of messageList to msgInfo
                        end repeat
                    end if
                    
                    return messageList
                on error errMsg
                    return "Error: " & errMsg
                end try
            end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', find_chat_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output.startswith("Error:") or output == "Chat not found":
                    raise SendError(output)
                    
                # Parse the output into a list of message dictionaries
                messages = []
                raw_messages = output.split(', ')
                
                # Group every 4 items into a message dictionary
                for i in range(0, len(raw_messages), 4):
                    if i + 3 < len(raw_messages):
                        messages.append({
                            'text': raw_messages[i],
                            'sender': raw_messages[i + 1],
                            'timestamp': raw_messages[i + 2],
                            'is_from_me': raw_messages[i + 3].lower() == 'true'
                        })
                
                return messages
            else:
                raise SendError(f"Failed to get messages: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to get messages: {e.stderr}"
            logger.error(error_msg)
            raise SendError(error_msg) from e
            
    def send_bulk_messages(
        self, 
        recipients: List[str], 
        message: str,
        continue_on_error: bool = False
    ) -> Dict[str, bool]:
        """
        Send the same message to multiple recipients.
        
        Args:
            recipients: List of phone numbers or emails
            message: Message content to send
            continue_on_error: If True, continue sending to remaining recipients
                             even if some fail
                             
        Returns:
            Dictionary mapping recipients to success status
        """
        results = {}
        
        for recipient in recipients:
            try:
                success = self.send_message(recipient, message)
                results[recipient] = success
            except SendError as e:
                results[recipient] = False
                if not continue_on_error:
                    raise
                logger.error(f"Failed to send to {recipient}, continuing: {e}")
                
        return results
