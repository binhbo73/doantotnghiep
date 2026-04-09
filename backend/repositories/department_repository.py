"""
DepartmentRepository - Specific queries for Department model.
"""
from typing import List, Optional
from django.db.models import Q
from apps.users.models import Department
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class DepartmentRepository(BaseRepository):
    """
    Repository cho Department model.
    
    Methods:
    - get_by_code(code): Get department by code (unique field)
    - get_default_department(): Get or create default department
    - list_by_parent(parent_id): Get departments under parent
    """
    
    model_class = Department
    default_select_related = ['parent', 'manager']
    default_prefetch_related = []
    
    def get_by_code(self, code: str) -> Optional[Department]:
        """
        Get department by code (unique field).
        
        Args:
            code: Department code
        
        Returns:
            Department instance or None
        
        Example:
            dept = repo.get_by_code('SALES')
        """
        try:
            return self.get_base_queryset().get(code=code)
        except Department.DoesNotExist:
            return None
    
    def get_or_create_default(self) -> Department:
        """
        Get or create default department.
        
        Returns:
            Existing or newly created default Department
        
        Note:
            This is used when creating new users without department
        """
        try:
            # Try to get existing default
            return self.get_base_queryset().get(code='default_department')
        except Department.DoesNotExist:
            # Create if doesn't exist
            try:
                logger.info("Creating default department...")
                return self.create(
                    name='Default',
                    code='default_department',
                    description='Default department for users without assigned department'
                )
            except Exception as e:
                logger.error(f"Error creating default department: {e}")
                # Try one more time (race condition with concurrent creation)
                try:
                    return self.get_base_queryset().get(code='default_department')
                except Exception:
                    raise
    
    def list_by_parent(self, parent_id) -> List[Department]:
        """
        Get all departments under parent.
        
        Args:
            parent_id: Parent department ID
        
        Returns:
            List of Department instances
        """
        try:
            return list(self.get_base_queryset().filter(parent_id=parent_id))
        except Exception as e:
            logger.error(f"Error listing departments by parent: {e}")
            return []
    
    def get_by_manager(self, manager_id) -> List[Department]:
        """
        Get all departments managed by user.
        
        Args:
            manager_id: Manager user ID
        
        Returns:
            List of managed departments
        """
        try:
            return list(self.get_base_queryset().filter(manager_id=manager_id))
        except Exception as e:
            logger.error(f"Error listing departments by manager: {e}")
            return []
