"""
Folder Serializers - Validation và transformation cho Folder endpoints

Patterns:
1. FolderTreeSerializer - Read-only, nested tree structure (GET /folders)
2. FolderDetailSerializer - Single folder with full info (GET /folders/{id})
3. FolderCreateSerializer - Write-only, validation for create (POST /folders)
4. FolderUpdateSerializer - Write-only, validation for update (PUT /folders/{id})
5. FolderPermissionSerializer - For ACL endpoints (future)
"""

from rest_framework import serializers
from apps.documents.models import Folder


class FolderTreeSerializer(serializers.ModelSerializer):
    """
    Serializer for folder tree structure (nested recursive).
    
    Used in:
    - GET /api/v1/folders - Tree view
    
    Includes:
    - Folder info
    - Nested sub_folders recursively
    - Created by info
    """
    
    created_by_username = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    sub_folders = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'description',
            'access_scope',
            'parent_id',
            'department_id',
            'department_name',
            'created_by_id',
            'created_by_username',
            'created_at',
            'updated_at',
            'sub_folders',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_created_by_username(self, obj):
        """Get creator's username"""
        if obj.created_by:
            return obj.created_by.username
        return None
    
    def get_department_name(self, obj):
        """Get department name if associated"""
        if obj.department:
            return obj.department.name
        return None
    
    def get_sub_folders(self, obj):
        """Recursively serialize sub-folders"""
        sub_folders = obj.subfolders.filter(is_deleted=False)
        return FolderTreeSerializer(sub_folders, many=True).data


class FolderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for single folder detail.
    
    Used in:
    - GET /api/v1/folders/{id} - Detail view
    
    Includes:
    - Full folder info
    - Parent details
    - Department details
    - Creator details
    - Counts (documents, subfolders)
    - Nested sub_folders tree
    """
    
    parent = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    sub_folders = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'description',
            'access_scope',
            'parent_id',
            'parent',
            'department_id',
            'department',
            'created_by_id',
            'created_by',
            'subfolder_count',
            'document_count',
            'sub_folders',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_parent(self, obj):
        """Return parent folder info"""
        if not obj.parent:
            return None
        return {
            'id': str(obj.parent.id),
            'name': obj.parent.name,
        }
    
    def get_department(self, obj):
        """Return department info"""
        if not obj.department:
            return None
        return {
            'id': str(obj.department.id),
            'name': obj.department.name,
        }
    
    def get_created_by(self, obj):
        """Return creator info"""
        if not obj.created_by:
            return None
        return {
            'id': str(obj.created_by.id),
            'username': obj.created_by.username,
            'email': obj.created_by.email,
        }
    
    def get_subfolder_count(self, obj):
        """Count direct sub-folders"""
        return obj.subfolders.filter(is_deleted=False).count()
    
    def get_document_count(self, obj):
        """Count documents directly in this folder"""
        from apps.documents.models import Document
        return Document.objects.filter(
            folder_id=obj.id,
            is_deleted=False
        ).count()
    
    def get_sub_folders(self, obj):
        """Recursively serialize sub-folders"""
        sub_folders = obj.subfolders.filter(is_deleted=False)
        return FolderTreeSerializer(sub_folders, many=True).data


class FolderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating folder.
    
    Used in:
    - POST /api/v1/folders - Create
    
    Validates:
    - name: Required, max 100 chars
    - parent_id: Optional UUID
    - description: Optional string
    - access_scope: Optional, default='company'
    - department_id: Optional UUID
    """
    
    name = serializers.CharField(
        max_length=100,
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        help_text="Folder name"
    )
    
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Folder description"
    )
    
    parent_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Parent folder ID (optional, for subfolder)"
    )
    
    access_scope = serializers.ChoiceField(
        choices=['personal', 'department', 'company'],
        default='company',
        required=False,
        help_text="Access scope: personal, department, or company"
    )
    
    department_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Department association (optional)"
    )
    
    def validate_name(self, value):
        """Validate folder name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Folder name cannot be empty")
        
        if len(value.strip()) > 100:
            raise serializers.ValidationError("Folder name max 100 characters")
        
        return value.strip()
    
    def validate_access_scope(self, value):
        """Validate access_scope"""
        valid_scopes = ['personal', 'department', 'company']
        if value not in valid_scopes:
            raise serializers.ValidationError(
                f"Invalid access_scope. Must be one of: {', '.join(valid_scopes)}"
            )
        return value


class FolderUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating folder.
    
    Used in:
    - PUT /api/v1/folders/{id} - Update
    
    Validates:
    - name: Optional, max 100 chars
    - description: Optional string
    - access_scope: Optional scope
    - department_id: Optional UUID
    """
    
    name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=False,
        trim_whitespace=True,
        help_text="Folder name"
    )
    
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Folder description"
    )
    
    access_scope = serializers.ChoiceField(
        choices=['personal', 'department', 'company'],
        required=False,
        help_text="Access scope"
    )
    
    department_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Department association"
    )
    
    def validate_name(self, value):
        """Validate folder name if provided"""
        if value is not None:
            if not value.strip():
                raise serializers.ValidationError("Folder name cannot be empty")
            if len(value.strip()) > 100:
                raise serializers.ValidationError("Folder name max 100 characters")
            return value.strip()
        return value


class FolderMoveSerializer(serializers.Serializer):
    """
    Serializer for moving folder.
    
    Used in:
    - PATCH /api/v1/folders/{id}/move - Move to different parent
    
    Validates:
    - new_parent_id: Optional UUID (None = make root)
    """
    
    new_parent_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="New parent folder ID (null = make root)"
    )


class FolderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for folder lists.
    
    Used in:
    - List operations where full detail not needed
    """
    
    created_by_username = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'access_scope',
            'parent_id',
            'department_id',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None


class FolderPermissionSerializer(serializers.Serializer):
    """
    Serializer for managing folder permissions (ACL).
    
    Used in:
    - POST /api/v1/folders/{id}/permissions - Grant access
    - DELETE /api/v1/folders/{id}/permissions/{perm_id} - Revoke access
    - GET /api/v1/folders/{id}/permissions - List permissions
    
    For POST (create):
    {
        "subject_type": "account" | "role",
        "subject_id": "uuid",
        "permission": "read" | "write" | "delete"
    }
    """
    
    id = serializers.UUIDField(read_only=True)
    folder_id = serializers.UUIDField(read_only=True)
    subject_type = serializers.ChoiceField(
        choices=['account', 'role'],
        required=True,
        help_text="Type of subject (account or role)"
    )
    subject_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Account UUID or Role UUID"
    )
    permission = serializers.ChoiceField(
        choices=['read', 'write', 'delete'],
        required=True,
        help_text="Permission level"
    )
    is_active = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Is this permission active?"
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # For response - reference info
    subject_name = serializers.SerializerMethodField()
    
    def validate(self, data):
        """Validate permission creation data"""
        if data.get('subject_type') == 'account':
            # Validate account exists
            try:
                from apps.users.models import Account
                Account.objects.get(id=data.get('subject_id'))
            except Account.DoesNotExist:
                raise serializers.ValidationError(
                    f"Account {data.get('subject_id')} not found"
                )
        elif data.get('subject_type') == 'role':
            # Validate role exists
            try:
                from apps.users.models import Role
                Role.objects.get(id=data.get('subject_id'))
            except Role.DoesNotExist:
                raise serializers.ValidationError(
                    f"Role {data.get('subject_id')} not found"
                )
        
        return data
    
    def get_subject_name(self, obj):
        """Get subject name (account username or role name)"""
        if hasattr(obj, 'subject_type'):
            if obj.subject_type == 'account':
                try:
                    from apps.users.models import Account
                    account = Account.objects.get(id=obj.subject_id)
                    return account.username
                except:
                    return None
            elif obj.subject_type == 'role':
                try:
                    from apps.users.models import Role
                    role = Role.objects.get(id=obj.subject_id)
                    return role.name
                except:
                    return None
        return None


class FolderPermissionListSerializer(serializers.Serializer):
    """
    Serializer for listing all permissions for a folder.
    
    Response structure:
    {
        "folder_id": "uuid",
        "folder_name": "string",
        "access_scope": "company|department|personal",
        "permissions": [
            {
                "id": "perm-uuid",
                "subject_type": "account|role",
                "subject_id": "uuid",
                "subject_name": "username or role name",
                "permission": "read|write|delete",
                "is_active": true,
                "created_at": "2026-04-14T..."
            }
        ]
    }
    """
    
    folder_id = serializers.UUIDField()
    folder_name = serializers.CharField()
    access_scope = serializers.CharField()
    permissions = FolderPermissionSerializer(many=True, read_only=True)
