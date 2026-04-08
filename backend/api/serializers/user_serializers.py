"""
User Serializers - Serialization for Account, Role, Department models.
"""
from rest_framework import serializers
from apps.users.models import Account, Role, Permission, Department, AccountRole
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer


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
    """Serializer for creating new Account"""
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Account
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

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
        """Get all permission codes user has via roles"""
        return obj.get_permissions()


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
    
    def validate_role_id(self, value):
        """Validate role exists"""
        if not Role.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError(f"Role with ID {value} does not exist")
        return value


class RoleRemovalSerializer(serializers.Serializer):
    """Request serializer for removing role from user"""
    role_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RoleUpdateSerializer(serializers.Serializer):
    """Request serializer for updating role assignment (notes, etc.)"""
    role_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_role_id(self, value):
        """Validate role exists"""
        if not Role.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError(f"Role with ID {value} does not exist")
        return value


class DepartmentChangeSerializer(serializers.Serializer):
    """Request serializer for changing user's department"""
    department_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_department_id(self, value):
        """Validate department exists"""
        if not Department.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError(f"Department with ID '{value}' does not exist")
        return value


# ============================================================
# PASSWORD RESET SERIALIZERS
# ============================================================

class ForgotPasswordSerializer(serializers.Serializer):
    """
    Request serializer for POST /auth/forgot-password
    User quên password → gửi email link reset
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate email exists and account is active"""
        if not Account.objects.filter(email=value, is_deleted=False).exists():
            # Don't reveal if email exists or not for security reasons
            raise serializers.ValidationError(
                "Nếu email tồn tại, bạn sẽ nhận được email hướng dẫn reset password"
            )
        return value


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
