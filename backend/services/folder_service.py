"""
FolderService - Business logic cho Folder management.

Responsibilities:
- Folder CRUD operations
- Hierarchical tree building
- Permission checking
- Recursive deletion with cascade
- Audit logging

Flow: View → Service → Repository → ORM
"""

import logging
from typing import Optional, List, Dict, Any
from collections import defaultdict

from uuid import UUID
from django.db import transaction, models
from django.utils import timezone
from django.apps import apps

from repositories.folder_repository import FolderRepository
from services.base_service import BaseService
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    PermissionDeniedError,
)
from core.constants import PermissionCodes
from core.permissions.drf_permissions import user_has_any_permission, user_has_permission

logger = logging.getLogger(__name__)


class FolderService(BaseService):
    """
    Folder Management Service - Logic cho Folder (thư mục)
    """
    
    repository_class = FolderRepository
    
    def __init__(self):
        super().__init__()  # Initialize self.repository (FolderRepository)
        self.Folder = apps.get_model('documents', 'Folder')
        self.Account = apps.get_model('users', 'Account')
        self.UserProfile = apps.get_model('users', 'UserProfile')
        self.AuditLog = apps.get_model('operations', 'AuditLog')

    def _user_can_manage_department(self, user_id: str, target_department_id: str) -> bool:
        """
        Check if user has management rights over a department.
        A user can manage a department if:
        1. They are the direct manager (manager_id) of the department
        2. They are in the managers M2M relation of the department
        3. They manage an ancestor department (transitive: manager of parent
           also manages all sub-departments)

        This check does NOT rely on hardcoded roles - it uses the actual
        Department.manager_id / Department.managers M2M fields set in the
        data model.  Callers should already have verified the user has the
        FOLDER_CREATE permission before calling this helper.
        """
        try:
            Department = apps.get_model('users', 'Department')
            # Collect all departments the user directly manages
            directly_managed = set(
                Department.objects.filter(
                    is_deleted=False
                ).filter(
                    models.Q(manager_id=user_id) |
                    models.Q(managers__id=user_id)
                ).values_list('id', flat=True)
            )
            if not directly_managed:
                return False

            # Walk up the target department's ancestor chain and check for overlap
            visited = set()
            current_id = str(target_department_id)
            while current_id and current_id not in visited:
                visited.add(current_id)
                # If the current ancestor (or target itself) is managed by user → allow
                if UUID(current_id) in directly_managed or current_id in {str(d) for d in directly_managed}:
                    return True
                dept = Department.objects.filter(id=current_id, is_deleted=False).first()
                if not dept or not dept.parent_id:
                    break
                current_id = str(dept.parent_id)
            return False
        except Exception as e:
            logger.debug(f"_user_can_manage_department error: {e}")
            return False
    
    # ============================================================
    # FOLDER TREE RETRIEVAL
    # ============================================================
    
    def get_folder_tree(self, account_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get accessible folders in tree structure for a user.
        
        Business Logic:
        1. Get user's department
        2. Get accessible folders (respects access_scope)
        3. Build nested tree structure
        
        Args:
            user_id: User account ID
            include_deleted: Whether to include soft-deleted folders
        
        Returns:
            List of folder dicts with nested sub_folders
        
        Example:
            tree = service.get_folder_tree(user_id="uuid-user")
            # Returns:
            # [
            #   {
            #     "id": "uuid-1",
            #     "name": "Projects",
            #     "sub_folders": [...]
            #   },
            #   ...
            # ]
        """
        try:
            # Get user and their department
            user = self.Account.objects.filter(id=account_id).first()
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            try:
                user_profile = self.UserProfile.objects.get(account_id=account_id)
                user_department_id = user_profile.department_id
            except self.UserProfile.DoesNotExist:
                user_department_id = None
            
            # Determine if user has system-level bypass
            is_admin = user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            
            # Get all accessible folders using unified PermissionManager
            from core.permissions.permission_manager import get_permission_manager
            pm = get_permission_manager()
            
            if is_admin:
                all_accessible_folders = self.Folder.objects.filter(is_deleted=False).order_by('name')
            else:
                all_accessible_folders = pm.get_accessible_folders(account_id)
            
            # Map folders by parent_id for efficient lookup
            folders_by_parent = defaultdict(list)
            for f in all_accessible_folders:
                folders_by_parent[str(f.parent_id) if f.parent_id else None].append(f)
            
            # Build tree structure recursively from memory
            tree = []
            root_folders = folders_by_parent[None]
            for folder in root_folders:
                tree.append(self._build_folder_tree_node_optimized(folder, folders_by_parent, account_id, user_department_id, is_admin))
            
            logger.info(f"Retrieved folder tree for account {account_id}: {len(tree)} root folders")
            return tree
            
        except Exception as e:
            logger.error(f"Error getting folder tree: {str(e)}")
            raise
    
    def _build_folder_tree_node_optimized(
        self,
        folder: 'Folder',
        folders_by_parent: Dict[Optional[str], List['Folder']],
        account_id: str,
        user_department_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Recursively build single folder node with sub_folders from memory map.
        """
        # Get children from map
        subfolders = folders_by_parent.get(str(folder.id), [])
        
        # Recursively build sub-nodes
        sub_nodes = [
            self._build_folder_tree_node_optimized(sf, folders_by_parent, account_id, user_department_id, is_admin)
            for sf in subfolders
        ]
        
        # Get documents count (still requires query per folder, but better than query per subfolder)
        # TODO: Could pre-fetch document counts for all folders in one query
        documents_query = folder.documents.filter(is_deleted=False)
        if not is_admin:
            documents_query = documents_query.filter(
                models.Q(access_scope='company') |
                models.Q(access_scope='department', department_id=user_department_id) |
                models.Q(access_scope='personal', uploader_id=account_id)
            ).distinct()
        
        document_count = documents_query.count()
        
        # Calculate effective permission level for user
        from core.permissions.permission_manager import get_permission_manager
        pm = get_permission_manager()
        my_permission = pm.get_effective_level(account_id, folder.id, is_folder=True)

        uploader_name = None
        if is_admin:
            creator = getattr(folder, 'created_by', None)
            if creator:
                profile = getattr(creator, 'user_profile', None)
                if profile and getattr(profile, 'full_name', None):
                    uploader_name = profile.full_name
                else:
                    full_name = creator.get_full_name() if hasattr(creator, 'get_full_name') else ''
                    uploader_name = full_name or creator.username
        
        return {
            'id': str(folder.id),
            'name': folder.name,
            'description': folder.description,
            'access_scope': folder.access_scope,
            'uploader_name': uploader_name,
            'department_id': str(folder.department_id) if folder.department_id else None,
            'parent_id': str(folder.parent_id) if folder.parent_id else None,
            'created_at': folder.created_at.isoformat(),
            'updated_at': folder.updated_at.isoformat(),
            'sub_folders': sub_nodes,
            'subfolder_count': len(subfolders),
            'document_count': document_count,
            'my_permission': my_permission,
        }
    
    def _is_folder_accessible(
        self,
        folder: 'Folder',
        user_id: str,
        user_department_id: Optional[str] = None
    ) -> bool:
        """
        Check if user can access folder based on access_scope.
        
        Rules:
        - 'company' → True (all users)
        - 'department' → Only if user.department_id == folder.department_id
        - 'personal' → Only if user created the folder
        """
        if folder.access_scope == 'company':
            return True
        elif folder.access_scope == 'department':
            return user_department_id and str(user_department_id) == str(folder.department_id)
        elif folder.access_scope == 'personal':
            return str(folder.created_by_id) == str(user_id)
        else:
            logger.warning(f"Unknown access_scope: {folder.access_scope}")
            return False

    def _get_user_department_id(self, user_id: str) -> Optional[str]:
        """Return the user's department_id if available."""
        try:
            user_profile = self.UserProfile.objects.get(account_id=user_id)
            return user_profile.department_id
        except self.UserProfile.DoesNotExist:
            return None

    def check_folder_permission(
        self,
        folder_id: str,
        user_id: str,
        permission: str = 'read'
    ) -> bool:
        """
        Check if user has specific permission on a folder.
        Checks: Admin status, Ownership, department membership, Department Manager status, and FolderPermission table.
        
        Permission hierarchy:
        1. Admin → All permissions
        2. Creator → All permissions
        3. Department Manager of folder's dept → Write + Read on dept-scoped folders
        4. Same Department → Read on dept-scoped folders
        5. Company-wide access → Read on company-scoped folders
        6. Explicit FolderPermission → As specified
        """
        try:
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                return False
            
            # 1. Admin bypass
            user = self.Account.objects.filter(id=user_id).first()
            if not user:
                return False
            
            is_admin = user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            if is_admin:
                return True
            
            # 2. Creator bypass (Ownership)
            if str(folder.created_by_id) == str(user_id):
                return True
            
            # 3. Check access scope first (Accessibility)
            try:
                user_profile = self.UserProfile.objects.get(account_id=user_id)
                user_department_id = user_profile.department_id
            except self.UserProfile.DoesNotExist:
                user_department_id = None
            
            if not self._is_folder_accessible(folder, user_id, user_department_id):
                return False

            # 4. Department-scoped folders are writable by users in the same department.
            # This covers both trưởng phòng and nhân viên in the folder's department.
            if folder.access_scope == 'department' and folder.department_id and user_department_id:
                if str(folder.department_id) == str(user_department_id):
                    if permission in ('read', 'write'):
                        return True
            
            # 5. Check if user is manager of the folder's department
            perm_levels = {'read': 1, 'write': 2, 'delete': 3}
            req_level = perm_levels.get(permission, 1)
            
            if folder.access_scope == 'department' and folder.department_id:
                # Check if user is a manager of this department
                try:
                    Department = apps.get_model('users', 'Department')
                    dept = Department.objects.get(id=folder.department_id)
                    
                    # Check if user is the main manager or in managers M2M
                    is_manager = (
                        str(dept.manager_id) == str(user_id) or
                        dept.managers.filter(id=user_id).exists()
                    )
                    
                    if is_manager and req_level <= perm_levels['write']:
                        return True
                except Exception as e:
                    logger.debug(f"Could not check department manager status: {e}")
            
            # 6. Check specific FolderPermission table (Account or Role)
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            # Get user's roles via Account helper
            user_role_ids = [str(role_id) for role_id in user.get_roles().values_list('role_id', flat=True)]
            
            # Query permissions for this account OR any of user's roles
            perms = FolderPermission.objects.filter(
                folder_id=folder_id,
                is_active=True,
                is_deleted=False
            ).filter(
                (models.Q(subject_type='account', subject_id=str(user_id))) |
                (models.Q(subject_type='role', subject_id__in=user_role_ids))
            )
            
            for p in perms:
                if perm_levels.get(p.permission, 0) >= req_level:
                    return True
            
            # 7. Default: If scope is company/department, user has 'read'
            if permission == 'read':
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking folder permission: {e}", exc_info=True)
            return False
    
    # ============================================================
    # CREATE FOLDER
    # ============================================================
    
    @transaction.atomic
    def create_folder(
        self,
        name: str,
        user_id: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        access_scope: str = 'company',
        department_id: Optional[str] = None,
    ) -> 'Folder':
        """
        Create new folder.
        
        Business Logic:
        1. Validate inputs (name required, access_scope valid)
        2. If parent_id provided:
           - Check parent exists
           - Check user has write permission on parent
           - Inherit department from parent if not specified
        3. Create folder
        4. Log AuditLog(action='CREATE_FOLDER')
        
        Args:
            name: Folder name (required, max 100 chars)
            user_id: Creator account ID
            parent_id: Optional parent folder ID
            description: Optional description
            access_scope: 'personal', 'department', or 'company' (default)
            department_id: Optional department association
        
        Returns:
            Created Folder object
        
        Raises:
            ValidationError: If inputs invalid
            NotFoundError: If parent not found
        """
        try:
            # Validate name
            if not name or not name.strip():
                raise ValidationError("Folder name is required")
            
            name = name.strip()
            if len(name) > 100:
                raise ValidationError("Folder name max 100 characters")
            
            # Validate access_scope
            valid_scopes = ['personal', 'department', 'company']
            if access_scope not in valid_scopes:
                raise ValidationError(f"invalid access_scope. Must be one of {valid_scopes}")

            user = self.Account.objects.filter(id=user_id).first()
            if not user:
                raise ValidationError(f"Account {user_id} not found")

            is_admin = user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            user_department_id = self._get_user_department_id(user_id)

            if not is_admin:
                if access_scope == 'company':
                    # Only users with FOLDER_CREATE + system_admin can create company-wide folders
                    raise ValidationError("Only system administrators can create company folders.")

                if access_scope == 'department':
                    effective_dept_id = department_id or user_department_id
                    if not effective_dept_id:
                        raise ValidationError("User has no department, cannot create a department folder.")

                    # Allow if user is a member of the target department OR manages it
                    is_own_dept = user_department_id and str(effective_dept_id) == str(user_department_id)
                    is_manager_of_dept = self._user_can_manage_department(user_id, effective_dept_id)

                    if not is_own_dept and not is_manager_of_dept:
                        raise ValidationError(
                            "You can only create folders in your own department or departments you manage."
                        )
                    department_id = effective_dept_id

                if access_scope == 'personal':
                    department_id = None
            
            # Resolve scope based on parent (similar to document upload logic)
            parent = None
            if parent_id:
                parent = self.repository.get_by_id(parent_id)
                if not parent:
                    raise NotFoundError(f"Parent folder {parent_id} not found")

                if not is_admin:
                    if parent.access_scope == 'company':
                        raise ValidationError("Only system administrators can create folders under company folders.")
                    if parent.access_scope == 'department':
                        parent_dept_id = parent.department_id
                        if not parent_dept_id:
                            raise ValidationError("Parent folder has no department set.")
                        is_own_dept = user_department_id and str(parent_dept_id) == str(user_department_id)
                        is_manager_of_dept = self._user_can_manage_department(user_id, str(parent_dept_id))
                        if not is_own_dept and not is_manager_of_dept:
                            raise ValidationError(
                                "You can only create sub-folders in your own department or departments you manage."
                            )
                    if parent.access_scope == 'personal':
                        if str(parent.created_by_id) != str(user_id):
                            raise ValidationError("You can only create subfolders under your own personal folders.")

                    # Subfolder inherits parent's scope
                    if access_scope != parent.access_scope:
                        raise ValidationError(
                            f"Subfolder cannot have different access_scope than parent. "
                            f"Parent has access_scope='{parent.access_scope}', "
                            f"but you requested '{access_scope}'. "
                            f"Subfolder will inherit parent's scope."
                        )

                    # CASE A: Parent has department → inherit parent's scope + department
                    if parent.department_id:
                        access_scope = parent.access_scope
                        if department_id and str(department_id) != str(parent.department_id):
                            raise ValidationError(
                                f"Subfolder cannot belong to different department than parent. "
                                f"Parent department: {parent.department_id}, "
                                f"you requested: {department_id}"
                            )
                        if not department_id:
                            department_id = parent.department_id

                        logger.info(
                            f"Subfolder '{name}' inheriting scope='{access_scope}' "
                            f"and department='{department_id}' from parent {parent_id}"
                        )
                    else:
                        # CASE B: Parent is company-wide or personal (no dept) → inherit parent scope
                        if parent.access_scope == 'personal':
                            access_scope = 'personal'
                            department_id = None
                        else:
                            access_scope = 'company'
                            department_id = None
                else:
                    # is_admin=True: inherit parent scope
                    if parent.access_scope == 'personal':
                        access_scope = 'personal'
                        department_id = None
                    elif parent.access_scope == 'department':
                        access_scope = 'department'
                        if not department_id:
                            department_id = parent.department_id
                    else:
                        access_scope = 'company'
                        department_id = None
            else:
                # No parent folder - CASE C/D
                if access_scope == 'department':
                    # CASE C: Department scope requires department_id
                    if not department_id:
                        department_id = user_department_id
                        if not department_id:
                            raise ValidationError("Department folder must have department_id")
                # CASE D: Company or personal scope - keep department_id as provided

            # Create folder
            folder = self.Folder(
                name=name,
                description=description,
                parent_id=parent_id,
                access_scope=access_scope,
                department_id=department_id,
                created_by_id=user_id,
            )

            folder.save()

            # Log audit
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.log_action(
                    account=user_account,
                    action='CREATE_FOLDER',
                    resource_id=str(folder.id),
                    query_text=f"Created folder: {name}",
                )
            except Exception as e:
                logger.warning(f"Failed to log CREATE_FOLDER action: {str(e)}")
            
            logger.info(f"Folder created: {folder.id} by user {user_id}")
            return folder
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise BusinessLogicError(f"Failed to create folder: {str(e)}")
    
    # ============================================================
    # UPDATE FOLDER
    # ============================================================
    
    @transaction.atomic
    def update_folder(
        self,
        folder_id: str,
        user_id: str,
        **update_data
    ) -> 'Folder':
        """
        Update folder metadata.
        
        Business Logic:
        1. Get folder
        2. Check user has write permission
        3. Validate update data
        4. Update folder
        5. Log AuditLog
        
        Allowed fields to update:
        - name
        - description
        - access_scope
        - department_id (careful - affects permissions!)
        
        Args:
            folder_id: Folder to update
            user_id: User performing update
            **update_data: Fields to update
        
        Returns:
            Updated Folder object
        """
        try:
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'write'):
                logger.warning(f"User {user_id} attempted to update folder {folder_id} created by {folder.created_by_id}")
                raise PermissionDeniedError("You don't have write permission on this folder")
            
            # Validate and apply updates
            allowed_fields = {'name', 'description', 'access_scope', 'department_id'}
            for key, value in update_data.items():
                if key not in allowed_fields:
                    logger.warning(f"Attempting to update disallowed field: {key}")
                    continue
                
                if key == 'name' and value:
                    value = value.strip()
                    if len(value) > 100:
                        raise ValidationError("Folder name max 100 characters")
                    setattr(folder, key, value)
                elif key in ['description', 'access_scope', 'department_id']:
                    setattr(folder, key, value)
            
            folder.save()
            
            # Log audit
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.log_action(
                    account=user_account,
                    action='UPDATE_FOLDER',
                    resource_id=str(folder_id),
                    query_text=f"Updated folder metadata",
                )
            except Exception as e:
                logger.warning(f"Failed to log UPDATE_FOLDER action: {str(e)}")
            
            logger.info(f"Folder updated: {folder_id} by user {user_id}")
            return folder
            
        except (ValidationError, NotFoundError, PermissionDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error updating folder: {str(e)}")
            raise BusinessLogicError(f"Failed to update folder: {str(e)}")
    
    # ============================================================
    # DELETE FOLDER (SOFT DELETE - RECURSIVE)
    # ============================================================
    
    @transaction.atomic
    def delete_folder_recursive(
        self,
        folder_id: str,
        user_id: str,
    ) -> None:
        """
        Delete folder and all contents (soft delete).
        
        Business Logic:
        1. Get folder
        2. Check user has delete permission
        3. Get all descendants (folders + documents)
        4. Soft delete all in transaction
        5. Invalidate caches
        6. Log AuditLog
        
        Args:
            folder_id: Folder to delete
            user_id: User performing deletion
        
        Raises:
            NotFoundError: If folder not found
            PermissionDeniedError: If user not authorized
        """
        try:
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'delete'):
                logger.warning(f"User {user_id} attempted to delete folder {folder_id} created by {folder.created_by_id}")
                raise PermissionDeniedError("You don't have delete permission on this folder")
            
            # Get all descendant folder IDs
            folder_ids_to_delete = self.repository.get_all_folder_ids_for_cascade_delete(folder_id)
            
            # Soft delete all folders
            self.Folder.objects.filter(id__in=folder_ids_to_delete).update(
                is_deleted=True,
                deleted_at=timezone.now(),
            )
            
            # TODO: Handle documents inside those folders
            # - Get all document IDs in those folders
            # - Soft delete documents
            # - Sync Qdrant to remove vectors
            # - Invalidate UserDocumentCache
            
            # Log audit
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.log_action(
                    account=user_account,
                    action='DELETE_FOLDER',
                    resource_id=str(folder_id),
                    query_text=f"Deleted folder recursively (affected {len(folder_ids_to_delete)} folders)",
                )
            except Exception as e:
                logger.warning(f"Failed to log DELETE_FOLDER action: {str(e)}")
            
            logger.info(f"Folder deleted recursively: {folder_id} by user {user_id} (affected {len(folder_ids_to_delete)} folders)")
            
        except (NotFoundError, PermissionDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error deleting folder: {str(e)}")
            raise BusinessLogicError(f"Failed to delete folder: {str(e)}")
    
    # ============================================================
    # MOVE FOLDER
    # ============================================================
    
    @transaction.atomic
    def move_folder(
        self,
        folder_id: str,
        new_parent_id: Optional[str],
        user_id: str,
    ) -> 'Folder':
        """
        Move folder to different parent (or root if new_parent_id=None).
        
        Business Logic:
        1. Get folder
        2. Check for circular reference
        3. Check user has move permission
        4. Update parent_id
        5. Inherit department from new parent if needed
        6. Invalidate caches (permissions may have changed)
        7. Log AuditLog
        
        Args:
            folder_id: Folder to move
            new_parent_id: New parent ID (None = make root)
            user_id: User performing move
        
        Returns:
            Updated Folder object
        
        Raises:
            ValidationError: If circular reference would be created
            NotFoundError: If folder or parent not found
        """
        try:
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'write'):
                logger.warning(f"User {user_id} attempted to move folder {folder_id} created by {folder.created_by_id}")
                raise PermissionDeniedError("You don't have write permission on this folder")
            
            # Check circular reference
            if self.repository.check_circular_reference(folder_id, new_parent_id):
                raise ValidationError("Cannot move folder to its own subfolder (circular reference)")
            
            # Validate new parent
            if new_parent_id:
                new_parent = self.repository.get_by_id(new_parent_id)
                if not new_parent:
                    raise NotFoundError(f"New parent folder {new_parent_id} not found")
            else:
                new_parent = None
            
            # Update parent
            folder.parent_id = new_parent_id
            
            # Inherit department from new parent if applicable
            if new_parent and new_parent.department_id:
                folder.department_id = new_parent.department_id
            
            folder.save()
            
            # TODO: Invalidate cache for all documents in this folder
            # (permissions may have changed due to inherited folder permissions)
            
            # Log audit
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.log_action(
                    account=user_account,
                    action='MOVE_FOLDER',
                    resource_id=str(folder_id),
                    query_text=f"Moved folder to parent {new_parent_id}",
                )
            except Exception as e:
                logger.warning(f"Failed to log MOVE_FOLDER action: {str(e)}")
            
            logger.info(f"Folder moved: {folder_id} to parent {new_parent_id} by user {user_id}")
            return folder
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error moving folder: {str(e)}")
            raise BusinessLogicError(f"Failed to move folder: {str(e)}")
    
    # ============================================================
    # FOLDER PERMISSIONS (Phase 4B)
    # ============================================================
    
    @transaction.atomic
    def grant_permission(
        self,
        user_id: str,
        folder_id: str,
        subject_type: str,
        subject_id: str,
        permission: str
    ) -> Dict[str, Any]:
        """
        Grant permission to folder for account or role.
        
        Business Logic:
        1. Check folder exists
        2. Check user is creator or admin (only creator can grant)
        3. Validate subject (account or role exists)
        4. Create or update FolderPermission record
        5. Log audit entry
        
        Args:
            user_id: User granting permission (must be creator)
            folder_id: Target folder UUID
            subject_type: 'account' or 'role'
            subject_id: Account/Role UUID
            permission: 'read', 'write', or 'delete'
        
        Returns:
            Created/updated FolderPermission dict
        
        Raises:
            ValidationError: Invalid inputs
            NotFoundError: Folder/subject not found
            PermissionDeniedError: User not authorized to grant
        """
        try:
            # Get folder
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'delete'):
                raise PermissionDeniedError(
                    f"Only users with delete permission can grant permissions. "
                    f"Folder creator: {folder.created_by_id}, Current user: {user_id}"
                )
            
            # Validate subject exists
            valid_permission = permission in ['read', 'write', 'delete']
            if not valid_permission:
                raise ValidationError(
                    f"Invalid permission '{permission}'. "
                    f"Must be 'read', 'write', or 'delete'"
                )
            
            if subject_type == 'account':
                subject = self.Account.objects.filter(id=subject_id).first()
                if not subject:
                    raise ValidationError(f"Account {subject_id} not found")
            elif subject_type == 'role':
                Role = apps.get_model('users', 'Role')
                subject = Role.objects.filter(id=subject_id).first()
                if not subject:
                    raise ValidationError(f"Role {subject_id} not found")
            else:
                raise ValidationError(
                    f"Invalid subject_type '{subject_type}'. "
                    f"Must be 'account' or 'role'"
                )
            
            # Create or update permission
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            user_account = self.Account.objects.get(id=user_id)
            perm, created = FolderPermission.objects.get_or_create(
                folder_id=folder_id,
                subject_type=subject_type,
                subject_id=subject_id,
                defaults={'permission': permission, 'is_active': True, 'granted_by': user_account}
            )
            
            if not created:
                # Update existing permission
                perm.permission = permission
                perm.is_active = True
                perm.granted_by = user_account
                perm.save()
            
            # Audit log
            try:
                self.AuditLog.objects.create(
                    account=user_account,
                    action='GRANT_PERMISSION',
                    resource_id=str(folder_id),
                    query_text=f"Granted {permission} permission to {subject_type} {subject_id}",
                )
            except Exception as e:
                logger.warning(f"Failed to log GRANT_PERMISSION action: {str(e)}")
            
            logger.info(
                f"Permission granted: {subject_type}:{subject_id} → {permission} "
                f"on folder {folder_id} by user {user_id}"
            )
            
            return {
                'id': str(perm.id),
                'folder_id': str(perm.folder_id),
                'subject_type': perm.subject_type,
                'subject_id': perm.subject_id,
                'subject_name': subject.username if subject_type == 'account' else subject.name,
                'permission': perm.permission,
                'is_active': perm.is_active,
                'granted_by_id': str(perm.granted_by_id) if perm.granted_by_id else None,
                'granted_by_username': perm.granted_by.username if perm.granted_by else None,
                'created': created,
                'created_at': perm.created_at.isoformat() if perm.created_at else None,
            }
            
        except (ValidationError, NotFoundError, PermissionDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error granting permission: {str(e)}")
            raise BusinessLogicError(f"Failed to grant permission: {str(e)}")
    
    @transaction.atomic
    def revoke_permission(
        self,
        user_id: str,
        folder_id: str,
        permission_id: str
    ) -> bool:
        """
        Revoke permission to folder.
        
        Business Logic:
        1. Check folder exists
        2. Check user is creator or admin (only creator can revoke)
        3. Check permission exists and belongs to folder
        4. Soft-delete FolderPermission record
        5. Log audit entry
        
        Args:
            user_id: User revoking permission (must be creator)
            folder_id: Target folder UUID
            permission_id: FolderPermission record UUID
        
        Returns:
            True if revoked successfully
        
        Raises:
            ValidationError: Invalid inputs
            NotFoundError: Folder/permission not found
            PermissionDeniedError: User not authorized to revoke
        """
        try:
            # Get folder
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'delete'):
                raise PermissionDeniedError(
                    f"Only users with delete permission can revoke permissions. "
                    f"Folder creator: {folder.created_by_id}, Current user: {user_id}"
                )
            
            # Get and verify permission
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            perm = FolderPermission.objects.filter(
                id=permission_id,
                folder_id=folder_id,
                is_deleted=False
            ).first()
            
            if not perm:
                raise NotFoundError(
                    f"Permission {permission_id} not found for folder {folder_id}"
                )
            
            # Soft-delete the permission
            perm.is_deleted = True
            perm.deleted_at = timezone.now()
            perm.save()
            
            # Audit log
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.objects.create(
                    account=user_account,
                    action='REVOKE_PERMISSION',
                    resource_id=str(folder_id),
                    query_text=f"Revoked permission {perm.id} ({perm.subject_type}:{perm.subject_id})",
                )
            except Exception as e:
                logger.warning(f"Failed to log REVOKE_PERMISSION action: {str(e)}")
            
            logger.info(
                f"Permission revoked: {perm.subject_type}:{perm.subject_id} "
                f"from folder {folder_id} by user {user_id}"
            )
            
            return True
            
        except (ValidationError, NotFoundError, PermissionDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error revoking permission: {str(e)}")
            raise BusinessLogicError(f"Failed to revoke permission: {str(e)}")
    
    def get_folder_permissions(self, folder_id: str, granted_by_id: str = None) -> Dict[str, Any]:
        """
        Get all active permissions for a folder.
        
        Args:
            folder_id: Target folder UUID
            granted_by_id: Optional user ID who granted the permission
        
        Returns:
            Dict with folder info and list of permissions
        
        Raises:
            NotFoundError: Folder not found
        """
        try:
            # Get folder
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            # Get active permissions
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            permissions = FolderPermission.objects.filter(
                folder_id=folder_id,
                is_deleted=False,
                is_active=True,
            )
            if granted_by_id:
                permissions = permissions.filter(granted_by_id=granted_by_id)
            permissions = permissions.order_by('created_at')
            
            # Build response
            perm_list = []
            for perm in permissions:
                # Get subject name
                subject_name = None
                if perm.subject_type == 'account':
                    account = self.Account.objects.filter(id=perm.subject_id).first()
                    subject_name = account.username if account else 'Unknown'
                elif perm.subject_type == 'role':
                    Role = apps.get_model('users', 'Role')
                    role = Role.objects.filter(id=perm.subject_id).first()
                    subject_name = role.name if role else 'Unknown'
                
                granted_by_username = perm.granted_by.username if perm.granted_by else None
                
                perm_list.append({
                    'id': str(perm.id),
                    'subject_type': perm.subject_type,
                    'subject_id': perm.subject_id,
                    'subject_name': subject_name,
                    'permission': perm.permission,
                    'is_active': perm.is_active,
                    'granted_by_id': str(perm.granted_by_id) if perm.granted_by_id else None,
                    'granted_by_username': granted_by_username,
                    'created_at': perm.created_at.isoformat() if perm.created_at else None,
                })
            
            return {
                'folder_id': str(folder.id),
                'folder_name': folder.name,
                'access_scope': folder.access_scope,
                'permissions': perm_list,
                'total_permissions': len(perm_list),
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting folder permissions: {str(e)}")
            raise BusinessLogicError(f"Failed to get permissions: {str(e)}")

    def list_folder_permissions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: str = None,
        granted_by_id: str = None,
    ) -> Dict[str, Any]:
        """
        Get a paginated list of folders with their active permissions.

        Only folders the current user can manage are included.
        """
        try:
            Account = apps.get_model('users', 'Account')
            Folder = apps.get_model('documents', 'Folder')
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            Role = apps.get_model('users', 'Role')
            
            user = self.Account.objects.filter(id=user_id).first()
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            managed_folders = []

            # When granted_by_id is provided, get all folders where user has granted permissions
            if granted_by_id:
                folder_ids_with_perms = FolderPermission.objects.filter(
                    granted_by_id=granted_by_id,
                    is_deleted=False,
                    is_active=True,
                ).values_list('folder_id', flat=True).distinct()
                
                folders_query = Folder.objects.filter(
                    id__in=folder_ids_with_perms,
                    is_deleted=False
                ).order_by('-created_at')
                
                if search and search.strip():
                    folders_query = folders_query.filter(name__icontains=search)
                
                managed_folders = list(folders_query)
            else:
                # Without granted_by_id, show only accessible folders
                accessible_folders = self.repository.get_accessible_folders(
                    user_id=user_id,
                    user_department_id=user.department_id if hasattr(user, 'department_id') else None,
                    is_admin=getattr(user, 'is_superuser', False),
                )

                for folder in accessible_folders:
                    if search and search.strip() and search.lower() not in (folder.name or '').lower():
                        continue

                    if str(folder.created_by_id) == str(user_id) or self.check_folder_permission(folder.id, user_id, 'write'):
                        managed_folders.append(folder)

            # Filter managed folders to only those that have active permission rows
            managed_with_perms = []
            for folder in managed_folders:
                permissions_query = FolderPermission.objects.filter(
                    folder_id=folder.id,
                    is_deleted=False,
                    is_active=True,
                )
                if granted_by_id:
                    permissions_query = permissions_query.filter(granted_by_id=granted_by_id)

                if not permissions_query.exists():
                    continue

                managed_with_perms.append(folder)

            total_items = len(managed_with_perms)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_folders = managed_with_perms[start_index:end_index]

            items = []
            for folder in page_folders:
                permissions = FolderPermission.objects.filter(
                    folder_id=folder.id,
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
                        'is_active': perm.is_active,
                        'granted_by_id': str(perm.granted_by_id) if perm.granted_by_id else None,
                        'granted_by_username': granted_by_username,
                        'created_at': perm.created_at.isoformat() if perm.created_at else None,
                    })

                items.append({
                    'folder_id': str(folder.id),
                    'folder_name': folder.name,
                    'access_scope': folder.access_scope,
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

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error listing folder permissions: {str(e)}")
            raise BusinessLogicError(f"Failed to list folder permissions: {str(e)}")
    
    @transaction.atomic
    def revoke_permission_by_subject(
        self,
        user_id: str,
        folder_id: str,
        subject_type: str,
        subject_id: str,
        permission: str
    ) -> bool:
        """
        Revoke permission to folder using subject identity.
        
        Uses the unique constraint: (folder_id, subject_type, subject_id)
        to identify the exact permission record to delete.
        
        Business Logic:
        1. Check folder exists
        2. Check user is creator (only creator can revoke)
        3. Check permission exists for this subject on folder
        4. Soft-delete FolderPermission record
        5. Log audit entry
        
        Args:
            user_id: User revoking permission (must be creator)
            folder_id: Target folder UUID
            subject_type: "account" or "role"
            subject_id: UUID of account or role
            permission: "read", "write", or "delete"
        
        Returns:
            True if revoked successfully
        
        Raises:
            ValidationError: Invalid inputs
            NotFoundError: Folder/permission not found
            PermissionDeniedError: User not authorized to revoke
        """
        try:
            # Get folder
            folder = self.repository.get_by_id(folder_id)
            if not folder:
                raise NotFoundError(f"Folder {folder_id} not found")
            
            if not self.check_folder_permission(folder_id, user_id, 'delete'):
                raise PermissionDeniedError(
                    f"Only users with delete permission can revoke permissions. "
                    f"Folder creator: {folder.created_by_id}, Current user: {user_id}"
                )
            
            # Get and verify permission using unique constraint
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            perm = FolderPermission.objects.filter(
                folder_id=folder_id,
                subject_type=subject_type,
                subject_id=subject_id,
                permission=permission,
                is_deleted=False
            ).first()
            
            if not perm:
                raise NotFoundError(
                    f"Permission not found: {subject_type}:{subject_id} has no '{permission}' "
                    f"access to folder {folder_id}"
                )
            
            # Soft-delete the permission
            perm.is_deleted = True
            perm.deleted_at = timezone.now()
            perm.save()
            
            # Audit log
            try:
                user_account = self.Account.objects.get(id=user_id)
                self.AuditLog.objects.create(
                    account=user_account,
                    action='REVOKE_PERMISSION',
                    resource_id=str(folder_id),
                    query_text=f"Revoked {permission} permission from {subject_type}:{subject_id}",
                )
            except Exception as e:
                logger.warning(f"Failed to log REVOKE_PERMISSION action: {str(e)}")
            
            logger.info(
                f"Permission revoked: {subject_type}:{subject_id} "
                f"'{permission}' from folder {folder_id} by user {user_id}"
            )
            
            return True
            
        except (ValidationError, NotFoundError, PermissionDeniedError):
            raise
        except Exception as e:
            logger.error(f"Error revoking permission by subject: {str(e)}")
            raise BusinessLogicError(f"Failed to revoke permission: {str(e)}")
