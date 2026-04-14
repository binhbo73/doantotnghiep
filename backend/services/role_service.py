"""
Role Service
============
Business logic for Role management (CRUD operations)

Responsibilities:
- Create new roles with permissions assignment
- Update role details and permissions
- Delete roles (soft delete)
- List roles with filtering
- Validate role uniqueness and permissions

Uses:
- RoleRepository (data access)
- PermissionRepository (permission validation)
- AuditService (audit logging)

Design:
- No direct ORM queries - all via Repository
- All changes logged to AuditLog
- Soft delete pattern (is_deleted=True)
- Transaction-aware for consistency
"""

import logging
from typing import List, Dict, Optional, Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from repositories.role_repository import RoleRepository
from repositories.permission_repository import PermissionRepository
from services.audit_service import AuditService
from services.base_service import BaseService
from apps.users.models import AccountRole
from core.exceptions import (
    ValidationError,
    BusinessLogicError,
    NotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class RoleService(BaseService):
    """
    Service for Role management
    
    Key Methods:
    - list_roles(page, page_size, filters)
    - create_role(data, requested_by_user_id)
    - update_role(role_id, data, requested_by_user_id)
    - delete_role(role_id, requested_by_user_id)
    - get_role_details(role_id)
    - check_role_exists(role_code)
    
    All operations are atomic (transaction-aware)
    All changes are audited via AuditService
    Soft delete pattern follows backend conventions
    """
    
    repository_class = RoleRepository
    
    def __init__(self):
        """Initialize with required repositories and services"""
        super().__init__()
        self.role_repo = self.repository  # From base (RoleRepository)
        self.permission_repo = PermissionRepository()
        self.audit_service = AuditService()
    
    # ============================================================================
    # READ OPERATIONS
    # ============================================================================
    
    def list_roles(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List all active roles with pagination and filtering.
        
        Business Rules:
        - Only return non-deleted roles (is_deleted=False)
        - Support search by name/code
        - Return permission count for each role
        - Paginated responses
        
        Args:
            page: Page number (1-based)
            page_size: Items per page
            search: Search by name/code
            filters: Additional filters (e.g., {'department_id': uuid})
        
        Returns:
            {
                'roles': [
                    {
                        'id': 'uuid',
                        'code': 'admin',
                        'name': 'Administrator',
                        'description': '...',
                        'permission_count': 45,
                        'account_count': 3,
                        'created_at': '2024-01-01T00:00:00Z',
                        'modified_at': '2024-01-02T00:00:00Z'
                    }
                ],
                'pagination': {
                    'page': 1,
                    'page_size': 20,
                    'total': 5,
                    'total_pages': 1
                }
            }
        
        Raises:
            ValidationError: If page/page_size invalid
        """
        try:
            # Validate pagination
            if page < 1:
                raise ValidationError("Page must be >= 1")
            if page_size < 1 or page_size > 100:
                raise ValidationError("Page size must be between 1 and 100")
            
            # Get paginated roles
            result = self.role_repo.list_with_pagination(
                page=page,
                page_size=page_size,
                search=search,
                filters=filters
            )
            
            logger.info(
                f"Listed roles: page={page}, page_size={page_size}, "
                f"total={result['pagination']['total']}"
            )
            
            return result
            
        except Exception as e:
            self.log_error('list_roles', e, page=page, page_size=page_size)
            raise
    
    def get_role_details(self, role_id: UUID) -> Dict[str, Any]:
        """
        Get full role details including all permissions and accounts.
        
        Args:
            role_id: Role ID (UUID)
        
        Returns:
            {
                'id': 'uuid',
                'code': 'admin',
                'name': 'Administrator',
                'description': '...',
                'is_system': True,
                'permissions': [
                    {'id': 'uuid', 'code': 'user_read', 'resource': 'user', 'action': 'read'},
                    ...
                ],
                'assigned_accounts': 5,
                'created_at': '2024-01-01T00:00:00Z',
                'modified_at': '2024-01-02T00:00:00Z'
            }
        
        Raises:
            NotFoundError: If role not found
        """
        try:
            # Get role with permissions prefetched
            role = self.role_repo.get_role_with_permissions(role_id)
            
            if not role or role.is_deleted:
                raise NotFoundError(f"Role {role_id} not found")
            
            # Return structured data
            return {
                'id': str(role.id),
                'code': role.code,
                'name': role.name,
                'description': role.description,
                'is_system': role.is_system_role,
                'permissions': [
                    {
                        'id': str(p.permission.id),
                        'code': p.permission.code,
                        'resource': p.permission.resource,
                        'action': p.permission.action,
                        'description': p.permission.description
                    }
                    for p in role.get_permissions()  # Returns RolePermission objects
                ],
                'assigned_accounts': AccountRole.objects.filter(
                    role_id=role_id,
                    is_deleted=False
                ).count(),
                'created_at': role.created_at.isoformat() if role.created_at else None,
                'modified_at': role.updated_at.isoformat() if role.updated_at else None
            }
            
        except Exception as e:
            self.log_error('get_role_details', e)
            raise
    
    def check_role_exists(self, role_code: str) -> bool:
        """
        Check if role with given code exists and is active.
        
        Args:
            role_code: Role code (e.g., 'admin', 'manager')
        
        Returns:
            True if role exists and not deleted
        """
        try:
            role = self.role_repo.get_by_code(role_code)
            return role is not None and not role.is_deleted
        except Exception as e:
            logger.error(f"Error checking role existence: {e}")
            return False
    
    # ============================================================================
    # WRITE OPERATIONS
    # ============================================================================
    
    def create_role(
        self,
        data: Dict[str, Any],
        requested_by_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create new role with permissions assignment.
        
        Business Rules:
        - Role code must be unique (case-insensitive)
        - Role name must be unique (case-insensitive)
        - Cannot create system roles (is_system=True)
        - At least one permission should be assigned (warning only)
        - All permission IDs must exist and not be deleted
        
        Args:
            data: {
                'code': 'custom_role',
                'name': 'Custom Role',
                'description': 'My custom role description',
                'permissions': ['uuid1', 'uuid2', ...]  # Optional
            }
            requested_by_user_id: Who is creating (for audit)
        
        Returns:
            {
                'id': 'uuid',
                'code': 'custom_role',
                'name': 'Custom Role',
                'permissions': [...]
            }
        
        Raises:
            ValidationError: If data invalid or role already exists
            PermissionDeniedError: If trying to create system role
        """
        try:
            # Validate required fields
            role_code = data.get('code', '').strip().lower()
            role_name = data.get('name', '').strip()
            role_description = data.get('description', '').strip()
            permission_data = data.get('permissions', [])  # Can be Permission instances or UUIDs
            
            if not role_code or len(role_code) < 2:
                raise ValidationError("Role code must be at least 2 characters")
            
            if not role_name or len(role_name) < 2:
                raise ValidationError("Role name must be at least 2 characters")
            
            # Check uniqueness
            if self.role_repo.get_by_code(role_code):
                raise ValidationError(f"Role code '{role_code}' already exists")
            
            if self.check_role_exists(role_code):
                raise ValidationError(f"Role '{role_name}' already exists")
            
            # Validate and convert permissions (handle both Permission instances and UUID strings)
            validated_permissions = []
            if permission_data:
                for perm in permission_data:
                    try:
                        # If it's a Permission instance, extract the ID
                        if hasattr(perm, 'id'):
                            perm_id = perm.id
                        else:
                            # Otherwise assume it's a UUID string
                            perm_id = UUID(perm)
                        
                        # Verify permission exists and is not deleted
                        perm_obj = self.permission_repo.get_by_id(perm_id)
                        if not perm_obj or perm_obj.is_deleted:
                            raise ValidationError(f"Permission not found or deleted")
                        validated_permissions.append(perm_id)
                    except (ValueError, TypeError, AttributeError) as e:
                        raise ValidationError(f"Invalid permission ID format")
            
            # Create role in transaction
            with transaction.atomic():
                # Create role
                role = self.role_repo.create(
                    code=role_code,
                    name=role_name,
                    description=role_description,
                    is_system_role=False,
                    is_deleted=False,
                    created_at=timezone.now()
                )
                
                # Add permissions if provided
                if validated_permissions:
                    self.role_repo.add_permissions(role.id, validated_permissions)
                
                logger.info(f"Role created: {role_code}")
            
            # Return role with permissions
            return self.get_role_details(role.id)
            
        except Exception as e:
            self.log_error('create_role', e)
            raise
    
    def update_role(
        self,
        role_id: UUID,
        data: Dict[str, Any],
        requested_by_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update existing role (name, description, permissions).
        
        Business Rules:
        - Cannot update system roles (is_system=True, raises PermissionDeniedError)
        - Cannot update role code (immutable after creation)
        - Can update permissions (add/remove)
        - Cannot update deleted roles
        
        Args:
            role_id: Role ID to update (UUID)
            data: {
                'name': 'Updated Name',  # Optional
                'description': 'Updated description',  # Optional
                'permissions': ['uuid1', 'uuid2', ...]  # Optional (replaces existing)
            }
            requested_by_user_id: Who is updating (for audit)
        
        Returns:
            Updated role data
        
        Raises:
            NotFoundError: If role not found
            PermissionDeniedError: If system role
            ValidationError: If data invalid
        """
        try:
            # Get existing role
            role = self.role_repo.get_by_id(role_id)
            if not role or role.is_deleted:
                raise NotFoundError(f"Role {role_id} not found")
            
            # Check if system role
            if role.is_system_role:
                raise PermissionDeniedError(
                    f"Cannot modify system role '{role.code}'"
                )
            
            # Prepare updates
            updates = {}
            
            if 'name' in data:
                new_name = data['name'].strip()
                if not new_name or len(new_name) < 2:
                    raise ValidationError("Role name must be at least 2 characters")
                updates['name'] = new_name
            
            if 'description' in data:
                updates['description'] = data.get('description', '').strip()
            
            # Handle permission updates (handle both Permission instances and UUID strings)
            new_permissions = []
            if 'permissions' in data:
                permission_data = data['permissions'] or []
                for perm in permission_data:
                    try:
                        # If it's a Permission instance, extract the ID
                        if hasattr(perm, 'id'):
                            perm_id = perm.id
                        else:
                            # Otherwise assume it's a UUID string
                            perm_id = UUID(perm)
                        
                        # Verify permission exists and is not deleted
                        perm_obj = self.permission_repo.get_by_id(perm_id)
                        if not perm_obj or perm_obj.is_deleted:
                            raise ValidationError(f"Permission not found or deleted")
                        new_permissions.append(perm_id)
                    except (ValueError, TypeError, AttributeError) as e:
                        raise ValidationError(f"Invalid permission ID format")
            
            # Update in transaction
            with transaction.atomic():
                # Update role fields
                if updates:
                    self.role_repo.update(role_id, **updates)
                
                # Update permissions if provided
                if 'permissions' in data:
                    # Remove old permissions
                    existing_perms = set(
                        p.permission_id for p in role.get_permissions()  # RolePermission -> permission_id
                    )
                    new_perms_set = set(new_permissions)
                    
                    # Remove permissions not in new list
                    to_remove = existing_perms - new_perms_set
                    if to_remove:
                        self.role_repo.remove_permissions(role_id, list(to_remove))
                    
                    # Add new permissions
                    to_add = new_perms_set - existing_perms
                    if to_add:
                        self.role_repo.add_permissions(role_id, list(to_add))
                
                logger.info(f"Role updated: {role.code}")
            
            # Return updated role
            return self.get_role_details(role_id)
            
        except Exception as e:
            self.log_error('update_role', e)
            raise
    
    def delete_role(
        self,
        role_id: UUID,
        requested_by_user_id: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Soft delete role (CANNOT BE UNDONE in current design).
        
        Business Rules:
        - Cannot delete system roles (is_system=True)
        - Cannot delete already deleted roles
        - When role deleted, all assignments are removed
        - Users assigned to role lose access (move to DEFAULT_USER_ROLE)
        - Audit log preserved
        
        Args:
            role_id: Role ID to delete (UUID)
            requested_by_user_id: Who is deleting (for audit)
        
        Returns:
            {'message': 'Role deleted successfully'}
        
        Raises:
            NotFoundError: If role not found
            PermissionDeniedError: If system role or already deleted
        """
        try:
            # Get role
            role = self.role_repo.get_by_id(role_id)
            if not role or role.is_deleted:
                raise NotFoundError(f"Role {role_id} not found or already deleted")
            
            # Check if system role
            if role.is_system_role:
                raise PermissionDeniedError(
                    f"Cannot delete system role '{role.code}'"
                )
            
            # Delete in transaction
            with transaction.atomic():
                # Get accounts with this role (for audit)
                accounts_affected = self.role_repo.get_accounts_with_role(role_id)
                accounts_count = len(accounts_affected) if accounts_affected else 0
                
                # Soft delete role
                self.role_repo.update(
                    role_id,
                    is_deleted=True,
                    deleted_at=timezone.now()
                )
                
                # Remove role from all accounts
                if accounts_count > 0:
                    self.role_repo.remove_role_from_all_accounts(role_id)
                

                
            
            return {'message': f"Role '{role.code}' deleted successfully"}
            
        except Exception as e:
            self.log_error('delete_role', e)
            raise
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def sync_permissions_for_role(
        self,
        role_id: UUID,
        permission_ids: List[UUID]
    ) -> bool:
        """
        Synchronize role permissions (replace all with provided list).
        
        Removes old permissions and adds new ones in single transaction.
        
        Args:
            role_id: Role ID
            permission_ids: List of permission IDs to assign
        
        Returns:
            True if successful
        """
        try:
            role = self.role_repo.get_by_id(role_id)
            if not role:
                raise NotFoundError(f"Role {role_id} not found")
            
            with transaction.atomic():
                # Remove all current permissions
                self.role_repo.remove_all_permissions(role_id)
                
                # Add new permissions
                if permission_ids:
                    self.role_repo.add_permissions(role_id, permission_ids)
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing permissions for role {role_id}: {e}")
            raise
    
    def get_role_permissions(
        self,
        role_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str = ''
    ) -> Dict[str, Any]:
        """
        Get paginated list of permissions assigned to a role.
        
        Args:
            role_id: Role ID (UUID)
            page: Page number
            page_size: Items per page
            search: Search filter
        
        Returns:
            {
                'permissions': [...],
                'pagination': {...}
            }
        
        Raises:
            NotFoundError: If role not found
        """
        try:
            # Verify role exists
            role = self.role_repo.get_by_id(role_id)
            if not role or role.is_deleted:
                raise NotFoundError(f"Role {role_id} not found")
            
            # Get paginated permissions
            result = self.permission_repo.list_permissions_paginated(
                page=page,
                page_size=page_size,
                search=search,
                role_id=role_id  # Filter by role
            )
            
            logger.info(
                f"Retrieved permissions for role {role_id}: "
                f"page={page}, count={len(result['permissions'])}"
            )
            
            return result
            
        except Exception as e:
            self.log_error('get_role_permissions', e)
            raise
    
    def add_permission_to_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        requested_by_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add a permission to a role.
        
        Args:
            role_id: Role ID (UUID or string)
            permission_id: Permission ID (UUID or string)
            requested_by_user_id: Who is making change (for audit)
        
        Returns:
            {
                'role_id': 'uuid',
                'permission_id': 'uuid',
                'total_permissions': 15
            }
        
        Raises:
            NotFoundError: If role or permission not found
            ValidationError: If permission already assigned
            PermissionDeniedError: If system role
        """
        try:
            # Convert IDs to UUID if they're strings
            if isinstance(role_id, str):
                role_id = UUID(role_id)
            if isinstance(permission_id, str):
                permission_id = UUID(permission_id)
            
            # Verify role exists
            role = self.role_repo.get_by_id(role_id)
            if not role or role.is_deleted:
                raise NotFoundError(f"Role not found")
            
            # Verify not system role
            if role.is_system_role:
                raise PermissionDeniedError(
                    f"Cannot modify system role '{role.code}'"
                )
            
            # Verify permission exists
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission or permission.is_deleted:
                raise NotFoundError(f"Permission not found")
            
            # Check if already assigned
            existing_perms = [p.permission_id for p in role.get_permissions()]  # RolePermission -> permission_id
            if permission_id in existing_perms:
                raise ValidationError(
                    f"Permission already assigned to role"
                )
            
            # Add permission
            with transaction.atomic():
                self.role_repo.add_permissions(role_id, [permission_id])
            
            # Get updated permission count using the proper relationship
            from apps.users.models import RolePermission
            new_count = RolePermission.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).count()
            
            logger.info(
                f"Added permission to role, total permissions now: {new_count}"
            )
            
            return {
                'role_id': str(role_id),
                'permission_id': str(permission_id),
                'total_permissions': new_count
            }
            
        except Exception as e:
            self.log_error(
                'add_permission_to_role',
                e
            )
            raise
    
    def remove_permission_from_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        requested_by_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Remove a permission from a role.
        
        Args:
            role_id: Role ID (UUID or string)
            permission_id: Permission ID (UUID or string)
            requested_by_user_id: Who is making change (for audit)
        
        Returns:
            {
                'role_id': 'uuid',
                'permission_id': 'uuid',
                'total_permissions': 14
            }
        
        Raises:
            NotFoundError: If role or permission not found
            PermissionDeniedError: If system role
        """
        try:
            # Convert IDs to UUID if they're strings
            if isinstance(role_id, str):
                role_id = UUID(role_id)
            if isinstance(permission_id, str):
                permission_id = UUID(permission_id)
            
            # Verify role exists
            role = self.role_repo.get_by_id(role_id)
            if not role or role.is_deleted:
                raise NotFoundError(f"Role not found")
            
            # Verify not system role
            if role.is_system_role:
                raise PermissionDeniedError(
                    f"Cannot modify system role '{role.code}'"
                )
            
            # Verify permission exists
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission or permission.is_deleted:
                raise NotFoundError(f"Permission not found")
            
            # Check if assigned
            existing_perms = [p.permission_id for p in role.get_permissions()]  # RolePermission -> permission_id
            if permission_id not in existing_perms:
                raise NotFoundError(
                    f"Permission not assigned to role"
                )
            
            # Remove permission
            with transaction.atomic():
                self.role_repo.remove_permissions(role_id, [permission_id])
            
            # Get updated permission count using the proper relationship
            from apps.users.models import RolePermission
            new_count = RolePermission.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).count()
            
            logger.info(
                f"Removed permission from role, total permissions now: {new_count}"
            )
            
            return {
                'role_id': str(role_id),
                'permission_id': str(permission_id),
                'total_permissions': new_count
            }
            
        except Exception as e:
            self.log_error(
                'remove_permission_from_role',
                e
            )
            raise
    
    def check_user_permission(
        self,
        user_id: UUID,
        permission_code: str
    ) -> Dict[str, Any]:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: User ID (UUID)
            permission_code: Permission code to check (e.g., 'user_read')
        
        Returns:
            {
                'user_id': 'uuid',
                'permission_code': 'user_read',
                'has_permission': True,
                'granted_via_roles': ['admin', 'manager'],
                'message': 'User has user_read permission via roles: admin, manager'
            }
        
        Raises:
            NotFoundError: If user not found
            ValidationError: If permission code not found
        """
        try:
            from apps.users.models import User, AccountRole
            
            # Get user
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                raise NotFoundError(f"User {user_id} not found")
            
            # Get permission
            permission = self.permission_repo.get_by_code(permission_code)
            if not permission or permission.is_deleted:
                raise ValidationError(f"Permission '{permission_code}' not found")
            
            # Get user's roles
            user_roles = AccountRole.objects.filter(
                user=user,
                is_active=True,
                is_deleted=False
            ).select_related('role')
            
            # Find which roles have this permission
            granting_roles = []
            for account_role in user_roles:
                if permission in account_role.role.get_permissions():
                    granting_roles.append(account_role.role.code)
            
            has_permission = len(granting_roles) > 0
            
            # Build message
            if has_permission:
                roles_str = ', '.join(granting_roles)
                message = f"User has '{permission_code}' permission via roles: {roles_str}"
            else:
                message = f"User does not have '{permission_code}' permission"
            
            logger.info(
                f"Permission check for user {user_id}, "
                f"permission '{permission_code}': {has_permission}"
            )
            
            return {
                'user_id': str(user_id),
                'permission_code': permission_code,
                'has_permission': has_permission,
                'granted_via_roles': granting_roles,
                'message': message
            }
            
        except Exception as e:
            self.log_error(
                'check_user_permission',
                e
            )
            raise

