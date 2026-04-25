"""
Document Serializers - Serialization for Folder, Document, Chunk, Tag models.
"""
from rest_framework import serializers
from apps.documents.models import Document, Folder, DocumentChunk, DocumentEmbedding, Tag
from .base import SoftDeleteModelSerializer


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at']


class FolderSerializer(SoftDeleteModelSerializer):
    """Serializer for Folder model"""
    uploader_name = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    child_count = serializers.IntegerField(source='subfolders.count', read_only=True)
    document_count = serializers.IntegerField(source='documents.count', read_only=True)

    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'created_by', 'uploader_name',
            'department', 'access_scope', 'description',
            'child_count', 'document_count', 'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(SoftDeleteModelSerializer):
    """Serializer for Document model - dùng cho list/detail response"""
    uploader_name = serializers.CharField(source='uploader.username', read_only=True, allow_null=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    tags_list = TagSerializer(source='tags', many=True, read_only=True)
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'original_name', 'file_type', 'file_size',
            'uploader', 'uploader_name',
            'department', 'department_name',
            'folder', 'folder_name',
            'status', 'access_scope',
            'tags_list', 'chunk_count', 'metadata',
            'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'status', 'created_at', 'updated_at'
        ]

    def get_chunk_count(self, obj):
        return obj.chunks.filter(is_deleted=False).count()


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
