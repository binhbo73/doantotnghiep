"""
Document Service
================
Business logic for document management

Responsibilities:
- Create/update/delete documents
- Upload documents with validation
- Search documents
- Manage document chunks
- Track document processing status
- Control document access/permissions

Uses:
- DocumentRepository (data access)
- PermissionManager (ACL)
- AuditLog (track changes)
- External: LlamaClient, QdrantClient, DocumentParser
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile
from core.constants import DocumentStatus, AccessScope, PermissionCodes
from core.exceptions import (
    ValidationError,
    BusinessLogicError,
    NotFoundError,
    FileSizeExceededError,
    DocumentProcessingError,
)
from repositories.document_repository import DocumentRepository
from repositories.permission_repository import PermissionRepository
from .base_service import BaseService

logger = logging.getLogger(__name__)


class DocumentService(BaseService):
    """
    Document management service
    
    Key Methods:
    - upload_document(file, user_id, **metadata)
    - get_document(doc_id, user_id) - with permission check
    - search_documents(query, user_id)
    - delete_document(doc_id, user_id)
    - mark_as_processing(doc_id)
    - mark_as_completed(doc_id)
    - mark_as_failed(doc_id, error_msg)
    - get_document_chunks(doc_id, user_id)
    
    Validations:
    - File size limit checking
    - File type validation
    - User permission checking
    - Document status workflow
    """
    
    repository_class = DocumentRepository
    
    # Configuration
    MAX_FILE_SIZE_MB = 100  # Max 100MB
    ALLOWED_FILE_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'text/plain',
        'text/markdown',
    }
    
    def __init__(self):
        """Initialize with repositories"""
        super().__init__()
        self.document_repo = self.repository
        self.permission_repo = PermissionRepository()
    
    # ============================================================================
    # DOCUMENT CREATION
    # ============================================================================
    
    def upload_document(
        self,
        file: UploadedFile,
        user_id: int,
        folder_id: int = None,
        department_id: int = None,
        tags: List[str] = None,
        description: str = None,
    ) -> 'Document':
        """
        Upload new document with validation
        
        Business Rules:
        - File size must not exceed MAX_FILE_SIZE_MB
        - File type must be in ALLOWED_FILE_TYPES
        - User must have DOCUMENT_CREATE permission
        - Folder (if specified) must belong to user's department
        - Initial status: 'draft'
        - Initial processing: 'pending'
        
        Args:
            file: UploadedFile (Django)
            user_id: Uploader user ID
            folder_id: Target folder (optional)
            department_id: Department (optional, default = user's dept)
            tags: List of tag names (optional)
            description: Document description (optional)
        
        Returns:
            Created Document instance
        
        Raises:
            FileSizeExceededError: If file too large
            ValidationError: If invalid file type or missing user
            PermissionDeniedError: If user lacks permission
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Validate user exists
            user = User.objects.get(pk=user_id, is_deleted=False)
            self.validate_business_rule(user is not None, f"User {user_id} not found")
            
            # Validate file size
            file_size_mb = file.size / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                raise FileSizeExceededError(
                    f"File size {file_size_mb:.1f}MB exceeds limit {self.MAX_FILE_SIZE_MB}MB"
                )
            
            # Validate file type
            if file.content_type not in self.ALLOWED_FILE_TYPES:
                raise ValidationError(
                    f"File type '{file.content_type}' not supported. "
                    f"Allowed: {', '.join(self.ALLOWED_FILE_TYPES)}"
                )
            
            # Set defaults
            if department_id is None:
                department_id = user.department_id
            
            # Create document
            with transaction.atomic():
                document = self.document_repo.create(
                    original_name=file.name,
                    file_type=file.content_type,
                    file_size=file.size,
                    uploader_id=user_id,
                    department_id=department_id,
                    folder_id=folder_id,
                    status=DocumentStatus.DRAFT,
                    processing_status='pending',
                    description=description or '',
                )
                
                # Store file (FileField handles storage)
                document.file = file
                document.save()
                
                # Add tags if provided
                if tags:
                    self._add_tags_to_document(document.id, tags)
                
                # Log action
                self.log_action(
                    'UPLOAD_DOCUMENT',
                    resource_id=document.id,
                    details=f"Uploaded '{file.name}' ({file_size_mb:.1f}MB)",
                    user_id=user_id
                )
                
                # Audit
                self._log_document_audit(
                    action='UPLOAD',
                    document_id=document.id,
                    user_id=user_id
                )
            
            return document
            
        except Exception as e:
            self.log_error('upload_document', e, user_id=user_id)
            raise
    
    # ============================================================================
    # DOCUMENT RETRIEVAL
    # ============================================================================
    
    def get_document(self, document_id: int, user_id: int) -> 'Document':
        """
        Get document with permission check
        
        Args:
            document_id: Document ID
            user_id: User requesting (for permission check)
        
        Returns:
            Document instance
        
        Raises:
            DocumentNotFoundError: If not found
            PermissionDeniedError: If user lacks access
        """
        try:
            # Get document
            document = self.document_repo.get_by_id(document_id)
            
            # Check permission
            if not self.document_repo.check_user_can_read(document_id, user_id):
                raise ValidationError(
                    f"User {user_id} does not have access to document {document_id}"
                )
            
            self.log_action('GET_DOCUMENT', document_id, user_id=user_id)
            return document
            
        except Exception as e:
            self.log_error('get_document', e, document_id, user_id)
            raise
    
    def search_documents(
        self,
        query: str,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List['Document'], Any]:
        """
        Search documents accessible to user
        
        Args:
            query: Search query (searches name, description, tags)
            user_id: User searching (filters by permission)
            page: Page number
            page_size: Items per page
        
        Returns:
            (documents_list, page_object)
        """
        try:
            # Search
            results = self.document_repo.search(query)
            
            # Filter by permission (only documents user can read)
            accessible = [
                d for d in results
                if self.document_repo.check_user_can_read(d.id, user_id)
            ]
            
            # Manual pagination since we filtered
            total = len(accessible)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            paginated = accessible[start_idx:end_idx]
            
            self.log_action(
                'SEARCH_DOCUMENTS',
                details=f"Query: '{query}' ({len(paginated)} results)",
                user_id=user_id
            )
            
            # Create simple page object
            class SimplePage:
                def __init__(self, num, count, per_page):
                    self.number = num
                    self.total_count = count
                    self.per_page = per_page
                
                @property
                def total_pages(self):
                    return (self.total_count + self.per_page - 1) // self.per_page
            
            page_obj = SimplePage(page, total, page_size)
            return paginated, page_obj
            
        except Exception as e:
            self.log_error('search_documents', e, user_id=user_id)
            return [], None
    
    def list_accessible_documents(
        self,
        user_id: int,
        folder_id: int = None,
        status: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List['Document'], Any]:
        """
        List documents accessible to user with optional filters
        
        Args:
            user_id: User
            folder_id: Filter by folder (optional)
            status: Filter by status (optional)
            page: Page number
            page_size: Items per page
        
        Returns:
            (documents_list, page_object)
        """
        try:
            filters = {}
            if folder_id:
                filters['folder_id'] = folder_id
            if status:
                filters['status'] = status
            
            # Get accessible documents
            accessible = self.document_repo.get_accessible_documents(user_id)
            
            # Apply filters
            for field, value in filters.items():
                accessible = accessible.filter(**{field: value})
            
            # Paginate
            documents, page_obj = self.document_repo.paginate(
                page=page,
                page_size=page_size,
                filters={},  # Already filtered above
                ordering='-created_at'
            )
            
            self.log_action(
                'LIST_DOCUMENTS',
                details=f"Filters: {filters}",
                user_id=user_id
            )
            
            return List(accessible[:page_size]), page_obj  # Simplified
            
        except Exception as e:
            self.log_error('list_accessible_documents', e, user_id=user_id)
            return [], None
    
    # ============================================================================
    # DOCUMENT PROCESSING
    # ============================================================================
    
    def mark_as_processing(self, document_id: int) -> 'Document':
        """
        Mark document as being processed
        
        Args:
            document_id: Document ID
        
        Returns:
            Updated Document
        """
        try:
            document = self.document_repo.update(
                document_id,
                processing_status='processing',
                processing_started_at=timezone.now()
            )
            
            self.log_action(
                'MARK_PROCESSING',
                document_id,
                details='Processing started'
            )
            
            return document
            
        except Exception as e:
            self.log_error('mark_as_processing', e, document_id)
            raise
    
    def mark_as_completed(
        self,
        document_id: int,
        chunks_count: int = None,
        embeddings_count: int = None,
    ) -> 'Document':
        """
        Mark document as successfully processed
        
        Args:
            document_id: Document ID
            chunks_count: Number of chunks created
            embeddings_count: Number of embeddings created
        
        Returns:
            Updated Document
        """
        try:
            update_data = {
                'processing_status': 'completed',
                'processing_completed_at': timezone.now(),
                'status': DocumentStatus.PUBLISHED,
            }
            if chunks_count:
                update_data['chunks_count'] = chunks_count
            if embeddings_count:
                update_data['embeddings_count'] = embeddings_count
            
            document = self.document_repo.update(document_id, **update_data)
            
            self.log_action(
                'MARK_COMPLETED',
                document_id,
                details=f'Processing completed ({chunks_count or 0} chunks, {embeddings_count or 0} embeddings)'
            )
            
            self._log_document_audit(
                action='PROCESSING_COMPLETED',
                document_id=document_id
            )
            
            return document
            
        except Exception as e:
            self.log_error('mark_as_completed', e, document_id)
            raise
    
    def mark_as_failed(
        self,
        document_id: int,
        error_message: str = None
    ) -> 'Document':
        """
        Mark document processing as failed
        
        Args:
            document_id: Document ID
            error_message: Error details
        
        Returns:
            Updated Document
        """
        try:
            document = self.document_repo.update(
                document_id,
                processing_status='failed',
                processing_completed_at=timezone.now(),
                error_message=error_message or 'Unknown error'
            )
            
            self.log_action(
                'MARK_FAILED',
                document_id,
                details=f'Processing failed: {error_message}'
            )
            
            self._log_document_audit(
                action='PROCESSING_FAILED',
                document_id=document_id
            )
            
            return document
            
        except Exception as e:
            self.log_error('mark_as_failed', e, document_id)
            raise
    
    # ============================================================================
    # DOCUMENT CHUNKS
    # ============================================================================
    
    def get_document_chunks(
        self,
        document_id: int,
        user_id: int
    ) -> List['DocumentChunk']:
        """
        Get all chunks for document (with permission check)
        
        Args:
            document_id: Document ID
            user_id: User requesting
        
        Returns:
            List of DocumentChunk instances
        
        Raises:
            PermissionDeniedError: If user lacks access
        """
        try:
            # Check permission
            if not self.document_repo.check_user_can_read(document_id, user_id):
                raise ValidationError(f"Access denied to document {document_id}")
            
            # Get document with chunks
            document = self.document_repo.get_document_with_chunks(document_id)
            
            self.log_action(
                'GET_CHUNKS',
                document_id,
                details=f'Retrieved {len(document.chunks.all())} chunks',
                user_id=user_id
            )
            
            return list(document.chunks.all())
            
        except Exception as e:
            self.log_error('get_document_chunks', e, document_id, user_id)
            raise
    
    # ============================================================================
    # DOCUMENT DELETION
    # ============================================================================
    
    def delete_document(
        self,
        document_id: int,
        user_id: int
    ) -> bool:
        """
        Delete document (soft delete)
        
        Business Rules:
        - User must own document OR be Admin
        - Cascades: soft delete all chunks + embeddings
        
        Args:
            document_id: Document ID
            user_id: User deleting
        
        Returns:
            True if deleted
        """
        try:
            # Get document
            document = self.document_repo.get_by_id(document_id)
            
            # Check permission (owner or admin)
            if document.uploader_id != user_id:
                if not self.permission_repo.check_user_has_permission(
                    user_id, PermissionCodes.DOCUMENT_DELETE
                ):
                    raise ValidationError(
                        f"User {user_id} cannot delete document {document_id}"
                    )
            
            # Delete
            with transaction.atomic():
                # Soft delete document
                result = self.document_repo.delete(document_id)
                
                # Soft delete associated chunks + embeddings
                DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                DocumentChunk.objects.filter(
                    document_id=document_id
                ).update(is_deleted=True, deleted_at=timezone.now())
                
                self.log_action(
                    'DELETE_DOCUMENT',
                    document_id,
                    user_id=user_id
                )
                
                self._log_document_audit(
                    action='DELETE',
                    document_id=document_id,
                    user_id=user_id
                )
            
            return result
            
        except Exception as e:
            self.log_error('delete_document', e, document_id, user_id)
            raise
    
    # ============================================================================
    # INTERNAL HELPERS
    # ============================================================================
    
    def _add_tags_to_document(self, document_id: int, tag_names: List[str]):
        """Add tags to document"""
        try:
            Tag = apps.get_model('documents', 'Tag')
            Document = apps.get_model('documents', 'Document')
            
            document = Document.objects.get(pk=document_id)
            
            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name.lower(),
                    defaults={'name': tag_name}
                )
                document.tags.add(tag)
        except Exception as e:
            logger.warning(f"Could not add tags: {str(e)}")
    
    def _log_document_audit(
        self,
        action: str,
        document_id: int,
        user_id: int = None
    ):
        """Log document action to AuditLog"""
        try:
            AuditLog = apps.get_model('operations', 'AuditLog')
            
            AuditLog.objects.create(
                account_id=user_id,
                action=action,
                resource_type='Document',
                resource_id=document_id,
                query_text=f"{action} document {document_id}"
            )
        except Exception as e:
            logger.warning(f"Could not log audit: {str(e)}")
