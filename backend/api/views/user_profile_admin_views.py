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
    AdminUserProfileUpdateSerializer,
    EnhancedUserProfileReadSerializer,
)
from services.user_service import UserService
from core.constants import PermissionCodes
from core.permissions.drf_permissions import user_has_any_permission
from core.exceptions import ValidationError, BusinessLogicError

logger = logging.getLogger(__name__)


def _get_request_user_department_id(user):
    profile = getattr(user, 'user_profile', None)
    department_id = getattr(profile, 'department_id', None)
    return str(department_id) if department_id else None


def _has_global_user_scope(user) -> bool:
    """Permission-based scope bypass for users who can manage organization-wide users."""
    return user_has_any_permission(user, [
        PermissionCodes.SYSTEM_ADMIN,
        PermissionCodes.DEPARTMENT_MANAGE,
    ])


def _profile_in_request_scope(request, profile) -> bool:
    if _has_global_user_scope(request.user):
        return True

    target_department_id = getattr(profile, 'department_id', None)
    if not target_department_id:
        return False

    scoped_department_ids = UserService().get_user_management_scope_department_ids(request.user)
    return str(target_department_id) in scoped_department_ids


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
        
        required_permissions = getattr(view, 'required_permissions', [PermissionCodes.USER_READ])
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        return user_has_any_permission(request.user, required_permissions)


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
    
    ✅ CORRECT FLOW:
    View → Service (fetch with filters) → Repository (DB queries) → ORM → DB
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    required_permissions = [PermissionCodes.USER_READ]
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
            enforce_department_scope = not _has_global_user_scope(request.user)
            scoped_department_ids = self.user_service.get_user_management_scope_department_ids(request.user)
            
            # SERVICE LAYER: Get users with filters
            users_list = self.user_service.list_users(
                search=search_query,
                department_id=department_id,
                status=status_filter,
                scope_department_ids=scoped_department_ids,
                enforce_department_scope=enforce_department_scope,
            )
            
            # Pagination
            paginator = self.pagination_class()
            paginated_users = paginator.paginate_queryset(users_list, request)
            
            # ✅ SERIALIZER LAYER: Use EnhancedUserProfileReadSerializer for detailed user info
            # This returns profile + account data (roles, permissions, status) for each user
            serializer = EnhancedUserProfileReadSerializer(paginated_users, many=True)
            
            # Response
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=paginator.page.number,
                    page_size=paginator.page.paginator.per_page,
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
    
    ✅ CORRECT FLOW:
    View (get user_id) → Service (fetch/update profile) 
    → Repository (DB query/update) → ORM → DB
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_permissions(self):
        self.required_permissions = [
            PermissionCodes.USER_UPDATE if self.request.method == 'PATCH' else PermissionCodes.USER_READ
        ]
        return super().get_permissions()
    
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

            if not _profile_in_request_scope(request, profile):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to access users outside your department"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ✅ SERIALIZER LAYER: Use EnhancedUserProfileReadSerializer to include account data
            # This returns BOTH profile info + account info (roles, permissions, status)
            serializer = EnhancedUserProfileReadSerializer(profile)
            
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
        """
        Update user profile with admin capabilities.
        ✅ CORRECT FLOW: View → Service → Repository → ORM → DB
        
        Supports updating:
        - email: Update account email
        - first_name: Update account first name
        - last_name: Update account last name
        - department_id: Change department
        - role_id: Change role
        - is_active: Activate/deactivate account
        - full_name: Update profile full name
        - address: Update profile address
        - birthday: Update profile birthday
        """
        try:
            # Resolve current profile/account first so serializer can validate against the real account
            current_profile = self.user_service.get_user_profile(user_id)
            if not _profile_in_request_scope(request, current_profile):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to update users outside your department"),
                    status=status.HTTP_403_FORBIDDEN
                )

            current_account_id = str(current_profile.account_id)
            current_email = current_profile.account.email

            requested_department_id = request.data.get('department_id')
            if requested_department_id and not _has_global_user_scope(request.user):
                scoped_department_ids = self.user_service.get_user_management_scope_department_ids(request.user)
                if str(requested_department_id) not in scoped_department_ids:
                    return Response(
                        ResponseBuilder.error(message="You can only assign users to your managed department tree"),
                        status=status.HTTP_403_FORBIDDEN
                    )

            # SERIALIZER LAYER: Validate request data with admin serializer
            serializer = AdminUserProfileUpdateSerializer(
                data=request.data,
                partial=True,
                context={
                    'user_id': user_id,
                    'account_id': current_account_id,
                    'current_email': current_email,
                }
            )
            
            if not serializer.is_valid():
                logger.warning(f"Validation errors for user {user_id}: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        message="Validation failed",
                        data=serializer.errors
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            logger.info(f"Validated data for update: {validated_data}")
            
            # SERVICE LAYER: Use service method to handle update (not direct ORM)
            # ✅ Service handles: account, profile, department, role through repositories
            updated_profile = self.user_service.update_user_by_admin(
                current_account_id,
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
                    query_text=f"Admin updated user {user_id}. Fields: {', '.join(changed_fields)}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log user profile update: {str(e)}")
            
            # Return updated profile
            response_serializer = EnhancedUserProfileReadSerializer(updated_profile)
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
        except BusinessLogicError as e:
            logger.warning(f"Business logic error updating user {user_id}: {str(e)}")
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
