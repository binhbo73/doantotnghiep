"""
User Serializers - Serialization for Account, Role, Department, UserProfile models.
"""
from rest_framework import serializers
from apps.users.models import Account, Role, Permission, Department, AccountRole, UserProfile
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer
from core.validators import (
    validate_strong_password,
    validate_email_format,
)


class DepartmentSerializer(SoftDeleteModelSerializer):
    """Serializer for Department model"""
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'description', 'parent', 'manager', 'created_at', 'updated_at', 'is_deleted']


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model (read-only)"""
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'code', 'resource', 'action', 'description']


class RoleSerializer(SoftDeleteModelSerializer):
    """Serializer for Role model (now uses UUIDField instead of IntegerField)"""
    permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'description', 'permissions', 'created_at', 'updated_at', 'is_deleted']


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializer for Account (User) model.
    Note: Account is only for authentication, not profile info.
    Department info is in UserProfile now.
    Account.id is now UUIDField instead of BigAutoField.
    """
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'status', 'roles', 'is_active', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_roles(self, obj):
        """Get roles associated with this account"""
        roles = obj.account_roles.filter(is_deleted=False).select_related('role')
        return [
            {'id': str(r.role.id), 'name': r.role.name, 'code': r.role.code}
            for r in roles
        ]


class AccountCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new Account.
    Includes validation for username, email, and password strength.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_strong_password],
        help_text="Min 8 chars, 1 uppercase, 1 digit, 1 special char"
    )
    password_confirm = serializers.CharField(write_only=True, help_text="Confirm password")
    email = serializers.EmailField(validators=[validate_email_format])
    username = serializers.CharField()
    
    class Meta:
        model = Account
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, data):
        """Object-level validation: check passwords match"""
        password = data.get('password')
        password_confirm = data.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match"
            })
        
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        account = Account(**validated_data)
        account.set_password(password)
        account.save()
        return account


# ============================================================
# USER MANAGEMENT SERIALIZERS (Phase 1)
# ============================================================

class UserListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing users (admin view)"""
    role_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'status', 'role_names', 'date_joined', 'last_login', 'is_active'
        ]
    
    def get_role_names(self, obj):
        """Get role codes (simpler than full role objects)"""
        return list(
            obj.account_roles.filter(is_deleted=False)
            .select_related('role')
            .values_list('role__code', flat=True)
        )


class UserDetailSerializer(serializers.ModelSerializer):
    """Extended serializer with full user details"""
    roles = serializers.SerializerMethodField()
    permission_codes = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'status', 'roles', 'permission_codes', 'is_active', 'date_joined', 'last_login',
            'is_deleted', 'deleted_at'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'is_deleted', 'deleted_at',
            'roles', 'permission_codes'
        ]
    
    def get_roles(self, obj):
        """Get full role objects"""
        roles = obj.account_roles.filter(is_deleted=False).select_related('role')
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
            for r in roles
        ]
    
    def get_permission_codes(self, obj):
        """
        Get all permission codes user has via roles
        
        ✅ Uses PermissionRepository instead of Model method
        """
        try:
            from repositories.permission_repository import PermissionRepository
            perm_repo = PermissionRepository()
            return list(perm_repo.get_user_permission_codes(obj.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting permission codes for user {obj.id}: {str(e)}")
            return []


class UserProfileListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing UserProfile objects (with Account info).
    Used in: UserListView for admin to list all users with account & profile info.
    
    This serializer properly handles UserProfile objects and extracts Account data
    via SerializerMethodField to avoid AttributeError issues.
    """
    id = serializers.SerializerMethodField()
    account_id = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    role_names = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'account_id', 'username', 'email', 'first_name', 'last_name',
            'status', 'is_active', 'date_joined', 'last_login', 'role_names',
            'full_name', 'avatar_url', 'address', 'birthday', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_id(self, obj):
        """Get UserProfile ID"""
        return str(obj.id)
    
    def get_account_id(self, obj):
        """Get Account ID"""
        return str(obj.account.id)
    
    def get_username(self, obj):
        """Get username from related Account"""
        return obj.account.username
    
    def get_email(self, obj):
        """Get email from related Account"""
        return obj.account.email
    
    def get_first_name(self, obj):
        """Get first_name from related Account"""
        return obj.account.first_name
    
    def get_last_name(self, obj):
        """Get last_name from related Account"""
        return obj.account.last_name
    
    def get_status(self, obj):
        """Get status from related Account"""
        return obj.account.status
    
    def get_is_active(self, obj):
        """Get is_active from related Account"""
        return obj.account.is_active
    
    def get_date_joined(self, obj):
        """Get date_joined from related Account"""
        return obj.account.date_joined
    
    def get_last_login(self, obj):
        """Get last_login from related Account"""
        return obj.account.last_login
    
    def get_role_names(self, obj):
        """Get role codes from related Account"""
        return list(
            obj.account.account_roles.filter(is_deleted=False)
            .select_related('role')
            .values_list('role__code', flat=True)
        )


class UserStatusChangeSerializer(serializers.Serializer):
    """Request serializer for changing account status"""
    status = serializers.ChoiceField(choices=['active', 'blocked', 'inactive'])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_status(self, value):
        """Validate status is one of valid choices"""
        if value not in ['active', 'blocked', 'inactive']:
            raise serializers.ValidationError(
                f"Status must be 'active', 'blocked', or 'inactive'. Got: {value}"
            )
        return value


class RoleAssignmentSerializer(serializers.Serializer):
    """Request serializer for assigning role to account"""
    role_id = serializers.UUIDField(required=True)
    role_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    # ✅ NOTE: Removed ORM validation from Serializer
    # Database validation happens in Service layer, not Serializer
    # Serializer only validates format/type, not database existence


class RoleRemovalSerializer(serializers.Serializer):
    """Request serializer for removing role from user"""
    role_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RoleUpdateSerializer(serializers.Serializer):
    """Request serializer for updating role assignment (notes, etc.)"""
    role_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    # ✅ NOTE: Removed ORM validation from Serializer
    # Database validation happens in Service layer, not Serializer


class DepartmentChangeSerializer(serializers.Serializer):
    """Request serializer for changing user's department"""
    department_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    # ✅ NOTE: Removed ORM validation from Serializer
    # Database validation happens in Service layer, not Serializer


# ============================================================
# PASSWORD RESET SERIALIZERS
# ============================================================

class ForgotPasswordSerializer(serializers.Serializer):
    """
    Request serializer for POST /auth/forgot-password
    User quên password → gửi email link reset
    """
    email = serializers.EmailField(required=True)
    
    # ✅ NOTE: Removed ORM validation from Serializer
    # Database validation (check if email exists) happens in Service layer
    # Serializer only validates format (is_valid_email), not database existence


class ResetPasswordSerializer(serializers.Serializer):
    """
    Request serializer for POST /auth/reset-password
    Click link từ email → reset password mới
    """
    token = serializers.CharField(required=True, min_length=10, max_length=255)
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        help_text="New password (min 8 chars)"
    )
    confirm_password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        help_text="Confirm password must match new_password"
    )
    
    def validate(self, data):
        """Validate passwords match"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": "Mật khẩu xác nhận không khớp"}
            )
        return data


class AdminResetPasswordSerializer(serializers.Serializer):
    """
    Request serializer for POST /accounts/{id}/reset-password
    Admin reset password cho user mà không cần biết password cũ
    """
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        help_text="New password (min 8 chars)"
    )
    confirm_password = serializers.CharField(
        required=True,
        min_length=8,
        max_length=128,
        help_text="Confirm password must match new_password"
    )
    send_email = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Send notification email to user about password reset"
    )
    
    def validate(self, data):
        """Validate passwords match"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": "Mật khẩu xác nhận không khớp"}
            )
        return data
