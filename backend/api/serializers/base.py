"""
Base Serializers - Định dạng response chuẩn cho toàn bộ API.
Tất cả API endpoint đều return response qua StandardResponseSerializer.
"""
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from typing import Any, Optional, Dict, List


class StandardResponseSerializer(serializers.Serializer):
    """
    Định dạng response chuẩn cho tất cả API endpoint.
    
    Format:
    {
        "success": true,
        "status_code": 200,
        "message": "Operation successful",
        "data": {...},
        "timestamp": "2024-01-15T10:30:45Z",
        "request_id": "abc-123-def-456"
    }
    """
    
    success = serializers.BooleanField(help_text="Whether request succeeded")
    status_code = serializers.IntegerField(help_text="HTTP status code")
    message = serializers.CharField(help_text="Response message", required=False)
    data = serializers.JSONField(help_text="Response data", required=False, allow_null=True)
    timestamp = serializers.DateTimeField(help_text="Response timestamp", required=False)
    request_id = serializers.CharField(help_text="Unique request ID", required=False, allow_blank=True)
    
    class Meta:
        fields = ['success', 'status_code', 'message', 'data', 'timestamp', 'request_id']


class PaginatedResponseSerializer(serializers.Serializer):
    """
    Response cho paginated list (có pagination meta).
    
    Format:
    {
        "success": true,
        "status_code": 200,
        "message": "List records",
        "data": {
            "items": [...],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total_items": 100,
                "total_pages": 10,
                "has_next": true,
                "has_previous": false
            }
        },
        "timestamp": "2024-01-15T10:30:45Z",
        "request_id": "abc-123-def-456"
    }
    """
    
    class PaginationSerializer(serializers.Serializer):
        page = serializers.IntegerField()
        page_size = serializers.IntegerField()
        total_items = serializers.IntegerField()
        total_pages = serializers.IntegerField()
        has_next = serializers.BooleanField()
        has_previous = serializers.BooleanField()
    
    class DataSerializer(serializers.Serializer):
        items = serializers.ListField()
        pagination = PaginationSerializer()
    
    success = serializers.BooleanField()
    status_code = serializers.IntegerField()
    message = serializers.CharField()
    data = DataSerializer()
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    """
    Error response (exception caught by GlobalExceptionHandler).
    
    Format:
    {
        "success": false,
        "status_code": 400,
        "message": "Validation error",
        "data": {
            "field_name": ["Error message 1", "Error message 2"],
            "other_field": ["Error message"]
        },
        "timestamp": "2024-01-15T10:30:45Z",
        "request_id": "abc-123-def-456"
    }
    """
    
    success = serializers.BooleanField()
    status_code = serializers.IntegerField()
    message = serializers.CharField()
    data = serializers.JSONField(required=False, allow_null=True)
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField()


# ============================================================
# RESPONSE BUILDER UTILITIES
# ============================================================
class ResponseBuilder:
    """Helper class để build response theo chuẩn"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        request_id: str = None
    ) -> Dict:
        """Build success response"""
        return {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id or "",
        }
    
    @staticmethod
    def error(
        message: str = "Error",
        status_code: int = 400,
        data: Dict = None,
        request_id: str = None
    ) -> Dict:
        """Build error response"""
        return {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data or {},
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id or "",
        }
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "Created successfully",
        request_id: str = None
    ) -> Dict:
        """Build created (201) response"""
        return ResponseBuilder.success(
            data=data,
            message=message,
            status_code=201,
            request_id=request_id
        )
    
    @staticmethod
    def updated(
        data: Any = None,
        message: str = "Updated successfully",
        request_id: str = None
    ) -> Dict:
        """Build updated response"""
        return ResponseBuilder.success(
            data=data,
            message=message,
            status_code=200,
            request_id=request_id
        )
    
    @staticmethod
    def deleted(
        message: str = "Deleted successfully",
        request_id: str = None
    ) -> Dict:
        """Build deleted response"""
        return ResponseBuilder.success(
            data=None,
            message=message,
            status_code=204,
            request_id=request_id
        )
    
    @staticmethod
    def paginated(
        items: List,
        page: int,
        page_size: int,
        total_items: int,
        message: str = "List records",
        request_id: str = None
    ) -> Dict:
        """Build paginated list response"""
        total_pages = (total_items + page_size - 1) // page_size  # Ceiling division
        
        return {
            "success": True,
            "status_code": 200,
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                }
            },
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id or "",
        }


# ============================================================
# VALIDATION SERIALIZERS
# ============================================================
class TimestampedModelSerializer(serializers.ModelSerializer):
    """
    Base model serializer cho các model có timestamps.
    Tự động include created_at, updated_at fields.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        fields = ['id', 'created_at', 'updated_at']


class SoftDeleteModelSerializer(TimestampedModelSerializer):
    """
    Base model serializer cho các model dùng soft delete.
    Include is_deleted, deleted_at fields.
    """
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True, allow_null=True)
    
    class Meta:
        fields = ['id', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']


# ============================================================
# COMMON VALIDATION SERIALIZERS
# ============================================================
class ListQueryParamsSerializer(serializers.Serializer):
    """Validation cho query params của list endpoint"""
    page = serializers.IntegerField(
        required=False, 
        min_value=1, 
        default=1,
        help_text="Page number (1-indexed)"
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=10,
        help_text="Items per page (1-100)"
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Search keyword"
    )
    ordering = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Order by field (prefix with - for descending)"
    )


class LoginSerializer(serializers.Serializer):
    """Login request validation"""
    username = serializers.CharField(
        max_length=150,
        help_text="Username or email"
    )
    password = serializers.CharField(
        write_only=True,
        help_text="Account password"
    )


class RefreshTokenSerializer(serializers.Serializer):
    """Refresh token request validation"""
    refresh = serializers.CharField(
        help_text="Refresh token"
    )


class ChangePasswordSerializer(serializers.Serializer):
    """Change password request validation"""
    old_password = serializers.CharField(
        write_only=True,
        help_text="Current password"
    )
    new_password = serializers.CharField(
        write_only=True,
        help_text="New password (min 8 chars)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirm new password"
    )
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        if len(data['new_password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters")
        return data


class FileUploadSerializer(serializers.Serializer):
    """File upload validation"""
    file = serializers.FileField(
        help_text="File to upload (max 50MB)"
    )
    folder_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Target folder ID"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="File description"
    )
