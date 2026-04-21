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


# ============================================================================
# HYBRID APPROACH SERIALIZERS - For Detail Endpoints
# ============================================================================

class UserSimpleSerializer(serializers.Serializer):
    """
    Lightweight user serializer for department user lists.
    
    Used in:
    - GET /api/v1/departments/{id}/users
    - GET /api/v1/departments/{id}/detail?expand=users
    
    Returns: Basic user info without sensitive data
    """
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    avatar_url = serializers.URLField(allow_null=True)
    
    class Meta:
        fields = ['id', 'username', 'email', 'full_name', 'avatar_url']


class FolderSimpleSerializer(serializers.Serializer):
    """
    Lightweight folder serializer for department folder lists.
    
    Used in:
    - GET /api/v1/departments/{id}/folders
    - GET /api/v1/departments/{id}/detail?expand=folders
    
    Returns: Basic folder info + child count
    """
    id = serializers.UUIDField()
    name = serializers.CharField()
    parent_id = serializers.UUIDField(allow_null=True)
    access_scope = serializers.CharField()
    created_by_id = serializers.UUIDField()
    document_count = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    
    def get_document_count(self, obj):
        """Count documents in this folder"""
        return obj.documents.filter(is_deleted=False).count()
    
    def get_subfolder_count(self, obj):
        """Count direct subfolders"""
        return obj.subfolders.filter(is_deleted=False).count()


class DocumentSimpleSerializer(serializers.Serializer):
    """
    Lightweight document serializer for department/folder document lists.
    
    Used in:
    - GET /api/v1/departments/{id}/documents
    - GET /api/v1/folders/{id}/documents
    - GET /api/v1/departments/{id}/detail?expand=documents
    
    Returns: Basic document info
    """
    id = serializers.UUIDField()
    filename = serializers.CharField()
    original_name = serializers.CharField()
    file_type = serializers.CharField()
    file_size = serializers.IntegerField()
    status = serializers.CharField()
    uploader_id = serializers.UUIDField()
    department_id = serializers.UUIDField(allow_null=True)
    folder_id = serializers.UUIDField(allow_null=True)
    access_scope = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class DepartmentDetailWithCountsSerializer(serializers.ModelSerializer):
    """
    Department detail with counts (BASIC view).
    
    Used in:
    - GET /api/v1/departments/{id}
    
    Returns:
    {
        "id": "uuid",
        "name": "Sales",
        "parent_id": null,
        "description": "...",
        "manager": {...},
        "member_count": 10,
        "folder_count": 5,
        "document_count": 20,
        "sub_department_count": 3,
        "sub_departments": [{...}],  # Recursive
        "created_at": "...",
        "updated_at": "..."
    }
    """
    manager = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    folder_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    sub_department_count = serializers.SerializerMethodField()
    sub_departments = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'parent', 'parent_id',
            'manager', 'manager_id', 'member_count',
            'folder_count', 'document_count', 'sub_department_count',
            'sub_departments', 'created_at', 'updated_at'
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
            'full_name': obj.manager.get_full_name() if hasattr(obj.manager, 'get_full_name') else ''
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
        """Count direct members (not including sub-departments)"""
        return obj.get_all_members(include_subdepts=False).count()
    
    def get_folder_count(self, obj):
        """Count folders in this department"""
        return obj.folders.filter(is_deleted=False).count()
    
    def get_document_count(self, obj):
        """Count documents in this department"""
        return obj.documents.filter(is_deleted=False).count()
    
    def get_sub_department_count(self, obj):
        """Count direct sub-departments"""
        return obj.sub_departments.filter(is_deleted=False).count()
    
    def get_sub_departments(self, obj):
        """Recursively serialize sub-departments"""
        sub_depts = obj.sub_departments.filter(is_deleted=False)
        return DepartmentDetailWithCountsSerializer(sub_depts, many=True).data


class DepartmentExpandedSerializer(serializers.Serializer):
    """
    Department detail with EXPANDED data (FULL view).
    
    Used in:
    - GET /api/v1/departments/{id}/detail?expand=users,folders,documents
    
    Returns: Basic department info + expanded lists (paginated)
    
    Query Parameters:
    - expand: Comma-separated list of fields to expand (users, folders, documents)
    - page: Page number for each expanded field (default: 1)
    - page_size: Items per page (default: 10)
    
    Example Response:
    {
        "id": "uuid",
        "name": "Sales",
        "parent_id": null,
        "manager": {...},
        "member_count": 10,
        "folder_count": 5,
        "document_count": 20,
        "sub_departments": [{...}],
        "users": {
            "items": [...],
            "pagination": {...}
        },
        "folders": {
            "items": [...],
            "pagination": {...}
        },
        "documents": {
            "items": [...],
            "pagination": {...}
        }
    }
    """
    # Basic department info
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    parent_id = serializers.UUIDField(allow_null=True)
    parent = serializers.SerializerMethodField()
    manager_id = serializers.UUIDField(allow_null=True)
    manager = serializers.SerializerMethodField()
    
    # Counts
    member_count = serializers.IntegerField()
    folder_count = serializers.IntegerField()
    document_count = serializers.IntegerField()
    sub_department_count = serializers.IntegerField()
    
    # Tree structure
    sub_departments = serializers.ListField(allow_empty=True)
    
    # Expanded fields (optional)
    users = serializers.SerializerMethodField()
    folders = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    
    def get_parent(self, obj):
        """Return parent department info"""
        if not obj.get('parent'):
            return None
        parent = obj['parent']
        return {
            'id': str(parent.id),
            'name': parent.name,
        }
    
    def get_manager(self, obj):
        """Return manager object with basic info"""
        if not obj.get('manager'):
            return None
        manager = obj['manager']
        return {
            'id': str(manager.id),
            'username': manager.username,
            'email': manager.email,
            'full_name': manager.get_full_name() if hasattr(manager, 'get_full_name') else ''
        }
    
    def get_users(self, obj):
        """Return expanded users with pagination"""
        if 'users' not in obj:
            return None
        return obj['users']
    
    def get_folders(self, obj):
        """Return expanded folders with pagination"""
        if 'folders' not in obj:
            return None
        return obj['folders']
    
    def get_documents(self, obj):
        """Return expanded documents with pagination"""
        if 'documents' not in obj:
            return None
        return obj['documents']
