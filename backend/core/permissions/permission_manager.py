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
from repositories.permission_manager_repository import PermissionManagerRepository

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
        """Initialize permission manager (lazy load repositories)"""
        self._permission_repo = None
        self._user_repo = None
        self._perm_mgr_repo = None
    
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
    
    @property
    def perm_mgr_repo(self):
        """Lazy load PermissionManagerRepository"""
        if self._perm_mgr_repo is None:
            self._perm_mgr_repo = PermissionManagerRepository()
        return self._perm_mgr_repo
    
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
        1. Get document + user via Repository
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
        """
        try:
            # Get document via Repository (ORM call centralized)
            document = self.perm_mgr_repo.get_document_by_id(document_id)
            if not document:
                raise DocumentNotFoundError(f"Document {document_id} not found")
            
            # Get user via Repository (ORM call centralized)
            user = self.perm_mgr_repo.get_account_by_id(user_id)
            if not user:
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
            
            # Load the user's department from the profile relation. Department lives
            # on UserProfile, not on Account.
            user_department = None
            try:
                user_department = user.user_profile.department if hasattr(user, 'user_profile') else None
            except Exception:
                user_department = None

            # Check permission hierarchy
            return self._check_document_permission_hierarchy(user, user_department, document, action)
            
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
        1. Get documents user uploaded (implicit access)
        2. Get documents with explicit DocumentPermission via Repository
        3. Get documents in accessible folders via Repository
        4. Union all + distinct
        
        For LARGE datasets, consider pagination + caching
        
        Returns:
            QuerySet of accessible documents
        """
        try:
            Document = apps.get_model('documents', 'Document')
            
            # Query 1: Documents user uploaded
            uploaded_query = self.perm_mgr_repo.get_documents_by_uploader(user_id)
            
            # Query 2: Documents with explicit permission
            explicit_perms = self.perm_mgr_repo.get_documents_with_explicit_permission(user_id)
            
            # Query 3: Documents via folder permission
            accessible_folder_ids = self.perm_mgr_repo.get_accessible_folder_ids(user_id)
            folder_docs = self.perm_mgr_repo.get_documents_by_folder_ids(accessible_folder_ids)
            
            # Union all + remove duplicates
            result = (uploaded_query | explicit_perms | folder_docs).distinct()
            
            logger.debug(f"User {user_id} has access to {result.count()} documents for {action}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting accessible documents: {str(e)}", exc_info=True)
            Document = apps.get_model('documents', 'Document')
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
                user = Account.objects.select_related('user_profile__department').get(
                    pk=user_id, is_deleted=False
                )
            except Account.DoesNotExist:
                logger.warning(f"User {user_id} not found for folder access check")
                return False

            try:
                user_department = user.user_profile.department if hasattr(user, 'user_profile') else None
            except Exception:
                user_department = None
            
            # Department check: can access own or sub-departments
            if not self._check_department_hierarchy(user_department, folder.department):
                logger.info(
                    f"User {user_id} (dept {getattr(user_department, 'id', None)}) cannot access "
                    f"folder {folder_id} (dept {folder.department_id})"
                )
                return False
            
            # Check folder inheritance
            access_scope = self._check_folder_inheritance(user, user_department, folder)
            return access_scope in [AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
            
        except Exception as e:
            logger.error(f"Error checking folder access: {str(e)}", exc_info=True)
            return False
    
    def get_accessible_folders(self, user_id: int) -> 'QuerySet':
        """
        Get all folders user can access
        
        Uses PermissionManagerRepository for all ORM operations
        
        Returns:
            QuerySet of accessible folders
        """
        try:
            return self.perm_mgr_repo.get_accessible_folders(user_id)
        except Exception as e:
            logger.error(f"Error getting accessible folders: {str(e)}", exc_info=True)
            Folder = apps.get_model('documents', 'Folder')
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
        user_department: Optional['Department'],
        document: 'Document', 
        action: str
    ) -> bool:
        """
        CORE ALGORITHM: Check document access via permission hierarchy
        
        Hier archy:
        1. Explicit DENY (deny access takes precedence)
        2. Explicit ALLOW on document (DocumentPermission)
        3. Role-based on document
        4. Inherit from folder  
        5. Default = DENY
        
        All ORM operations delegated to PermissionManagerRepository
        """
        try:
            # Get required permission code for action
            required_permission_code = self.ACTION_PERMISSION_MAP.get(action)
            if not required_permission_code:
                logger.warning(f"Unknown action: {action}")
                return False
            
            # LEVEL 1: Check explicit DENY on document via Repository
            deny_perm = self.perm_mgr_repo.get_document_deny_permission(document.id, user.id)
            if deny_perm:
                logger.info(f"User {user.id} has DENY permission on document {document.id}")
                return False

            # LEVEL 2: Document access scope can grant read access directly.
            # This preserves the existing read model used by the document repository
            # while still allowing explicit DENY to override it.
            if action == 'read':
                if document.access_scope == 'company':
                    logger.debug(f"User {user.id} granted read on company-scoped document {document.id}")
                    return True

                if document.access_scope == 'department' and self._check_department_hierarchy(
                    user_department,
                    document.department,
                ):
                    logger.debug(f"User {user.id} granted read on department-scoped document {document.id}")
                    return True

                if document.access_scope == 'personal' and document.uploader_id == user.id:
                    logger.debug(f"User {user.id} granted read on personal document {document.id}")
                    return True
            
            # LEVEL 3: Check explicit ALLOW on document via Repository
            allow_perm = self.perm_mgr_repo.get_document_allow_permission(document.id, user.id)
            if allow_perm:
                # Check if permission level allows action
                if self._scope_allows_action(allow_perm.access_scope, action):
                    logger.debug(f"User {user.id} has explicit permission on document {document.id}")
                    return True
            
            # LEVEL 4: Check role-based RBAC
            user_roles = self.perm_mgr_repo.get_user_role_ids(user.id)
            if user_roles:
                # Check if user's role has required permission
                if self.permission_repo.check_user_has_permission(user.id, required_permission_code):
                    logger.debug(f"User {user.id} has role-based permission via RBAC")
                    return True
            
            # LEVEL 5: Inherit from folder
            if document.folder:
                folder_access = self._check_folder_inheritance(user, user_department, document.folder)
                if folder_access in [AccessScope.WRITE, AccessScope.ADMIN]:
                    # WRITE/ADMIN on folder → can do all on document
                    logger.debug(f"User {user.id} has folder-level permission on parent folder")
                    return True
                elif folder_access == AccessScope.READ and action == 'read':
                    # READ on folder → only can read documents inside
                    return True
            
            # LEVEL 6: Default = DENY
            logger.info(f"User {user.id} denied access ({action}) to document {document.id}: no permission found")
            return False
            
        except Exception as e:
            logger.error(f"Error in permission hierarchy check: {str(e)}", exc_info=True)
            return False
    
    def _check_folder_inheritance(
        self, 
        user: 'Account', 
        user_dept: Optional['Department'],
        folder: 'Folder'
    ) -> str:
        """
        Check folder permissions via inheritance
        
        HIERARCHY:
        1. Direct folder permission for user's roles
        2. Parent folder permission (inherited)
        3. Default = DENY (AccessScope.NONE)
        
        All ORM operations delegated to Repository
        
        Args:
            user: Account instance
            folder: Folder instance
        
        Returns:
            AccessScope: READ, WRITE, ADMIN, DENY, or NONE (default)
        """
        try:
            user_role_ids = [str(role_id) for role_id in self.perm_mgr_repo.get_user_role_ids(user.id)]

            # Check current folder
            current_folder = folder
            iterations = 0
            max_iterations = 10  # Prevent infinite recursion

            while current_folder and iterations < max_iterations:
                iterations += 1

                # Check direct account permission first
                account_perm = self.perm_mgr_repo.get_folder_permission_for_subject(
                    current_folder.id,
                    'account',
                    str(user.id),
                )
                if account_perm:
                    logger.debug(
                        f"Folder {current_folder.id} has account permission {account_perm.permission} for user {user.id}"
                    )
                    return self._permission_to_scope(account_perm.permission)

                # Then check any role permission on this folder
                if user_role_ids:
                    role_perms = self.perm_mgr_repo.get_folder_permissions_for_subject_ids(
                        current_folder.id,
                        'role',
                        user_role_ids,
                    )
                    if role_perms.exists():
                        strongest_perm = self._pick_strongest_folder_permission(role_perms)
                        if strongest_perm:
                            logger.debug(
                                f"Folder {current_folder.id} has role permission {strongest_perm.permission} for user {user.id}"
                            )
                            return self._permission_to_scope(strongest_perm.permission)

                # Move to parent folder
                current_folder = current_folder.parent if hasattr(current_folder, 'parent') else None

            # No permission found in hierarchy
            logger.debug(f"User {user.id} has no permission in folder hierarchy at {folder.id}")
            return AccessScope.NONE

        except Exception as e:
            logger.error(f"Error checking folder inheritance: {str(e)}", exc_info=True)
            return AccessScope.NONE

    def _permission_to_scope(self, permission: str) -> str:
        """Map FolderPermission levels to AccessScope values."""
        if permission == 'delete':
            return AccessScope.ADMIN
        if permission == 'write':
            return AccessScope.WRITE
        if permission == 'read':
            return AccessScope.READ
        return AccessScope.NONE

    def _pick_strongest_folder_permission(self, permissions):
        """Pick the strongest permission from a FolderPermission queryset."""
        priority = {'read': 1, 'write': 2, 'delete': 3}
        best_permission = None
        best_rank = 0

        for permission in permissions:
            rank = priority.get(permission.permission, 0)
            if rank > best_rank:
                best_rank = rank
                best_permission = permission

        return best_permission
    
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
