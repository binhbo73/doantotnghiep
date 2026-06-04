"""
Chat Attachment Service
========================
Business logic for fetching documents/folders accessible to user
considering roles, permissions, and access scopes.

Responsibilities:
- Get accessible documents for current user
- Get accessible folders for current user
- Apply permission checks (access_scope, role, DocumentPermission, FolderPermission)
- Return unified attachments response
"""

import logging
from typing import Dict, List, Any, Tuple
from django.db.models import Q

from core.constants import PermissionCodes
from core.permissions.drf_permissions import user_has_permission
from repositories.document_repository import DocumentRepository
from repositories.folder_repository import FolderRepository
from repositories.permission_manager_repository import PermissionManagerRepository
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ChatAttachmentService:
    """
    Service for retrieving documents and folders accessible for chat attachments.
    
    Respects:
    - access_scope (personal/department/company)
    - User roles via AccountRole
    - Explicit DocumentPermission entries
    - Explicit FolderPermission entries
    """
    
    def __init__(self):
        self.doc_repo = DocumentRepository()
        self.folder_repo = FolderRepository()
        self.perm_repo = PermissionManagerRepository()
    
    def get_accessible_attachments(self, user_id: int) -> Dict[str, Any]:
        """
        Get all documents and folders accessible by user for chat attachment.
        
        Args:
            user_id: Current authenticated user ID
            
        Returns:
            {
                'documents': [accessible documents],
                'folders': [accessible folders],
                'pagination': {
                    'total_documents': int,
                    'total_folders': int
                }
            }
        """
        try:
            logger.info(f"📎 Getting accessible attachments for user: {user_id}")
            
            # Get accessible documents (uses access_scope + permissions)
            accessible_docs = self._get_accessible_documents(user_id)
            
            # Get accessible folders (uses access_scope + permissions)
            accessible_folders = self._get_accessible_folders(user_id)
            
            logger.info(
                f"✅ Found {len(accessible_docs)} documents and "
                f"{len(accessible_folders)} folders accessible to user {user_id}"
            )
            
            return {
                'documents': accessible_docs,
                'folders': accessible_folders,
                'pagination': {
                    'total_documents': len(accessible_docs),
                    'total_folders': len(accessible_folders),
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting accessible attachments: {str(e)}", exc_info=True)
            raise
    
    def _get_accessible_documents(self, user_id: int) -> List[Any]:
        """
        Get documents accessible to user via:
        1. access_scope rules
        2. Explicit DocumentPermission entries
        3. Role-based permissions
        """
        try:
            from apps.users.models import Account, AccountRole, UserProfile
            from apps.documents.models import Document, DocumentPermission, FolderPermission
            
            # Get user's info
            user = Account.objects.select_related('user_profile').get(pk=user_id)
            account_id = str(user.id)
            user_profile = user.user_profile if hasattr(user, 'user_profile') else None
            user_dept_id = user_profile.department_id if user_profile else None
            
            # Check system-level bypass by permission, not role code.
            is_admin = user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            
            if is_admin:
                # Admin sees all documents
                return list(
                    Document.objects.filter(is_deleted=False)
                    .select_related('uploader', 'department', 'folder')
                    .values('id', 'original_name', 'file_type', 'file_size', 'status',
                           'access_scope', 'created_at', 'updated_at')
                )
            
            # Get accessible departments (user dept + descendants)
            accessible_depts = self._get_dept_and_descendants(user_dept_id) if user_dept_id else []
            
            # Get user's roles
            role_ids = list(
                AccountRole.objects.filter(account_id=user_id, is_deleted=False)
                .values_list('role_id', flat=True)
            )
            
            # PART 1: Documents via access_scope
            scope_docs = Document.objects.filter(
                Q(access_scope='company') |
                Q(access_scope='department', department_id__in=accessible_depts) |
                Q(access_scope='personal', uploader_id=user_id)
            ).filter(is_deleted=False)
            
            # PART 2: Documents via explicit DocumentPermission
            explicit_perms = DocumentPermission.objects.filter(
                Q(subject_id=account_id, subject_type='account') |
                Q(subject_id__in=[str(rid) for rid in role_ids], subject_type='role'),
                permission__in=['read', 'write', 'delete'],
                is_active=True,
                is_deleted=False
            ).values_list('document_id', flat=True).distinct()
            perm_docs = Document.objects.filter(id__in=explicit_perms, is_deleted=False)

            # PART 3: Documents inside folders the user/role has permissions on (FolderPermission)
            folder_perms = FolderPermission.objects.filter(
                Q(subject_id=account_id, subject_type='account') |
                Q(subject_id__in=[str(rid) for rid in role_ids], subject_type='role'),
                permission__in=['read', 'write', 'delete'],
                is_active=True,
                is_deleted=False
            ).values_list('folder_id', flat=True).distinct()
            folder_docs = Document.objects.filter(folder_id__in=folder_perms, is_deleted=False)
            
            # Combine (union)
            all_accessible_ids = set(
                list(scope_docs.values_list('id', flat=True)) +
                list(perm_docs.values_list('id', flat=True)) +
                list(folder_docs.values_list('id', flat=True))
            )
            
            docs = Document.objects.filter(
                id__in=all_accessible_ids
            ).select_related('uploader', 'department', 'folder').order_by('-created_at')
            
            return list(docs.values(
                'id', 'original_name', 'file_type', 'file_size', 'status',
                'access_scope', 'created_at', 'updated_at'
            ))
        
        except Exception as e:
            logger.error(f"Error getting accessible documents: {str(e)}", exc_info=True)
            return []
    
    def _get_accessible_folders(self, user_id: int) -> List[Any]:
        """
        Get folders accessible to user via:
        1. access_scope rules
        2. Explicit FolderPermission entries
        3. Role-based permissions
        """
        try:
            from apps.users.models import Account, AccountRole, UserProfile
            from apps.documents.models import Folder, FolderPermission
            
            # Get user's info
            user = Account.objects.select_related('user_profile').get(pk=user_id)
            user_profile = user.user_profile if hasattr(user, 'user_profile') else None
            user_dept_id = user_profile.department_id if user_profile else None
            
            # Check system-level bypass by permission, not role code.
            is_admin = user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            
            if is_admin:
                # Admin sees all folders
                return list(
                    Folder.objects.filter(is_deleted=False)
                    .select_related('department')
                    .values('id', 'name', 'access_scope', 'parent_id', 'created_at', 'updated_at')
                )
            
            # Get accessible departments
            accessible_depts = self._get_dept_and_descendants(user_dept_id) if user_dept_id else []
            
            # Get user's roles
            role_ids = list(
                AccountRole.objects.filter(account_id=user_id, is_deleted=False)
                .values_list('role_id', flat=True)
            )
            
            # PART 1: Folders via access_scope
            scope_folders = Folder.objects.filter(
                Q(access_scope='company') |
                Q(access_scope='department', department_id__in=accessible_depts) |
                Q(access_scope='personal', created_by_id=user_id)
            ).filter(is_deleted=False)
            
            # PART 2: Folders via explicit FolderPermission
            explicit_perms = FolderPermission.objects.filter(
                Q(subject_id=str(user_id), subject_type='account') |
                Q(subject_id__in=[str(rid) for rid in role_ids], subject_type='role'),
                permission__in=['read', 'write', 'delete'],
                is_active=True,
                is_deleted=False
            ).values_list('folder_id', flat=True).distinct()
            
            perm_folders = Folder.objects.filter(id__in=explicit_perms, is_deleted=False)
            
            # Combine (union)
            all_accessible_ids = set(
                list(scope_folders.values_list('id', flat=True)) +
                list(perm_folders.values_list('id', flat=True))
            )
            
            folders = Folder.objects.filter(
                id__in=all_accessible_ids
            ).select_related('department').order_by('-created_at')
            
            return list(folders.values(
                'id', 'name', 'access_scope', 'parent_id', 'created_at', 'updated_at'
            ))
        
        except Exception as e:
            logger.error(f"Error getting accessible folders: {str(e)}", exc_info=True)
            return []
    
    def _get_dept_and_descendants(self, dept_id: str) -> List[str]:
        """Get department ID plus all descendant department IDs"""
        if not dept_id:
            return []
        
        from apps.users.models import Department
        
        dept_ids = [str(dept_id)]
        queue = [str(dept_id)]
        
        try:
            while queue:
                current_id = queue.pop(0)
                child_ids = list(
                    Department.objects.filter(
                        parent_id=current_id, is_deleted=False
                    ).values_list('id', flat=True)
                )
                for child_id in child_ids:
                    child_id = str(child_id)
                    if child_id not in dept_ids:
                        dept_ids.append(child_id)
                        queue.append(child_id)
        except Exception as e:
            logger.error(f"Error loading department descendants: {str(e)}")
        
        return dept_ids
