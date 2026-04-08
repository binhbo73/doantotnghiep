"""
PermissionRepository - Specific queries for Permission/Role/RolePermission models.
Queries: get permissions by role, check user permission, etc.
"""
from typing import List, Optional, Set
from django.db.models import Q, Prefetch
from apps.users.models import Role, Permission, RolePermission, AccountRole, Account
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class PermissionRepository(BaseRepository):
    """
    Repository cho Permission/Role models.
    """
    
    model_class = Permission
    
    # ============================================================
    # PERMISSION QUERIES
    # ============================================================
    
    def get_by_code(self, code: str) -> Optional[Permission]:
        """
        Get permission by code.
        
        Example:
            perm = repo.get_by_code('document_read')
        """
        try:
            return self.get_base_queryset().get(code=code)
        except Permission.DoesNotExist:
            return None
    
    def list_by_resource(self, resource: str) -> List[Permission]:
        """
        Get all permissions for a resource.
        
        Example:
            perms = repo.list_by_resource('document')
            # Returns: document_create, document_read, document_update, document_delete...
        """
        return self.list(resource=resource)
    
    def list_by_resource_and_action(self, resource: str, action: str) -> List[Permission]:
        """
        Get all permissions matching resource and action.
        
        Example:
            perms = repo.list_by_resource_and_action('document', 'read')
        """
        return self.list(resource=resource, action=action)
    
    # ============================================================
    # ROLE QUERIES
    # ============================================================
    
    def get_role_by_id(self, role_id) -> Optional[Role]:
        """
        Get role by ID (role_id is now UUID).
        
        Example:
            role = repo.get_role_by_id(RoleIds.ADMIN)
        """
        try:
            queryset = Role.objects.filter(is_deleted=False)
            return queryset.get(pk=role_id)
        except Role.DoesNotExist:
            return None
    
    def get_role_with_permissions(self, role_id) -> Optional[Role]:
        """
        Get role with all permissions loaded (role_id is now UUID).
        
        Example:
            role = repo.get_role_with_permissions(RoleIds.ADMIN)
            # role.get_permissions() will be fast
        """
        try:
            perm_prefetch = Prefetch(
                'role_permissions',
                queryset=RolePermission.objects.filter(is_deleted=False).select_related('permission')
            )
            queryset = Role.objects.filter(is_deleted=False).prefetch_related(perm_prefetch)
            return queryset.get(pk=role_id)
        except Role.DoesNotExist:
            return None
    
    def list_all_roles(self) -> List[Role]:
        """
        Get all roles (usually Admin/Manager/User).
        
        Example:
            roles = repo.list_all_roles()
        """
        try:
            return list(Role.objects.filter(is_deleted=False).order_by('id'))
        except Exception as e:
            logger.error(f"Error listing roles: {e}", exc_info=True)
            return []
    
    # ============================================================
    # ROLE-PERMISSION ASSIGNMENT QUERIES
    # ============================================================
    
    def get_role_permissions(self, role_id) -> List[Permission]:
        """
        Get all permissions assigned to a role (role_id is now UUID).
        
        Example:
            perms = repo.get_role_permissions(RoleIds.ADMIN)
        """
        try:
            permissions = Permission.objects.filter(
                role_permission_mappings__role_id=role_id,
                role_permission_mappings__is_deleted=False,
                is_deleted=False
            ).distinct()
            return list(permissions)
        except Exception as e:
            logger.error(f"Error getting role permissions: {e}", exc_info=True)
            return []
    
    def get_role_permission_codes(self, role_id) -> Set[str]:
        """
        Get all permission codes for a role (role_id is now UUID, optimized).
        Returns set of codes for O(1) lookup.
        
        Example:
            codes = repo.get_role_permission_codes(RoleIds.ADMIN)
            # {'document_read', 'document_create', 'user_read', ...}
        """
        try:
            codes = RolePermission.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).values_list('permission__code', flat=True).distinct()
            return set(codes)
        except Exception as e:
            logger.error(f"Error getting role permission codes: {e}", exc_info=True)
            return set()
    
    # ============================================================
    # USER PERMISSION QUERIES
    # ============================================================
    
    def get_user_permissions(self, user_id) -> List[Permission]:
        """
        Get all permissions a user has (through their roles).
        
        Example:
            user_perms = repo.get_user_permissions(123)
        """
        try:
            # Get all role IDs for user
            role_ids = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).values_list('role_id', flat=True)
            
            # Get all permissions for those roles
            permissions = Permission.objects.filter(
                role_permission_mappings__role_id__in=role_ids,
                role_permission_mappings__is_deleted=False,
                is_deleted=False
            ).distinct()
            
            return list(permissions)
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}", exc_info=True)
            return []
    
    def get_user_permission_codes(self, user_id) -> Set[str]:
        """
        Get all permission codes for a user (optimized set return).
        
        Example:
            codes = repo.get_user_permission_codes(123)
            # {'document_read', 'user_read', 'document_create', ...}
        """
        try:
            # Get all role IDs for user
            role_ids = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).values_list('role_id', flat=True)
            
            # Get all permission codes for those roles
            codes = RolePermission.objects.filter(
                role_id__in=role_ids,
                is_deleted=False
            ).values_list('permission__code', flat=True).distinct()
            
            return set(codes)
        except Exception as e:
            logger.error(f"Error getting user permission codes: {e}", exc_info=True)
            return set()
    
    def check_user_has_permission(self, user_id, permission_code: str) -> bool:
        """
        Check if user has specific permission.
        
        Example:
            can_read = repo.check_user_has_permission(123, 'document_read')
        """
        try:
            # Get all role IDs for user
            role_ids = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).values_list('role_id', flat=True)
            
            # Check if any role has this permission
            return RolePermission.objects.filter(
                role_id__in=role_ids,
                permission__code=permission_code,
                is_deleted=False
            ).exists()
        except Exception as e:
            logger.error(f"Error checking user permission: {e}", exc_info=True)
            return False
    
    def check_user_has_any_permission(self, user_id, permission_codes: List[str]) -> bool:
        """
        Check if user has ANY of the permissions in list.
        
        Example:
            can_modify = repo.check_user_has_any_permission(123, ['document_write', 'document_delete'])
        """
        try:
            # Get all role IDs for user
            role_ids = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).values_list('role_id', flat=True)
            
            # Check if any role has any of these permissions
            return RolePermission.objects.filter(
                role_id__in=role_ids,
                permission__code__in=permission_codes,
                is_deleted=False
            ).exists()
        except Exception as e:
            logger.error(f"Error checking user any permission: {e}", exc_info=True)
            return False
    
    def check_user_has_all_permissions(self, user_id, permission_codes: List[str]) -> bool:
        """
        Check if user has ALL of the permissions in list.
        
        Example:
            is_admin = repo.check_user_has_all_permissions(123, ['role_manage', 'permission_manage'])
        """
        try:
            user_codes = self.get_user_permission_codes(user_id)
            return all(code in user_codes for code in permission_codes)
        except Exception as e:
            logger.error(f"Error checking user all permissions: {e}", exc_info=True)
            return False
    
    # ============================================================
    # ROLE ASSIGNMENT QUERIES
    # ============================================================
    
    def get_user_roles(self, user_id) -> List[Role]:
        """
        Get all roles assigned to a user.
        
        Example:
            roles = repo.get_user_roles(123)
        """
        try:
            roles = Role.objects.filter(
                account_role_mappings__account_id=user_id,
                account_role_mappings__is_deleted=False,
                is_deleted=False
            ).distinct()
            return list(roles)
        except Exception as e:
            logger.error(f"Error getting user roles: {e}", exc_info=True)
            return []
    
    def get_user_role_ids(self, user_id) -> Set:
        """
        Get all role IDs for a user (role IDs are now UUIDs, optimized set return).
        
        Example:
            role_ids = repo.get_user_role_ids(123)
            # {UUID(...), UUID(...)}  # Admin + Manager UUIDs
        """
        try:
            role_ids = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).values_list('role_id', flat=True).distinct()
            return set(role_ids)
        except Exception as e:
            logger.error(f"Error getting user role IDs: {e}", exc_info=True)
            return set()
    
    def grant_role_to_user(self, user_id, role_id, granted_by_user_id=None) -> bool:
        """
        Assign a role to user (role_id is now UUID).
        
        Example:
            repo.grant_role_to_user(123, RoleIds.ADMIN, granted_by=admin_user_id)
        """
        try:
            granted_by = None
            if granted_by_user_id:
                granted_by = Account.objects.get(pk=granted_by_user_id)
            
            AccountRole.objects.get_or_create(
                account_id=user_id,
                role_id=role_id,
                defaults={'granted_by': granted_by}
            )
            
            logger.info(f"Granted role {role_id} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error granting role: {e}", exc_info=True)
            return False
    
    def revoke_role_from_user(self, user_id, role_id) -> bool:
        """
        Remove a role from user (role_id is now UUID, soft delete).
        
        Example:
            repo.revoke_role_from_user(123, RoleIds.ADMIN)
        """
        try:
            account_role = AccountRole.objects.get(
                account_id=user_id,
                role_id=role_id,
                is_deleted=False
            )
            account_role.delete()  # Soft delete
            
            logger.info(f"Revoked role {role_id} from user {user_id}")
            return True
        except AccountRole.DoesNotExist:
            logger.warning(f"Account role not found: user={user_id}, role={role_id}")
            return False
        except Exception as e:
            logger.error(f"Error revoking role: {e}", exc_info=True)
            return False
    
    # ============================================================
    # PERMISSION ASSIGNMENT TO ROLE
    # ============================================================
    
    def grant_permission_to_role(self, role_id, permission_code: str, granted_by_user_id=None) -> bool:
        """
        Assign a permission to a role (role_id is now UUID).
        
        Example:
            repo.grant_permission_to_role(RoleIds.ADMIN, 'document_read', granted_by=admin_user_id)
        """
        try:
            permission = Permission.objects.get(code=permission_code, is_deleted=False)
            granted_by = None
            if granted_by_user_id:
                granted_by = Account.objects.get(pk=granted_by_user_id)
            
            RolePermission.objects.get_or_create(
                role_id=role_id,
                permission=permission,
                defaults={'granted_by': granted_by}
            )
            
            logger.info(f"Granted permission {permission_code} to role {role_id}")
            return True
        except Exception as e:
            logger.error(f"Error granting permission: {e}", exc_info=True)
            return False
    
    def revoke_permission_from_role(self, role_id, permission_code: str) -> bool:
        """
        Remove a permission from a role (role_id is now UUID, soft delete).
        
        Example:
            repo.revoke_permission_from_role(RoleIds.ADMIN, 'document_write')
        """
        try:
            permission = Permission.objects.get(code=permission_code, is_deleted=False)
            role_perm = RolePermission.objects.get(
                role_id=role_id,
                permission=permission,
                is_deleted=False
            )
            role_perm.delete()  # Soft delete
            
            logger.info(f"Revoked permission {permission_code} from role {role_id}")
            return True
        except (RolePermission.DoesNotExist, Permission.DoesNotExist):
            logger.warning(f"Role permission not found: role={role_id}, permission={permission_code}")
            return False
        except Exception as e:
            logger.error(f"Error revoking permission: {e}", exc_info=True)
            return False
