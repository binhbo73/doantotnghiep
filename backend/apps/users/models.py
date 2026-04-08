"""
User Management Models - Accounts, Roles, Permissions, Departments.
Includes soft delete, timestamps, and fine-grained permission system.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from core.models import BaseModel
from core.constants import (
    AccountStatus,
    ACCOUNT_STATUSES,
    PermissionCodes,
    ALL_PERMISSIONS,
    RoleIds,
    ROLES,
)


class Account(AbstractUser):
    """
    Authentication/Account model (extends Django AbstractUser).
    Maps to 'accounts' table.
    
    Features:
    - Soft delete (is_deleted flag)
    - Account status (active/blocked/inactive)
    - Linked to Roles (many-to-many via AccountRole)
    
    Note: Department info is in UserProfile (users table), not here.
    This table is for authentication only.
    """
    
    # Primary key - UUID instead of default BigAutoField
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Account status
    status = models.CharField(
        max_length=20,
        default=AccountStatus.ACTIVE,
        choices=ACCOUNT_STATUSES,
        db_index=True,
        help_text="Account status: active, blocked, or inactive"
    )
    
    # Soft delete fields
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Last login tracking
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "accounts"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['status']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def get_roles(self):
        """Get all roles của user"""
        return self.account_roles.filter(is_deleted=False).select_related('role')
    
    def has_role(self, role_id) -> bool:
        """Check nếu user có role nào đó (role_id is now UUID)"""
        return self.account_roles.filter(role_id=role_id, is_deleted=False).exists()
    
    def get_permissions(self):
        """Get tất cả permission codes từ roles"""
        roles = self.get_roles().values_list('role_id', flat=True)
        if not roles:
            return []
        # Lazy import để tránh circular imports khi model definition
        from django.apps import apps
        RolePermission = apps.get_model('users', 'RolePermission')
        permissions = RolePermission.objects.filter(
            role_id__in=roles,
            is_deleted=False
        ).values_list('permission__code', flat=True).distinct()
        return list(permissions)
    
    def has_permission(self, permission_code: str) -> bool:
        """Check nếu user có permission"""
        roles = self.get_roles().values_list('role_id', flat=True)
        if not roles:
            return False
        # Lazy import để tránh circular imports
        from django.apps import apps
        RolePermission = apps.get_model('users', 'RolePermission')
        return RolePermission.objects.filter(
            role_id__in=roles,
            permission__code=permission_code,
            is_deleted=False
        ).exists()


class Department(BaseModel):
    """
    Organization department (hierarchical tree structure).
    Each department can have a parent department for organizational hierarchy.
    Inherit từ BaseModel → có soft delete + timestamps.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Department name")
    
    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments',
        help_text="Parent department (for hierarchical structure)"
    )
    
    # Meta
    manager = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        help_text="Department manager"
    )
    description = models.TextField(max_length=500, null=True, blank=True)
    
    class Meta:
        db_table = "departments"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        indexes = [
            models.Index(fields=['parent_id']),
            models.Index(fields=['manager_id']),
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_parent_chain(self):
        """Get tất cả parent departments (từ current lên root)"""
        chain = [self]
        current = self.parent
        while current:
            chain.append(current)
            current = current.parent
        return chain
    
    def get_all_members(self, include_subdepts=True):
        """Get tất cả members (của department này + sub-departments)"""
        if include_subdepts:
            dept_ids = [self.id]
            def get_sub_depts(dept):
                for sub in dept.sub_departments.filter(is_deleted=False):
                    dept_ids.append(sub.id)
                    get_sub_depts(sub)
            get_sub_depts(self)
            return Account.objects.filter(department_id__in=dept_ids, is_deleted=False)
        else:
            return Account.objects.filter(department=self, is_deleted=False)


class Role(BaseModel):
    """
    Role definition (e.g., Admin, Manager, User).
    Changed from IntegerField(1,2,3) to UUIDField for consistency.
    
    Migration: Old IDs (1=ADMIN, 2=MANAGER, 3=USER) are mapped to new UUIDs
    via constants in core/constants.py
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text="Role code (e.g., 'admin')")
    name = models.CharField(max_length=100, help_text="Role name (e.g., 'Administrator')")
    description = models.TextField(max_length=500, blank=True, help_text="Role description")
    
    # System role flag
    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted (Admin/Manager/User)"
    )
    
    class Meta:
        db_table = "roles"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_permissions(self):
        """Get tất cả permissions của role này"""
        return self.role_permissions.filter(
            is_deleted=False
        ).select_related('permission')


class Permission(BaseModel):
    """
    Permission definition (e.g., document_read, user_update).
    Code theo pattern: {resource}_{action}
    
    Ví dụ:
        - document_create
        - document_read
        - document_update
        - document_delete
        - user_change_role
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Permission code (e.g., 'document_read')"
    )
    name = models.CharField(max_length=200, help_text="Permission name")
    description = models.TextField(max_length=500, blank=True, help_text="Permission description")
    resource = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Resource (e.g., 'document', 'user', 'folder')"
    )
    action = models.CharField(
        max_length=50,
        help_text="Action (e.g., 'create', 'read', 'update', 'delete')"
    )
    
    class Meta:
        db_table = "permissions"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['resource']),
            models.Index(fields=['is_deleted']),
        ]
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class RolePermission(BaseModel):
    """
    Role-Permission mapping (many-to-many with extra fields).
    Tracks khi nào permission được gán/revoke vào role.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        help_text="Role"
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permission_mappings',
        help_text="Permission"
    )
    granted_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
        help_text="Admin who granted this permission"
    )
    notes = models.TextField(blank=True, help_text="Notes about this assignment")
    
    class Meta:
        db_table = "role_permissions"
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
        unique_together = ('role', 'permission')  # Một role không thể có cùng permission 2 lần
        indexes = [
            models.Index(fields=['role', 'permission']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.role.name} → {self.permission.code}"


class AccountRole(BaseModel):
    """
    Account-Role mapping (many-to-many).
    Tracks khi nào role được gán cho user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='account_roles',
        help_text="User account"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='account_role_mappings',
        help_text="Role"
    )
    granted_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_roles',
        help_text="Admin who granted this role"
    )
    notes = models.TextField(blank=True, help_text="Notes about this assignment")
    
    class Meta:
        db_table = "account_roles"
        verbose_name = "Account Role"
        verbose_name_plural = "Account Roles"
        constraints = [
            models.UniqueConstraint(
                fields=['account', 'role'],
                condition=models.Q(is_deleted=False),
                name='unique_account_role_active'
            )
        ]
        indexes = [
            models.Index(fields=['account', 'role']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.account.username} → {self.role.name}"


class Company(BaseModel):
    """
    Single-company configuration store (on-premise).
    Typically only 1 record in this table for on-premise deployments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Company name")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="URL-friendly slug"
    )
    tax_code = models.CharField(max_length=50, null=True, blank=True, help_text="Tax identification number")
    domain = models.CharField(max_length=100, null=True, blank=True, help_text="Company domain (e.g., company.com)")

    def __str__(self):
        return self.name


class UserProfile(BaseModel):
    """
    User profile (personal information).
    1:1 relationship with Account (authentication).
    Contains user metadata and profile info.
    
    Inherits from BaseModel: automatic soft delete + timestamps + SoftDeleteManager
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='user_profile',
        help_text="Link to Account (authentication)"
    )
    full_name = models.CharField(max_length=100, help_text="Full name of user")
    avatar_url = models.URLField(max_length=500, null=True, blank=True, help_text="Avatar URL (S3/CDN)")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="User's department"
    )
    address = models.TextField(null=True, blank=True, help_text="User's address")
    birthday = models.DateField(null=True, blank=True, help_text="User's birthday")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (phone, social_id, etc.)"
    )

    class Meta:
        db_table = "users"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            models.Index(fields=['account_id']),
            models.Index(fields=['department_id']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.account.username})"


class PasswordResetToken(models.Model):
    """
    Password Reset Token - Lưu tokens cho phép reset password qua email.
    
    Sử dụng Django's make_password_reset_link hoặc UUID tokens.
    Auto-deleted sau khi hết hạn (TTL) hoặc được sử dụng.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        help_text="Account which can reset password"
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Reset token (generated randomly)"
    )
    
    # Token expiration (24 hours)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Token expiration time")
    
    # Track usage
    is_used = models.BooleanField(default=False, help_text="Token has been used")
    used_at = models.DateTimeField(null=True, blank=True, help_text="Khi token được sử dụng")
    
    # Admin action (optional)
    is_admin_action = models.BooleanField(
        default=False,
        help_text="Token được tạo bởi Admin reset password"
    )
    generated_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reset_tokens',
        help_text="Admin who generated this token (if admin action)"
    )
    
    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['account_id']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset token for {self.account.username} (expires: {self.expires_at})"
    
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired and not used)"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()
