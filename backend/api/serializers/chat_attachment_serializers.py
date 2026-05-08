"""
Chat Attachment Serializers
============================
Serializers for available attachments response
"""

from rest_framework import serializers
from django.apps import apps


class AccessibleDocumentSerializer(serializers.Serializer):
    """Serializer for documents accessible for chat attachment"""
    id = serializers.UUIDField()
    original_name = serializers.CharField()
    file_type = serializers.CharField()
    file_size = serializers.IntegerField()
    status = serializers.CharField()
    access_scope = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AccessibleFolderSerializer(serializers.Serializer):
    """Serializer for folders accessible for chat attachment"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    access_scope = serializers.CharField()
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AvailableAttachmentsSerializer(serializers.Serializer):
    """Serializer for available attachments response"""
    documents = AccessibleDocumentSerializer(many=True)
    folders = AccessibleFolderSerializer(many=True)
    
    pagination = serializers.SerializerMethodField()
    
    def get_pagination(self, obj):
        """Get pagination info"""
        return {
            'total_documents': len(obj.get('documents', [])),
            'total_folders': len(obj.get('folders', [])),
        }
