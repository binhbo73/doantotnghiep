"""
RoleRepository - Specific queries for Role model.
"""
from typing import List, Optional
from django.db.models import Q
from apps.users.models import Role
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class RoleRepository(BaseRepository):
    """
    Repository cho Role model.
    
    Methods:
    - get_by_code(code): Get role by code (unique field)
    - get_default_user_role(): Get user default role
    - list_admin_roles(): Get admin/manager roles only
    """
    
    model_class = Role
    default_select_related = []
    default_prefetch_related = ['role_permissions']
    
    def get_by_code(self, code: str) -> Optional[Role]:
        """
        Get role by code (unique field).
        
        Args:
            code: Role code (e.g., 'admin', 'user', 'viewer')
        
        Returns:
            Role instance or None
        
        Example:
            admin_role = repo.get_by_code('admin')
        """
        try:
            return self.get_base_queryset().get(code=code)
        except Role.DoesNotExist:
            return None
    
    def get_by_id_with_permissions(self, role_id) -> Optional[Role]:
        """
        Get role with all permissions eagerly loaded.
        
        Args:
            role_id: Role ID (UUID now)
        
        Returns:
            Role instance with permissions prefetched
        """
        try:
            return self.get_base_queryset().prefetch_related('role_permissions').get(id=role_id)
        except Role.DoesNotExist:
            return None
    
    def get_default_user_role(self) -> Optional[Role]:
        """
        Get default USER role for new registrations.
        
        Returns:
            Role instance for regular users
        
        Note:
            Used in: UserService.register_account()
                     AdminCreateAccountView.post()
        """
        try:
            # Try to get role by code first (more reliable)
            role = self.get_by_code('user')
            if role:
                return role
            
            # Fallback: try by some other identifier if code not available
            logger.warning("User role not found by code, trying fallback...")
            # Could also check by id=fixed_uuid if that's your setup
            return None
        except Exception as e:
            logger.error(f"Error getting default user role: {e}")
            return None
    
    def list_admin_roles(self) -> List[Role]:
        """
        Get all admin/manager roles.
        
        Returns:
            List of admin-level roles
        """
        try:
            return list(self.get_base_queryset().filter(
                Q(code='admin') | Q(code='manager')
            ))
        except Exception as e:
            logger.error(f"Error listing admin roles: {e}")
            return []
    
    def role_code_exists(self, code: str) -> bool:
        """
        Check if role code already exists (uniqueness check).
        
        Args:
            code: Role code to check
        
        Returns:
            True if exists, False otherwise
        
        Note:
            Used before creating new role to ensure unique codes
        """
        try:
            return self.get_base_queryset().filter(code=code).exists()
        except Exception as e:
            logger.error(f"Error checking role code exists: {e}")
            return False
    
    def get_all_with_permissions(self) -> List[Role]:
        """
        Get all roles with permissions prefetched (optimized for listing).
        
        Returns:
            List of all roles with permissions eagerly loaded
        
        Note:
            Prevents N+1 queries when displaying roles with permission counts
            Used in: RoleListView.get()
        """
        try:
            return list(
                self.get_base_queryset()
                .prefetch_related('role_permissions')
                .order_by('created_at')
            )
        except Exception as e:
            logger.error(f"Error getting all roles with permissions: {e}")
            return []
    
    # ============================================================
    # PERMISSION MANAGEMENT
    # ============================================================
    
    def add_permissions(self, role_id, permission_ids: List) -> bool:
        """
        Add permissions to role (many-to-many).
        
        Args:
            role_id: Role ID (UUID)
            permission_ids: List of permission IDs (UUIDs)
        
        Returns:
            True if successful
        """
        try:
            from apps.users.models import RolePermission
            from django.utils import timezone
            
            role = self.get_by_id(role_id)
            if not role:
                return False
            
            # Create RolePermission records
            for perm_id in permission_ids:
                # Skip if already exists
                if not RolePermission.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    is_deleted=False
                ).exists():
                    RolePermission.objects.get_or_create(
                        role_id=role_id,
                        permission_id=perm_id,
                        defaults={'is_deleted': False, 'created_at': timezone.now()}
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding permissions to role: {e}")
            return False
    
    def remove_permissions(self, role_id, permission_ids: List) -> bool:
        """
        Soft-delete permissions from role.
        
        Args:
            role_id: Role ID (UUID)
            permission_ids: List of permission IDs to remove (UUIDs)
        
        Returns:
            True if successful
        """
        try:
            from apps.users.models import RolePermission
            from django.utils import timezone
            
            for perm_id in permission_ids:
                RolePermission.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    is_deleted=False
                ).update(is_deleted=True, deleted_at=timezone.now())
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing permissions from role: {e}")
            return False
    
    def remove_all_permissions(self, role_id) -> bool:
        """
        Remove all permissions from role.
        
        Args:
            role_id: Role ID (UUID)
        
        Returns:
            True if successful
        """
        try:
            from apps.users.models import RolePermission
            from django.utils import timezone
            
            RolePermission.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).update(is_deleted=True, deleted_at=timezone.now())
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing all permissions: {e}")
            return False
    
    def remove_role_from_all_accounts(self, role_id) -> bool:
        """
        Remove role assignment from all accounts (soft delete).
        Called when role is deleted.
        
        Args:
            role_id: Role ID (UUID)
        
        Returns:
            True if successful
        """
        try:
            from apps.users.models import AccountRole
            from django.utils import timezone
            
            AccountRole.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).update(is_deleted=True, deleted_at=timezone.now())
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing role from all accounts: {e}")
            return False
    
    def get_accounts_with_role(self, role_id):
        """
        Get list of accounts assigned to role.
        
        Args:
            role_id: Role ID (UUID)
        
        Returns:
            List of Account instances
        """
        try:
            from apps.users.models import AccountRole
            
            account_ids = AccountRole.objects.filter(
                role_id=role_id,
                is_deleted=False
            ).values_list('account_id', flat=True)
            
            from apps.users.models import Account
            return list(Account.objects.filter(id__in=account_ids, is_deleted=False))
            
        except Exception as e:
            logger.error(f"Error getting accounts with role: {e}")
            return []
    
    # ============================================================
    # PAGINATION & LISTING
    # ============================================================
    
    def list_with_pagination(self, page: int = 1, page_size: int = 20, search: str = None, filters: dict = None):
        """
        Get paginated list of roles with optional filtering.
        
        Args:
            page: Page number (1-based)
            page_size: Items per page
            search: Search by name/code
            filters: Additional filters dict (e.g., {'department_id': uuid})
        
        Returns:
            {
                'roles': [...],
                'pagination': {'page': 1, 'page_size': 20, 'total': 5, 'total_pages': 1}
            }
        """
        try:
            # Base queryset (non-deleted only)
            queryset = self.get_base_queryset()
            
            # Apply search filter
            if search:
                queryset = queryset.filter(
                    Q(code__icontains=search) | Q(name__icontains=search)
                )
            
            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    queryset = queryset.filter(**{key: value})
            
            # Count total
            total = queryset.count()
            
            # Paginate
            offset = (page - 1) * page_size
            roles = list(queryset[offset:offset + page_size].values(
                'id', 'code', 'name', 'description', 'created_at', 'updated_at'
            ))
            
            # Add permission count for each role
            for role_dict in roles:
                from apps.users.models import RolePermission
                perm_count = RolePermission.objects.filter(
                    role_id=role_dict['id'],
                    is_deleted=False
                ).count()
                role_dict['permission_count'] = perm_count
            
            # Calculate total pages
            total_pages = (total + page_size - 1) // page_size
            
            return {
                'roles': roles,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing roles with pagination: {e}")
            return {
                'roles': [],
                'pagination': {'page': page, 'page_size': page_size, 'total': 0, 'total_pages': 0}
            }
    
    def list_by_department(self, department_id):
        """
        Get roles by department.
        
        Args:
            department_id: Department ID (UUID)
        
        Returns:
            List of roles
        """
        try:
            return list(self.get_base_queryset().filter(department_id=department_id))
        except Exception as e:
            logger.error(f"Error listing roles by department: {e}")
            return []
    
    def check_role_permission(self, role_id, permission_id) -> bool:
        """
        Check if role has specific permission.
        
        Args:
            role_id: Role ID (UUID)
            permission_id: Permission ID (UUID)
        
        Returns:
            True if role has permission
        """
        try:
            from apps.users.models import RolePermission
            
            return RolePermission.objects.filter(
                role_id=role_id,
                permission_id=permission_id,
                is_deleted=False
            ).exists()
            
        except Exception as e:
            logger.error(f"Error checking role permission: {e}")
            return False
    
    def get_role_with_permissions(self, role_id):
        """
        Get role with all permissions (alias for get_by_id_with_permissions).
        
        Args:
            role_id: Role ID (UUID)
        
        Returns:
            Role instance with permissions prefetched
        """
        return self.get_by_id_with_permissions(role_id)

