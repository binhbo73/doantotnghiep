"""
Department Serializers
======================
Input validation and output serialization for Department API.

Includes:
- DepartmentTreeSerializer: Full tree structure with nested sub_departments
- DepartmentDetailSerializer: Single department with all info
- DepartmentCreateSerializer: Validate input for POST/PUT
- DepartmentListSerializer: Lightweight for listing
"""

from rest_framework import serializers
from apps.users.models import Department, Account
from django.utils.translation import gettext_lazy as _


class DepartmentTreeSerializer(serializers.ModelSerializer):
    """
    Serializer for department tree structure (nested).
    
    Used in:
    - GET /api/v1/departments (tree view)
    
    Includes:
    - All department info
    - Nested sub_departments recursively
    - Member count
    - Manager info
    """
    
    manager_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    sub_departments = serializers.SerializerMethodField()
    parent_id = serializers.CharField(source='parent.id', allow_null=True, required=False)
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'parent_id', 'manager_id',
            'manager_name', 'member_count', 'created_at', 'updated_at',
            'sub_departments'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_manager_name(self, obj):
        """Get manager username if exists"""
        return obj.manager.username if obj.manager else None
    
    def get_member_count(self, obj):
        """Count direct members (not including sub-departments)"""
        return obj.get_all_members(include_subdepts=False).count()
    
    def get_sub_departments(self, obj):
        """Recursively serialize sub-departments"""
        sub_depts = obj.sub_departments.filter(is_deleted=False)
        return DepartmentTreeSerializer(sub_depts, many=True).data


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for single department detail.
    
    Used in:
    - GET /api/v1/departments/{id}
    - POST/PUT response
    
    Includes:
    - Full department info
    - Manager details (not just ID)
    - Parent info
    - Member count
    """
    
    manager = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    sub_department_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'parent', 'parent_id',
            'manager', 'manager_id', 'member_count',
            'sub_department_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_manager(self, obj):
        """Return manager object with basic info"""
        if not obj.manager:
            return None
        return {
            'id': str(obj.manager.id),
            'username': obj.manager.username,
            'email': obj.manager.email,
            'full_name': obj.manager.get_full_name()
        }
    
    def get_parent(self, obj):
        """Return parent department info"""
        if not obj.parent:
            return None
        return {
            'id': str(obj.parent.id),
            'name': obj.parent.name,
        }
    
    def get_member_count(self, obj):
        """Count direct members"""
        return obj.get_all_members(include_subdepts=False).count()
    
    def get_sub_department_count(self, obj):
        """Count direct sub-departments"""
        return obj.sub_departments.filter(is_deleted=False).count()


class DepartmentCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer for creating/updating department.
    
    Used in:
    - POST /api/v1/departments (create)
    - PUT /api/v1/departments/{id} (update)
    
    Validates:
    - name: Required, max 100 chars
    - parent_id: Optional UUID, must exist
    - manager_id: Optional UUID, must exist and be active
    - description: Optional string
    """
    
    name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=False,
        help_text="Department name"
    )
    
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Department description"
    )
    
    parent_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Parent department ID (for sub-departments)"
    )
    
    manager_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Manager account ID"
    )
    
    def validate_name(self, value):
        """Validate name is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError(_("Name cannot be empty"))
        return value.strip()
    
    def validate_parent_id(self, value):
        """Validate parent exists"""
        if value is None:
            return value
        
        from repositories.department_repository import DepartmentRepository
        repo = DepartmentRepository()
        
        parent = repo.get_by_id(value)
        if not parent:
            raise serializers.ValidationError(
                _("Parent department not found")
            )
        
        if parent.is_deleted:
            raise serializers.ValidationError(
                _("Parent department is deleted")
            )
        
        return value
    
    def validate_manager_id(self, value):
        """Validate manager exists and is active"""
        if value is None:
            return value
        
        from repositories.user_repository import UserRepository
        repo = UserRepository()
        
        manager = repo.get_by_id(value)
        if not manager:
            raise serializers.ValidationError(
                _("Manager account not found")
            )
        
        if manager.is_deleted:
            raise serializers.ValidationError(
                _("Manager account is deleted")
            )
        
        if manager.status != 'active':
            raise serializers.ValidationError(
                _("Manager account is not active")
            )
        
        return value


class DepartmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views.
    
    Used in:
    - Listing departments
    - Dropdown selections
    - Embeds in other serializers
    """
    
    manager_name = serializers.CharField(
        source='manager.username',
        allow_null=True,
        read_only=True
    )
    
    parent_name = serializers.CharField(
        source='parent.name',
        allow_null=True,
        read_only=True
    )
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'parent_id', 'parent_name',
            'manager_id', 'manager_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
