"""
Conversation Repository - Data access layer for Conversation model.

Responsibility:
- Create conversations
- Retrieve conversations with permission checking
- List conversations for a user
"""
from typing import List, Optional
from django.utils import timezone
from django.apps import apps
from repositories.base_repository import BaseRepository

import logging

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository):
    """
    Repository for Conversation model.
    
    Encapsulates all data access for RAG chat conversations.
    """
    
    model_class = None  # Will be set in __init__
    
    def __init__(self):
        """Initialize with Conversation model"""
        self.Conversation = apps.get_model('operations', 'Conversation')
        self.model_class = self.Conversation
        super().__init__()
    
    # ============================================================
    # CONVERSATION CREATION
    # ============================================================
    
    def create_conversation(
        self,
        account_id: int,
        title: str = None,
        metadata: dict = None
    ) -> 'Conversation':
        """
        Create new conversation
        
        Args:
            account_id: User account ID
            title: Conversation title (auto-generated if not provided)
            metadata: Additional metadata (filters, context, etc.)
        
        Returns:
            Created Conversation instance
        """
        try:
            if not title:
                title = f"Conversation {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            
            conversation = self.create(
                account_id=account_id,
                title=title,
                metadata=metadata or {}
            )
            logger.info(f"Conversation created: {conversation.id} for Account {account_id}")
            return conversation
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise
    
    # ============================================================
    # CONVERSATION RETRIEVAL
    # ============================================================
    
    def get_conversation_by_id(
        self,
        conversation_id: int,
        account_id: int = None
    ) -> Optional['Conversation']:
        """
        Get conversation by ID
        
        Args:
            conversation_id: Conversation ID
            account_id: Optional - for permission verification
        
        Returns:
            Conversation instance or None
        """
        try:
            conversation = self.get_by_id(conversation_id)
            
            # Permission check if account_id provided
            if account_id and conversation.account_id != account_id:
                logger.warning(f"Unauthorized access to conversation {conversation_id} by account {account_id}")
                return None
            
            return conversation
        except Exception:
            return None
    
    def get_user_conversations(
        self,
        account_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List['Conversation']:
        """
        Get all conversations for a user
        
        Args:
            account_id: User account ID
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of Conversation instances
        """
        return self.get_base_queryset().filter(
            account_id=account_id
        ).order_by('-updated_at')[offset:offset + limit]
    
    def get_user_conversation_count(self, account_id: int) -> int:
        """Get total conversation count for user"""
        return self.get_base_queryset().filter(account_id=account_id).count()
    
    # ============================================================
    # CONVERSATION UPDATES
    # ============================================================
    
    def update_conversation(
        self,
        conversation_id: int,
        **data
    ) -> 'Conversation':
        """
        Update conversation fields
        
        Args:
            conversation_id: Conversation ID
            **data: Fields to update (title, metadata, etc.)
        
        Returns:
            Updated Conversation instance
        """
        conversation = self.get_by_id(conversation_id)
        for key, value in data.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
        conversation.save()
        logger.debug(f"Conversation {conversation_id} updated")
        return conversation
    
    # ============================================================
    # CONVERSATION DELETION
    # ============================================================
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Soft delete conversation
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            True if deleted successfully
        """
        result = self.delete(conversation_id)
        logger.info(f"Conversation {conversation_id} deleted")
        return result
