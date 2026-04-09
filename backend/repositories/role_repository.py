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
    default_prefetch_related = ['permissions']
    
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
            return self.get_base_queryset().prefetch_related('permissions').get(id=role_id)
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
