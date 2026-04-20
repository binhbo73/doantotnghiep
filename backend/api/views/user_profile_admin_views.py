"""
Admin User Profile Views - Admin endpoints for user personnel management.

✅ CORRECT FLOW:
Request → View (orchestration) → Serializer (validate) 
→ Service (business logic) → Repository (DB queries) → ORM → Database

Endpoints (Admin Only):
- GET    /api/v1/users/              List all users (search, filter, pagination)
- GET    /api/v1/users/{user_id}/    Get user profile details
- PATCH  /api/v1/users/{user_id}/    Update user profile info

Permissions:
- Admin/Manager only
"""

import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.db import transaction

from api.serializers.base import ResponseBuilder
from api.serializers.user_profile_serializers import (
    UserProfileReadSerializer,
    UserProfileWriteSerializer,
    EnhancedUserProfileReadSerializer,
)
from services.user_service import UserService
from core.constants import RoleIds
from core.exceptions import ValidationError, BusinessLogicError

logger = logging.getLogger(__name__)


# ============================================================
# CUSTOM PAGINATION
# ============================================================

class UserProfilePagination(PageNumberPagination):
    """Pagination for user list"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================
# PERMISSION CLASSES
# ============================================================

class IsAdmin(permissions.BasePermission):
    """Check if user has admin role"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has ADMIN (id=1) or MANAGER (id=2) role
        return request.user.account_roles.filter(
            role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
            is_deleted=False
        ).exists()


# ============================================================
# VIEWS
# ============================================================

class UserProfileAdminListView(APIView):
    """
    Admin API: List all user profiles
    
    GET /api/v1/users/
    
    Query Parameters:
    - search: Search by username, email, full_name (case-insensitive)
    - department_id: Filter by department UUID
    - status: Filter by account status (active, blocked, inactive)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    
    Response:
    - items: List of user profiles
    - page: Current page number
    - page_size: Items per page
    - total_items: Total user count
    
    Accessible by: Admin/Manager only
    Audit: Logs action as LIST_USERS
    
    ✅ CORRECT FLOW:
    View → Service (fetch with filters) → Repository (DB queries) → ORM → DB
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = UserProfilePagination
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()
    
    def get(self, request):
        """List all user profiles with search and filters"""
        try:
            # Extract query parameters
            search_query = request.query_params.get('search', '').strip()
            department_id = request.query_params.get('department_id', '').strip()
            status_filter = request.query_params.get('status', '').strip()
            
            # SERVICE LAYER: Get users with filters
            users_list = self.user_service.list_users(
                search=search_query,
                department_id=department_id,
                status=status_filter
            )
            
            # Pagination
            paginator = self.pagination_class()
            paginated_users = paginator.paginate_queryset(users_list, request)
            
            # ✅ SERIALIZER LAYER: Use EnhancedUserProfileReadSerializer for detailed user info
            # This returns profile + account data (roles, permissions, status) for each user
            serializer = EnhancedUserProfileReadSerializer(paginated_users, many=True)
            
            # Audit log
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='LIST_USERS',
                    resource_id='N/A',
                    query_text=f"Listed users. Filters: search={search_query}, dept={department_id}, status={status_filter}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log user list: {str(e)}")
            
            # Response
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=paginator.page.number,
                    page_size=paginator.page_size,
                    total_items=paginator.page.paginator.count,
                    message="User list retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error listing users: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileAdminDetailView(APIView):
    """
    Admin API: Get and update user profile
    
    GET /api/v1/users/{user_id}/ - Get user profile details
    PATCH /api/v1/users/{user_id}/ - Update user profile
    
    URL Parameter:
    - user_id: Account ID (UUID format)
    
    GET Response:
    - User profile with all fields: id, account_id, username, email, full_name,
      avatar_url, address, birthday, department_name, metadata, created_at, updated_at
    
    PATCH Request Body:
    {
      "full_name": "New Name",
      "address": "New Address",
      "birthday": "1990-01-01",
      "metadata": {"phone": "0123456789"}
    }
    
    Accessible by: Admin/Manager only
    Audit: Logs action as GET_USER_DETAIL and UPDATE_USER_PROFILE
    
    ✅ CORRECT FLOW:
    View (get user_id) → Service (fetch/update profile) 
    → Repository (DB query/update) → ORM → DB
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()
    
    def get(self, request, user_id):
        """Get single user profile details with account info (roles, permissions, status)"""
        try:
            # SERVICE LAYER: Fetch specific user profile
            profile = self.user_service.get_user_profile(user_id)
            
            if not profile:
                return Response(
                    ResponseBuilder.error(message=f"User profile not found for ID: {user_id}"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ✅ SERIALIZER LAYER: Use EnhancedUserProfileReadSerializer to include account data
            # This returns BOTH profile info + account info (roles, permissions, status)
            serializer = EnhancedUserProfileReadSerializer(profile)
            
            # Audit log
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='GET_USER_DETAIL',
                    resource_id=str(profile.id),
                    query_text=f"Viewed user profile: {profile.account.username}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log user detail view: {str(e)}")
            
            # Response
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="User profile retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error getting user {user_id}: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def patch(self, request, user_id):
        """Update user profile"""
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
            updated_profile = self.user_service.update_user_profile(
                user_id,
                validated_data
            )
            
            # Audit log
            try:
                from apps.operations.models import AuditLog
                changed_fields = list(request.data.keys())
                AuditLog.log_action(
                    account=request.user,
                    action='UPDATE_USER_PROFILE',
                    resource_id=str(updated_profile.id),
                    query_text=f"Admin updated user profile {user_id}. Fields: {', '.join(changed_fields)}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log user profile update: {str(e)}")
            
            # Return updated profile
            response_serializer = UserProfileReadSerializer(updated_profile)
            return Response(
                ResponseBuilder.updated(
                    data=response_serializer.data,
                    message="User profile updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error updating user {user_id}: {str(e)}")
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
