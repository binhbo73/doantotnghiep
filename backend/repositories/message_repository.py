"""
Message Repository - Data access layer for Message model.

Responsibility:
- Create messages (user and bot)
- Retrieve messages from conversations
- Manage message history
"""
from typing import List, Optional, Dict, Any
from django.apps import apps
from repositories.base_repository import BaseRepository

import logging

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository):
    """
    Repository for Message model.
    
    Encapsulates all data access for RAG chat messages.
    """
    
    model_class = None  # Will be set in __init__
    
    def __init__(self):
        """Initialize with Message model"""
        self.Message = apps.get_model('operations', 'Message')
        self.model_class = self.Message
        super().__init__()
    
    # ============================================================
    # MESSAGE CREATION
    # ============================================================
    
    def create_user_message(
        self,
        conversation_id: int,
        account_id: int,
        content: str,
        metadata: dict = None
    ) -> 'Message':
        """
        Create user message in conversation
        
        Args:
            conversation_id: Conversation ID
            account_id: Account/User ID
            content: Message content
            metadata: Additional data
        
        Returns:
            Created Message instance
        """
        try:
            message = self.create(
                conversation_id=conversation_id,
                account_id=account_id,
                role='user',
                content=content,
                metadata=metadata or {}
            )
            logger.debug(f"User message created in conversation {conversation_id}")
            return message
        except Exception as e:
            logger.error(f"Error creating user message: {str(e)}")
            raise
    
    def create_bot_message(
        self,
        conversation_id: int,
        content: str,
        metadata: dict = None
    ) -> 'Message':
        """
        Create bot/assistant message in conversation
        
        Args:
            conversation_id: Conversation ID
            content: Message content (response)
            metadata: Additional data (sources, context, etc.)
        
        Returns:
            Created Message instance
        """
        try:
            message = self.create(
                conversation_id=conversation_id,
                account_id=None,  # System message
                role='assistant',
                content=content,
                metadata=metadata or {}
            )
            logger.debug(f"Bot message created in conversation {conversation_id}")
            return message
        except Exception as e:
            logger.error(f"Error creating bot message: {str(e)}")
            raise
    
    # ============================================================
    # MESSAGE RETRIEVAL
    # ============================================================
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List['Message']:
        """
        Get messages from a conversation
        
        Args:
            conversation_id: Conversation ID
            limit: Max results
            offset: Pagination offset
            include_deleted: Include deleted messages (admin)
        
        Returns:
            List of Message instances
        """
        filters = {'conversation_id': conversation_id}
        
        if include_deleted:
            queryset = self.get_all_including_deleted()
        else:
            queryset = self.get_base_queryset()
        
        return queryset.filter(**filters).order_by('created_at')[offset:offset + limit]
    
    def get_latest_messages(
        self,
        conversation_id: int,
        count: int = 10
    ) -> List['Message']:
        """
        Get N latest messages from conversation (for context window)
        
        Args:
            conversation_id: Conversation ID
            count: Number of recent messages to retrieve
        
        Returns:
            List of Message instances (ordered chronologically)
        """
        messages = list(
            self.get_base_queryset().filter(
                conversation_id=conversation_id
            ).order_by('-created_at')[:count]
        )
        # Reverse to get chronological order
        return list(reversed(messages))
    
    def get_message_history(
        self,
        conversation_id: int,
        as_dicts: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get full conversation history formatted for LLM
        
        Args:
            conversation_id: Conversation ID
            as_dicts: Return as list of dicts with role/content
        
        Returns:
            List of messages or formatted dicts
        """
        messages = self.get_base_queryset().filter(
            conversation_id=conversation_id
        ).order_by('created_at')
        
        if as_dicts:
            return [
                {'role': msg.role, 'content': msg.content}
                for msg in messages
            ]
        
        return list(messages)
    
    def get_message_count(self, conversation_id: int) -> int:
        """Get total messages in conversation"""
        return self.get_base_queryset().filter(conversation_id=conversation_id).count()
    
    # ============================================================
    # MESSAGE UPDATES
    # ============================================================
    
    def update_message(
        self,
        message_id: int,
        **data
    ) -> 'Message':
        """
        Update message fields
        
        Args:
            message_id: Message ID
            **data: Fields to update
        
        Returns:
            Updated Message instance
        """
        message = self.get_by_id(message_id)
        for key, value in data.items():
            if hasattr(message, key):
                setattr(message, key, value)
        message.save()
        logger.debug(f"Message {message_id} updated")
        return message
    
    # ============================================================
    # MESSAGE DELETION
    # ============================================================
    
    def delete_message(self, message_id: int) -> bool:
        """
        Soft delete message
        
        Args:
            message_id: Message ID
        
        Returns:
            True if deleted successfully
        """
        result = self.delete(message_id)
        logger.info(f"Message {message_id} deleted")
        return result
    
    def delete_conversation_messages(self, conversation_id: int) -> int:
        """
        Soft delete all messages in conversation
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            Number of messages deleted
        """
        messages = self.get_base_queryset().filter(conversation_id=conversation_id)
        count = messages.count()
        for msg in messages:
            self.delete(msg.id)
        logger.info(f"Deleted {count} messages from conversation {conversation_id}")
        return count
