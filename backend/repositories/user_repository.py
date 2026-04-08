"""
UserRepository - Specific queries for User/Account model.
Extend BaseRepository với user-specific business logic.
"""
from typing import List, Optional, Dict, Tuple
from django.db.models import Q, Prefetch
from apps.users.models import Account, Role, AccountRole, Permission
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Repository cho Account model.
    Optimize queries: select_related roles + permissions
    Note: department is on UserProfile, not Account anymore
    """
    
    model_class = Account
    default_select_related = []  # No FKs on Account anymore (department moved to UserProfile)
    default_prefetch_related = ['account_roles__role']  # M2M
    
    # ============================================================
    # USER-SPECIFIC QUERIES
    # ============================================================
    
    def get_by_email(self, email: str) -> Optional[Account]:
        """
        Get user by email.
        
        Example:
            user = repo.get_by_email("john@example.com")
        """
        try:
            return self.get_base_queryset().get(email=email)
        except Account.DoesNotExist:
            return None
    
    def get_by_username(self, username: str) -> Optional[Account]:
        """
        Get user by username.
        
        Example:
            user = repo.get_by_username("john_doe")
        """
        try:
            return self.get_base_queryset().get(username=username)
        except Account.DoesNotExist:
            return None
    
    def get_by_email_or_username(self, email_or_username: str) -> Optional[Account]:
        """
        Get user by email or username (for login).
        
        Example:
            user = repo.get_by_email_or_username("john@example.com")
            # or
            user = repo.get_by_email_or_username("john_doe")
        """
        try:
            return self.get_base_queryset().get(
                Q(email=email_or_username) | Q(username=email_or_username)
            )
        except Account.DoesNotExist:
            return None
        except Account.MultipleObjectsReturned:
            # Data integrity issue: multiple accounts with same email/username
            logger.error(f"CRITICAL: Multiple accounts found for {email_or_username}")
            # Try to get by username first (more specific)
            try:
                return self.get_base_queryset().filter(username=email_or_username).first()
            except Exception as e:
                logger.error(f"Failed to recover from MultipleObjectsReturned: {e}")
                return None
    
    def list_by_department(self, department_id) -> List[Account]:
        """
        Get all users in a department.
        
        Example:
            users = repo.list_by_department(dept_id)
        """
        return self.list(department_id=department_id)
    
    def list_by_role(self, role_id) -> List[Account]:
        """
        Get all users with specific role (role_id is now UUID).
        
        Example:
            admins = repo.list_by_role(RoleIds.ADMIN)
        """
        try:
            # Get users through AccountRole many-to-many
            queryset = self.get_base_queryset().filter(
                account_roles__role_id=role_id,
                account_roles__is_deleted=False
            ).distinct()
            return list(queryset)
        except Exception as e:
            logger.error(f"Error listing users by role: {e}", exc_info=True)
            return []
    
    def search(self, query: str) -> List[Account]:
        """
        Search users by username, email, or full name.
        
        Example:
            results = repo.search("john")  # Matches username, email, first_name, last_name
        """
        try:
            queryset = self.get_base_queryset().filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
            return list(queryset)
        except Exception as e:
            logger.error(f"Error searching users: {e}", exc_info=True)
            return []
    
    def get_active_users(self) -> List[Account]:
        """
        Get all active (non-blocked) users.
        
        Example:
            active_users = repo.get_active_users()
        """
        return self.list(status='active')
    
    # ============================================================
    # USER WITH ROLES & PERMISSIONS
    # ============================================================
    
    def get_user_with_roles(self, user_id) -> Optional[Account]:
        """
        Get user with all roles and their permissions loaded.
        Optimized to avoid N+1 queries.
        
        Example:
            user = repo.get_user_with_roles(123)
            # user.get_roles() will be fast
            # user.get_permissions() will be fast
        """
        try:
            # Prefetch roles + permissions for those roles
            role_prefetch = Prefetch(
                'account_roles__role__role_permissions',
                queryset=Permission.objects.filter(
                    role_permission_mappings__is_deleted=False
                )
            )
            
            queryset = self.get_base_queryset().prefetch_related(role_prefetch)
            return queryset.get(pk=user_id)
        except Account.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting user with roles: {e}", exc_info=True)
            return None
    
    # ============================================================
    # BULK OPERATIONS
    # ============================================================
    
    def deactivate_users(self, user_ids: list) -> int:
        """
        Deactivate (block) multiple users (user_ids are now UUIDs).
        
        Example:
            count = repo.deactivate_users([uuid1, uuid2, uuid3])
        """
        try:
            count = 0
            for user_id in user_ids:
                user = self.get_by_id(user_id)
                user.status = 'blocked'
                user.save()
                count += 1
            
            logger.info(f"Deactivated {count} users")
            return count
        except Exception as e:
            logger.error(f"Error deactivating users: {e}", exc_info=True)
            return 0
    
    def activate_users(self, user_ids: list) -> int:
        """
        Activate (unblock) multiple users (user_ids are now UUIDs).
        
        Example:
            count = repo.activate_users([uuid1, uuid2, uuid3])
        """
        try:
            count = 0
            for user_id in user_ids:
                user = self.get_by_id(user_id)
                user.status = 'active'
                user.save()
                count += 1
            
            logger.info(f"Activated {count} users")
            return count
        except Exception as e:
            logger.error(f"Error activating users: {e}", exc_info=True)
            return 0
    
    def move_users_to_department(self, user_ids: List[int], department_id) -> int:
        """
        Move multiple users to different department.
        
        Example:
            count = repo.move_users_to_department([1, 2, 3], new_dept_id)
        """
        try:
            count = 0
            for user_id in user_ids:
                user = self.get_by_id(user_id)
                user.department_id = department_id
                user.save()
                count += 1
            
            logger.info(f"Moved {count} users to department {department_id}")
            return count
        except Exception as e:
            logger.error(f"Error moving users to department: {e}", exc_info=True)
            return 0
    
    # ============================================================
    # PAGINATION WITH SEARCH
    # ============================================================
    
    def search_paginated(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict] = None,
        ordering: str = '-created_at'
    ) -> Tuple[List[Account], object]:
        """
        Search users with pagination.
        
        Example:
            users, page = repo.search_paginated(
                "john",
                page=2,
                page_size=20,
                filters={'status': 'active'}
            )
        """
        try:
            queryset = self.get_base_queryset()
            
            # Apply search
            if query:
                queryset = queryset.filter(
                    Q(username__icontains=query) |
                    Q(email__icontains=query) |
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query)
                )
            
            # Apply filters
            if filters:
                queryset = queryset.filter(**filters)
            
            # Apply ordering
            queryset = queryset.order_by(ordering)
            
            # Paginate using Django paginator
            from django.core.paginator import Paginator
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            items = list(page_obj.object_list)
            
            logger.debug(f"Search paginated users: query={query}, page={page}, total={paginator.count}")
            
            return items, page_obj
        except Exception as e:
            logger.error(f"Error searching paginated users: {e}", exc_info=True)
            return [], None
