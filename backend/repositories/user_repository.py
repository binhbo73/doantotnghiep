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
    
    # ============================================================
    # SAVE/PERSIST OPERATIONS
    # ============================================================
    
    def save_account(self, account: Account, update_fields: List[str] = None) -> Account:
        """
        Save account to database.
        
        Args:
            account: Account instance to save
            update_fields: List of fields to update (optional, None = save all)
        
        Returns:
            Saved Account instance
        
        Example:
            account.status = 'blocked'
            repo.save_account(account, update_fields=['status', 'updated_at'])
        """
        try:
            if update_fields:
                account.save(update_fields=update_fields)
            else:
                account.save()
            logger.info(f"Account saved: {account.id}")
            return account
        except Exception as e:
            logger.error(f"Error saving account {account.id}: {str(e)}")
            raise
    
    def update_account(self, account_id, **update_data) -> Account:
        """
        Update account fields.
        
        Args:
            account_id: Account UUID
            **update_data: Fields to update
        
        Returns:
            Updated Account instance
        
        Example:
            repo.update_account(user_id, status='active', first_name='John')
        """
        try:
            account = self.get_by_id(account_id)
            for key, value in update_data.items():
                if hasattr(account, key) and value is not None:
                    setattr(account, key, value)
            self.save_account(account, update_fields=list(update_data.keys()) + ['updated_at'])
            logger.info(f"Account updated: {account_id}. Fields: {list(update_data.keys())}")
            return account
        except Exception as e:
            logger.error(f"Error updating account {account_id}: {str(e)}")
            raise
    
    # ============================================================
    # USER PROFILE OPERATIONS
    # ============================================================
    
    def create_user_profile(self, account, department=None, **profile_data) -> any:
        """
        Create UserProfile for account.
        
        Args:
            account: Account instance
            department: Department instance (optional)
            **profile_data: Additional profile fields
        
        Returns:
            Created UserProfile instance
        
        Example:
            profile = repo.create_user_profile(account, department=dept, full_name="John Doe")
        """
        try:
            from apps.users.models import UserProfile
            
            profile_data['account'] = account
            if department:
                profile_data['department'] = department
            
            profile = UserProfile.objects.create(**profile_data)
            logger.info(f"UserProfile created for account: {account.id}")
            return profile
        except Exception as e:
            logger.error(f"Error creating UserProfile: {str(e)}")
            raise
    
    # ============================================================
    # ACCOUNT ROLE OPERATIONS
    # ============================================================
    
    def create_account_role(self, account_id, role_id, granted_by=None, notes: str = '') -> AccountRole:
        """
        Create AccountRole (assign role to user).
        
        Args:
            account_id: Account UUID
            role_id: Role UUID
            granted_by: Admin user who granted the role (optional)
            notes: Optional notes
        
        Returns:
            Created AccountRole instance
        
        Example:
            ar = repo.create_account_role(user_id, admin_role_id, granted_by=admin_user)
        """
        try:
            ar = AccountRole.objects.create(
                account_id=account_id,
                role_id=role_id,
                granted_by=granted_by,
                notes=notes
            )
            logger.info(f"Role {role_id} assigned to account {account_id}")
            return ar
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            raise
    
    def get_account_role(self, account_id, role_id) -> Optional[AccountRole]:
        """
        Get specific account role assignment.
        
        Args:
            account_id: Account UUID
            role_id: Role UUID
        
        Returns:
            AccountRole instance or None
        
        Example:
            ar = repo.get_account_role(user_id, admin_role_id)
        """
        try:
            return AccountRole.objects.filter(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting account role: {str(e)}")
            return None
    
    def get_all_account_roles(self, account_id) -> List[AccountRole]:
        """
        Get all active role assignments for an account.
        
        Args:
            account_id: Account UUID
        
        Returns:
            List of AccountRole instances
        
        Example:
            roles = repo.get_all_account_roles(user_id)
        """
        try:
            return list(AccountRole.objects.filter(
                account_id=account_id,
                is_deleted=False
            ).select_related('role'))
        except Exception as e:
            logger.error(f"Error getting account roles: {str(e)}")
            return []
    
    def update_account_role(self, account_id, role_id, notes: str = '') -> AccountRole:
        """
        Update account role assignment (notes only).
        
        Args:
            account_id: Account UUID
            role_id: Role UUID
            notes: Updated notes
        
        Returns:
            Updated AccountRole instance
        
        Example:
            ar = repo.update_account_role(user_id, role_id, notes="Updated note")
        """
        try:
            ar = AccountRole.objects.get(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            )
            ar.notes = notes
            ar.save(update_fields=['notes', 'updated_at'])
            logger.info(f"Account role updated for account {account_id} role {role_id}")
            return ar
        except Exception as e:
            logger.error(f"Error updating account role: {str(e)}")
            raise
    
    def delete_account_role(self, account_id, role_id) -> bool:
        """
        Soft-delete account role assignment.
        
        Args:
            account_id: Account UUID
            role_id: Role UUID
        
        Returns:
            True if deleted, False otherwise
        
        Example:
            repo.delete_account_role(user_id, old_role_id)
        """
        try:
            ar = AccountRole.objects.get(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            )
            ar.is_deleted = True
            from django.utils import timezone
            ar.deleted_at = timezone.now()
            ar.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            logger.info(f"Account role deleted for account {account_id} role {role_id}")
            return True
        except AccountRole.DoesNotExist:
            logger.warning(f"Account role not found: account {account_id}, role {role_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting account role: {str(e)}")
            raise
    
    # ============================================================
    # VALIDATION OPERATIONS
    # ============================================================
    
    def check_email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email to check
            exclude_id: Account ID to exclude (for updates)
        
        Returns:
            True if exists, False otherwise
        
        Example:
            if repo.check_email_exists("john@example.com"):
                raise ValidationError("Email already exists")
        """
        try:
            queryset = Account.objects.filter(email=email, is_deleted=False)
            if exclude_id:
                queryset = queryset.exclude(id=exclude_id)
            return queryset.exists()
        except Exception as e:
            logger.error(f"Error checking email exists: {str(e)}")
            return False
    
    def check_username_exists(self, username: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if username already exists.
        
        Args:
            username: Username to check
            exclude_id: Account ID to exclude (for updates)
        
        Returns:
            True if exists, False otherwise
        
        Example:
            if repo.check_username_exists("john_doe"):
                raise ValidationError("Username already exists")
        """
        try:
            queryset = Account.objects.filter(username=username, is_deleted=False)
            if exclude_id:
                queryset = queryset.exclude(id=exclude_id)
            return queryset.exists()
        except Exception as e:
            logger.error(f"Error checking username exists: {str(e)}")
            return False
