"""
User Profile Views - Self-Service API endpoints for users to manage their profile.

✅ CORRECT FLOW:
Request → View → Serializer (validate) → Service (business logic) 
→ Repository (DB queries) → Model/ORM → Database → Response

Endpoints:
- GET    /api/v1/users/me              (Get own profile)
- PATCH  /api/users/me                 (Update own profile)
- POST   /api/v1/users/me/avatar       (Upload avatar)

Permissions:
- Authenticated users can only access/modify their own profile
- Admin can also access user profiles via different endpoints
"""

import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.apps import apps

from api.serializers.base import ResponseBuilder
from api.serializers.user_profile_serializers import (
    UserProfileReadSerializer,
    UserProfileWriteSerializer,
    UserProfileAvatarSerializer,
)
from services.user_service import UserService
from core.exceptions import ValidationError, BusinessLogicError

import uuid
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# PERMISSION CLASSES
# ============================================================

class IsOwner(permissions.BasePermission):
    """Permission: User can only access their own profile"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if object belongs to current user"""
        return obj.account_id == request.user.id


# ============================================================
# VIEWS
# ============================================================

class UserProfileSelfView(APIView):
    """
    User Self-Service Profile API
    
    GET  /api/v1/users/me   - View own profile (full_name, avatar_url, address, birthday, department_name)
    PATCH /api/users/me     - Update own profile (full_name, address, birthday, metadata)
    
    Accessible by: Any authenticated user (own profile only)
    
    ✅ CORRECT FLOW:
    View → Service (business logic) → Repository (DB queries) → Model/ORM → DB
    """
    permission_classes = [permissions.IsAuthenticated]
    user_service = UserService()
    
    def get(self, request):
        """
        GET /api/v1/users/me
        
        Return:
        - User profile with: id, account_id, username, email, full_name,
                            avatar_url, address, birthday, department_name, metadata, timestamps
        """
        try:
            # SERVICE LAYER: Fetch profile through service using Account ID
            # request.user.id is Account ID, get_user_profile_by_account_id() will fetch UserProfile
            profile = self.user_service.get_user_profile_by_account_id(request.user.id)
            
            if not profile:
                return Response(
                    ResponseBuilder.error(message="User profile not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ✅ FIXED: Add audit log for GET operation
            try:
                from apps.operations.models import AuditLog
                action_desc = f"User {request.user.username} viewed own profile"
                AuditLog.log_action(
                    account=request.user,
                    action='VIEW_OWN_PROFILE',
                    resource_id=str(profile.id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.warning(f"Failed to log view_own_profile action: {str(e)}")
            
            serializer = UserProfileReadSerializer(profile)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Profile retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving profile for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def patch(self, request):
        """
        PATCH /api/users/me
        
        Update user's own profile information.
        
        ✅ CORRECT FLOW:
        View (orchestration) → Serializer (validate) → Service (business logic) 
        → Repository (DB queries) → Model/ORM → Database
        
        Allowed fields:
        - full_name: string (user's full name)
        - address: string (user's address)
        - birthday: date (YYYY-MM-DD format)
        - metadata: object (additional info: phone, social_id, etc.)
        
        ⚠️ NOT allowed:
        - account: cannot change authentication link
        - department: use separate API PATCH /api/v1/users/{id}/department
        - avatar_url: use separate API POST /api/v1/users/me/avatar
        
        Audit: Logs action as UPDATE_OWN_PROFILE
        """
        try:
            # SERIALIZER LAYER: Validate request data
            serializer = UserProfileWriteSerializer(data=request.data, partial=True)
            
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        message="Validation failed",
                        errors=serializer.errors
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            # SERVICE LAYER: Update profile through service
            # request.user.id is Account ID, update_user_profile_by_account_id() will fetch and update UserProfile
            updated_profile = self.user_service.update_user_profile_by_account_id(
                request.user.id,
                validated_data
            )
            
            # Audit log
            try:
                from apps.operations.models import AuditLog
                changed_fields = list(request.data.keys())
                AuditLog.log_action(
                    account=request.user,
                    action='UPDATE_OWN_PROFILE',
                    resource_id=str(updated_profile.id),
                    query_text=f"User updated own profile. Fields: {', '.join(changed_fields)}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log profile update: {str(e)}")
            
            # Return updated profile
            response_serializer = UserProfileReadSerializer(updated_profile)
            return Response(
                ResponseBuilder.updated(
                    data=response_serializer.data,
                    message="Profile updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating profile for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileAvatarView(APIView):
    """
    User Avatar Upload API
    
    POST /api/v1/users/me/avatar - Upload and update user's avatar
    
    Request:
    - multipart/form-data
    - avatar: binary image file (JPG, PNG, WebP. Max 5MB)
    
    Response:
    - avatar_url: string (URL to uploaded image on S3/CDN)
    
    Accessible by: Any authenticated user (own avatar only)
    
    ✅ CORRECT FLOW:
    Request → View (orchestration) → Serializer (validate file)
    → Service (upload + business logic) → Repository (update DB) → Model/ORM → Database → Response
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()
    
    @transaction.atomic
    def post(self, request):
        """
        POST /api/v1/users/me/avatar
        
        Upload and update user's avatar image.
        
        ✅ CORRECT FLOW:
        View (orchestration) → Serializer (validate file) 
        → Service (upload + business logic via Repository) 
        → Repository (DB queries) → Model/ORM → Database
        
        Audit: Logs action as UPLOAD_AVATAR
        """
        try:
            # SERIALIZER LAYER: Validate image file
            serializer = UserProfileAvatarSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        message="Validation failed",
                        errors=serializer.errors
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get validated file
            avatar_file = serializer.validated_data['avatar']
            
            # SERVICE LAYER: Upload avatar (Service handles file upload + DB update via Repository)
            # request.user.id is Account ID, upload_avatar_by_account_id() will fetch and update UserProfile
            avatar_url = self.user_service.upload_avatar_by_account_id(request.user.id, avatar_file)
            
            # Audit log
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='UPLOAD_AVATAR',
                    resource_id=str(request.user.id),
                    query_text=f"User uploaded new avatar: {avatar_url}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log avatar upload: {str(e)}")
            
            # Return result
            return Response(
                ResponseBuilder.success(
                    data={
                        'avatar_url': avatar_url,
                        'message': 'Avatar uploaded successfully'
                    },
                    message="Avatar updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading avatar for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
