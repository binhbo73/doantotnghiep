"""
Chat Serializers - Serialization for Conversation, Message, and HumanFeedback models.
Used for API endpoints related to RAG chat and real-time messaging.
"""
from rest_framework import serializers
from django.utils import timezone
from apps.operations.models import (
    Conversation,
    ConversationAttachedDocument,
    ConversationAttachedFolder,
    Message,
    HumanFeedback,
)
from apps.documents.models import Document, Folder
from apps.users.models import Account
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer


# ============================================================
# CONVERSATION SERIALIZERS
# ============================================================

class ConversationSimpleSerializer(serializers.ModelSerializer):
    """Simple Conversation serializer for list endpoints"""
    account_username = serializers.CharField(source='account.username', read_only=True)
    account_id = serializers.UUIDField(source='account.id', read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'account_id', 'account_username', 'title', 'summary',
            'latest_message', 'message_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_latest_message(self, obj):
        """Get the latest message in the conversation"""
        latest = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if latest:
            return {
                'id': str(latest.id),
                'role': latest.role,
                'preview': latest.content[:100] + "..." if len(latest.content) > 100 else latest.content,
                'created_at': latest.created_at.isoformat()
            }
        return None
    
    def get_message_count(self, obj):
        """Get total message count in conversation"""
        return obj.messages.filter(is_deleted=False).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed Conversation serializer including related data"""
    account = serializers.SerializerMethodField()
    messages_preview = serializers.SerializerMethodField()
    attached_documents = serializers.SerializerMethodField()
    attached_folders = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'account', 'title', 'summary',
            'attached_documents', 'attached_folders',
            'messages_preview', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_account(self, obj):
        return {
            'id': str(obj.account.id),
            'username': obj.account.username,
            'email': obj.account.email,
            'first_name': obj.account.first_name,
            'last_name': obj.account.last_name,
        }
    
    def get_messages_preview(self, obj):
        """Get preview of latest 5 messages"""
        messages = obj.messages.filter(is_deleted=False).order_by('created_at')[:5]
        return MessageSimpleSerializer(messages, many=True).data
    
    def get_attached_documents(self, obj):
        """Get list of attached documents"""
        attachments = obj.attached_documents.filter(is_deleted=False)
        return [
            {
                'id': str(att.document.id),
                'name': att.document.original_name,
                'document_type': att.document.document_type,
            }
            for att in attachments if att.document and not att.document.is_deleted
        ]
    
    def get_attached_folders(self, obj):
        """Get list of attached folders"""
        attachments = obj.attached_folders.filter(is_deleted=False)
        return [
            {
                'id': str(att.folder.id),
                'name': att.folder.name,
            }
            for att in attachments if att.folder and not att.folder.is_deleted
        ]


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new RAG conversation"""
    title = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Conversation title"
    )
    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Folder IDs to attach as context"
    )
    
    def create(self, validated_data):
        """Create RAG conversation with attached documents/folders"""
        account = self.context['request'].user
        title = validated_data.get('title', '')
        document_ids = validated_data.get('document_ids', [])
        folder_ids = validated_data.get('folder_ids', [])
        summary = validated_data.get('summary', '')
        
        # Create conversation
        conversation = Conversation.objects.create(
            account=account,
            title=title or f"RAG Chat - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            summary=summary
        )
        
        # Attach documents
        for doc_id in document_ids:
            try:
                doc = Document.objects.get(id=doc_id, is_deleted=False)
                ConversationAttachedDocument.objects.create(
                    conversation=conversation,
                    document=doc
                )
            except Document.DoesNotExist:
                pass
        
        # Attach folders
        for folder_id in folder_ids:
            try:
                folder = Folder.objects.get(id=folder_id, is_deleted=False)
                ConversationAttachedFolder.objects.create(
                    conversation=conversation,
                    folder=folder
                )
            except Folder.DoesNotExist:
                    pass
            
            # Attach folders
            for folder_id in folder_ids:
                try:
                    folder = Folder.objects.get(id=folder_id, is_deleted=False)
                    ConversationAttachedFolder.objects.create(
                        conversation=conversation,
                        folder=folder
                    )
                except Folder.DoesNotExist:
                    pass
        
        return conversation


# ============================================================
# MESSAGE SERIALIZERS
# ============================================================

class MessageSimpleSerializer(serializers.ModelSerializer):
    """Simple message serializer for list/preview endpoints"""
    sender = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'sender', 'content', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sender(self, obj):
        """Get sender info if available"""
        if obj.role == 'user' and hasattr(obj, 'account') and obj.account:
            return {
                'id': str(obj.account.id),
                'username': obj.account.username,
                'full_name': f"{obj.account.first_name} {obj.account.last_name}".strip(),
            }
        elif obj.role == 'assistant':
            return {
                'id': 'system',
                'username': 'AI Assistant',
                'full_name': 'AI Assistant',
            }
        return None


class MessageDetailSerializer(serializers.ModelSerializer):
    """Detailed message serializer"""
    sender = serializers.SerializerMethodField()
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    citations = serializers.JSONField(read_only=True)
    tokens_used = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation_id', 'role', 'sender', 'content',
            'citations', 'tokens_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'citations', 'tokens_used']
    
    def get_sender(self, obj):
        """Get sender info"""
        if obj.role == 'user' and hasattr(obj, 'account') and obj.account:
            return {
                'id': str(obj.account.id),
                'username': obj.account.username,
                'full_name': f"{obj.account.first_name} {obj.account.last_name}".strip(),
                'avatar': obj.account.userprofile.avatar.url if hasattr(obj.account, 'userprofile') and obj.account.userprofile.avatar else None,
            }
        elif obj.role == 'assistant':
            return {
                'id': 'system',
                'username': 'AI Assistant',
                'full_name': 'AI Assistant',
                'avatar': None,
            }
        return None


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a new message (sending query to AI)"""
    conversation_id = serializers.UUIDField(
        required=True,
        help_text="ID of the conversation to send message to"
    )
    content = serializers.CharField(
        max_length=10000,
        min_length=1,
        help_text="Message content (1-10000 characters)"
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Optional: Specific documents to search for context"
    )
    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Optional: Specific folders to search for context"
    )
    
    def validate_content(self, value):
        """Validate message content"""
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty or whitespace only")
        return value.strip()
    
    def create(self, validated_data):
        """
        Create user message and get AI response.
        This integrates with ChatService to handle RAG pipeline.
        """
        from services.chat_service import ChatService
        from repositories.conversation_repository import ConversationRepository
        
        account = self.context['request'].user
        conversation_id = validated_data['conversation_id']
        content = validated_data['content']
        
        # Verify conversation ownership
        conv_repo = ConversationRepository()
        conversation = conv_repo.get_conversation_by_id(conversation_id, account_id=account.id)
        
        if not conversation:
            raise serializers.ValidationError("Conversation not found or access denied")
        
        # Build filters for RAG context
        filters = {}
        if validated_data.get('document_ids'):
            filters['document_ids'] = validated_data['document_ids']
        if validated_data.get('folder_ids'):
            filters['folder_ids'] = validated_data['folder_ids']
        
        # Get AI response via ChatService
        chat_service = ChatService()
        ai_response, bot_message = chat_service.ask(
            user_id=account.id,
            query=content,
            conversation_id=conversation_id,
            filters=filters if filters else None
        )
        
        # Return the bot message (AI response)
        return bot_message


class MessageListQuerySerializer(serializers.Serializer):
    """Query serializer for listing messages with filters"""
    conversation_id = serializers.UUIDField(required=True)
    role = serializers.ChoiceField(
        choices=['user', 'assistant', 'system'],
        required=False,
        help_text="Filter by message role"
    )
    limit = serializers.IntegerField(
        default=50,
        max_value=500,
        min_value=1,
        help_text="Max messages to return"
    )
    offset = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Pagination offset"
    )


# ============================================================
# HUMAN FEEDBACK SERIALIZERS
# ============================================================

class HumanFeedbackCreateSerializer(serializers.Serializer):
    """Serializer for creating feedback on a message"""
    message_id = serializers.UUIDField(required=True)
    rating = serializers.ChoiceField(
        choices=['upvote', 'downvote'],
        help_text="User's rating (upvote or downvote)"
    )
    comment = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Optional feedback comment"
    )
    
    def create(self, validated_data):
        """Create or update feedback"""
        account = self.context['request'].user
        message_id = validated_data['message_id']
        rating = validated_data['rating']
        comment = validated_data.get('comment', '')
        
        # Get message and verify it exists
        try:
            message = Message.objects.get(id=message_id, is_deleted=False)
        except Message.DoesNotExist:
            raise serializers.ValidationError("Message not found")
        
        # Create or update feedback
        feedback, created = HumanFeedback.objects.update_or_create(
            message=message,
            account=account,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        return feedback


class HumanFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for HumanFeedback model"""
    message_id = serializers.UUIDField(source='message.id', read_only=True)
    account_username = serializers.CharField(source='account.username', read_only=True)
    
    class Meta:
        model = HumanFeedback
        fields = [
            'id', 'message_id', 'account_username', 'rating',
            'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================
# CONVERSATION HISTORY SERIALIZER
# ============================================================

class ConversationHistorySerializer(serializers.Serializer):
    """Serializer for getting full conversation history"""
    conversation = ConversationSimpleSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    
    def get_messages(self, obj):
        """Get all messages in conversation"""
        messages = obj.messages.filter(is_deleted=False).order_by('created_at')
        return MessageDetailSerializer(messages, many=True).data
