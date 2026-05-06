"""
Document Serializers - Serialization for Folder, Document, Chunk, Tag models.
"""
import logging
from rest_framework import serializers
from apps.documents.models import Document, Folder, DocumentChunk, DocumentEmbedding, Tag
from .base import SoftDeleteModelSerializer

logger = logging.getLogger(__name__)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at']


class FolderSerializer(SoftDeleteModelSerializer):
    """Serializer for Folder model"""
    uploader_name = serializers.SerializerMethodField()
    child_count = serializers.IntegerField(source='subfolders.count', read_only=True)
    document_count = serializers.IntegerField(source='documents.count', read_only=True)
    my_permission = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'created_by', 'uploader_name',
            'department', 'access_scope', 'description',
            'child_count', 'document_count', 'my_permission', 'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_uploader_name(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        # Only admin can see owner full name for management use-cases.
        is_admin = request.user.is_superuser
        if hasattr(request.user, 'has_role'):
            try:
                from core.constants import RoleIds
                is_admin = is_admin or request.user.has_role(RoleIds.ADMIN)
            except Exception:
                pass

        if not is_admin:
            return None

        creator = getattr(obj, 'created_by', None)
        if not creator:
            return None

        profile = getattr(creator, 'user_profile', None)
        if profile and getattr(profile, 'full_name', None):
            return profile.full_name

        full_name = creator.get_full_name() if hasattr(creator, 'get_full_name') else ''
        return full_name or creator.username

    def get_my_permission(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'none'
        
        from core.permissions.permission_manager import get_permission_manager
        # For folders, we reuse the inheritance logic
        pm = get_permission_manager()
        # Helper to convert scope to level.
        # Keep the response in the frontend-supported permission scale.
        if pm.check_folder_access(request.user.id, obj.id, 'delete'):
            return 'delete'
        if pm.check_folder_access(request.user.id, obj.id, 'write'):
            return 'write'
        if pm.check_folder_access(request.user.id, obj.id, 'read'):
            return 'read'
        return 'none'


class DocumentSerializer(SoftDeleteModelSerializer):
    """Serializer for Document model - dùng cho list/detail response"""
    uploader_name = serializers.SerializerMethodField()
    folder_name = serializers.CharField(source='folder.name', read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    tags_list = TagSerializer(source='tags', many=True, read_only=True)
    chunk_count = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'original_name', 'file_type', 'file_size',
            'uploader', 'uploader_name',
            'department', 'department_name',
            'folder', 'folder_name',
            'status', 'access_scope',
            'tags_list', 'chunk_count', 'my_permission', 'metadata',
            'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'status', 'created_at', 'updated_at'
        ]

    def get_chunk_count(self, obj):
        return obj.chunks.filter(is_deleted=False).count()

    def get_uploader_name(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        # Only admin can see owner full name for personal docs management.
        is_admin = request.user.is_superuser
        if hasattr(request.user, 'has_role'):
            try:
                from core.constants import RoleIds
                is_admin = is_admin or request.user.has_role(RoleIds.ADMIN)
            except Exception:
                pass

        if not is_admin:
            return None

        uploader = getattr(obj, 'uploader', None)
        if not uploader:
            return None

        profile = getattr(uploader, 'user_profile', None)
        if profile and getattr(profile, 'full_name', None):
            return profile.full_name

        full_name = uploader.get_full_name() if hasattr(uploader, 'get_full_name') else ''
        return full_name or uploader.username

    def get_my_permission(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'none'
        
        try:
            from core.permissions.permission_manager import get_permission_manager
            level = get_permission_manager().get_effective_level(request.user.id, obj.id, is_folder=False)
            return level or 'none'
        except Exception as e:
            logger.warning(f"Error calculating my_permission for doc {obj.id}: {e}")
            return 'none'


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentChunk model (read-only)"""

    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document', 'content', 'chunk_index',
            'node_type', 'vector_id', 'token_count', 'page_number',
            'created_at'
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer dành riêng cho upload tài liệu nội bộ.

    Scoping logic (xử lý ở service):
      - folder_id có dept    → scope = folder.access_scope, dept = folder.dept    (Case A)
      - folder_id không dept → scope = 'company', dept = None                    (Case B)
      - department_id, no folder → scope = 'department', dept = department_id    (Case C)
      - không có gì           → scope = 'company', dept = None                   (Case D)
    """
    file = serializers.FileField(required=True)
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    access_scope = serializers.ChoiceField(
        choices=['personal', 'department', 'company'],
        required=False,
        allow_null=True,
        default=None,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=2000,
    )
    tags = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Tags phân cách bằng dấu phẩy. VD: 'hợp đồng,tài chính,2024'"
    )

    def validate_tags(self, value):
        """Chuyển chuỗi 'a,b,c' thành list ['a', 'b', 'c']"""
        if not value:
            return []
        return [t.strip() for t in value.split(',') if t.strip()]


class DocumentPermissionListItemSerializer(serializers.Serializer):
    """Read-only serializer for a single document permission row in list views."""

    id = serializers.UUIDField()
    subject_type = serializers.CharField()
    subject_id = serializers.CharField()
    subject_name = serializers.CharField(allow_null=True, required=False)
    permission = serializers.CharField()
    permission_precedence = serializers.CharField(required=False)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField(allow_null=True, required=False)


class DocumentPermissionListSerializer(serializers.Serializer):
    """Serializer for document permission overview rows."""

    document_id = serializers.UUIDField()
    document_name = serializers.CharField()
    access_scope = serializers.CharField()
    permissions = DocumentPermissionListItemSerializer(many=True, read_only=True)
    total_permissions = serializers.IntegerField()


class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật metadata document (không có file)"""
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        write_only=True
    )
    access_scope = serializers.ChoiceField(
        choices=['personal', 'department', 'company'],
        required=False,
        default='company'
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000
    )

    class Meta:
        model = Document
        fields = ['original_name', 'folder', 'department', 'access_scope', 'description', 'tags']
