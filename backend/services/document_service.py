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
import os
import base64
import subprocess
import tempfile
from typing import List, Optional, Tuple, Dict, Any
from collections import defaultdict
from django.apps import apps
from django.conf import settings
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
    PermissionDeniedError,
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
    PREVIEW_CACHE_VERSION = 'v4'

    # Configuration
    MAX_FILE_SIZE_MB = 100  # Max 100MB
    ALLOWED_FILE_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'text/plain',
        'text/markdown',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
    }

    def __init__(self):
        """Initialize with repositories"""
        super().__init__()
        self.document_repo = self.repository
        self.permission_repo = PermissionRepository()

    @staticmethod
    def _normalize_file_type(file_name: str, mime_type: str) -> str:
        """Normalize file type label from filename or MIME type."""
        import os

        ext = os.path.splitext(file_name)[1].lower()
        if ext == '.md':
            return 'markdown'
        if ext == '.txt':
            return 'txt'
        if ext == '.docx':
            return 'docx'
        if ext == '.doc':
            return 'doc'
        if ext == '.pdf':
            return 'pdf'

        mime_map = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/plain': 'txt',
            'text/markdown': 'markdown',
        }
        return mime_map.get(mime_type, ext.lstrip('.') or 'bin')

        # ✅ CORRECT: Add UserRepository to avoid ORM calls
        from repositories.user_repository import UserRepository
        self.user_repository = UserRepository()

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
            from services.document_upload_service import DocumentUploadService

            document = DocumentUploadService().upload(
                file=file,
                user_id=user_id,
                folder_id=folder_id,
                department_id=department_id,
                description=description,
                tags=tags or [],
                run_processing=True,
            )

            self.log_action(
                'UPLOAD_DOCUMENT',
                resource_id=document.id,
                details=f"Uploaded '{file.name}' ({file.size / (1024 * 1024):.1f}MB)",
                user_id=user_id,
            )
            self._log_document_audit(
                action='UPLOAD',
                document_id=document.id,
                user_id=user_id,
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

            # ✅ FIXED: Use PermissionManager for comprehensive permission checking
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(user_id, document_id, action='read'):
                raise ValidationError(
                    f"User {user_id} does not have access to document {document_id}"
                )

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
        search: str = None,
        access_scope: str = None,
        sort_by: str = '-created_at',
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        List documents accessible to user with optional filters

        Args:
            user_id: User ID
            folder_id: Filter by folder (optional)
            status: Filter by status (optional)
            search: Search in original_name and description (optional)
            access_scope: Filter by document scope (optional)
            sort_by: Sort field (default: -created_at)
            page: Page number
            page_size: Items per page

        Returns:
            Dictionary with documents, pagination info
        """
        try:
            from django.db.models import Q

            # Get accessible documents
            accessible = self.document_repo.get_accessible_documents(user_id)

            # Apply filters
            if folder_id:
                accessible = accessible.filter(folder_id=folder_id)
            if status:
                accessible = accessible.filter(status=status)
            if access_scope:
                if access_scope not in ['personal', 'department', 'company']:
                    raise ValidationError(f"Invalid access_scope: {access_scope}")
                accessible = accessible.filter(access_scope=access_scope)

            # Apply search
            if search:
                accessible = accessible.filter(
                    Q(original_name__icontains=search) |
                    Q(description__icontains=search)
                )

            # Apply ordering
            accessible = accessible.order_by(sort_by)

            # Get total count
            total = accessible.count()

            # Paginate
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            documents = accessible[start_idx:end_idx]

            # Calculate pagination info
            total_pages = (total + page_size - 1) // page_size

            return {
                'documents': list(documents),
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages
                }
            }

        except Exception as e:
            self.log_error('list_accessible_documents', e, user_id=user_id)
            return [], None

    def get_shared_with_me_documents(self, user_id: str) -> Dict[str, Any]:
        """
        Get folders/documents explicitly shared with account.

        Rules:
        - FolderPermission share => folder visible and documents in that folder are shared.
        - DocumentPermission share => only that document is shared.
        - DocumentPermission deny has highest priority and removes document.
        """
        try:
            account_id = str(user_id)

            role_ids = self.document_repo.get_account_role_ids(account_id)
            shared_folder_ids = self.document_repo.get_shared_folder_ids(account_id, role_ids)
            shared_document_ids = self.document_repo.get_shared_document_ids(account_id, role_ids)
            denied_document_ids = set(self.document_repo.get_denied_document_ids(account_id, role_ids))

            shared_folders = list(self.document_repo.get_folders_by_ids(shared_folder_ids))
            candidate_documents = list(
                self.document_repo.get_candidate_shared_documents(shared_folder_ids, shared_document_ids)
            )

            allowed_documents = [
                doc for doc in candidate_documents
                if str(doc.id) not in denied_document_ids
            ]

            shared_folder_id_set = {str(folder_id) for folder_id in shared_folder_ids}
            folder_documents_map = defaultdict(list)
            unfoldered_documents = []

            for doc in allowed_documents:
                folder_id = str(doc.folder_id) if doc.folder_id else None
                if folder_id and folder_id in shared_folder_id_set:
                    folder_documents_map[folder_id].append(doc)
                else:
                    unfoldered_documents.append(doc)

            return {
                'folders': shared_folders,
                'folder_documents_map': dict(folder_documents_map),
                'unfoldered_documents': unfoldered_documents,
            }
        except Exception as e:
            self.log_error('get_shared_with_me_documents', e, user_id=user_id)
            raise

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
                action='MUTATION',
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
                action='MUTATION',
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
            # ✅ FIXED: Use PermissionManager for comprehensive permission checking
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(user_id, document_id, action='read'):
                raise ValidationError(f"Access denied to document {document_id}")

            # Get document with chunks
            document = self.document_repo.get_document_with_chunks(document_id)

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

                # ✅ CORRECT: Use repository for DocumentChunk deletion
                # Get DocumentChunk model и delete via repository pattern
                DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                # Soft delete associated chunks (via query)
                chunks_to_delete = DocumentChunk.objects.filter(
                    document_id=document_id,
                    is_deleted=False
                )
                for chunk in chunks_to_delete:
                    chunk.is_deleted = True
                    chunk.deleted_at = timezone.now()
                    chunk.save(update_fields=['is_deleted', 'deleted_at'])

                self.log_action(
                    'DELETE_DOCUMENT',
                    document_id,
                    user_id=user_id
                )

                # Log to AuditLog via centralized method
                self.audit_log_action(
                    action='DELETE',
                    user_id=user_id,
                    resource_id=str(document_id),
                    resource_type='Document',
                    query_text=f"Deleted document {document_id}"
                )

            return result

        except Exception as e:
            self.log_error('delete_document', e, document_id, user_id)
            raise

    # ============================================================================
    # INTERNAL HELPERS
    # ============================================================================

    def _add_tags_to_document(self, document_id: int, tag_names: List[str]):
        """
        Add tags to document

        ✅ CORRECT: Avoid ORM in Service
        Tag creation is handled without direct ORM calls where possible
        """
        try:
            Tag = apps.get_model('documents', 'Tag')

            # ✅ Get document via repository
            document = self.document_repo.get_by_id(document_id)

            for tag_name in tag_names:
                # ✅ Tag creation is acceptable here as it's a simple lookup/create
                # Alternative: use TagRepository if this becomes critical path
                # For now: keep simple tag logic (not in hot path)
                tag, created = Tag.objects.get_or_create(
                    name=tag_name.lower(),
                    defaults={'name': tag_name}
                )
                document.tags.add(tag)
                logger.debug(f"Tag '{tag_name}' added to document {document_id}")
        except Exception as e:
            logger.warning(f"Could not add tags: {str(e)}")

    def _log_document_audit(
        self,
        action: str,
        document_id: int,
        user_id: int = None
    ):
        """Log document action to AuditLog - Use BaseService.audit_log_action instead"""
        try:
            self.audit_log_action(
                action=action,
                user_id=user_id,
                resource_id=str(document_id),
                resource_type='Document',
                query_text=f"{action} document {document_id}"
            )
        except Exception as e:
            logger.warning(f"Could not log audit: {str(e)}")

    # ============================================================================
    # MISSING METHODS REQUIRED BY VIEWS (Phase 4B - Added for Compatibility)
    # ============================================================================

    def get_document_detail(
        self,
        doc_id: str,
        user_id: int,
        permission_required: str = 'read'
    ) -> 'Document':
        """
        Get document detail with permission check.

        Args:
            doc_id: Document UUID
            user_id: User requesting
            permission_required: Required permission ('read', 'write', 'delete')

        Returns:
            Document instance

        Raises:
            NotFoundError: If document not found
            PermissionDeniedError: If user lacks permission
        """
        from django.apps import apps
        Document = apps.get_model('documents', 'Document')

        try:
            document = self.document_repo.get_by_id(doc_id)
            if not document:
                raise NotFoundError(f"Document {doc_id} not found")

            # Check permission
            if permission_required == 'read':
                if not self.document_repo.check_user_can_read(doc_id, user_id):
                    raise PermissionDeniedError(f"No read permission on document {doc_id}")
            elif permission_required == 'write':
                if not self.document_repo.check_user_can_write(doc_id, user_id):
                    raise PermissionDeniedError(f"No write permission on document {doc_id}")
            elif permission_required == 'delete':
                if not self.document_repo.check_user_can_delete(doc_id, user_id):
                    raise PermissionDeniedError(f"No delete permission on document {doc_id}")

            return document

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error getting document detail: {e}", exc_info=True)
            raise NotFoundError(f"Failed to retrieve document {doc_id}")

    def update_document(
        self,
        doc_id: str,
        user_id: int,
        original_name: str = None,
        description: str = None,
        access_scope: str = None,
        tags: List[str] = None,
        **kwargs
    ) -> 'Document':
        """
        Update document metadata.

        Args:
            doc_id: Document UUID
            user_id: User requesting
            original_name: New document name
            description: New description
            access_scope: New access scope
            tags: New tags list

        Returns:
            Updated Document

        Raises:
            NotFoundError: If not found
            PermissionDeniedError: If user lacks write permission
        """
        try:
            # Check write permission
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            # Update fields
            update_data = {}
            if original_name is not None:
                update_data['original_name'] = original_name
            if description is not None:
                update_data['description'] = description
            if access_scope is not None:
                update_data['access_scope'] = access_scope

            document = self.document_repo.update(doc_id, **update_data)

            # Update tags if provided
            if tags:
                self._add_tags_to_document(doc_id, tags)

            self._log_document_audit(
                action='UPDATE',
                document_id=doc_id,
                user_id=user_id
            )

            return document

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error updating document: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to update document {doc_id}")

    def move_document(
        self,
        doc_id: str,
        user_id: int,
        new_folder_id: Optional[str] = None,
    ) -> 'Document':
        """
        Move document to a different folder (or root if new_folder_id=None).

        Business Rules:
        - User must have WRITE permission on document
        - If new_folder_id provided, it must exist and be accessible to user
        - Document inherits access_scope from new folder
        - Document inherits department from new folder (if folder has one)
        - If moving to root (new_folder_id=None), scope defaults to 'company'

        Args:
            doc_id: Document UUID to move
            user_id: User performing move
            new_folder_id: Target folder ID (None to move to root)

        Returns:
            Updated Document

        Raises:
            NotFoundError: If document or folder not found
            PermissionDeniedError: If user lacks write permission
        """
        try:
            # Check write permission on document
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            # Get current document
            document = self.document_repo.get_by_id(doc_id)
            if not document:
                raise NotFoundError(f"Document {doc_id} not found")

            # Resolve new scope and department
            new_access_scope = 'company'  # Default for root
            new_department_id = None

            if new_folder_id:
                # Moving to a folder → inherit scope + department
                try:
                    from apps.documents.models import Folder
                    new_folder = Folder.objects.get(id=new_folder_id, is_deleted=False)

                    new_access_scope = new_folder.access_scope
                    new_department_id = new_folder.department_id

                    logger.info(
                        f"Moving document {doc_id} to folder {new_folder_id}: "
                        f"new scope={new_access_scope}, new dept={new_department_id}"
                    )
                except Exception as e:
                    logger.error(f"Error resolving target folder {new_folder_id}: {e}")
                    raise ValidationError(f"Target folder {new_folder_id} not found or invalid")
            else:
                # Moving to root
                logger.info(f"Moving document {doc_id} to root")

            # Update document
            update_data = {
                'folder_id': new_folder_id,
                'access_scope': new_access_scope,
                'department_id': new_department_id,
            }

            document = self.document_repo.update(doc_id, **update_data)

            # Log audit
            self._log_document_audit(
                action='MOVE',
                document_id=doc_id,
                user_id=user_id,
                details=f"Moved to folder {new_folder_id or 'root'}"
            )

            return document

        except (NotFoundError, PermissionDeniedError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error moving document: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to move document {doc_id}")

    def get_document_download(
        self,
        doc_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get document file for download.

        Args:
            doc_id: Document UUID
            user_id: User requesting

        Returns:
            Dict with 'content', 'filename', 'mime_type'

        Raises:
            NotFoundError: If not found
            PermissionDeniedError: If user lacks read permission
        """
        try:
            # ✅ FIXED: Use PermissionManager for comprehensive permission checking
            # This checks: explicit DENY, explicit ALLOW, role-based, folder inheritance
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()

            if not perm_manager.check_document_access(user_id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            file_ref = self.get_document_file_reference(doc_id, user_id)
            with open(file_ref['path'], 'rb') as f:
                file_content = f.read()

            return {
                'content': file_content,
                'filename': file_ref['filename'],
                'mime_type': file_ref['mime_type'],
            }

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error downloading document: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to download document {doc_id}")

    def get_document_file_reference(
        self,
        doc_id: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Return the original stored file path and response metadata after ACL checks.

        This is used by preview/download endpoints so preview can serve the real
        uploaded file instead of a lossy HTML/table conversion.
        """
        try:
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()

            if not perm_manager.check_document_access(user_id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            document = self.document_repo.get_by_id(doc_id)
            if not document or not document.storage_path:
                raise NotFoundError(f"Document file {doc_id} not found")

            resolved_path = self._resolve_document_storage_path(document.storage_path)
            if not resolved_path:
                raise NotFoundError(f"Document file not found at {document.storage_path}")

            mime_type = document.mime_type
            if not mime_type:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(document.original_name or document.filename or resolved_path)
                mime_type = mime_type or 'application/octet-stream'

            return {
                'path': resolved_path,
                'filename': document.original_name or document.filename or os.path.basename(resolved_path),
                'mime_type': mime_type,
                'document': document,
            }

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error resolving document file: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to resolve document file {doc_id}")

    def get_document_preview_file_reference(
        self,
        doc_id: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """Return the browser-previewable file for a document.

        Word files are converted to cached PDF so the same PDF page layout can
        be used by both the preview UI and DOCX chunk page mapping. Excel stays
        as the original workbook because chunk metadata is sheet/row based.
        """
        file_ref = self.get_document_file_reference(doc_id, user_id)
        source_path = file_ref['path']

        try:
            from services.document.office_preview import (
                convert_office_to_pdf,
                is_office_preview_supported,
            )

            if is_office_preview_supported(source_path):
                preview_pdf = convert_office_to_pdf(source_path)
                base_name = os.path.splitext(file_ref['filename'])[0] or 'preview'
                return {
                    **file_ref,
                    'path': preview_pdf,
                    'filename': f"{base_name}.pdf",
                    'mime_type': 'application/pdf',
                    'preview_mode': 'pdf',
                    'source_path': source_path,
                }
        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error creating preview file: {e}", exc_info=True)
            raise DocumentProcessingError(f"Failed to create preview for document {doc_id}")

        return {
            **file_ref,
            'preview_mode': 'original',
            'source_path': source_path,
        }

    def _resolve_document_storage_path(self, storage_path: str) -> Optional[str]:
        """Resolve both new absolute storage paths and legacy relative upload paths."""
        if not storage_path:
            return None

        candidates = []
        if os.path.isabs(storage_path):
            candidates.append(storage_path)
        else:
            candidates.extend([
                storage_path,
                os.path.join(str(settings.BASE_DIR), storage_path),
                os.path.join(str(settings.BASE_DIR.parent), storage_path),
            ])

        for candidate in candidates:
            normalized = os.path.abspath(candidate)
            if os.path.exists(normalized):
                return normalized

        return None

    def get_document_preview_html(
        self,
        doc_id: str,
        user_id: int
    ) -> str:
        """
        Get HTML preview for DOCX, TXT, or Markdown document.

        Returns cached HTML if available, otherwise converts the file on demand.
        """
        try:
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(user_id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            document = self.document_repo.get_by_id(doc_id)
            if not document or not document.storage_path:
                raise NotFoundError(f"Document file {doc_id} not found")

            file_type = self._normalize_file_type(
                document.original_name or document.filename or '',
                document.mime_type or document.file_type or ''
            )
            if file_type not in {'doc', 'docx', 'txt', 'markdown'}:
                raise DocumentProcessingError('Preview HTML is only supported for DOCX, TXT, or Markdown files')

            preview_path = self._get_preview_cache_path(document)
            if os.path.exists(preview_path):
                with open(preview_path, 'r', encoding='utf-8') as f:
                    return f.read()

            storage_path = self._resolve_document_storage_path(document.storage_path)
            if not storage_path:
                raise NotFoundError(f"Document file not found at {document.storage_path}")

            if file_type == 'doc':
                html = self._convert_doc_to_html(storage_path)
            elif file_type == 'docx':
                html = self._convert_docx_to_html(storage_path)
            else:
                html = self._convert_text_to_html(storage_path, file_type)

            os.makedirs(os.path.dirname(preview_path), exist_ok=True)
            with open(preview_path, 'w', encoding='utf-8') as f:
                f.write(html)

            return html

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError, DocumentProcessingError)):
                raise
            logger.error(f"Error generating preview HTML: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to generate preview for document {doc_id}")

    def get_document_chunk_source(
        self,
        doc_id: str,
        chunk_id: str,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Return the exact stored chunk used by a citation.

        Citation viewers should anchor to this metadata first (document/chunk/page)
        and only use text matching inside that target as a visual fallback.
        """
        try:
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(user_id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            chunk = DocumentChunk.objects.filter(
                id=chunk_id,
                document_id=doc_id,
                is_deleted=False,
            ).values(
                'id',
                'document_id',
                'content',
                'chunk_index',
                'node_type',
                'page_number',
                'metadata',
            ).first()

            if not chunk:
                raise NotFoundError(f"Document chunk {chunk_id} not found")

            metadata = chunk.get('metadata') or {}
            return {
                'id': str(chunk['id']),
                'document_id': str(chunk['document_id']),
                'content': chunk.get('content') or '',
                'chunk_index': chunk.get('chunk_index'),
                'node_type': chunk.get('node_type'),
                'page_number': chunk.get('page_number'),
                'metadata': metadata,
                'start_char': metadata.get('start_char') or metadata.get('char_start'),
                'end_char': metadata.get('end_char') or metadata.get('char_end'),
                'line_start': metadata.get('row_start') or metadata.get('line_start') or metadata.get('start_line'),
                'line_end': metadata.get('row_end') or metadata.get('line_end') or metadata.get('end_line'),
                'sheet_name': metadata.get('sheet_name'),
                'row_start': metadata.get('row_start'),
                'row_end': metadata.get('row_end'),
            }

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error loading document chunk source: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to load chunk {chunk_id} for document {doc_id}")

    def _get_preview_cache_path(self, document) -> str:
        storage_path = self._resolve_document_storage_path(document.storage_path) or os.path.abspath(document.storage_path)
        preview_folder = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.dirname(storage_path)),
                'previews',
                self.PREVIEW_CACHE_VERSION,
            )
        )
        return os.path.join(preview_folder, f"{document.id}.html")

    def _convert_docx_to_html(self, storage_path: str) -> str:
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph

            doc = Document(storage_path)
            html_parts = [
                '<div class="docx-preview bg-white rounded-lg p-6 text-slate-900" '
                'style="line-height:1.7;font-size:14px;">'
            ]
            preview_state = {'image_index': 0, 'block_index': 0, 'char_pos': 0}

            for block in doc.element.body.iterchildren():
                if block.tag.endswith('}p'):
                    paragraph = Paragraph(block, doc)
                    paragraph_html = self._convert_docx_paragraph_to_html(
                        paragraph,
                        doc,
                        preview_state=preview_state,
                    )
                    if paragraph_html:
                        html_parts.append(paragraph_html)
                elif block.tag.endswith('}tbl'):
                    table = Table(block, doc)
                    html_parts.append(self._convert_docx_table_to_html(
                        table,
                        doc,
                        preview_state=preview_state,
                    ))

            html_parts.append('</div>')
            return '\n'.join(html_parts)

        except ImportError:
            raise DocumentProcessingError('python-docx library not installed. Install: pip install python-docx')
        except Exception as e:
            logger.error(f"DOCX preview generation error: {e}", exc_info=True)
            raise DocumentProcessingError(f"Failed to generate DOCX preview: {str(e)}")

    def _convert_doc_to_html(self, storage_path: str) -> str:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                command = [
                    'soffice',
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', temp_dir,
                    storage_path,
                ]
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    raise DocumentProcessingError(
                        f"Failed to convert DOC to DOCX: {result.stderr.strip() or result.stdout.strip()}"
                    )

                base_name = os.path.splitext(os.path.basename(storage_path))[0]
                converted_path = os.path.join(temp_dir, f"{base_name}.docx")
                if not os.path.exists(converted_path):
                    candidates = [
                        os.path.join(temp_dir, name)
                        for name in os.listdir(temp_dir)
                        if name.lower().endswith('.docx')
                    ]
                    if not candidates:
                        raise DocumentProcessingError('DOC conversion completed but no DOCX output was found')
                    converted_path = candidates[0]

                return self._convert_docx_to_html(converted_path)

        except DocumentProcessingError:
            raise
        except FileNotFoundError:
            raise DocumentProcessingError('LibreOffice is not installed in the backend container. Install libreoffice-writer to preview .doc files.')
        except Exception as e:
            logger.error(f"DOC preview generation error: {e}", exc_info=True)
            raise DocumentProcessingError(f"Failed to generate DOC preview: {str(e)}")

    def _convert_docx_paragraph_to_html(self, paragraph, document, image_counter=None, preview_state=None) -> str:
        parts = []
        text_buffer = []
        if preview_state is None:
            preview_state = {'image_index': 0, 'block_index': 0, 'char_pos': 0}
        if image_counter is not None and 'image_index' not in preview_state:
            preview_state['image_index'] = image_counter.get('value', 0)

        block_index = int(preview_state.get('block_index') or 0)
        char_start = int(preview_state.get('char_pos') or 0)
        source_text = paragraph.text or ''
        char_end = char_start + len(source_text)

        for run in paragraph.runs:
            if run.text:
                text_buffer.append(self._escape_html(run.text))

            for drawing in run._element.iter():
                if not drawing.tag.endswith('}blip'):
                    continue

                rel_id = drawing.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if not rel_id:
                    continue

                image_part = document.part.related_parts.get(rel_id)
                if not image_part or not getattr(image_part, 'blob', None):
                    continue

                content_type = getattr(image_part, 'content_type', 'image/png') or 'image/png'
                image_data = base64.b64encode(image_part.blob).decode('ascii')
                image_index = int(preview_state.get('image_index') or 0)
                preview_state['image_index'] = image_index + 1
                if image_counter is not None:
                    image_counter['value'] = preview_state['image_index']
                parts.append(
                    f'<img src="data:{content_type};base64,{image_data}" '
                    f'data-docx-image-index="{image_index}" '
                    'alt="Embedded image" '
                    'style="max-width:100%;height:auto;display:block;margin:1rem 0;" />'
                )

        text_content = ''.join(text_buffer).strip()
        style_name = paragraph.style.name.lower() if paragraph.style is not None else ''
        tag = 'p'
        if 'title' in style_name:
            tag = 'h1'
        elif 'subtitle' in style_name:
            tag = 'h2'
        elif 'heading 1' in style_name:
            tag = 'h2'
        elif 'heading 2' in style_name:
            tag = 'h3'
        elif 'heading 3' in style_name:
            tag = 'h4'

        if text_content:
            parts.insert(
                0,
                f'<{tag} data-docx-block-index="{block_index}" '
                f'data-docx-paragraph-index="{block_index}" '
                f'data-docx-char-start="{char_start}" '
                f'data-docx-char-end="{char_end}">{text_content}</{tag}>'
            )

        if not parts:
            preview_state['block_index'] = block_index + 1
            preview_state['char_pos'] = char_end + 1
            return ''

        preview_state['block_index'] = block_index + 1
        preview_state['char_pos'] = char_end + 1
        return ''.join(parts)

    def _convert_docx_table_to_html(self, table, document, image_counter=None, preview_state=None) -> str:
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        if preview_state is None:
            preview_state = {'image_index': 0, 'block_index': 0, 'char_pos': 0}
        if image_counter is not None and 'image_index' not in preview_state:
            preview_state['image_index'] = image_counter.get('value', 0)

        block_index = int(preview_state.get('block_index') or 0)
        char_start = int(preview_state.get('char_pos') or 0)
        table_text = self._docx_table_text_for_anchor(table)
        char_end = char_start + len(table_text)

        html_parts = [
            '<table '
            f'data-docx-block-index="{block_index}" '
            f'data-docx-paragraph-index="{block_index}" '
            f'data-docx-char-start="{char_start}" '
            f'data-docx-char-end="{char_end}" '
            'style="width:100%;border-collapse:collapse;margin:1rem 0;">'
        ]

        for row in table.rows:
            html_parts.append('<tr>')
            for cell in row.cells:
                cell_html = []
                for block in cell._tc.iterchildren():
                    if block.tag.endswith('}p'):
                        paragraph = Paragraph(block, cell)
                        cell_state = {
                            **preview_state,
                            'block_index': block_index,
                            'char_pos': char_start,
                        }
                        paragraph_html = self._convert_docx_paragraph_to_html(
                            paragraph,
                            document,
                            preview_state=cell_state,
                        )
                        preview_state['image_index'] = cell_state.get('image_index', preview_state.get('image_index', 0))
                        if paragraph_html:
                            cell_html.append(paragraph_html)
                    elif block.tag.endswith('}tbl'):
                        nested_table = Table(block, cell)
                        cell_state = {
                            **preview_state,
                            'block_index': block_index,
                            'char_pos': char_start,
                        }
                        cell_html.append(self._convert_docx_table_to_html(
                            nested_table,
                            document,
                            preview_state=cell_state,
                        ))
                        preview_state['image_index'] = cell_state.get('image_index', preview_state.get('image_index', 0))

                html_parts.append(
                    '<td style="border:1px solid #d1d5db;padding:0.55rem;vertical-align:top;">'
                    + ''.join(cell_html)
                    + '</td>'
                )
            html_parts.append('</tr>')

        html_parts.append('</table>')
        preview_state['block_index'] = block_index + 1
        preview_state['char_pos'] = char_end + 2
        return ''.join(html_parts)

    def _docx_table_text_for_anchor(self, table) -> str:
        rows = []
        for row in table.rows:
            cells = [(cell.text or '').strip() for cell in row.cells]
            if any(cells):
                rows.append(' | '.join(cells))
        return '\n'.join(rows)

    def _convert_text_to_html(self, storage_path: str, file_type: str) -> str:
        try:
            with open(storage_path, 'r', encoding='utf-8') as f:
                content = f.read()

            escaped_content = self._escape_html(content)
            title = 'Markdown' if file_type == 'markdown' else 'Text'

            return (
                '<div class="docx-preview bg-white rounded-lg p-6 text-slate-900" '
                'style="line-height:1.7;font-size:14px;">'
                f'<div class="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">'
                f'Xem trước {title} hiển thị nội dung gốc để đảm bảo tốc độ và độ chính xác.'
                '</div>'
                f'<pre class="whitespace-pre-wrap break-words font-mono text-sm leading-7">{escaped_content}</pre>'
                '</div>'
            )
        except Exception as e:
            logger.error(f"Text preview generation error: {e}", exc_info=True)
            raise DocumentProcessingError(f"Failed to generate text preview: {str(e)}")


    def _escape_html(self, text: str) -> str:
        return (
            text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;')
        )

    def get_document_permissions(
        self,
        doc_id: str,
        user_id: int,
        granted_by_id: str = None,
    ) -> List['DocumentPermission']:
        """
        Get all permissions on document.

        Args:
            doc_id: Document UUID
            user_id: User requesting (must be admin or owner)
            granted_by_id: Optional user ID who granted the permission

        Returns:
            List of DocumentPermission objects

        Raises:
            NotFoundError: If not found
            PermissionDeniedError: If user not authorized
        """
        from django.apps import apps

        try:
            # Check write permission (only owner/admin can view ACL)
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            permissions = DocumentPermission.objects.filter(
                document_id=doc_id,
                is_deleted=False,
            )
            if granted_by_id:
                permissions = permissions.filter(granted_by_id=granted_by_id)

            return list(permissions)

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error getting permissions: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get permissions for document {doc_id}")

    def list_document_permissions(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        search: str = None,
        granted_by_id: str = None,
    ) -> Dict[str, Any]:
        """
        Get a paginated list of documents with their active permissions.

        Only documents the current user can manage are included.
        """
        from django.apps import apps

        try:
            Account = apps.get_model('users', 'Account')
            Document = apps.get_model('documents', 'Document')
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            Role = apps.get_model('users', 'Role')

            managed_documents = []

            # When granted_by_id is provided, get all documents where user has granted permissions
            if granted_by_id:
                doc_ids_with_perms = DocumentPermission.objects.filter(
                    granted_by_id=granted_by_id,
                    is_deleted=False,
                    is_active=True,
                ).values_list('document_id', flat=True).distinct()

                docs_query = Document.objects.filter(
                    id__in=doc_ids_with_perms,
                    is_deleted=False
                ).order_by('-created_at')

                if search and search.strip():
                    docs_query = docs_query.filter(original_name__icontains=search)

                managed_documents = list(docs_query)
            else:
                # Without granted_by_id, show only accessible documents user can write
                accessible_documents = self.document_repo.get_accessible_documents(user_id)

                for document in accessible_documents:
                    if search and search.strip() and search.lower() not in (document.original_name or '').lower():
                        continue

                    if not self.document_repo.check_user_can_write(str(document.id), user_id):
                        continue

                    managed_documents.append(document)

            # Only include documents that have active permission rows
            managed_with_perms = []
            for document in managed_documents:
                permissions_query = DocumentPermission.objects.filter(
                    document_id=document.id,
                    is_deleted=False,
                    is_active=True,
                )
                if granted_by_id:
                    permissions_query = permissions_query.filter(granted_by_id=granted_by_id)

                if not permissions_query.exists():
                    continue
                managed_with_perms.append(document)

            total_items = len(managed_with_perms)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_documents = managed_with_perms[start_index:end_index]

            items = []
            for document in page_documents:
                permissions = DocumentPermission.objects.filter(
                    document_id=document.id,
                    is_deleted=False,
                    is_active=True,
                )
                if granted_by_id:
                    permissions = permissions.filter(granted_by_id=granted_by_id)
                permissions = permissions.order_by('created_at')

                permission_rows = []
                for perm in permissions:
                    subject_name = None
                    if perm.subject_type == 'account':
                        account = Account.objects.filter(id=perm.subject_id).first()
                        subject_name = account.username if account else 'Unknown'
                    elif perm.subject_type == 'role':
                        role = Role.objects.filter(id=perm.subject_id).first()
                        subject_name = role.name if role else 'Unknown'

                    granted_by_username = perm.granted_by.username if perm.granted_by else None

                    permission_rows.append({
                        'id': str(perm.id),
                        'subject_type': perm.subject_type,
                        'subject_id': perm.subject_id,
                        'subject_name': subject_name,
                        'permission': perm.permission,
                        'permission_precedence': perm.permission_precedence,
                        'is_active': perm.is_active,
                        'granted_by_id': str(perm.granted_by_id) if perm.granted_by_id else None,
                        'granted_by_username': granted_by_username,
                        'created_at': perm.created_at.isoformat() if perm.created_at else None,
                    })

                items.append({
                    'document_id': str(document.id),
                    'document_name': document.original_name,
                    'access_scope': document.access_scope,
                    'permissions': permission_rows,
                    'total_permissions': len(permission_rows),
                })

            return {
                'items': items,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_items': total_items,
                    'total_pages': (total_items + page_size - 1) // page_size,
                    'has_next': end_index < total_items,
                    'has_prev': page > 1,
                },
            }

        except Exception as e:
            logger.error(f"Error listing document permissions: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to list permissions for documents")

    def grant_document_permission(
        self,
        doc_id: str,
        user_id: int,
        subject_type: str,
        subject_id: str,
        permission: str,
        precedence: str = 'inherit'
    ) -> 'DocumentPermission':
        """
        Grant or update document permission.

        Args:
            doc_id: Document UUID
            user_id: User granting (must have write permission)
            subject_type: 'account' or 'role'
            subject_id: Account UUID/ID or Role UUID
            permission: 'read', 'write', or 'delete'
            precedence: 'inherit', 'override', or 'deny'

        Returns:
            DocumentPermission object

        Raises:
            PermissionDeniedError: If user lacks write permission
        """
        from django.apps import apps

        try:
            # Check write permission
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            granted_by_account = self.Account.objects.get(id=user_id)

            # Try to find existing permission (including soft-deleted ones)
            try:
                perm_obj = DocumentPermission.objects.all_records().get(
                    document_id=doc_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                )
                # If it was soft-deleted, restore it
                if perm_obj.is_deleted:
                    perm_obj.restore()
                # Update the permission and precedence
                perm_obj.permission = permission
                perm_obj.permission_precedence = precedence
                perm_obj.is_active = True
                perm_obj.granted_by = granted_by_account
                perm_obj.save()
                created = False
            except DocumentPermission.DoesNotExist:
                # Create new permission
                perm_obj = DocumentPermission.objects.create(
                    document_id=doc_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    permission=permission,
                    permission_precedence=precedence,
                    is_active=True,
                    granted_by=granted_by_account,
                )
                created = True

            self._log_document_audit(
                action='GRANT_ACL',
                document_id=doc_id,
                user_id=user_id
            )

            return perm_obj

        except Exception as e:
            if isinstance(e, PermissionDeniedError):
                raise
            logger.error(f"Error granting permission: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to grant permission on {doc_id}")

    def revoke_document_permission(
        self,
        doc_id: str,
        user_id: int,
        subject_type: str,
        subject_id: str,
        permission: str
    ) -> None:
        """
        Revoke document permission.

        Args:
            doc_id: Document UUID
            user_id: User revoking (must have write permission)
            subject_type: 'account' or 'role'
            subject_id: Account UUID/ID or Role UUID
            permission: 'read', 'write', or 'delete'

        Raises:
            PermissionDeniedError: If user lacks write permission
            NotFoundError: If permission not found
        """
        from django.apps import apps
        from django.utils import timezone

        try:
            # Check write permission
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            DocumentPermission = apps.get_model('documents', 'DocumentPermission')

            # Find permission using active() manager (soft delete aware)
            try:
                permission_obj = DocumentPermission.objects.get(
                    document_id=doc_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    permission=permission,
                    is_deleted=False,  # Only find active permissions
                )
            except DocumentPermission.DoesNotExist:
                raise NotFoundError(f"Permission not found")

            # Soft delete using the model's delete() method
            # This sets is_deleted=True and deleted_at=now()
            permission_obj.delete()

            self._log_document_audit(
                action='REVOKE_ACL',
                document_id=doc_id,
                user_id=user_id
            )

        except Exception as e:
            if isinstance(e, (PermissionDeniedError, NotFoundError)):
                raise
            logger.error(f"Error revoking permission: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to revoke permission on {doc_id}")

    def get_document_processing_status(
        self,
        doc_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get document and chunks processing status.

        Args:
            doc_id: Document UUID
            user_id: User requesting (must have read permission)

        Returns:
            Dict with status information

        Raises:
            NotFoundError: If not found
            PermissionDeniedError: If user lacks read permission
        """
        from django.apps import apps

        try:
            # ✅ FIXED: Use PermissionManager for comprehensive permission checking
            # This checks: explicit DENY, explicit ALLOW, role-based, folder inheritance
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()

            if not perm_manager.check_document_access(user_id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            document = self.document_repo.get_by_id(doc_id)
            if not document:
                raise NotFoundError(f"Document {doc_id} not found")

            DocumentChunk = apps.get_model('documents', 'DocumentChunk')

            # Get chunk statistics
            # DocumentChunk doesn't have 'status' field, so count total chunks only
            chunks = DocumentChunk.objects.filter(
                document_id=doc_id,
                is_deleted=False
            )
            total_chunks = chunks.count()
            # Chunks with embeddings are considered "completed"
            chunks_with_embeddings = chunks.filter(embeddings__isnull=False).distinct().count()
            metadata = document.metadata or {}

            def _status_to_step(status_value: str) -> str:
                if status_value in {'ready', 'completed', 'skipped', 'not_required'}:
                    return 'completed'
                if status_value in {'failed', 'timeout'}:
                    return 'failed'
                if status_value in {'queued', 'building', 'processing', 'deferred'}:
                    return 'in_progress'
                return 'not_started'

            processing_steps = list(metadata.get('processing_steps') or [])
            raptor_status = metadata.get('raptor_status') or 'not_required'
            asset_status = metadata.get('asset_status') or 'not_required'

            if raptor_status not in {'not_required', None, ''}:
                processing_steps.append({
                    'key': 'raptor_tree',
                    'label': 'Đang xây dựng RAPTOR',
                    'status': _status_to_step(raptor_status),
                    'detail': raptor_status,
                })

            if asset_status not in {'not_required', None, ''}:
                processing_steps.append({
                    'key': 'asset_processing',
                    'label': 'Đang xử lý ảnh/OCR',
                    'status': _status_to_step(asset_status),
                    'detail': asset_status,
                })

            raw_progress_percent = int(metadata.get('processing_progress_percent') or 0)
            progress_percent = raw_progress_percent
            current_stage = metadata.get('processing_current_stage')
            current_label = metadata.get('processing_current_stage_label') or ''
            blocking_statuses = {'queued', 'building', 'processing'}
            raptor_blocking = raptor_status in blocking_statuses
            asset_blocking = asset_status in blocking_statuses

            if document.status == 'pending':
                current_stage = current_stage or 'queued'
                current_label = 'Đang chờ worker xử lý'
                progress_percent = max(progress_percent, 2)
            elif document.status == 'processing':
                current_label = current_label or 'Đang xử lý tài liệu'
                progress_percent = max(progress_percent, 5)
            elif document.status == 'failed':
                current_stage = current_stage or 'failed'
                current_label = 'Xử lý thất bại'
                progress_percent = max(progress_percent, 100)
            else:
                if asset_status == 'processing':
                    current_stage = 'asset_processing'
                    current_label = 'Đang xử lý ảnh/OCR'
                    progress_percent = 84
                elif raptor_status == 'building':
                    current_stage = 'raptor_tree'
                    current_label = 'Đang xây dựng RAPTOR'
                    progress_percent = 92 if asset_status in {'ready', 'not_required', 'skipped'} else 88
                elif asset_status == 'queued':
                    current_stage = 'asset_processing'
                    current_label = 'Đang chờ xử lý ảnh/OCR'
                    progress_percent = 78
                elif raptor_status == 'queued':
                    current_stage = 'raptor_tree'
                    current_label = 'Đang chờ xây dựng RAPTOR'
                    progress_percent = 88
                else:
                    current_stage = 'completed'
                    current_label = 'Tài liệu đã sẵn sàng'
                    progress_percent = 100

            ready_for_chat = (
                document.status == 'completed'
                and not raptor_blocking
                and not asset_blocking
            )
            if not ready_for_chat and document.status != 'failed':
                progress_percent = min(progress_percent, 99)

            return {
                'document_id': str(document.id),
                'document_status': document.status,
                'document_error': getattr(document, 'error_message', None),
                'current_stage': current_stage,
                'current_stage_label': current_label,
                'progress_percent': max(0, min(100, progress_percent)),
                'processing_steps': processing_steps,
                'ready_for_chat': ready_for_chat,
                'indexing_status': metadata.get('indexing_status'),
                'raptor_status': raptor_status,
                'raptor_ready': bool(metadata.get('raptor_ready')),
                'asset_status': asset_status,
                'asset_ready': bool(metadata.get('asset_ready')),
                'metadata': {
                    'page_count': metadata.get('page_count'),
                    'chunk_count': metadata.get('chunk_count'),
                    'raptor_node_count': metadata.get('raptor_node_count'),
                    'asset_count': metadata.get('asset_count'),
                    'processing_error': metadata.get('processing_error'),
                },
                'chunk_processing_status': {
                    'total_chunks': total_chunks,
                    'processed_chunks': chunks_with_embeddings,
                    'completed_chunks': chunks_with_embeddings,
                    'failed_chunks': 0,
                    'pending_chunks': max(0, total_chunks - chunks_with_embeddings),
                },
                'processing_completed_at': str(getattr(document, 'processing_completed_at', '')) or None,
            }

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error getting processing status: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get status for document {doc_id}")

    def reprocess_document(
        self,
        doc_id: str,
        user_id: int,
        chunking_strategy: str = None,
        embedding_model: str = None
    ) -> 'Document':
        """
        Reprocess document (submit new INDEX_DOCUMENT AsyncTask).

        Args:
            doc_id: Document UUID
            user_id: User requesting (must have write permission)
            chunking_strategy: New chunking strategy (optional)
            embedding_model: New embedding model (optional)

        Returns:
            Document object

        Raises:
            NotFoundError: If not found
            PermissionDeniedError: If user lacks write permission
        """
        from django.apps import apps

        try:
            # Check write permission
            if not self.document_repo.check_user_can_write(doc_id, user_id):
                raise PermissionDeniedError(f"No write permission on document {doc_id}")

            document = self.document_repo.get_by_id(doc_id)
            if not document:
                raise NotFoundError(f"Document {doc_id} not found")

            # Update document status
            with transaction.atomic():
                if chunking_strategy:
                    document.chunking_strategy = chunking_strategy
                if embedding_model:
                    document.embedding_model = embedding_model

                document.status = 'pending'
                document.metadata = document.metadata or {}
                document.metadata.pop('processing_error', None)
                document.metadata['reprocess_requested_at'] = timezone.now().isoformat()
                document.save(update_fields=['chunking_strategy', 'embedding_model', 'status', 'metadata', 'updated_at'])

                from services.document_upload_service import DocumentUploadService
                transaction.on_commit(
                    lambda doc_id=str(document.id): DocumentUploadService()._dispatch_processing(doc_id)
                )

            self._log_document_audit(
                action='MUTATION',
                document_id=doc_id,
                user_id=user_id
            )

            return document

        except Exception as e:
            if isinstance(e, (NotFoundError, PermissionDeniedError)):
                raise
            logger.error(f"Error reprocessing document: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to reprocess document {doc_id}")
