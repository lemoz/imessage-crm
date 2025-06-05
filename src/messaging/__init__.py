"""
Messaging module for iMessage CRM.
"""

from .message_sender import MessageSender, SendError, RateLimit

__all__ = ['MessageSender', 'SendError', 'RateLimit']
