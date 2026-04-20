"""
Role & Permission Serializers
Used by IAM endpoints
"""

from rest_framework import serializers
from apps.users.models import Role, Permission, RolePermission


class PermissionSerializer(serializers.ModelSerializer):
    """Serialize Permission objects - used for GET responses"""
    
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'resource', 'action', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PermissionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating permissions
    
    Write Operations:
    - PUT /api/v1/iam/permissions/{id} - Update permission details
    
    Features:
    - Validates permission code uniqueness (on update)
    - Validates required fields (name cannot be empty)
    - Allows partial updates
    - Validates code pattern {resource}_{action}
    """
    
    class Meta:
        model = Permission
        fields = ['code', 'name', 'description', 'resource', 'action']
        extra_kwargs = {
            'code': {'required': False},
            'name': {'required': False},
            'description': {'required': False},
            'resource': {'required': False},
            'action': {'required': False},
        }
    
    def validate_code(self, value):
        """Validate permission code is unique (excluding current permission)"""
        if not value:
            return value  # Allow None/empty for partial update
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Permission code cannot be empty.")
        
        # Check uniqueness (exclude current instance if updating)
        queryset = Permission.objects.filter(code=value, is_deleted=False)
        
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Permission with code '{value}' already exists."
            )
        
        return value
    
    def validate_name(self, value):
        """Validate permission name is not empty"""
        if value is None:
            return value  # Allow None for partial update
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Permission name cannot be empty.")
        
        return value
    
    def validate_resource(self, value):
        """Validate resource is not empty if provided"""
        if value is None:
            return value  # Allow None for partial update
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Resource cannot be empty.")
        
        return value
    
    def validate_action(self, value):
        """Validate action is not empty if provided"""
        if value is None:
            return value  # Allow None for partial update
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Action cannot be empty.")
        
        return value
    
    def validate(self, data):
        """Validate combined fields"""
        # At least one field should be provided for update
        if not data:
            raise serializers.ValidationError("At least one field must be provided for update.")
        
        return data


class PermissionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new permissions
    
    Write Operations:
    - POST /api/v1/iam/permissions - Create new permission
    
    Features:
    - Validates all required fields
    - Validates permission code uniqueness
    - Validates code pattern {resource}_{action}
    """
    
    class Meta:
        model = Permission
        fields = ['code', 'name', 'description', 'resource', 'action']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'description': {'required': False},
            'resource': {'required': True},
            'action': {'required': True},
        }
    
    def validate_code(self, value):
        """Validate permission code"""
        if not value:
            raise serializers.ValidationError("Permission code is required.")
        
        value = str(value).strip().lower()
        
        # Check uniqueness
        if Permission.objects.filter(code=value, is_deleted=False).exists():
            raise serializers.ValidationError(
                f"Permission with code '{value}' already exists."
            )
        
        # Validate format: resource_action
        if '_' not in value:
            raise serializers.ValidationError(
                "Permission code must follow pattern: {resource}_{action} (e.g., document_read)"
            )
        
        return value
    
    def validate_name(self, value):
        """Validate permission name"""
        if not value:
            raise serializers.ValidationError("Permission name is required.")
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Permission name cannot be empty.")
        
        return value
    
    def validate_resource(self, value):
        """Validate resource"""
        if not value:
            raise serializers.ValidationError("Resource is required.")
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Resource cannot be empty.")
        
        return value
    
    def validate_action(self, value):
        """Validate action"""
        if not value:
            raise serializers.ValidationError("Action is required.")
        
        value = str(value).strip()
        
        if not value:
            raise serializers.ValidationError("Action cannot be empty.")
        
        return value


class RolePermissionSerializer(serializers.ModelSerializer):
    """Serialize RolePermission (M2M relation)"""
    permission = PermissionSerializer(read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission']


class RoleSerializer(serializers.ModelSerializer):
    """
    Serialize Role with related permissions
    
    Handles:
    - Role CRUD
    - Permission assignment (via permission_ids write-only field)
    - Nested permission data (read-only)
    """
    
    # Read-only: nested permissions
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    
    # Write-only: accept permission IDs to assign
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        source='permissions',
        required=False
    )
    
    class Meta:
        model = Role
        fields = [
            'id', 'code', 'name', 'description', 'is_custom',
            'permissions', 'permission_ids', 'permission_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_custom', 'created_at', 'updated_at']
    
    def get_permission_count(self, obj):
        """Return count of permissions assigned to role"""
        return obj.permissions.count()
    
    def create(self, validated_data):
        """Create new role"""
        permissions = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        
        # Assign permissions
        if permissions:
            role.permissions.set(permissions)
        
        return role
    
    def update(self, instance, validated_data):
        """Update existing role"""
        permissions = validated_data.pop('permissions', None)
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update permissions if provided
        if permissions is not None:
            instance.permissions.set(permissions)
        
        return instance
    
    def validate_code(self, value):
        """Validate role code is unique"""
        # Check uniqueness (exclude current instance if updating)
        queryset = Role.objects.filter(code=value, is_deleted=False)
        
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Role with code '{value}' already exists."
            )
        
        return value
    
    def validate_name(self, value):
        """Validate role name is not empty"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Role name cannot be empty.")
        return value


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating roles with permission assignment
    
    Write Operations:
    - POST /api/v1/iam/roles - Create new role
    - PUT /api/v1/iam/roles/{id} - Update existing role
    
    Features:
    - Validates role code uniqueness
    - Validates role name not empty
    - Accepts permission_ids for permission assignment
    - Replaces all permissions on update
    """
    
    # Write-only: accept permission IDs to assign/update
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.filter(is_deleted=False),
        many=True,
        write_only=True,
        source='permissions',
        required=False,
        label='Permission IDs'
    )
    
    class Meta:
        model = Role
        fields = ['code', 'name', 'description', 'permission_ids']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'description': {'required': False}
        }
    
    def validate_code(self, value):
        """Validate role code is unique and not system role"""
        if not value:
            raise serializers.ValidationError("Role code cannot be empty.")
        
        # Check if code is reserved for system roles
        if value.upper() in ['ADMIN', 'MANAGER', 'USER', 'GUEST']:
            raise serializers.ValidationError(
                f"Role code '{value}' is reserved for system roles."
            )
        
        # Check uniqueness (exclude current instance if updating)
        queryset = Role.objects.filter(code=value, is_deleted=False)
        
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Role with code '{value}' already exists."
            )
        
        return value
    
    def validate_name(self, value):
        """Validate role name is not empty"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Role name cannot be empty.")
        return value
    
    def create(self, validated_data):
        """Create new role with permissions"""
        permissions = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        
        if permissions:
            role.permissions.set(permissions)
        
        return role
    
    def update(self, instance, validated_data):
        """Update existing role with permissions"""
        permissions = validated_data.pop('permissions', None)
        
        # Update basic fields
        for attr in ['name', 'description']:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        
        instance.save()
        
        # Update permissions if provided (replaces all)
        if permissions is not None:
            instance.permissions.set(permissions)
        
        return instance


class RoleDetailSerializer(serializers.ModelSerializer):
    """
    Detailed role serializer (includes permission list and counts)
    Used when returning single role details
    """
    
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id', 'code', 'name', 'description', 'is_custom',
            'permissions', 'permission_count', 'user_count',
            'created_at', 'updated_at'
        ]
    
    def get_permission_count(self, obj):
        """Get permission count"""
        return obj.permissions.count()
    
    def get_user_count(self, obj):
        """
        Count active users with this role
        Note: This is counted at serialization time (acceptable for detail view)
        For list views, pre-calculate and pass in context
        """
        from apps.users.models import AccountRole
        return AccountRole.objects.filter(
            role=obj,
            is_active=True,
            is_deleted=False
        ).count()


# Alias for backward compatibility and clarity
PermissionDetailSerializer = PermissionSerializer
