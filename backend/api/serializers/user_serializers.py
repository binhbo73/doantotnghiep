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
    """Serializer for Role model"""
    permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'description', 'permissions', 'created_at', 'updated_at', 'is_deleted']


class AccountSerializer(serializers.ModelSerializer):
    """
    Serializer for Account (User) model.
    Note: Account inherits from AbstractUser, not BaseModel.
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'department', 'department_name', 'status', 'roles',
            'is_active', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_roles(self, obj):
        """Get roles associated with this account"""
        roles = obj.account_roles.filter(is_deleted=False).select_related('role')
        return [
            {'id': r.role.id, 'name': r.role.name, 'code': r.role.code}
            for r in roles
        ]


class AccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new Account"""
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Account
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'department']

    def create(self, validated_data):
        password = validated_data.pop('password')
        account = Account(**validated_data)
        account.set_password(password)
        account.save()
        return account
