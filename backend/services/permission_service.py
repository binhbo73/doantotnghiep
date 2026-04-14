"""
Permission Service
==================
Business logic for permission/role management

Responsibilities:
- Grant/revoke roles to users
- Assign/remove permissions to roles
- Check hierarchical permissions (account > role > document)
- Manage permission inheritance
- Audit permission changes

Uses:
- PermissionRepository (data access)
- PermissionManager (ACL evaluation)
- AuditLog (track changes)
"""

import logging
from typing import List, Set, Optional, Dict, Any
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from core.constants import PermissionCodes, RoleIds
from core.exceptions import (
    ValidationError,
    BusinessLogicError,
    NotFoundError,
    PermissionDeniedError,
)
from repositories.permission_repository import PermissionRepository
from repositories.user_repository import UserRepository
from .base_service import BaseService

logger = logging.getLogger(__name__)


class PermissionService(BaseService):
    """
    Permission & Role management service
    
    Key Methods:
    - grant_role_to_user(user_id, role_id, granted_by)
    - revoke_role_from_user(user_id, role_id)
    - assign_permission_to_role(role_id, permission_code, assigned_by)
    - remove_permission_from_role(role_id, permission_code)
    - check_user_has_permission(user_id, permission_code)
    - get_user_full_permissions(user_id)
    
    AUDIT:
    - All changes logged to AuditLog
    - Tracks who granted/revoked (not just what)
    """
    
    repository_class = PermissionRepository
    
    def __init__(self):
        """Initialize with repositories"""
        super().__init__()
        self.permission_repo = self.repository  # From base
        self.user_repo = UserRepository()
    
    # ============================================================================
    # ROLE MANAGEMENT
    # ============================================================================
    
    def grant_role_to_user(
        self,
        user_id: int,
        role_id: int,
        granted_by_user_id: int = None
    ) -> bool:
        """
        Grant role to user
        
        Business Rules:
        - User must exist
        - Role must exist
        - User cannot already have role
        - Only Admin can assign Manger/Admin roles
        - User can assign to themselves if Admin
        
        Args:
            user_id: Target user ID
            role_id: Role ID to grant
            granted_by_user_id: Who is granting (audit)
        
        Returns:
            True if granted
        
        Raises:
            ValidationError: If user/role not found
            PermissionDeniedError: If not authorized
            BusinessLogicError: If role already assigned
        """
        try:
            # Validate user exists
            user = self.user_repo.get_by_id(user_id)
            self.validate_business_rule(
                user is not None,
                f"User {user_id} not found"
            )
            
            # Validate role exists
            role = self.permission_repo.get_role_by_id(role_id)
            self.validate_business_rule(
                role is not None,
                f"Role {role_id} not found"
            )
            
            # Check if already has role
            if self.permission_repo.check_user_has_role(user_id, role_id):
                raise BusinessLogicError(
                    f"User {user_id} already has role {role.code}"
                )
            
            # Create AccountRole
            with transaction.atomic():
                result = self.permission_repo.grant_role_to_user(
                    user_id,
                    role_id,
                    granted_by_user_id
                )
                
                # Log action
                self.log_action(
                    'GRANT_ROLE',
                    resource_id=user_id,
                    details=f"Granted role '{role.code}' to user",
                    user_id=granted_by_user_id
                )
                
                # Audit
                self._log_permission_audit(
                    action='GRANT_ROLE',
                    target_user_id=user_id,
                    role_id=role_id,
                    granted_by_user_id=granted_by_user_id
                )
            
            return result
            
        except Exception as e:
            self.log_error('grant_role_to_user', e, user_id, granted_by_user_id)
            raise
    
    def revoke_role_from_user(
        self,
        user_id: int,
        role_id: int,
        revoked_by_user_id: int = None
    ) -> bool:
        """
        Revoke role from user
        
        Business Rules:
        - User must exist
        - Role must exist
        - User must have role
        - Cannot revoke last admin (at least 1 admin required always)
        
        Args:
            user_id: Target user ID
            role_id: Role ID to revoke
            revoked_by_user_id: Who is revoking (audit)
        
        Returns:
            True if revoked
        
        Raises:
            ValidationError: If user/role not found
            BusinessLogicError: If would leave no admins
        """
        try:
            # Validate user/role exist
            user = self.user_repo.get_by_id(user_id)
            self.validate_business_rule(user is not None, f"User {user_id} not found")
            
            role = self.permission_repo.get_role_by_id(role_id)
            self.validate_business_rule(role is not None, f"Role {role_id} not found")
            
            # Check user has role
            if not self.permission_repo.check_user_has_role(user_id, role_id):
                raise BusinessLogicError(
                    f"User {user_id} does not have role {role.code}"
                )
            
            # Safety: prevent removing last admin
            if role_id == RoleIds.ADMIN:
                admin_count = self.permission_repo.get_role_user_count(RoleIds.ADMIN)
                if admin_count <= 1:
                    raise BusinessLogicError(
                        "Cannot revoke - at least one Admin required"
                    )
            
            # Revoke
            with transaction.atomic():
                result = self.permission_repo.revoke_role_from_user(user_id, role_id)
                
                self.log_action(
                    'REVOKE_ROLE',
                    resource_id=user_id,
                    details=f"Revoked role '{role.code}'",
                    user_id=revoked_by_user_id
                )
                
                self._log_permission_audit(
                    action='REVOKE_ROLE',
                    target_user_id=user_id,
                    role_id=role_id,
                    granted_by_user_id=revoked_by_user_id
                )
            
            return result
            
        except Exception as e:
            self.log_error('revoke_role_from_user', e, user_id, revoked_by_user_id)
            raise
    
    # ============================================================================
    # PERMISSION MANAGEMENT
    # ============================================================================
    
    def assign_permission_to_role(
        self,
        role_id: int,
        permission_code: str,
        assigned_by_user_id: int = None
    ) -> bool:
        """
        Assign permission to role
        
        Business Rules:
        - Role must exist
        - Permission must exist
        - Role cannot already have permission
        - System roles (Admin) can assign any permission
        
        Args:
            role_id: Role ID
            permission_code: Permission code
            assigned_by_user_id: Who is assigning (audit)
        
        Returns:
            True if assigned
        
        Raises:
            ValidationError: If role/permission not found
            BusinessLogicError: If already assigned
        """
        try:
            # Validate role exists
            role = self.permission_repo.get_role_by_id(role_id)
            self.validate_business_rule(role is not None, f"Role {role_id} not found")
            
            # Validate permission exists
            permission = self.permission_repo.get_permission_by_code(permission_code)
            self.validate_business_rule(
                permission is not None,
                f"Permission '{permission_code}' not found"
            )
            
            # Check not already assigned
            role_permissions = self.permission_repo.get_role_permission_codes(role_id)
            if permission_code in role_permissions:
                raise BusinessLogicError(
                    f"Role {role.code} already has permission {permission_code}"
                )
            
            # Assign
            with transaction.atomic():
                result = self.permission_repo.grant_permission_to_role(
                    role_id,
                    permission_code,
                    assigned_by_user_id
                )
                
                self.log_action(
                    'ASSIGN_PERMISSION',
                    resource_id=role_id,
                    details=f"Assigned permission '{permission_code}'",
                    user_id=assigned_by_user_id
                )
                
                self._log_permission_audit(
                    action='ASSIGN_PERMISSION',
                    role_id=role_id,
                    permission_code=permission_code,
                    granted_by_user_id=assigned_by_user_id
                )
            
            return result
            
        except Exception as e:
            self.log_error('assign_permission_to_role', e, role_id, assigned_by_user_id)
            raise
    
    def remove_permission_from_role(
        self,
        role_id: int,
        permission_code: str,
        removed_by_user_id: int = None
    ) -> bool:
        """
        Remove permission from role
        
        Args:
            role_id: Role ID
            permission_code: Permission code
            removed_by_user_id: Who is removing (audit)
        
        Returns:
            True if removed
        """
        try:
            role = self.permission_repo.get_role_by_id(role_id)
            self.validate_business_rule(role is not None, f"Role {role_id} not found")
            
            permission = self.permission_repo.get_permission_by_code(permission_code)
            self.validate_business_rule(
                permission is not None,
                f"Permission '{permission_code}' not found"
            )
            
            with transaction.atomic():
                result = self.permission_repo.revoke_permission_from_role(
                    role_id,
                    permission_code
                )
                
                self.log_action(
                    'REMOVE_PERMISSION',
                    resource_id=role_id,
                    details=f"Removed permission '{permission_code}'",
                    user_id=removed_by_user_id
                )
                
                self._log_permission_audit(
                    action='REMOVE_PERMISSION',
                    role_id=role_id,
                    permission_code=permission_code,
                    granted_by_user_id=removed_by_user_id
                )
            
            return result
            
        except Exception as e:
            self.log_error('remove_permission_from_role', e, role_id, removed_by_user_id)
            raise
    
    # ============================================================================
    # PERMISSION CHECKING
    # ============================================================================
    
    def check_user_has_permission(
        self,
        user_id: int,
        permission_code: str
    ) -> bool:
        """
        Check if user has permission
        
        Args:
            user_id: User ID
            permission_code: Permission code
        
        Returns:
            True if has permission
        """
        try:
            return self.permission_repo.check_user_has_permission(
                user_id,
                permission_code
            )
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    def check_user_has_any_permission(
        self,
        user_id: int,
        permission_codes: List[str]
    ) -> bool:
        """
        Check if user has ANY of the permissions
        
        Args:
            user_id: User ID
            permission_codes: List of permission codes
        
        Returns:
            True if has at least one
        """
        try:
            return self.permission_repo.check_user_has_any_permission(
                user_id,
                permission_codes
            )
        except Exception as e:
            logger.error(f"Error checking -any- permissions: {str(e)}")
            return False
    
    def check_user_has_all_permissions(
        self,
        user_id: int,
        permission_codes: List[str]
    ) -> bool:
        """
        Check if user has ALL permissions
        
        Args:
            user_id: User ID
            permission_codes: List of permission codes
        
        Returns:
            True if has all
        """
        try:
            return self.permission_repo.check_user_has_all_permissions(
                user_id,
                permission_codes
            )
        except Exception as e:
            logger.error(f"Error checking -all- permissions: {str(e)}")
            return False
    
    # ============================================================================
    # GET USER PERMISSIONS
    # ============================================================================
    
    def get_user_roles(self, user_id: int) -> List[dict]:
        """
        Get all roles for user
        
        Returns:
            List of role dicts with: id, code, name, description
        """
        try:
            roles = self.permission_repo.get_user_roles(user_id)
            return [
                {
                    'id': r.id,
                    'code': r.code,
                    'name': r.name,
                    'description': r.description,
                }
                for r in roles
            ]
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            return []
    
    def get_user_permissions(self, user_id: int) -> List[dict]:
        """
        Get all permissions for user (via roles)
        
        Returns:
            List of permission dicts with: code, name, resource, action
        """
        try:
            permissions = self.permission_repo.get_user_permissions(user_id)
            return [
                {
                    'code': p.code,
                    'name': p.name,
                    'resource': p.resource,
                    'action': p.action,
                    'description': p.description,
                }
                for p in permissions
            ]
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return []
    
    def get_user_permission_codes(self, user_id: int) -> Set[str]:
        """
        Get set of permission codes for user (fast lookup)
        
        Returns:
            Set of permission codes (e.g., {'document_read', 'document_write'})
        """
        try:
            return self.permission_repo.get_user_permission_codes(user_id)
        except Exception as e:
            logger.error(f"Error getting user permission codes: {str(e)}")
            return set()
    
    # ============================================================================
    # LIST PERMISSIONS (For API responses)
    # ============================================================================
    
    def list_permissions(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all permissions with pagination.
        
        Args:
            page: Page number (1-based)
            page_size: Items per page  
            search: Optional search term
        
        Returns:
            {
                'permissions': [...],
                'pagination': {
                    'page': 1,
                    'page_size': 20,
                    'total': 145,
                    'total_pages': 8
                }
            }
        """
        try:
            # Validate pagination
            if page < 1:
                raise ValidationError("page must be >= 1")
            if page_size < 1 or page_size > 100:
                raise ValidationError("page_size must be between 1 and 100")
            
            # Call repository
            result = self.permission_repo.list_permissions_paginated(
                page=page,
                page_size=page_size,
                search=search
            )
            
            logger.info(f"Listed permissions: page={page}, total={result['pagination']['total']}")
            
            return result
            
        except Exception as e:
            self.log_error('list_permissions', e, page=page, page_size=page_size)
            raise
    
    # ============================================================================
    # PERMISSION CRUD (Get, Update, Delete)
    # ============================================================================
    
    def get_permission(self, permission_id: str) -> Dict[str, Any]:
        """
        Get single permission by ID with all details
        
        Args:
            permission_id: UUID permission ID
        
        Returns:
            {
                'id': '...',
                'code': 'document_read',
                'name': 'Read Document',
                'description': '...',
                'resource': 'document',
                'action': 'read',
                'created_at': '...',
                'updated_at': '...'
            }
        
        Raises:
            NotFoundError: If permission not found
        """
        try:
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission:
                raise NotFoundError(f"Permission {permission_id} not found")
            
            return {
                'id': str(permission.id),
                'code': permission.code,
                'name': permission.name,
                'description': permission.description,
                'resource': permission.resource,
                'action': permission.action,
                'created_at': permission.created_at.isoformat() if permission.created_at else None,
                'updated_at': permission.updated_at.isoformat() if permission.updated_at else None,
            }
        except Exception as e:
            self.log_error('get_permission', e, permission_id=permission_id)
            raise
    
    def update_permission(
        self,
        permission_id: str,
        data: Dict[str, Any],
        requested_by_user_id: int = None
    ) -> Dict[str, Any]:
        """
        Update permission details
        
        Business Rules:
        - Permission must exist
        - Code field must be unique (if being updated)
        - Cannot update a deleted permission
        - All changes logged to AuditLog
        
        Args:
            permission_id: UUID permission ID
            data: Update data (name, description, code, resource, action)
            requested_by_user_id: Who is updating (for audit)
        
        Returns:
            Updated permission dict
        
        Raises:
            NotFoundError: If permission not found
            ValidationError: If code already exists (duplicate)
            BusinessLogicError: If permission is deleted
        
        Example:
            result = service.update_permission(
                permission_id='uuid-123',
                data={
                    'name': 'New Name',
                    'description': 'New description'
                },
                requested_by_user_id=admin_id
            )
        """
        try:
            # Validate permission exists and not deleted
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission:
                raise NotFoundError(f"Permission {permission_id} not found")
            
            self.validate_business_rule(
                not permission.is_deleted,
                f"Cannot update deleted permission {permission_id}"
            )
            
            # Validate input data
            allowed_fields = {'name', 'description', 'code', 'resource', 'action'}
            update_fields = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
            
            if not update_fields:
                raise ValidationError("No valid fields to update")
            
            # Validate required fields if present
            if 'name' in update_fields:
                name_value = update_fields['name']
                self.validate_business_rule(
                    name_value and len(str(name_value).strip()) > 0,
                    "Permission name cannot be empty"
                )
            
            if 'code' in update_fields:
                code_value = update_fields['code']
                self.validate_business_rule(
                    code_value and len(str(code_value).strip()) > 0,
                    "Permission code cannot be empty"
                )
                # Validate uniqueness
                existing = self.permission_repo.get_by_code(code_value)
                if existing and str(existing.id) != permission_id:
                    raise ValidationError(
                        f"Permission code '{code_value}' already exists"
                    )
            
            # Update in transaction
            with transaction.atomic():
                updated_perm = self.permission_repo.update_permission(
                    permission_id,
                    **update_fields
                )
                
                if not updated_perm:
                    raise BusinessLogicError(
                        f"Failed to update permission {permission_id}"
                    )
                
                # Log action
                self.log_action(
                    'UPDATE_PERMISSION',
                    resource_id=permission_id,
                    details=f"Updated fields: {list(update_fields.keys())}",
                    user_id=requested_by_user_id
                )
                
                # Audit
                self._log_permission_audit(
                    action='UPDATE_PERMISSION',
                    permission_code=updated_perm.code,
                    granted_by_user_id=requested_by_user_id
                )
            
            # Return updated permission
            return self.get_permission(permission_id)
        
        except Exception as e:
            self.log_error('update_permission', e, permission_id=permission_id, requested_by_user_id=requested_by_user_id)
            raise
    
    def delete_permission(
        self,
        permission_id: str,
        requested_by_user_id: int = None
    ) -> bool:
        """
        Delete (soft delete) a permission
        
        Business Rules:
        - Permission must exist
        - Cannot delete already deleted permission
        - Cannot delete permissions used by system roles (optional validation)
        - Sets is_deleted=True (soft delete)
        - All changes logged to AuditLog
        
        Args:
            permission_id: UUID permission ID
            requested_by_user_id: Who is deleting (for audit)
        
        Returns:
            True if deleted successfully
        
        Raises:
            NotFoundError: If permission not found
            BusinessLogicError: If permission already deleted or still in use
        
        Example:
            service.delete_permission(
                permission_id='uuid-123',
                requested_by_user_id=admin_id
            )
        """
        try:
            # Validate permission exists
            permission = self.permission_repo.get_by_id(permission_id)
            if not permission:
                raise NotFoundError(f"Permission {permission_id} not found")
            
            # Cannot delete already deleted
            self.validate_business_rule(
                not permission.is_deleted,
                f"Permission {permission_id} is already deleted"
            )
            
            # Delete in transaction
            with transaction.atomic():
                result = self.permission_repo.delete_permission(permission_id)
                
                if not result:
                    raise BusinessLogicError(
                        f"Failed to delete permission {permission_id}"
                    )
                
                # Log action
                self.log_action(
                    'DELETE_PERMISSION',
                    resource_id=permission_id,
                    details=f"Deleted permission: {permission.code}",
                    user_id=requested_by_user_id
                )
                
                # Audit
                self._log_permission_audit(
                    action='DELETE_PERMISSION',
                    permission_code=permission.code,
                    granted_by_user_id=requested_by_user_id
                )
            
            logger.info(f"Permission deleted: {permission_id} ({permission.code})")
            return True
        
        except Exception as e:
            self.log_error('delete_permission', e, permission_id=permission_id, requested_by_user_id=requested_by_user_id)
            raise
    
    # ============================================================================
    # INTERNAL HELPERS
    # ============================================================================
    
    def _log_permission_audit(
        self,
        action: str,
        target_user_id: int = None,
        role_id: int = None,
        permission_code: str = None,
        granted_by_user_id: int = None
    ):
        """
        Log permission change to AuditLog
        
        Args:
            action: GRANT_ROLE, REVOKE_ROLE, ASSIGN_PERMISSION, REMOVE_PERMISSION
            target_user_id: User affected (for GRANT/REVOKE)
            role_id: Role affected
            permission_code: Permission affected
            granted_by_user_id: Who made the change
        """
        try:
            query_text = f"{action}"
            if role_id:
                query_text += f" role_id={role_id}"
            if target_user_id:
                query_text += f" user_id={target_user_id}"
            if permission_code:
                query_text += f" permission={permission_code}"
            
            self.audit_log_action(
                action=action,
                user_id=granted_by_user_id,
                resource_id=str(role_id) if role_id else None,
                resource_type='Permission',
                query_text=query_text,
                details={'target_user_id': target_user_id, 'permission_code': permission_code}
            )
        except Exception as e:
            logger.warning(f"Could not log permission audit: {str(e)}")

