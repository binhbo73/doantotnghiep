"""
User Profile Repository - Database queries for UserProfile model.

Encapsulates all database operations related to UserProfile.
Used by UserService to access UserProfile data.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from django.db.models import QuerySet
from django.apps import apps
from django.db import transaction

import logging

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """
    Repository for UserProfile model.
    Handles all database queries for user profiles.
    
    ✅ SOLID Principle: Single Responsibility
    - Only database queries, no business logic
    - Encapsulates ORM layer
    - Reusable by Services
    """
    
    def __init__(self):
        self.UserProfile = apps.get_model('users', 'UserProfile')
        self.Account = apps.get_model('users', 'Account')
    
    # ============================================================
    # READ OPERATIONS
    # ============================================================
    
    def get_profile_by_account_id(self, account_id: UUID) -> Optional[object]:
        """
        Get UserProfile by Account ID.
        
        Args:
            account_id: UUID of Account
        
        Returns:
            UserProfile object or None if not found
        """
        try:
            return self.UserProfile.objects.select_related(
                'account', 'department'
            ).get(account_id=account_id, is_deleted=False)
        except self.UserProfile.DoesNotExist:
            logger.warning(f"UserProfile not found for account_id: {account_id}")
            return None
    
    def get_profile_by_id(self, profile_id: UUID) -> Optional[object]:
        """
        Get UserProfile by ID.
        
        Args:
            profile_id: UUID of UserProfile
        
        Returns:
            UserProfile object or None
        """
        try:
            return self.UserProfile.objects.select_related(
                'account', 'department'
            ).get(id=profile_id, is_deleted=False)
        except self.UserProfile.DoesNotExist:
            return None
    
    def get_all_profiles(self, active_only: bool = True) -> QuerySet:
        """
        Get all UserProfiles (active or all).
        
        Args:
            active_only: If True, only non-deleted profiles
        
        Returns:
            QuerySet of UserProfile objects
        """
        queryset = self.UserProfile.objects.select_related('account', 'department')
        
        if active_only:
            queryset = queryset.filter(is_deleted=False)
        
        return queryset.order_by('-created_at')
    
    def get_profiles_by_department(self, department_id: UUID) -> QuerySet:
        """
        Get all UserProfiles in a department.
        
        Args:
            department_id: UUID of Department
        
        Returns:
            QuerySet of UserProfile objects
        """
        return self.UserProfile.objects.select_related(
            'account', 'department'
        ).filter(
            department_id=department_id,
            is_deleted=False
        ).order_by('account__username')
    
    def profile_exists(self, account_id: UUID) -> bool:
        """
        Check if UserProfile exists for Account.
        
        Args:
            account_id: UUID of Account
        
        Returns:
            True if profile exists, False otherwise
        """
        return self.UserProfile.objects.filter(
            account_id=account_id,
            is_deleted=False
        ).exists()
    
    # ============================================================
    # CREATE OPERATIONS
    # ============================================================
    
    @transaction.atomic
    def create_profile(self, account_id: UUID, profile_data: Dict[str, Any]) -> object:
        """
        Create new UserProfile for an Account.
        
        Args:
            account_id: UUID of Account
            profile_data: Dict with fields: full_name, address, birthday, department_id, metadata
        
        Returns:
            Created UserProfile object
        
        Raises:
            ValueError: If Account not found
        """
        try:
            account = self.Account.objects.get(id=account_id, is_deleted=False)
        except self.Account.DoesNotExist:
            raise ValueError(f"Account {account_id} not found")
        
        profile = self.UserProfile(
            account=account,
            **profile_data
        )
        profile.save()
        
        logger.info(f"UserProfile created for account: {account.username}")
        return profile
    
    # ============================================================
    # UPDATE OPERATIONS
    # ============================================================
    
    @transaction.atomic
    def update_profile(self, account_id: UUID, update_data: Dict[str, Any]) -> object:
        """
        Update UserProfile fields.
        
        Args:
            account_id: UUID of Account
            update_data: Dict with fields to update (full_name, address, birthday, metadata)
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile_by_account_id(account_id)
        
        if not profile:
            raise ValueError(f"UserProfile not found for account: {account_id}")
        
        # Update only allowed fields
        allowed_fields = ['full_name', 'address', 'birthday', 'metadata']
        for field, value in update_data.items():
            if field in allowed_fields and value is not None:
                setattr(profile, field, value)
        
        profile.save(update_fields=list(update_data.keys()) + ['updated_at'])
        
        logger.info(f"UserProfile updated for account: {account_id}")
        return profile
    
    @transaction.atomic
    def update_avatar_url(self, account_id: UUID, avatar_url: str) -> object:
        """
        Update avatar_url for UserProfile.
        
        Args:
            account_id: UUID of Account
            avatar_url: New avatar URL
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile_by_account_id(account_id)
        
        if not profile:
            raise ValueError(f"UserProfile not found for account: {account_id}")
        
        old_avatar = profile.avatar_url
        profile.avatar_url = avatar_url
        profile.save(update_fields=['avatar_url', 'updated_at'])
        
        logger.info(f"Avatar updated for {account_id}: {old_avatar} → {avatar_url}")
        return profile
    
    @transaction.atomic
    def update_department(self, account_id: UUID, department_id: UUID) -> object:
        """
        Update department for UserProfile.
        
        Args:
            account_id: UUID of Account
            department_id: UUID of new Department
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValueError: If profile or department not found
        """
        profile = self.get_profile_by_account_id(account_id)
        
        if not profile:
            raise ValueError(f"UserProfile not found for account: {account_id}")
        
        # Verify department exists
        Department = apps.get_model('users', 'Department')
        try:
            department = Department.objects.get(id=department_id, is_deleted=False)
        except Department.DoesNotExist:
            raise ValueError(f"Department {department_id} not found")
        
        old_dept = profile.department
        profile.department = department
        profile.save(update_fields=['department', 'updated_at'])
        
        logger.info(f"Department updated for {account_id}: {old_dept} → {department.name}")
        return profile
    
    # ============================================================
    # DELETE OPERATIONS
    # ============================================================
    
    @transaction.atomic
    def soft_delete_profile(self, account_id: UUID) -> bool:
        """
        Soft delete UserProfile (set is_deleted=True).
        
        Args:
            account_id: UUID of Account
        
        Returns:
            True if deleted, False if not found
        """
        profile = self.get_profile_by_account_id(account_id)
        
        if not profile:
            return False
        
        from django.utils import timezone
        profile.is_deleted = True
        profile.deleted_at = timezone.now()
        profile.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        
        logger.info(f"UserProfile soft deleted for account: {account_id}")
        return True
    
    # ============================================================
    # UTILITY OPERATIONS
    # ============================================================
    
    def count_profiles_in_department(self, department_id: UUID) -> int:
        """
        Count active UserProfiles in a department.
        
        Args:
            department_id: UUID of Department
        
        Returns:
            Count of profiles
        """
        return self.UserProfile.objects.filter(
            department_id=department_id,
            is_deleted=False
        ).count()
    
    def search_profiles(self, search: str = None, department_id: str = None, status: str = None) -> QuerySet:
        """
        Search profiles with filters.
        
        Args:
            search: Search string (username, email, full_name)
            department_id: Filter by department UUID
            status: Filter by account status (active, blocked, inactive)
        
        Returns:
            QuerySet of matching profiles
        """
        from django.db.models import Q
        
        queryset = self.UserProfile.objects.select_related(
            'account', 'department'
        ).filter(is_deleted=False)
        
        # Search filter
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(account__username__icontains=search) |
                Q(account__email__icontains=search)
            )
        
        # Department filter
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        # Status filter
        if status:
            queryset = queryset.filter(account__status=status)
        
        return queryset.order_by('-account__date_joined', 'id')
