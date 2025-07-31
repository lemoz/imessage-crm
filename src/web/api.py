#!/usr/bin/env python3
"""
iMessage CRM API Routes
RESTful API endpoints for the web dashboard
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_connector import DatabaseConnector, DatabaseError, PermissionError
from messaging.message_reader import MessageReader
from ai.conversation_analyzer import ConversationAnalyzer
from ai.conversation_simulator import ConversationSimulator
from ai.conversation_memory import ConversationMemory
from contacts.contact_manager import ContactManager

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
api_router = APIRouter()

# Pydantic models for request/response

class ConversationResponse(BaseModel):
    chat_id: str
    contact_name: Optional[str]
    last_message_date: Optional[str]
    message_count: int

class AttachmentInfo(BaseModel):
    filename: Optional[str]
    mime_type: Optional[str]
    file_extension: Optional[str]
    attachment_type: Optional[str]  # 'image', 'video', 'audio', 'document', 'unknown'

class MessageResponse(BaseModel):
    message_id: str
    text: Optional[str]
    is_from_me: bool
    date: Optional[str]
    sender: Optional[str]
    has_attachment: bool = False
    attachment: Optional[AttachmentInfo] = None

# Global contact manager instance for performance
_contact_manager_instance = None
_macos_contact_cache = {}  # Clear cache to force fresh lookups

def get_contact_manager():
    """Get or create a singleton ContactManager instance"""
    global _contact_manager_instance
    if _contact_manager_instance is None:
        try:
            from contacts.contact_manager import ContactManager
            _contact_manager_instance = ContactManager()
        except Exception as e:
            logger.error(f"Failed to initialize ContactManager: {e}")
            _contact_manager_instance = None
    return _contact_manager_instance

# Helper functions
def get_attachment_type(mime_type: str, filename: str = None) -> str:
    """Determine attachment type from mime type and filename"""
    if not mime_type:
        if filename:
            # Try to determine from file extension
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'tiff']:
                return 'image'
            elif extension in ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v']:
                return 'video'
            elif extension in ['mp3', 'wav', 'aac', 'm4a', 'flac']:
                return 'audio'
            elif extension in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
                return 'document'
        return 'unknown'
    
    mime_lower = mime_type.lower()
    if mime_lower.startswith('image/'):
        return 'image'
    elif mime_lower.startswith('video/'):
        return 'video'
    elif mime_lower.startswith('audio/'):
        return 'audio'
    elif mime_lower in ['application/pdf', 'text/plain', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return 'document'
    else:
        return 'unknown'


def get_attachment_display_text(attachment_info: AttachmentInfo) -> str:
    """Generate user-friendly attachment display text"""
    if not attachment_info:
        return '[📎 attachment]'
    
    attachment_type = attachment_info.attachment_type or 'unknown'
    filename = attachment_info.filename or 'unknown file'
    
    # Type-specific icons and descriptions
    type_info = {
        'image': ('🖼️', 'image'),
        'video': ('🎥', 'video'),
        'audio': ('🎵', 'audio'),
        'document': ('📄', 'document'),
        'unknown': ('📎', 'file')
    }
    
    icon, type_name = type_info.get(attachment_type, ('📎', 'file'))
    
    # Show filename if available and reasonable length
    if filename and filename != 'unknown file' and len(filename) < 50:
        return f'[{icon} {filename}]'
    else:
        return f'[{icon} {type_name}]'


def format_attachment_for_context(attachment_info: AttachmentInfo) -> str:
    """Format attachment information for LLM context (without emojis, more descriptive)"""
    if not attachment_info:
        return '[shared attachment]'
    
    attachment_type = attachment_info.attachment_type or 'file'
    filename = attachment_info.filename
    
    # Create descriptive text for LLM context
    if filename and len(filename) < 50:
        return f"[shared {attachment_type}: {filename}]"
    else:
        return f"[shared {attachment_type}]"


def get_contact_display_name(contact_id: str) -> str:
    """Get a friendly display name for a contact"""
    try:
        # Check cache first for macOS contacts
        if contact_id in _macos_contact_cache:
            cached_name = _macos_contact_cache[contact_id]
            if cached_name:
                return cached_name
        
        # Try to get name from contacts manager (singleton)
        contact_manager = get_contact_manager()
        if contact_manager:
            contact = contact_manager.find_by_identifier(contact_id)
            if contact and contact.name:
                return contact.name
        
        # Try macOS Contacts database (caching is handled inside the function)
        macos_name = get_macos_contact_name(contact_id)
        if macos_name:
            return macos_name
            
        # Fallback to formatted phone number or email
        formatted_name = format_contact_fallback(contact_id)
        return formatted_name
        
    except Exception as e:
        logger.error(f"Error getting contact display name for {contact_id}: {e}")
        # Fallback to formatted contact_id
        return format_contact_fallback(contact_id)

def format_contact_fallback(contact_id: str) -> str:
    """Format contact ID as a fallback display name"""
    if contact_id.startswith('+'):
        # Format phone number
        clean_number = contact_id.replace('+1', '')
        if len(clean_number) == 10:
            return f"({clean_number[:3]}) {clean_number[3:6]}-{clean_number[6:]}"
    # Return as-is for emails or other formats
    return contact_id


def get_macos_contact_name(contact_id: str) -> Optional[str]:
    """Get contact name from macOS Contacts database with optimizations"""
    try:
        # Check if we already checked this contact and found nothing
        if contact_id in _macos_contact_cache:
            return _macos_contact_cache[contact_id]
        
        import sqlite3
        from pathlib import Path
        import glob
        
        # Limit cache size to prevent memory issues
        if len(_macos_contact_cache) > 1000:
            _macos_contact_cache.clear()
        
        # Find all AddressBook database files (main + sources)
        addressbook_paths = []
        
        # Add main database
        main_db = Path.home() / "Library/Application Support/AddressBook/AddressBook-v22.abcddb"
        if main_db.exists():
            addressbook_paths.append(main_db)
        
        # Add source databases
        sources_pattern = str(Path.home() / "Library/Application Support/AddressBook/Sources/*/AddressBook-v22.abcddb")
        source_dbs = glob.glob(sources_pattern)
        addressbook_paths.extend([Path(db) for db in source_dbs])
        
        if not addressbook_paths:
            _macos_contact_cache[contact_id] = None
            return None
        
        # Normalize the contact ID for searching
        search_id = contact_id.replace('+1', '').replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Try each database until we find a match
        for db_path in addressbook_paths:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Search for phone numbers with pattern matching
                    if contact_id.startswith('+') or contact_id.replace('+', '').isdigit():
                        # Extract individual digits for pattern matching
                        digits = search_id
                        
                        # Try exact match first
                        cursor = conn.execute("""
                            SELECT DISTINCT r.ZFIRSTNAME, r.ZLASTNAME, r.ZORGANIZATION, r.ZNICKNAME
                            FROM ZABCDRECORD r
                            JOIN ZABCDPHONENUMBER pn ON r.Z_PK = pn.ZOWNER
                            WHERE pn.ZFULLNUMBER LIKE '%' || ? || '%'
                            LIMIT 1
                        """, (digits,))
                        
                        result = cursor.fetchone()
                        if not result and len(digits) >= 10:
                            # For US numbers, try breaking into parts: area code + exchange + number
                            area_code = digits[-10:-7]  # First 3 digits of the 10-digit number
                            exchange = digits[-7:-4]    # Next 3 digits
                            last_four = digits[-4:]     # Last 4 digits
                            
                            cursor = conn.execute("""
                                SELECT DISTINCT r.ZFIRSTNAME, r.ZLASTNAME, r.ZORGANIZATION, r.ZNICKNAME
                                FROM ZABCDRECORD r
                                JOIN ZABCDPHONENUMBER pn ON r.Z_PK = pn.ZOWNER
                                WHERE pn.ZFULLNUMBER LIKE '%' || ? || '%' 
                                  AND pn.ZFULLNUMBER LIKE '%' || ? || '%' 
                                  AND pn.ZFULLNUMBER LIKE '%' || ? || '%'
                                LIMIT 1
                            """, (area_code, exchange, last_four))
                    else:
                        # Search for email addresses
                        cursor = conn.execute("""
                            SELECT DISTINCT r.ZFIRSTNAME, r.ZLASTNAME, r.ZORGANIZATION, r.ZNICKNAME
                            FROM ZABCDRECORD r
                            JOIN ZABCDEMAILADDRESS e ON r.Z_PK = e.ZOWNER
                            WHERE LOWER(e.ZADDRESS) = LOWER(?)
                            LIMIT 1
                        """, (contact_id,))
                    
                    result = cursor.fetchone()
                    if result:
                        first_name = result['ZFIRSTNAME'] or ''
                        last_name = result['ZLASTNAME'] or ''
                        organization = result['ZORGANIZATION'] or ''
                        nickname = result['ZNICKNAME'] or ''
                        
                        # Build full name with priority: nickname > full name > organization
                        contact_name = None
                        if nickname:
                            contact_name = nickname
                        elif first_name or last_name:
                            full_name = f"{first_name} {last_name}".strip()
                            contact_name = full_name if full_name else organization
                        elif organization:
                            contact_name = organization
                        
                        if contact_name:
                            _macos_contact_cache[contact_id] = contact_name
                            logger.info(f"Found contact name for {contact_id}: {contact_name}")
                            return contact_name
                        
            except Exception as db_error:
                logger.error(f"Error querying database {db_path}: {db_error}")
                continue
        
        # Cache negative result after checking all databases
        _macos_contact_cache[contact_id] = None
        return None
        
    except Exception as e:
        logger.error(f"Error accessing macOS Contacts for {contact_id}: {e}")
        _macos_contact_cache[contact_id] = None
        return None

# Initialize services
def get_database():
    """Get database connection with error handling"""
    try:
        return DatabaseConnector()
    except (PermissionError, DatabaseError) as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@api_router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations():
    """Get list of all conversations with metadata"""
    try:
        db = get_database()
        contacts = db.get_all_contacts()
        
        conversations = []
        for contact in contacts:
            # Convert date to string if it's a number
            last_date = contact.get('last_message_date')
            if isinstance(last_date, (int, float)):
                last_date = str(last_date)
            
            # Try to get a friendly name for the contact
            contact_id = contact.get('contact_id', '')
            contact_name = get_contact_display_name(contact_id)
            
            conversations.append(ConversationResponse(
                chat_id=contact_id,
                contact_name=contact_name,
                last_message_date=last_date,
                message_count=contact.get('message_count', 0) or 0
            ))
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations/{chat_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(chat_id: str, limit: int = 500):
    """Get full message history for a conversation"""
    try:
        reader = MessageReader()
        
        # Try direct conversation first
        conversation = reader.get_direct_conversation(chat_id, limit=limit)
        messages = conversation.get('messages', [])
        
        # If we don't have enough messages or only have one-sided messages, 
        # try a broader search that includes all messages with this contact
        if len(messages) < 10 or all(not msg.get('is_from_me') for msg in messages):
            try:
                # Use the search method to get all messages with this contact
                search_results = reader.search_messages(
                    query="",  # Empty query to get all messages
                    sender=chat_id,  # Messages from this sender
                    limit=limit
                )
                
                # Also search for messages TO this contact (our messages)
                our_messages = reader.search_messages(
                    query="",
                    limit=limit
                )
                
                # Filter our_messages to only include ones we sent (is_from_me=True)
                # and manually filter by looking for the contact in the context
                combined_messages = messages.copy()
                
                # For now, use the original messages but log the issue
                logger.warning(f"Only found {len(messages)} messages for {chat_id}, all from contact. May be missing user messages.")
                
            except Exception as e:
                logger.error(f"Error with broader message search: {e}")
        
        messages = conversation.get('messages', [])
        
        response_messages = []
        for msg in messages:
            # Handle attachment information
            has_attachment = bool(msg.get('has_attachment', False))
            attachment_info = None
            
            if has_attachment:
                filename = msg.get('attachment_name')
                mime_type = msg.get('attachment_type')  # This is actually mime_type from the DB
                
                # Get file extension from filename
                file_extension = None
                if filename and '.' in filename:
                    file_extension = filename.split('.')[-1].lower()
                
                # Determine attachment type
                attachment_type = get_attachment_type(mime_type, filename)
                
                attachment_info = AttachmentInfo(
                    filename=filename,
                    mime_type=mime_type,
                    file_extension=file_extension,
                    attachment_type=attachment_type
                )
            
            response_messages.append(MessageResponse(
                message_id=str(msg.get('ROWID', '')),
                text=msg.get('text'),
                is_from_me=bool(msg.get('is_from_me', False)),
                date=msg.get('date'),
                sender="You" if msg.get('is_from_me') else chat_id,
                has_attachment=has_attachment,
                attachment=attachment_info
            ))
        
        return response_messages
        
    except Exception as e:
        logger.error(f"Error getting messages for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/conversations/{chat_id}/analyze")
async def analyze_conversation(chat_id: str, limit: int = 500):
    """Analyze a conversation and return relationship profile"""
    try:
        # Get conversation messages
        reader = MessageReader()
        conversation = reader.get_direct_conversation(chat_id, limit=limit)
        messages = conversation.get('messages', [])
        
        # Filter for text messages
        text_messages = [msg for msg in messages if msg.get('text') and len(msg['text'].strip()) > 2]
        
        if len(text_messages) < 3:
            raise HTTPException(
                status_code=400, 
                detail=f"Not enough messages for analysis. Found {len(text_messages)} text messages, minimum 3 required."
            )
        
        # Analyze conversation
        analyzer = ConversationAnalyzer()
        contact_info = {
            'name': chat_id.replace('+', '').replace('@', '_at_'),
            'phone': chat_id if chat_id.startswith('+') else None,
            'email': chat_id if '@' in chat_id else None
        }
        
        analysis = analyzer.analyze_conversation(text_messages, contact_info)
        
        return {
            "chat_id": chat_id,
            "messages_analyzed": len(text_messages),
            "analysis": analysis,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class StarterRequest(BaseModel):
    analysis: Optional[dict] = None
    previous_starters: Optional[List[str]] = None

@api_router.post("/conversations/{chat_id}/starters")
async def generate_message_starters(
    chat_id: str, 
    request: Optional[StarterRequest] = None,
    goal: str = None,
    limit: int = 500  # Message limit to use for fresh analysis
):
    """Generate contextual message starters for a conversation"""
    try:
        # Extract request data
        analysis = request.analysis if request else None
        previous_starters = request.previous_starters if request else []
        
        # Always get recent messages for context, regardless of whether we have cached analysis
        reader = MessageReader()
        conversation = reader.get_direct_conversation(chat_id, limit=limit)
        messages = conversation.get('messages', [])
        
        if analysis:
            # Use provided analysis (from previous analyze call)
            logger.info(f"Using provided analysis for starters generation: {chat_id}")
            starters = generate_contextual_starters(analysis, goal, chat_id, previous_starters, messages, limit)
        else:
            # Fall back to running analysis (slower path)
            logger.info(f"Running fresh analysis for starters generation: {chat_id}")
            
            # Get conversation analysis
            analyzer = ConversationAnalyzer()
            contact_info = {
                'name': chat_id.replace('+', '').replace('@', '_at_'),
                'phone': chat_id if chat_id.startswith('+') else None,
                'email': chat_id if '@' in chat_id else None
            }
            
            # Filter for text messages for analysis
            text_messages = [msg for msg in messages if msg.get('text') and len(msg['text'].strip()) > 2]
            
            if len(text_messages) < 3:
                # Fallback to basic starters if not enough conversation history
                starters = generate_basic_starters(goal, previous_starters)
            else:
                # Generate contextual starters based on fresh analysis
                fresh_analysis = analyzer.analyze_conversation(text_messages, contact_info)
                starters = generate_contextual_starters(fresh_analysis, goal, chat_id, previous_starters, messages, limit)
        
        return {
            "chat_id": chat_id,
            "goal": goal,
            "starters": starters,
            "generated_count": len(starters),
            "status": "completed",
            "used_cached_analysis": bool(analysis)
        }
        
    except Exception as e:
        logger.error(f"Error generating starters for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_basic_starters(goal: str = None, previous_starters: List[str] = None) -> list:
    """Generate basic conversation starters using LLM when no analysis is available"""
    # Create minimal analysis for LLM generation
    basic_analysis = {
        'relationship_context': 'friend',
        'topics': [],
        'sentiment_label': 'neutral',
        'summary': 'No conversation history available',
        'suggested_response_tone': 'friendly'
    }
    
    # Use LLM generation with basic context
    return generate_llm_starters(basic_analysis, goal, "", previous_starters, None, 500)


def generate_llm_starters(analysis: dict, goal: str = None, contact_id: str = "", previous_starters: List[str] = None, recent_messages: List[dict] = None, message_limit: int = 500) -> list:
    """Generate intelligent conversation starters using LLM with full message context"""
    try:
        import openai
        import os
        
        # Initialize OpenAI client with API key
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Extract context from analysis
        relationship = analysis.get('relationship_context', 'friend')
        topics = analysis.get('topics', [])
        sentiment = analysis.get('sentiment_label', 'neutral')
        summary = analysis.get('summary', '')
        suggested_tone = analysis.get('suggested_response_tone', 'friendly')
        
        # Format recent messages for context (use last 15-20 for optimal context)
        recent_context = ""
        if recent_messages:
            # Limit to most recent messages to avoid overwhelming the prompt
            context_messages = recent_messages[-min(20, len(recent_messages), message_limit//25):]
            context_lines = []
            for msg in context_messages:
                sender = "Me" if msg.get('is_from_me') else "Contact"
                
                # Build message content including attachments
                content_parts = []
                
                # Add text content if present
                text = msg.get('text', '').strip()
                if text:
                    content_parts.append(text)
                
                # Add attachment information if present
                if msg.get('has_attachment') and msg.get('attachment'):
                    attachment = msg['attachment']
                    attachment_desc = format_attachment_for_context(attachment)
                    if attachment_desc:
                        content_parts.append(attachment_desc)
                
                # Only include message if it has some content
                if content_parts:
                    full_content = " ".join(content_parts)
                    context_lines.append(f"{sender}: {full_content}")
                    
            recent_context = "\n".join(context_lines[-15:])  # Last 15 messages for context
        
        # Create intelligent system prompt
        system_prompt = f"""You are an expert at generating natural, contextual conversation starters for text messages. 
        
You help people reconnect with their {relationship} by creating authentic message starters that:
1. Reference recent conversation context when relevant
2. Match the relationship tone and history
3. Understand the user's specific goals or intentions
4. Feel natural and conversational, not robotic or templated
5. Avoid repeating previous attempts"""

        # Build the user prompt with rich context
        user_prompt_parts = [
            f"Generate 6 conversation starters for texting my {relationship}.",
            "",
            "CONVERSATION CONTEXT:"
        ]
        
        if recent_context:
            user_prompt_parts.extend([
                "Recent conversation:",
                recent_context,
                ""
            ])
        
        user_prompt_parts.extend([
            f"Relationship: {relationship}",
            f"Recent topics: {', '.join(topics) if topics else 'General conversation'}",
            f"Overall sentiment: {sentiment}",
            f"Suggested tone: {suggested_tone}"
        ])
        
        if summary:
            user_prompt_parts.append(f"Conversation summary: {summary}")
        
        if goal:
            user_prompt_parts.extend([
                "",
                f"SPECIFIC GOAL: {goal}",
                "Important: Understand the intent behind this goal. If it's about responding to a message, reference what they actually said. If it's about planning something, build on recent relevant conversation."
            ])
        
        if previous_starters:
            user_prompt_parts.extend([
                "",
                "AVOID repeating these previous attempts:",
                "\n".join(f"- {starter}" for starter in previous_starters[-10:])  # Show last 10 to avoid
            ])
        
        user_prompt_parts.extend([
            "",
            "Generate 6 starters that are:",
            "- Natural and authentic to this relationship",
            "- Contextually aware of recent conversation",
            "- Varied in approach and tone",
            f"- Focused on the goal: {goal}" if goal else "- Good conversation openers",
            "",
            "Return only the 6 starters, one per line, no numbering or extra text."
        ])
        
        user_prompt = "\n".join(user_prompt_parts)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            temperature=0.8
        )
        
        # Parse and clean the response
        starters = response.choices[0].message.content.strip().split('\n')
        starters = [s.strip('- ').strip() for s in starters if s.strip()]
        
        return starters[:6]
        
    except Exception as e:
        logger.error(f"Error generating LLM starters: {e}")
        # Fallback to existing AI generation
        return generate_ai_starters(analysis, goal, contact_id, previous_starters)


def generate_contextual_starters(analysis: dict, goal: str = None, contact_id: str = "", previous_starters: List[str] = None, recent_messages: List[dict] = None, message_limit: int = 500) -> list:
    """Generate contextual starters using LLM based on conversation analysis and recent messages"""
    # Always use LLM-based generation - no more hardcoded templates
    return generate_llm_starters(analysis, goal, contact_id, previous_starters, recent_messages, message_limit)


def generate_ai_starters(analysis: dict, goal: str = None, contact_id: str = "", previous_starters: List[str] = None) -> list:
    """Use AI to generate fresh starters when we have many previous ones"""
    try:
        import openai
        import os
        
        # Initialize OpenAI client with API key
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Build context for AI generation
        relationship = analysis.get('relationship_context', 'friend')
        topics = analysis.get('topics', [])
        sentiment = analysis.get('sentiment_label', 'neutral')
        
        system_prompt = f"""You are helping generate conversation starters for someone to text their {relationship}. 
        
Context:
- Relationship: {relationship}
- Recent topics: {', '.join(topics) if topics else 'None'}
- Overall sentiment: {sentiment}
- Goal: {goal if goal else 'Just checking in naturally'}

Generate 6 fresh, natural conversation starters that:
1. Match the relationship tone ({relationship})
2. Feel authentic and not robotic
3. Are completely different from the previous starters shown below
4. {"Focus on the goal: " + goal if goal else "Are casual check-ins or natural conversation openers"}

AVOID these previous starters:
{chr(10).join(f"- {starter}" for starter in (previous_starters or []))}

Return only the 6 starters, one per line, no numbering or extra text."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=500,
            temperature=0.8
        )
        
        starters = response.choices[0].message.content.strip().split('\n')
        starters = [s.strip('- ').strip() for s in starters if s.strip()]
        
        return starters[:6]
        
    except Exception as e:
        logger.error(f"Error generating AI starters: {e}")
        # Fallback to basic LLM generation
        return generate_basic_starters(goal, previous_starters)



@api_router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        db = get_database()
        message_count = db.get_message_count()
        contacts = db.get_all_contacts()
        active_contacts = len([c for c in contacts if (c.get('message_count') or 0) > 0])
        
        return {
            "total_messages": message_count,
            "total_contacts": len(contacts),
            "active_contacts": active_contacts,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))