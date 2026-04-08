"""
PERMISSION MANAGER - ACL (Access Control Logic) Layer
=====================================================
Implements hierarchical permission checking:
Account-level > Role-level > Document/Folder-level > Inheritance

This layer sits between ViewSets and PermissionRepository.
It orchestrates permission decisions considering:
1. Direct account permissions (highest priority)
2. Role-based permissions (via AccountRole)
3. Document/Folder-level permissions
4. Department hierarchy (can see own dept + sub-depts)

PATTERN: Account > Role > Document-Permission > Folder Permission > Inheritance
Priority:
  - DENY (highest)
  - User-Specific (Account-level)
  - Role-Based 
  - Folder Inherited
  - Default = DENY (lowest)

NO PERMISSIONS = DENIED (principle of least privilege)
"""

import logging
from typing import List, Optional, Tuple
from django.db.models import Q, Exists, OuterRef
from django.apps import apps
from core.constants import PermissionCodes, AccessScope
from core.exceptions import (
    PermissionDeniedError,
    NotFoundError,
    DocumentNotFoundError,
    InsufficientPermissionError,
)

logger = logging.getLogger(__name__)


class PermissionManager:
    """
    ACL Manager - Orchestrates permission checking
    
    Public Methods:
    - check_document_access(user_id, doc_id, action) → bool
    - check_folder_access(user_id, folder_id, action) → bool
    - get_accessible_documents(user_id) → QuerySet
    - get_accessible_folders(user_id) → QuerySet
    - check_user_has_role(user_id, role_id) → bool
    - check_account_permission(account, permission_code) → bool
    
    Internal Methods:
    - _check_document_permission_hierarchy(user, doc, action) → bool
    - _check_folder_inheritance(user, folder) → AccessScope
    - _get_user_roles(user_id) → set
    - _can_read/write/delete_document(user, doc) → bool
    """
    
    # Action to minimum required permission mapping
    ACTION_PERMISSION_MAP = {
        'read': PermissionCodes.DOCUMENT_READ,
        'write': PermissionCodes.DOCUMENT_WRITE,
        'delete': PermissionCodes.DOCUMENT_DELETE,
        'share': PermissionCodes.DOCUMENT_SHARE,
    }
    
    def __init__(self):
        """Initialize permission manager (lazy load models)"""
        self._permission_repo = None
        self._user_repo = None
    
    @property
    def permission_repo(self):
        """Lazy load PermissionRepository"""
        if self._permission_repo is None:
            from repositories.permission_repository import PermissionRepository
            self._permission_repo = PermissionRepository()
        return self._permission_repo
    
    @property
    def user_repo(self):
        """Lazy load UserRepository"""
        if self._user_repo is None:
            from repositories.user_repository import UserRepository
            self._user_repo = UserRepository()
        return self._user_repo
    
    # ============================================================================
    # PUBLIC METHODS - Document Access
    # ============================================================================
    
    def check_document_access(
        self, 
        user_id: int, 
        document_id: int, 
        action: str = 'read'
    ) -> bool:
        """
        Check if user can perform action on document
        
        ALGORITHM:
        1. Get document + user
        2. Check account-level permissions (RBAC)
        3. Check document-level permissions (DocumentPermission)
        4. Check folder inheritance (parent folder's permissions)
        5. Return result
        
        Args:
            user_id: User ID
            document_id: Document ID
            action: 'read', 'write', 'delete', 'share'
        
        Returns:
            True if allowed, False otherwise
        
        Raises:
            DocumentNotFoundError: If document not found
            PermissionDeniedError: If denied (with detailed reason)
        """
        try:
            Document = apps.get_model('documents', 'Document')
            Account = apps.get_model('users', 'Account')
            
            # Get document
            try:
                document = Document.objects.select_related('uploader', 'department', 'folder').get(
                    pk=document_id, is_deleted=False
                )
            except Document.DoesNotExist:
                raise DocumentNotFoundError(f"Document {document_id} not found")
            
            # Get user
            try:
                user = Account.objects.get(pk=user_id, is_deleted=False)
            except Account.DoesNotExist:
                logger.warning(f"User {user_id} not found for permission check on document {document_id}")
                return False
            
            # Principle of least privilege: if user is blocked/inactive, deny
            if not user.is_active:
                logger.info(f"User {user_id} is inactive, denying access to document {document_id}")
                return False
            
            # Uploader gets all permissions (implicit)
            if document.uploader_id == user_id:
                logger.debug(f"User {user_id} is uploader of document {document_id}, granting {action}")
                return True
            
            # Check permission hierarchy
            return self._check_document_permission_hierarchy(user, document, action)
            
        except Exception as e:
            logger.error(f"Error checking document access: {str(e)}", exc_info=True)
            return False
    
    def check_document_access_strict(
        self, 
        user_id: int, 
        document_id: int, 
        action: str = 'read'
    ) -> bool:
        """
        Strict version that raises exceptions
        
        Raises:
            PermissionDeniedError: If user doesn't have permission
            DocumentNotFoundError: If document not found
        """
        if not self.check_document_access(user_id, document_id, action):
            Document = apps.get_model('documents', 'Document')
            try:
                doc = Document.objects.get(pk=document_id, is_deleted=False)
                raise PermissionDeniedError(
                    f"User {user_id} cannot {action} document '{doc.original_name}'"
                )
            except Document.DoesNotExist:
                raise DocumentNotFoundError(f"Document {document_id} not found")
        return True
    
    def get_accessible_documents(self, user_id: int, action: str = 'read') -> 'QuerySet':
        """
        Get all documents user can access
        
        ALGORITHM:
        1. Get user's roles
        2. Get documents user uploaded (implicit access)
        3. Get documents in accessible folders
        4. Get documents with explicit DocumentPermission for user
        5. Union all + distinct
        
        For LARGE datasets, consider pagination + caching
        
        Returns:
            QuerySet of accessible documents
        """
        try:
            Document = apps.get_model('documents', 'Document')
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            Folder = apps.get_model('documents', 'Folder')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            # Query 1: Documents user uploaded
            uploaded_query = Document.objects.filter(
                uploader_id=user_id, is_deleted=False
            )
            
            # Query 2: Documents with explicit permission
            explicit_perms = Document.objects.filter(
                is_deleted=False,
                documentpermission__account_id=user_id,
                documentpermission__access_scope__in=[
                    AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN
                ]
            ).distinct()
            
            # Query 3: Documents via folder permission
            user_role_ids = list(
                AccountRole.objects.filter(
                    account_id=user_id, is_deleted=False
                ).values_list('role_id', flat=True)
            )
            
            if user_role_ids:
                # Folders where user's role has permission
                accessible_folder_ids = list(
                    FolderPermission.objects.filter(
                        role_id__in=user_role_ids,
                        is_deleted=False,
                        access_scope__in=[AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
                    ).values_list('folder_id', flat=True).distinct()
                )
                
                # Documents in accessible folders
                folder_docs = Document.objects.filter(
                    folder_id__in=accessible_folder_ids,
                    is_deleted=False
                ) if accessible_folder_ids else Document.objects.none()
            else:
                folder_docs = Document.objects.none()
            
            # Union all + remove duplicates
            result = (uploaded_query | explicit_perms | folder_docs).distinct()
            
            logger.debug(f"User {user_id} has access to {result.count()} documents for {action}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting accessible documents: {str(e)}", exc_info=True)
            return Document.objects.none()
    
    # ============================================================================
    # PUBLIC METHODS - Folder Access
    # ============================================================================
    
    def check_folder_access(
        self, 
        user_id: int, 
        folder_id: int, 
        action: str = 'read'
    ) -> bool:
        """
        Check if user can access folder
        
        ALGORITHM:
        1. Get folder + user
        2. Check RBAC (user's roles vs folder permissions)
        3. Check ACL (department hierarchy)
        4. Return result
        
        Returns:
            True if allowed, False otherwise
        """
        try:
            Folder = apps.get_model('documents', 'Folder')
            Account = apps.get_model('users', 'Account')
            
            # Get folder
            try:
                folder = Folder.objects.select_related('department').get(
                    pk=folder_id, is_deleted=False
                )
            except Folder.DoesNotExist:
                logger.warning(f"Folder {folder_id} not found")
                return False
            
            # Get user
            try:
                user = Account.objects.select_related('department').get(
                    pk=user_id, is_deleted=False
                )
            except Account.DoesNotExist:
                logger.warning(f"User {user_id} not found for folder access check")
                return False
            
            # Department check: can access own or sub-departments
            if not self._check_department_hierarchy(user.department, folder.department):
                logger.info(
                    f"User {user_id} (dept {user.department_id}) cannot access "
                    f"folder {folder_id} (dept {folder.department_id})"
                )
                return False
            
            # Check folder inheritance
            access_scope = self._check_folder_inheritance(user, folder)
            return access_scope in [AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
            
        except Exception as e:
            logger.error(f"Error checking folder access: {str(e)}", exc_info=True)
            return False
    
    def get_accessible_folders(self, user_id: int) -> 'QuerySet':
        """
        Get all folders user can access
        
        Returns:
            QuerySet of accessible folders
        """
        try:
            Folder = apps.get_model('documents', 'Folder')
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            # User's role IDs
            user_role_ids = list(
                AccountRole.objects.filter(
                    account_id=user_id, is_deleted=False
                ).values_list('role_id', flat=True)
            )
            
            if not user_role_ids:
                return Folder.objects.none()
            
            # Accessible folders via role permissions
            accessible_folder_ids = list(
                FolderPermission.objects.filter(
                    role_id__in=user_role_ids,
                    is_deleted=False,
                    access_scope__in=[AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
                ).values_list('folder_id', flat=True).distinct()
            )
            
            return Folder.objects.filter(
                id__in=accessible_folder_ids, is_deleted=False
            ).distinct()
            
        except Exception as e:
            logger.error(f"Error getting accessible folders: {str(e)}", exc_info=True)
            return Folder.objects.none()
    
    # ============================================================================
    # PUBLIC METHODS - Role/Permission Checks
    # ============================================================================
    
    def check_user_has_role(self, user_id, role_id) -> bool:
        """Check if user has specific role (role_id is now UUID)"""
        try:
            return self.permission_repo.check_user_has_role(user_id, role_id)
        except Exception as e:
            logger.error(f"Error checking user role: {str(e)}")
            return False
    
    def check_user_has_permission(self, user_id: int, permission_code: str) -> bool:
        """Check if user has specific permission (via role)"""
        try:
            return self.permission_repo.check_user_has_permission(user_id, permission_code)
        except Exception as e:
            logger.error(f"Error checking user permission: {str(e)}")
            return False
    
    def check_user_has_any_permission(self, user_id: int, permission_codes: List[str]) -> bool:
        """Check if user has ANY of the permissions in list"""
        try:
            return self.permission_repo.check_user_has_any_permission(user_id, permission_codes)
        except Exception as e:
            logger.error(f"Error checking user -any- permission: {str(e)}")
            return False
    
    def check_user_has_all_permissions(self, user_id: int, permission_codes: List[str]) -> bool:
        """Check if user has ALL permissions in list"""
        try:
            return self.permission_repo.check_user_has_all_permissions(user_id, permission_codes)
        except Exception as e:
            logger.error(f"Error checking user -all- permissions: {str(e)}")
            return False
    
    # ============================================================================
    # INTERNAL METHODS - Permission Hierarchy Logic
    # ============================================================================
    
    def _check_document_permission_hierarchy(
        self, 
        user: 'Account', 
        document: 'Document', 
        action: str
    ) -> bool:
        """
        CORE ALGORITHM: Check document access via permission hierarchy
        
        Hierarchy:
        1. Explicit DENY (deny access takes precedence)
        2. Explicit ALLOW on document (DocumentPermission)
        3. Role-based on document
        4. Inherit from folder
        5. Default = DENY
        
        Args:
            user: Account instance
            document: Document instance
            action: 'read', 'write', 'delete', 'share'
        
        Returns:
            bool: True if allowed
        """
        try:
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            
            # Get required permission code for action
            required_permission_code = self.ACTION_PERMISSION_MAP.get(action)
            if not required_permission_code:
                logger.warning(f"Unknown action: {action}")
                return False
            
            # LEVEL 1: Check explicit DENY on document
            deny_perm = DocumentPermission.objects.filter(
                document=document,
                account=user,
                access_scope=AccessScope.DENY,
                is_deleted=False
            ).first()
            
            if deny_perm:
                logger.info(f"User {user.id} has DENY permission on document {document.id}")
                return False
            
            # LEVEL 2: Check explicit ALLOW on document (user-level)
            allow_perm = DocumentPermission.objects.filter(
                document=document,
                account=user,
                access_scope__in=[AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN],
                is_deleted=False
            ).first()
            
            if allow_perm:
                # Check if permission level allows action
                if self._scope_allows_action(allow_perm.access_scope, action):
                    logger.debug(f"User {user.id} has explicit permission on document {document.id}")
                    return True
            
            # LEVEL 3: Check role-based RBAC
            user_roles = self._get_user_roles(user.id)
            if user_roles:
                # Check if user's role has required permission
                if self.permission_repo.check_user_has_permission(user.id, required_permission_code):
                    logger.debug(f"User {user.id} has role-based permission via RBAC")
                    return True
            
            # LEVEL 4: Inherit from folder
            if document.folder:
                folder_access = self._check_folder_inheritance(user, document.folder)
                if folder_access in [AccessScope.WRITE, AccessScope.ADMIN]:
                    # WRITE/ADMIN on folder → can do all on document
                    logger.debug(f"User {user.id} has folder-level permission on parent folder")
                    return True
                elif folder_access == AccessScope.READ and action == 'read':
                    # READ on folder → only can read documents inside
                    return True
            
            # LEVEL 5: Default = DENY
            logger.info(f"User {user.id} denied access ({action}) to document {document.id}: no permission found")
            return False
            
        except Exception as e:
            logger.error(f"Error in permission hierarchy check: {str(e)}", exc_info=True)
            return False
    
    def _check_folder_inheritance(
        self, 
        user: 'Account', 
        folder: 'Folder'
    ) -> str:
        """
        Check folder permissions via inheritance
        
        HIERARCHY:
        1. Direct folder permission for user's roles
        2. Parent folder permission (inherited)
        3. Default = DENY (AccessScope.NONE)
        
        Args:
            user: Account instance
            folder: Folder instance
        
        Returns:
            AccessScope: READ, WRITE, ADMIN, DENY, or NONE (default)
        """
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            user_role_ids = list(
                self._get_user_role_ids(user.id)
            )
            
            if not user_role_ids:
                logger.debug(f"User {user.id} has no roles")
                return AccessScope.NONE
            
            # Check current folder
            current_folder = folder
            iterations = 0
            max_iterations = 10  # Prevent infinite recursion
            
            while current_folder and iterations < max_iterations:
                iterations += 1
                
                # Check for explicit permission on this folder
                perm = FolderPermission.objects.filter(
                    folder=current_folder,
                    role_id__in=user_role_ids,
                    is_deleted=False
                ).order_by('-access_scope').first()  # Higher scope takes precedence
                
                if perm:
                    logger.debug(f"Folder {current_folder.id} has permission scope {perm.access_scope}")
                    return perm.access_scope
                
                # Move to parent folder
                current_folder = current_folder.parent
            
            # No permission found in hierarchy
            logger.debug(f"User {user.id} has no permission in folder hierarchy at {folder.id}")
            return AccessScope.NONE
            
        except Exception as e:
            logger.error(f"Error checking folder inheritance: {str(e)}", exc_info=True)
            return AccessScope.NONE
    
    def _check_department_hierarchy(
        self, 
        user_dept: Optional['Department'], 
        target_dept: Optional['Department']
    ) -> bool:
        """
        Check if user can access content in target department
        
        Rules:
        - User can access their own department
        - User can access sub-departments of their own
        - User CANNOT access parent or sibling departments (unless admin)
        
        Args:
            user_dept: User's department
            target_dept: Target department (folder's department)
        
        Returns:
            bool: True if user can access target department
        """
        if not target_dept:
            # No department restriction
            return True
        
        if not user_dept:
            # User has no department, can access all
            return True
        
        if user_dept.id == target_dept.id:
            # Same department
            return True
        
        # Check if target is sub-department of user's dept
        try:
            Department = apps.get_model('users', 'Department')
            parent_chain = self._get_department_parent_chain(target_dept)
            return user_dept.id in parent_chain
        except Exception as e:
            logger.error(f"Error checking department hierarchy: {str(e)}")
            return False
    
    def _get_department_parent_chain(self, dept: 'Department') -> List[int]:
        """Get all parent department IDs up the hierarchy"""
        chain = []
        current = dept
        iterations = 0
        max_iterations = 10
        
        while current and iterations < max_iterations:
            chain.append(current.id)
            current = current.parent
            iterations += 1
        
        return chain
    
    def _get_user_roles(self, user_id: int) -> set:
        """Get all roles for user"""
        try:
            return self.permission_repo.get_user_role_ids(user_id)
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            return set()
    
    def _get_user_role_ids(self, user_id) -> list:
        """Get user role IDs as list (role IDs are now UUIDs)"""
        return list(self._get_user_roles(user_id))
    
    def _scope_allows_action(self, scope: str, action: str) -> bool:
        """
        Check if access scope allows action
        
        Scope hierarchy:
        - ADMIN: all actions
        - WRITE: read + write (no delete/share)
        - READ: read only
        - DENY: no actions
        - NONE: no actions
        """
        scope_hierarchy = {
            AccessScope.ADMIN: ['read', 'write', 'delete', 'share'],
            AccessScope.WRITE: ['read', 'write'],
            AccessScope.READ: ['read'],
            AccessScope.DENY: [],
            AccessScope.NONE: [],
        }
        
        allowed_actions = scope_hierarchy.get(scope, [])
        return action in allowed_actions


# ============================================================================
# SINGLETON INSTANCE - Global PermissionManager
# ============================================================================

_permission_manager_instance = None


def get_permission_manager() -> PermissionManager:
    """Get or create singleton PermissionManager instance"""
    global _permission_manager_instance
    if _permission_manager_instance is None:
        _permission_manager_instance = PermissionManager()
    return _permission_manager_instance
