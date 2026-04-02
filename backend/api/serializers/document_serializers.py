"""
Document Serializers - Serialization for Folder, Document, Chunk, Tag models.
"""
from rest_framework import serializers
from apps.documents.models import Document, Folder, DocumentChunk, DocumentEmbedding, Tag
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'count', 'created_at']


class FolderSerializer(SoftDeleteModelSerializer):
    """Serializer for Folder model"""
    uploader_name = serializers.CharField(source='uploader.username', read_only=True)
    child_count = serializers.IntegerField(source='children.count', read_only=True)
    document_count = serializers.IntegerField(source='documents.count', read_only=True)
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'parent', 'uploader', 'uploader_name', 
            'department', 'access_scope', 'description', 
            'child_count', 'document_count', 'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(SoftDeleteModelSerializer):
    """Serializer for Document model"""
    uploader_name = serializers.CharField(source='uploader.username', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    tags_list = TagSerializer(source='tags', many=True, read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'original_name', 'file', 'file_type', 'file_size', 
            'uploader', 'uploader_name', 'department', 'folder', 'folder_name',
            'status', 'processing_status', 'chunks_count', 'embeddings_count', 
            'description', 'tags_list', 'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'status', 'processing_status', 
            'chunks_count', 'embeddings_count', 'created_at', 'updated_at'
        ]


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentChunk model (read-only)"""
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document', 'content', 'sequence', 
            'start_char', 'end_char', 'created_at'
        ]


class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating document (upload context)"""
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), 
        required=False, 
        write_only=True
    )
    
    class Meta:
        model = Document
        fields = ['original_name', 'file', 'folder', 'department', 'description', 'tags']
