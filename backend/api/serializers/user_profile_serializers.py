"""
User Profile Serializers - Serialization for UserProfile model (personal information).
Phase 2: Self-Service APIs for user to manage own profile.

Used in:
- GET /api/v1/users/me (UserProfileReadSerializer)
- PATCH /api/users/me (UserProfileWriteSerializer)
- POST /api/v1/users/me/avatar (UserProfileAvatarSerializer)
- GET /api/v1/users/{id} (EnhancedUserProfileReadSerializer) - ✅ NEW: Includes account data
"""

from rest_framework import serializers
from django.db.models import Q
from apps.users.models import UserProfile, Department, Account
from .user_serializers import AccountSerializer, DepartmentSerializer


class UserProfileReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for User Profile (personal information).
    Used for: GET /api/v1/users/me
    
    Returns:
    - id, account_id, username, email (from Account)
    - full_name, avatar_url, address, birthday
    - department_name (from Department)
    - metadata, created_at, updated_at
    """
    account_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'account_id', 'username', 'email', 'full_name', 
            'avatar_url', 'address', 'birthday', 'department_name',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'account_id', 'username', 'email', 
            'created_at', 'updated_at'
        ]
    
    def get_account_id(self, obj):
        """Get account ID"""
        return str(obj.account.id)
    
    def get_username(self, obj):
        """Get username from related Account"""
        return obj.account.username
    
    def get_email(self, obj):
        """Get email from related Account"""
        return obj.account.email
    
    def get_department_name(self, obj):
        """Get department name if exists"""
        return obj.department.name if obj.department else None


class EnhancedUserProfileReadSerializer(serializers.ModelSerializer):
    """
    ✅ ENHANCED: Returns BOTH UserProfile + Account information
    
    Used for: GET /api/v1/users/{id}
    
    Combines:
    - User Profile: id, full_name, avatar_url, address, birthday, department_name
    - Account: id, username, email, first_name, last_name, status, is_active
    - Roles & Permissions: roles[], permission_codes[]
    - Timestamps: created_at, updated_at, date_joined, last_login
    
    ✅ Single API call replaces 2 old calls!
    """
    account_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    department_id = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    permission_codes = serializers.SerializerMethodField()
    managed_departments = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            # User Profile Fields
            'id', 'account_id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'avatar_url', 'address', 'birthday', 'department_id', 'department_name',
            'metadata',
            # Account Fields (Status & Activity)
            'status', 'is_active',
            # Roles & Permissions
            'roles', 'permission_codes', 'managed_departments',
            # Timestamps
            'created_at', 'updated_at', 'date_joined', 'last_login'
        ]
        read_only_fields = fields  # All fields are read-only
    
    # ============================================================
    # PROFILE FIELDS
    # ============================================================
    
    def get_account_id(self, obj):
        """Get account ID"""
        return str(obj.account.id) if obj.account else None
    
    def get_username(self, obj):
        """Get username from Account"""
        return obj.account.username if obj.account else None
    
    def get_email(self, obj):
        """Get email from Account"""
        return obj.account.email if obj.account else None
    
    def get_first_name(self, obj):
        """Get first name from Account"""
        return obj.account.first_name if obj.account else None
    
    def get_last_name(self, obj):
        """Get last name from Account"""
        return obj.account.last_name if obj.account else None

    def get_department_id(self, obj):
        """Get department ID if exists"""
        return str(obj.department_id) if obj.department_id else None
    
    def get_department_name(self, obj):
        """Get department name if exists"""
        return obj.department.name if obj.department else None

    def get_managed_departments(self, obj):
        """Get departments where this account is assigned as manager."""
        if not obj.account_id:
            return []

        departments = Department.objects.filter(
            Q(manager_id=obj.account_id) | Q(managers__id=obj.account_id),
            is_deleted=False,
        ).distinct().order_by('name')

        return [
            {
                'id': str(dept.id),
                'name': dept.name,
                'parent_id': str(dept.parent_id) if dept.parent_id else None,
            }
            for dept in departments
        ]
    
    # ============================================================
    # ACCOUNT FIELDS (Status & Activity)
    # ============================================================
    
    def get_status(self, obj):
        """Get account status (active, blocked, inactive)"""
        return obj.account.status if obj.account else None
    
    def get_is_active(self, obj):
        """Get account is_active flag"""
        return obj.account.is_active if obj.account else False
    
    def get_date_joined(self, obj):
        """Get account creation date"""
        return obj.account.date_joined if obj.account else None
    
    def get_last_login(self, obj):
        """Get last login timestamp"""
        return obj.account.last_login if obj.account else None
    
    # ============================================================
    # ROLES & PERMISSIONS
    # ============================================================
    
    def get_roles(self, obj):
        """
        ✅ Get full role objects with permissions
        
        Returns array of roles with structure:
        {
            "id": "uuid",
            "code": "admin",
            "name": "Administrator",
            "permissions": ["permission_code1", "permission_code2", ...]
        }
        """
        if not obj.account:
            return []
        
        try:
            roles = obj.account.account_roles.filter(is_deleted=False).select_related('role')
            unique_roles = {}
            for r in roles:
                unique_roles[r.role.id] = r
                
            return [
                {
                    'id': str(r.role.id),
                    'code': r.role.code,
                    'name': r.role.name,
                    'permissions': list(
                        r.role.role_permissions.filter(is_deleted=False)
                        .values_list('permission__code', flat=True)
                    )
                }
                for r in unique_roles.values()
            ]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting roles for user {obj.id}: {str(e)}")
            return []
    
    def get_permission_codes(self, obj):
        """
        ✅ Get all permission codes user has via roles
        
        Returns flat list of permission codes: ["document_read", "document_create", ...]
        
        Uses PermissionRepository for efficiency
        """
        if not obj.account:
            return []
        
        try:
            from repositories.permission_repository import PermissionRepository
            perm_repo = PermissionRepository()
            return list(perm_repo.get_user_permission_codes(obj.account.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting permission codes for user {obj.id}: {str(e)}")
            return []


class UserProfileWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for User Profile (personal information).
    Used for: PATCH /api/users/me
    
    Allows user to update own profile info:
    - full_name (tên đầu đủ)
    - address (địa chỉ)
    - birthday (ngày sinh)
    - metadata (thông tin bổ sung: phone, social_id, etc.)
    
    ⚠️ Cannot update:
    - account (link to authentication)
    - department (handled by separate API: PATCH /api/v1/users/{id}/department)
    - avatar_url (handled by separate API: POST /api/v1/users/me/avatar)
    """
    class Meta:
        model = UserProfile
        fields = [
            'full_name', 'address', 'birthday', 'metadata'
        ]
    
    def validate_full_name(self, value):
        """Validate full_name is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Tên không được bỏ trống")
        return value.strip()
    
    def validate_birthday(self, value):
        """Validate birthday is in the past"""
        if value:
            from django.utils import timezone
            from datetime import date
            today = timezone.now().date()
            if value > today:
                raise serializers.ValidationError("Ngày sinh không thể là ngày trong tương lai")
        return value
    
    def validate_metadata(self, value):
        """Validate metadata is a dict and not too large"""
        if value and len(str(value)) > 5000:
            raise serializers.ValidationError("Metadata quá lớn (max 5000 ký tự)")
        return value or {}
    
    def update(self, instance, validated_data):
        """Update only allowed fields"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AdminUserProfileUpdateSerializer(serializers.Serializer):
    """
    Write serializer for Admin User Profile Update.
    Used for: PATCH /api/v1/users/{user_id}/ (admin endpoint)
    
    Allows admin to update user's complete profile:
    - email (Account username)
    - first_name (Account first_name)
    - last_name (Account last_name)
    - department_id (UserProfile department)
    - role_id (via Account roles)
    - is_active (Account is_active status)
    
    This is different from UserProfileWriteSerializer which is for users updating their own profile.
    """
    email = serializers.EmailField(required=False, allow_blank=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=False)
    full_name = serializers.CharField(max_length=100, required=False, allow_blank=False)
    department_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    role_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    
    def validate_email(self, value):
        """Validate email is unique"""
        if not value:
            return value
        from django.contrib.auth import get_user_model
        Account = get_user_model()
        # Use account_id/current_email passed from the view (route user_id is profile id)
        account_id = self.context.get('account_id') if self.context else None
        current_email = self.context.get('current_email') if self.context else None

        # If the email is unchanged for the current account, allow it.
        if current_email and current_email == value:
            return value

        if account_id:
            if Account.objects.filter(email=value).exclude(id=account_id).exists():
                raise serializers.ValidationError("Email này đã được sử dụng")
        else:
            if Account.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email này đã được sử dụng")
        return value
    
    def validate_first_name(self, value):
        """Validate first_name"""
        if not value:
            return value
        if not value.strip():
            raise serializers.ValidationError("Tên không được để trống")
        return value.strip()
    
    def validate_last_name(self, value):
        """Validate last_name"""
        if not value:
            return value
        if not value.strip():
            raise serializers.ValidationError("Họ không được để trống")
        return value.strip()

    def validate_full_name(self, value):
        """Validate full_name"""
        if not value:
            return value
        if not value.strip():
            raise serializers.ValidationError("Họ và tên không được để trống")
        return value.strip()
    
    def validate_department_id(self, value):
        """Validate and convert department_id to UUID"""
        if not value:
            return None
        from uuid import UUID
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError):
            raise serializers.ValidationError("department_id phải là UUID hợp lệ")
    
    def validate_role_id(self, value):
        """Validate and convert role_id to UUID"""
        if not value or value == '':
            return None
        from uuid import UUID
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError):
            raise serializers.ValidationError("role_id phải là UUID hợp lệ")
    


class UserProfileAvatarSerializer(serializers.Serializer):
    """
    Serializer for avatar upload endpoint.
    Used for: POST /api/v1/users/me/avatar
    
    Request:
    - avatar: multipart/form-data (binary image file)
    
    Response:
    - avatar_url: string (URL to uploaded image on S3/CDN)
    
    Validations:
    - File size: max 5MB
    - File types: image/jpeg, image/png, image/webp
    """
    avatar = serializers.ImageField(
        required=True,
        help_text="Avatar image file (JPG, PNG, WebP. Max 5MB)"
    )
    
    def validate_avatar(self, value):
        """Validate avatar file: size and format"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError("Kích thước ảnh quá lớn (max 5MB)")
        
        # Check file type
        allowed_formats = ['image/jpeg', 'image/png', 'image/webp']
        if value.content_type not in allowed_formats:
            raise serializers.ValidationError(
                "Định dạng ảnh không hỗ trợ. Vui lòng dùng JPG, PNG hoặc WebP"
            )
        
        return value


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """
    Complete profile view with full details (account + department).
    Used by: Admin endpoints to view complete user profile
    
    Read-only view combining:
    - Account info (authentication)
    - UserProfile info (personal)
    - Department info (organization)
    """
    account = AccountSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'account', 'full_name', 'avatar_url', 'address', 
            'birthday', 'department', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'account', 'created_at', 'updated_at'
        ]


class UserProfileUpdateAsAdminSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer to update user profile (all fields).
    Used by: PATCH /api/v1/users/{user_id}/ (in user_management_views)
    
    Admin can update:
    - full_name, address, birthday, metadata (same as user)
    - NO: account (authentication), department (separate API)
    """
    class Meta:
        model = UserProfile
        fields = [
            'full_name', 'address', 'birthday', 'metadata'
        ]
    
    def validate_full_name(self, value):
        """Validate full_name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Tên không được bỏ trống")
        return value.strip()
    
    def validate_birthday(self, value):
        """Validate birthday"""
        if value:
            from django.utils import timezone
            from datetime import date
            today = timezone.now().date()
            if value > today:
                raise serializers.ValidationError("Ngày sinh không thể là ngày trong tương lai")
        return value
