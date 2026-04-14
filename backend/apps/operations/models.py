from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.users.models import Account
from apps.documents.models import Document, Folder
from core.models import BaseModel
import uuid
import json


class Conversation(BaseModel):
    """
    Chat conversation model.
    Each conversation contains multiple messages from user and AI.
    Supports attaching documents and folders as context.
    
    Inherits from BaseModel: automatic soft delete + timestamps + SoftDeleteManager
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='conversations',
        help_text="User who owns this conversation"
    )
    title = models.CharField(
        max_length=255,
        help_text="Conversation title (auto-generated from first message)"
    )
    summary = models.TextField(
        null=True,
        blank=True,
        help_text="AI-generated summary of conversation"
    )

    class Meta:
        db_table = "conversations"
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        indexes = [
            models.Index(fields=['account_id', 'updated_at'], name='idx_conversations_user_updated'),
            models.Index(fields=['created_at'], name='idx_conversations_created_at'),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.title} ({self.account.username})"


class ConversationAttachedDocument(BaseModel):
    """
    M2M model: Links documents to conversations.
    Allows constraining AI search to specific documents.
    
    Inherits from BaseModel for soft delete support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='attached_documents',
        help_text="Conversation"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversation_attachments',
        help_text="Attached document"
    )

    class Meta:
        db_table = "conversations_attached_documents"
        verbose_name = "Conversation Attached Document"
        verbose_name_plural = "Conversation Attached Documents"
        unique_together = [['conversation', 'document']]
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['document_id']),
        ]

    def __str__(self):
        return f"{self.conversation.title} → {self.document.original_name if self.document else 'deleted'}"


class ConversationAttachedFolder(BaseModel):
    """
    M2M model: Links folders to conversations.
    Allows constraining AI search to specific folders.
    
    Inherits from BaseModel for soft delete support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='attached_folders',
        help_text="Conversation"
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversation_attachments',
        help_text="Attached folder"
    )

    class Meta:
        db_table = "conversations_attached_folders"
        verbose_name = "Conversation Attached Folder"
        verbose_name_plural = "Conversation Attached Folders"
        unique_together = [['conversation', 'folder']]
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['folder_id']),
        ]

    def __str__(self):
        return f"{self.conversation.title} → {self.folder.name if self.folder else 'deleted'}"


class Message(BaseModel):
    """
    Messages in a conversation.
    Each message has content, role (user/assistant/system), and citations.
    
    Inherits from BaseModel for soft delete support.
    """
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Conversation containing this message"
    )
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='user',
        help_text="Message role (user, assistant, system)"
    )
    content = models.TextField(help_text="Message content (1-10000 characters)")
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of citation objects with chunk info"
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Token count for LLM cost calculation"
    )

    class Meta:
        db_table = "messages"
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        indexes = [
            models.Index(fields=['conversation_id', 'created_at'], name='idx_messages_conv_timestamp'),
            models.Index(fields=['conversation_id'], name='idx_messages_conversation'),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        preview = self.content[:50] if len(self.content) > 50 else self.content
        return f"{self.role.upper()}: {preview}..."


class HumanFeedback(BaseModel):
    """
    User feedback on AI responses.
    Users can upvote/downvote messages to improve model quality.
    
    Inherits from BaseModel for soft delete support.
    """
    RATING_CHOICES = [('upvote', 'Upvote'), ('downvote', 'Downvote')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='feedback',
        help_text="Message being rated"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='feedback_given',
        help_text="User providing feedback"
    )
    rating = models.CharField(
        max_length=50,
        choices=RATING_CHOICES,
        help_text="Rating (upvote or downvote)"
    )
    comment = models.TextField(null=True, blank=True, help_text="Additional feedback comment")

    class Meta:
        db_table = "human_feedback"
        verbose_name = "Human Feedback"
        verbose_name_plural = "Human Feedback"
        unique_together = [['message', 'account']]
        indexes = [
            models.Index(fields=['message_id']),
            models.Index(fields=['account_id']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.account.username} {self.rating} on message {self.message.id}"


class AuditLog(BaseModel):
    """
    System audit logs for compliance and security.
    Records all significant user actions with timestamp, IP, and user agent.
    
    Inherits from BaseModel for soft delete support (compliance requirement).
    """
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE', 'Create'),
        ('UPLOAD', 'Upload'),
        ('DELETE', 'Delete'),
        ('QUERY', 'Query'),
        ('EDIT', 'Edit'),
        ('UPDATE', 'Update'),
        ('DOWNLOAD', 'Download'),
        ('SHARE', 'Share'),
        ('IMPORT', 'Import'),
        ('DELETE_USER', 'Delete User'),
        ('CHANGE_ROLE', 'Change Role'),
        ('CREATE_ROLE', 'Create Role'),
        ('FEEDBACK', 'Feedback'),
        ('GRANT_ACL', 'Grant ACL'),
        ('REVOKE_ACL', 'Revoke ACL'),
        ('MUTATION', 'Mutation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )
    action = models.CharField(
        max_length=100,
        choices=ACTION_CHOICES,
        help_text="Action performed"
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of affected resource (document/folder/user)"
    )
    query_text = models.TextField(
        null=True,
        blank=True,
        help_text="Query text (for QUERY action)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Source IP address"
    )
    user_agent = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="Browser/device user agent"
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=['created_at'], name='idx_audit_logs_timestamp'),
            models.Index(fields=['account_id', 'created_at'], name='idx_audit_acct_time'),
            models.Index(fields=['action']),
            models.Index(fields=['resource_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        user = self.account.username if self.account else "system"
        return f"{self.action} by {user} at {self.created_at}"
    
    @classmethod
    def log_action(cls, account, action, resource_id=None, query_text=None, request=None):
        """
        Helper method để ghi audit log.
        
        Usage:
            AuditLog.log_action(
                account=user,
                action='UPLOAD',
                resource_id=document.id,
                request=request
            )
        """
        ip_address = None
        user_agent = None
        
        if request:
            # Extract IP from request
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Extract user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:1000]
        
        return cls.objects.create(
            account=account,
            action=action,
            resource_id=resource_id,
            query_text=query_text,
            ip_address=ip_address,
            user_agent=user_agent,
        )


class AsyncTask(BaseModel):
    """
    Background task queue for async operations.
    Handles embedding, vector store sync, indexing, and cleanup.
    Supports retry logic with exponential backoff.
    
    Inherits from BaseModel for soft delete support.
    """
    TASK_TYPE_CHOICES = [
        ('EMBED_CHUNK', 'Embed Chunk'),
        ('SYNC_QDRANT', 'Sync Qdrant'),
        ('INDEX_DOCUMENT', 'Index Document'),
        ('CLEANUP', 'Cleanup'),
        ('REGENERATE_CACHE', 'Regenerate Cache'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(
        max_length=100,
        choices=TASK_TYPE_CHOICES,
        help_text="Type of background task"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='async_tasks',
        help_text="Associated document"
    )
    chunk = models.ForeignKey(
        'documents.DocumentChunk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='async_tasks',
        help_text="Associated chunk (if task is chunk-specific)"
    )
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Task input data (content, model, parameters, etc.)"
    )
    status = models.CharField(
        max_length=50,
        default='pending',
        choices=STATUS_CHOICES,
        help_text="Task status"
    )
    priority = models.CharField(
        max_length=20,
        default='normal',
        choices=PRIORITY_CHOICES,
        help_text="Task priority for queue ordering"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts so far"
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum retry attempts"
    )
    scheduled_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When task was created"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When worker started processing"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When task completed successfully"
    )
    failed_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if task failed"
    )
    worker_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="ID of worker processing this task"
    )
    backoff_multiplier = models.FloatField(
        default=2.0,
        help_text="Exponential backoff multiplier for retries"
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to retry this task"
    )

    class Meta:
        db_table = "async_tasks"
        verbose_name = "Async Task"
        verbose_name_plural = "Async Tasks"
        indexes = [
            models.Index(fields=['status', 'priority'], name='idx_async_tasks_status_prio', 
                        condition=models.Q(status__in=['pending', 'retrying'])),
            models.Index(fields=['document_id', 'status']),
            models.Index(fields=['scheduled_at', 'priority']),
            models.Index(fields=['next_retry_at', 'status']),
        ]

    def __str__(self):
        return f"{self.task_type} ({self.status}) - {self.document.original_name}"


class UserDocumentCache(BaseModel):
    """
    Cache of accessible documents for each user.
    Improves performance of RBAC permission checks.
    Cached based on user roles and document permissions.
    
    Inherits from BaseModel for soft delete support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='document_cache',
        help_text="User (account)"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='user_cache_entries',
        help_text="Cached document"
    )
    max_permission = models.CharField(
        max_length=50,
        default='read',
        choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
        help_text="Maximum permission level for this user on this document"
    )
    expires_at = models.DateTimeField(
        help_text="When this cache entry expires"
    )

    class Meta:
        db_table = "user_document_cache"
        verbose_name = "User Document Cache"
        verbose_name_plural = "User Document Cache"
        unique_together = [['account', 'document']]
        indexes = [
            models.Index(fields=['account_id', 'document_id', 'is_deleted']),
            models.Index(fields=['account_id', 'updated_at'], name='idx_cache_user_updated'),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.account.username} → {self.document.original_name} ({self.max_permission})"
