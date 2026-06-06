"""
User Management Views - Admin endpoints for managing users, roles, departments.

Endpoints:
- GET    /api/users/                  (list all users)
- GET    /api/users/{id}/             (get user detail)
- POST   /api/users/{id}/change-status (block/unblock)
- DELETE /api/users/{id}/             (soft-delete)
- GET    /api/users/{id}/roles        (list roles)
- POST   /api/users/{id}/roles        (assign role)
- DELETE /api/users/{id}/roles/{rid}  (remove role)
- PATCH  /api/users/{id}/department   (change department)
"""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.apps import apps
from django.db.models import Q
from django.core.exceptions import ValidationError
from rest_framework import serializers

from api.serializers.base import ResponseBuilder
from api.serializers.user_serializers import (
    UserListSerializer, UserDetailSerializer, UserProfileListSerializer, UserStatusChangeSerializer,
    RoleAssignmentSerializer, RoleRemovalSerializer, RoleUpdateSerializer, DepartmentChangeSerializer
)
from services.user_service import UserService
from core.exceptions import ValidationError as ServiceValidationError
from core.constants import AccountStatus, RoleIds, PermissionCodes
from core.permissions.drf_permissions import user_has_any_permission, user_has_permission

import logging

logger = logging.getLogger(__name__)


def _get_request_user_department_id(user):
    profile = getattr(user, 'user_profile', None)
    department_id = getattr(profile, 'department_id', None)
    return str(department_id) if department_id else None


def _has_global_user_scope(user) -> bool:
    """Permission-based scope bypass for organization-wide user management."""
    return user_has_any_permission(user, [
        PermissionCodes.SYSTEM_ADMIN,
        PermissionCodes.DEPARTMENT_MANAGE,
    ])


# ============================================================
# CUSTOM PAGINATION
# ============================================================

class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================
# PERMISSION CLASSES
# ============================================================

class IsAdmin(permissions.BasePermission):
    """Permission-driven management guard kept for existing view wiring."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_permissions = getattr(view, 'required_permissions', [PermissionCodes.SYSTEM_ADMIN])
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        return user_has_any_permission(request.user, required_permissions)


class IsAdminOrOwner(permissions.BasePermission):
    """Allow users with the required permission, or the owner object."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        required_permissions = getattr(view, 'required_permissions', [PermissionCodes.USER_READ])
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        if user_has_any_permission(request.user, required_permissions):
            return True
        return str(obj.id) == str(request.user.id)


# ============================================================
# VIEWS
# ============================================================

class UserListView(APIView):
    """
    GET /api/users/
    List all users with search, filter, pagination.
    
    Query Parameters:
    - search: Search by username, email, first_name, last_name
    - status: Filter by account status (active, blocked, inactive)
    - department_id: Filter by department
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_READ]
    pagination_class = UserPagination
    user_service = UserService()
    
    def get(self, request):
        try:
            # Extract query parameters
            search_query = request.query_params.get('search', '').strip()
            status_filter = request.query_params.get('status', '').strip()
            dept_filter = request.query_params.get('department_id', '').strip()
            enforce_department_scope = not _has_global_user_scope(request.user)
            scoped_department_ids = self.user_service.get_user_management_scope_department_ids(request.user)
            
            # Validate status if provided
            if status_filter and status_filter not in ['active', 'blocked', 'inactive']:
                return Response(
                    ResponseBuilder.error(
                        message=f"Invalid status: {status_filter}. Must be active, blocked, or inactive"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # âœ… FIXED: Use SERVICE instead of ORM direct query
            # Service handles all business logic including filtering, searching, etc.
            users_list = self.user_service.list_users(
                search=search_query,
                department_id=dept_filter,
                status=status_filter,
                scope_department_ids=scoped_department_ids,
                enforce_department_scope=enforce_department_scope,
            )
            
            # Pagination
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(users_list, request)
            
            # âœ… FIXED: Use UserProfileListSerializer for UserProfile objects
            serializer = UserProfileListSerializer(paginated_queryset, many=True)
            
            page_size = paginator.page.paginator.per_page
            total_count = paginator.page.paginator.count
            
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=paginator.page.number,
                    page_size=page_size,
                    total_items=total_count,
                    message="User list retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error listing users: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(APIView):
    """
    GET /api/accounts/{account_id}/ - Get detailed information about an account
    DELETE /api/accounts/{account_id}/ - Soft-delete an account
    GET: Accessible by: admin OR the account owner
    DELETE: Accessible by: admin only
    """
    permission_classes = [IsAdminOrOwner]
    user_service = UserService()
    
    def get(self, request, account_id):
        try:
            # âœ… FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check: user_read permission or own account
            can_read_users = user_has_permission(request.user, PermissionCodes.USER_READ)
            is_own = str(request.user.id) == str(account_id)
            
            if not (can_read_users or is_own):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to view this account"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = UserDetailSerializer(user)
            return Response(
                ResponseBuilder.success(data=serializer.data, message="Account detail retrieved"),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting account detail: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def delete(self, request, account_id):
        """Delete (soft-delete) an account - requires admin permission"""
        # Check delete permission
        if not user_has_permission(request.user, PermissionCodes.USER_DELETE):
            return Response(
                ResponseBuilder.error(message="You don't have permission to delete accounts"),
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # âœ… FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent self-deletion
            if str(request.user.id) == str(account_id):
                return Response(
                    ResponseBuilder.error(message="Cannot delete your own account"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # âœ… FIXED: Use SERVICE for deactivate instead of direct save
            self.user_service.deactivate_account(account_id)
            
            # Log deletion
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='DELETE_USER',
                    query_text=f"User {user.username} deleted",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log deletion: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    message=f"User '{user.username}' has been deleted",
                    data={"account_id": user.id, "deleted_at": user.deleted_at}
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatusChangeView(APIView):
    """
    POST /api/accounts/{account_id}/change-status
    Block/Unblock account by changing status.
    Only admin can do this.
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_CHANGE_STATUS]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()
    
    @transaction.atomic
    def post(self, request, account_id):
        try:
            # âœ… FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent admin from blocking themselves
            if str(request.user.id) == str(account_id):
                return Response(
                    ResponseBuilder.error(message="Cannot change your own account status"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Validate request
            serializer = UserStatusChangeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            # âœ… FIXED: Use SERVICE to change status instead of direct save
            updated_user = self.user_service.change_account_status(account_id, new_status, reason)
            
            # Log status change via Service (which uses AuditLogRepository)
            try:
                self.user_service.audit_log_action(
                    action='CHANGE_USER_STATUS',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Status changed for account {account_id}: {user.status if 'user' in locals() else 'unknown'} â†’ {new_status}. Reason: {reason}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log status change: {str(e)}")
            
            # If blocking user, invalidate tokens (in real app, would use blacklist)
            if new_status == 'blocked':
                logger.warning(f"Account {account_id} blocked. Invalidating tokens...")
                # Note: Token invalidation would happen via blacklist app (not installed)
                # For now, tokens will fail on validation when user is checked
            
            serializer = UserDetailSerializer(updated_user)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message=f"Account status changed to '{new_status}'"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error changing user status: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')




class UserRolesView(APIView):
    """
    GET /api/accounts/{account_id}/roles - List all roles assigned to an account
    POST /api/accounts/{account_id}/roles - Assign a role to an account
    GET: Accessible by: admin OR the account owner
    POST: Accessible by: admin only
    """
    permission_classes = [IsAdminOrOwner]
    
    def get(self, request, account_id):
        try:
            # âœ… FIXED: Use SERVICE instead of direct ORM
            self.user_service = UserService()
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check: user_read permission or own account
            can_read_users = user_has_permission(request.user, PermissionCodes.USER_READ)
            is_own = str(request.user.id) == str(account_id)
            
            if not (can_read_users or is_own):
                return Response(
                    ResponseBuilder.error(message="You don't have permission"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # âœ… FIXED: Get detailed roles via Service method (NOT direct ORM)
            try:
                roles_data = self.user_service.get_user_roles_detailed(account_id)
            except ValidationError as e:
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                ResponseBuilder.success(
                    data=roles_data,
                    message=f"Retrieved {len(roles_data)} roles for account"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting account roles: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def post(self, request, account_id):
        """Assign a role to account (POST method on same endpoint)"""
        try:
            # Check role management permission
            if not user_has_permission(request.user, PermissionCodes.USER_CHANGE_ROLE):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to assign roles"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request
            serializer = RoleAssignmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            role_id = serializer.validated_data['role_id']
            notes = serializer.validated_data.get('notes', '')
            
            # Call Service (NOT ORM)
            self.user_service = UserService()
            ar = self.user_service.assign_role_to_user(
                account_id=account_id,
                role_id=role_id,
                notes=notes,
                granted_by=request.user
            )
            
            # Get role for response
            # âœ… CORRECT: ar already has role via FK - no ORM needed!
            role = ar.role
            
            # Log action via Service (which uses AuditLogRepository internally)
            try:
                self.user_service.audit_log_action(
                    action='ASSIGN_ROLE',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Role '{role.code}' assigned to account {account_id}. Notes: {notes}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log role assignment: {str(e)}")
            
            return Response(
                ResponseBuilder.created(
                    data={
                        'role_id': str(role.id),
                        'role_code': role.code,
                        'role_name': role.name,
                        'assigned_at': ar.created_at
                    },
                    message=f"Role '{role.code}' assigned to account"
                ),
                status=status.HTTP_201_CREATED
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class UserRoleRemoveView(APIView):
    """
    DELETE /api/accounts/{account_id}/roles/{role_id}
    Remove a role from account.
    Only admin can do this. Cannot remove last role.
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_CHANGE_ROLE]
    
    @transaction.atomic
    def delete(self, request, account_id, role_id):
        try:
            # Call Service (NOT ORM)
            self.user_service = UserService()
            self.user_service.remove_role_from_user(account_id, role_id)
            
            # âœ… CORRECT: No ORM calls needed for success response
            # Just acknowledge the deletion
            
            # Log action via Service
            try:
                self.user_service.audit_log_action(
                    action='REMOVE_ROLE',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Role {role_id} removed from account {account_id}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log role removal: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    message=f"Role removed from account successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class UserRoleUpdateView(APIView):
    """
    PATCH /api/accounts/{account_id}/roles/{role_id}
    Update role assignment info (notes, etc.) for a particular role.
    Only admin can do this.
    PUT /api/accounts/{account_id}/roles/{role_id}
    Replace a role for an account.
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_CHANGE_ROLE]
    
    @transaction.atomic
    def patch(self, request, account_id, role_id):
        try:
            # Validate request
            serializer = RoleUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_notes = serializer.validated_data.get('notes', '')
            
            # Call Service (NOT ORM)
            self.user_service = UserService()
            ar = self.user_service.update_role_assignment(
                account_id=account_id,
                role_id=role_id,
                notes=new_notes
            )
            
            # âœ… CORRECT: ar already has role via FK - no ORM needed!
            role = ar.role
            
            # Log action via Service
            try:
                self.user_service.audit_log_action(
                    action='UPDATE_ROLE',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Role {role_id} assignment updated for account {account_id}. Notes: {new_notes}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log role update: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'role_id': str(role.id),
                        'role_code': role.code,
                        'role_name': role.name,
                        'notes': new_notes,
                        'updated_at': ar.updated_at
                    },
                    message=f"Role assignment updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def put(self, request, account_id, role_id):
        """Replace single active role - only 1 role active per account"""
        try:
            # Validate request
            if 'new_role_id' not in request.data:
                return Response(
                    ResponseBuilder.error(message="Field 'new_role_id' is required"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            new_role_id = request.data.get('new_role_id')
            notes = request.data.get('notes', '')
            
            # Check not same role
            if role_id == new_role_id:
                return Response(
                    ResponseBuilder.error(message=f"New role must be different from current role"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # âœ… CORRECT: Use Service for ALL role replacement logic (NOT ORM direct calls)
            self.user_service = UserService()
            try:
                new_ar = self.user_service.replace_user_role(
                    account_id=account_id,
                    old_role_id=role_id,
                    new_role_id=new_role_id,
                    notes=notes,
                    granted_by=request.user
                )
            except ValidationError as e:
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # âœ… CORRECT: Get data from Service response (NOT ORM)
            new_role = new_ar.role
            account = new_ar.account
            
            # Log action via Service
            try:
                self.user_service.audit_log_action(
                    action='REPLACE_ROLE',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Role replaced for account {account_id}: {role_id} â†’ {new_role_id}. Notes: {notes}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log role replacement: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'new_role_id': str(new_role.id),
                        'new_role_code': new_role.code,
                        'new_role_name': new_role.name,
                        'account_id': str(account.id),
                        'account_username': account.username,
                        'notes': notes,
                        'action': 'REPLACE_ROLE'
                    },
                    message=f"Role replaced for account {account.username}"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error replacing role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class UserDepartmentChangeView(APIView):
    """
    PATCH /api/accounts/{account_id}/department
    Transfer account to a different department.
    Only admin can do this.
    
    Note: Department info is on UserProfile, not Account.
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_UPDATE]
    
    @transaction.atomic
    def patch(self, request, account_id):
        try:
            # Validate request
            serializer = DepartmentChangeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_dept_id = serializer.validated_data['department_id']
            reason = serializer.validated_data.get('reason', '')
            
            # Call Service (NOT ORM)
            self.user_service = UserService()
            user_profile = self.user_service.change_user_department(
                account_id=account_id,
                department_id=new_dept_id
            )
            
            # âœ… CORRECT: No ORM calls needed for response
            # user_profile already from Service and has department via FK
            
            # Log action via Service (which uses AuditLogRepository)
            try:
                old_dept_name = user_profile.department.name if user_profile.department else "None"
                
                self.user_service.audit_log_action(
                    action='CHANGE_ACCOUNT_DEPARTMENT',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Account {account_id} department changed to {new_dept_id}. Reason: {reason}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log department change: {str(e)}")
            
            # Response - don't need to fetch user again, use profile data
            return Response(
                ResponseBuilder.success(
                    data={
                        'account_id': str(account_id),
                        'department_id': str(new_dept_id),
                        'department_name': user_profile.department.name if user_profile.department else "None",
                        'reason': reason
                    },
                    message=f"Account department changed successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error changing department: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class AdminCreateAccountView(APIView):
    """
    Admin endpoint Ä‘á»ƒ táº¡o account má»›i cho user.
    - GET /api/accounts/create: Danh sÃ¡ch account active
    - POST /api/accounts/create: Táº¡o account má»›i + tá»± Ä‘á»™ng generate temp password + gá»­i email + gÃ¡n role
    
    Chá»‰ admin má»›i cÃ³ quyá»n truy cáº­p.
    """
    permission_classes = [IsAdmin]

    def get_permissions(self):
        self.required_permissions = [
            PermissionCodes.USER_CREATE if self.request.method == 'POST' else PermissionCodes.USER_READ
        ]
        return super().get_permissions()
    
    def get(self, request):
        """GET: List all active accounts"""
        try:
            from services.user_service import UserService
            
            self.user_service = UserService()
            enforce_department_scope = not _has_global_user_scope(request.user)
            scoped_department_ids = self.user_service.get_user_management_scope_department_ids(request.user)

            # âœ… FIXED: Use SERVICE instead of direct ORM
            accounts = self.user_service.list_users(
                status='active',
                scope_department_ids=scoped_department_ids,
                enforce_department_scope=enforce_department_scope,
            )
            
            # Convert model instances to dict for response
            paginator = UserPagination()
            page = paginator.paginate_queryset(accounts, request)
            if page is not None:
                # âœ… FIXED: Use UserProfileListSerializer for UserProfile objects (not UserListSerializer)
                serializer = UserProfileListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            # âœ… FIXED: Use UserProfileListSerializer for UserProfile objects
            serializer = UserProfileListSerializer(accounts, many=True)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message=f"Retrieved {accounts.count()} active accounts"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error listing accounts: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """POST: Create new account + generate temp password + send email"""
        try:
            self.user_service = UserService()
            created_account = self._create_account_from_payload(
                request=request,
                payload=request.data,
                send_email=True,
            )

            return Response(
                ResponseBuilder.created(
                    data=created_account,
                    message=(
                        f"Account '{created_account['username']}' created successfully "
                        f"with role '{created_account['role_name']}'. Email: {created_account['email_status']}"
                    ),
                ),
                status=status.HTTP_201_CREATED,
            )

        except PermissionDenied as e:
            return Response(
                ResponseBuilder.error(message=str(e)),
                status=status.HTTP_403_FORBIDDEN,
            )
        except (serializers.ValidationError, ServiceValidationError) as e:
            detail = e.detail if hasattr(e, 'detail') else str(e)
            return Response(
                ResponseBuilder.error(message=f"Validation: {detail}"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error creating account: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _create_account_from_payload(self, request, payload, send_email=True):
        """Create one account using the same validation rules for single and bulk APIs."""
        if not hasattr(self, 'user_service'):
            self.user_service = UserService()

        department = self._resolve_create_department(request, payload.get('department_id'))
        role_id, role_obj = self._resolve_create_role(payload.get('role_id'))

        if role_obj.code == 'admin' and department is not None:
            raise serializers.ValidationError(
                "Admin role is company-wide and must not be assigned to a department"
            )

        username = str(payload.get('username', '')).strip()
        email = str(payload.get('email', '')).strip()
        first_name = str(payload.get('first_name', '')).strip()
        last_name = str(payload.get('last_name', '')).strip()

        missing_fields = [
            field_name
            for field_name, value in {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }.items()
            if not value
        ]
        if missing_fields:
            raise serializers.ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

        temp_password = self._generate_temporary_password()
        account_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': temp_password,
        }

        user = self.user_service.register_account_admin(
            account_data=account_data,
            department=department,
            role_id=role_id,
            granted_by=request.user,
        )

        email_status = "skipped"
        if send_email:
            try:
                from services.email_service import EmailService
                email_sent = EmailService.send_account_creation_email(user, temp_password)
                email_status = "sent" if email_sent else "failed"
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                email_status = "error"

        role_name = role_obj.code
        try:
            self.user_service.audit_log_action(
                action='UPLOAD',
                user_id=request.user.id,
                resource_id=str(user.id),
                query_text=f"Admin created account: {username} ({email}) with role '{role_name}'. Email status: {email_status}",
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log account creation: {str(e)}")

        user_profile = getattr(user, 'user_profile', None)
        department_id = None
        department_name = None
        if user_profile and user_profile.department_id:
            department_id = str(user_profile.department_id)
            department_name = user_profile.department.name if user_profile.department else None

        return {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'status': user.status,
            'department_id': department_id,
            'department_name': department_name,
            'role_id': str(role_id),
            'role_name': role_name,
            'created_at': user.created_at,
            'email_sent': email_status == "sent",
            'email_status': email_status,
        }

    def _resolve_create_department(self, request, department_id):
        department_id = str(department_id).strip() if department_id else None
        enforce_department_scope = not _has_global_user_scope(request.user)

        if enforce_department_scope:
            scoped_department_ids = self.user_service.get_user_management_scope_department_ids(request.user)
            if not scoped_department_ids:
                raise PermissionDenied("Your account has no managed department scope")
            if department_id and str(department_id) not in scoped_department_ids:
                raise PermissionDenied("You can only create users in your managed department tree")
            if not department_id:
                department_id = scoped_department_ids[0]

        if not department_id:
            return None

        department = self.user_service.department_repository.get_by_id(department_id)
        if not department:
            raise serializers.ValidationError(f"Department '{department_id}' not found")
        return department

    def _resolve_create_role(self, role_id):
        from core.constants import RoleIds
        import uuid

        if not role_id:
            role_id = RoleIds.USER
        elif isinstance(role_id, str):
            role_id = role_id.strip()
            try:
                role_id = uuid.UUID(role_id)
            except ValueError:
                pass

        role_obj = self.user_service.role_repository.get_by_id(role_id)
        if not role_obj:
            raise serializers.ValidationError(f"Role '{role_id}' not found")
        return role_id, role_obj
    
    def _get_client_ip(self, request):
        """Extract client IP from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
    
    @staticmethod
    def _generate_temporary_password(length=16) -> str:
        """Generate a secure temporary password"""
        import secrets
        import string
        
        # Character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one from each category
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]
        
        # Fill rest randomly
        all_chars = uppercase + lowercase + digits + special
        password += [secrets.choice(all_chars) for _ in range(length - 4)]
        
        # Shuffle
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)


class AdminBulkCreateAccountView(AdminCreateAccountView):
    """
    Admin endpoint to create many accounts in one request.

    POST /api/accounts/bulk-create
    Body:
    {
      "accounts": [
        {"username": "...", "email": "...", "first_name": "...", "last_name": "...", "department_id": "...", "role_id": "..."}
      ],
      "department_id": "optional common department",
      "role_id": "optional common role",
      "send_email": true
    }
    """
    permission_classes = [IsAdmin]
    required_permissions = [PermissionCodes.USER_CREATE]
    max_bulk_accounts = 100

    def post(self, request):
        self.user_service = UserService()

        raw_accounts = request.data.get('accounts', request.data.get('users'))
        if not isinstance(raw_accounts, list):
            return Response(
                ResponseBuilder.error(message="Field 'accounts' must be a list"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not raw_accounts:
            return Response(
                ResponseBuilder.error(message="Field 'accounts' must contain at least one account"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(raw_accounts) > self.max_bulk_accounts:
            return Response(
                ResponseBuilder.error(message=f"Cannot create more than {self.max_bulk_accounts} accounts at once"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        common_department_id = request.data.get('department_id')
        common_role_id = request.data.get('role_id')
        send_email = request.data.get('send_email', True)
        send_email = False if str(send_email).lower() in ['false', '0', 'no'] else bool(send_email)

        created = []
        errors = []
        seen_usernames = {}
        seen_emails = {}

        for index, raw_account in enumerate(raw_accounts):
            if not isinstance(raw_account, dict):
                errors.append({
                    'index': index,
                    'identifier': None,
                    'message': "Account item must be an object",
                })
                continue

            username = str(raw_account.get('username', '')).strip().lower()
            email = str(raw_account.get('email', '')).strip().lower()
            duplicate_message = None

            if username:
                if username in seen_usernames:
                    duplicate_message = f"Duplicate username in request; first seen at index {seen_usernames[username]}"
                else:
                    seen_usernames[username] = index

            if email and not duplicate_message:
                if email in seen_emails:
                    duplicate_message = f"Duplicate email in request; first seen at index {seen_emails[email]}"
                else:
                    seen_emails[email] = index

            if duplicate_message:
                errors.append({
                    'index': index,
                    'identifier': raw_account.get('email') or raw_account.get('username'),
                    'message': duplicate_message,
                })
                continue

            payload = dict(raw_account)
            if not payload.get('department_id') and common_department_id:
                payload['department_id'] = common_department_id
            if not payload.get('role_id') and common_role_id:
                payload['role_id'] = common_role_id

            try:
                created_account = self._create_account_from_payload(
                    request=request,
                    payload=payload,
                    send_email=send_email,
                )
                created.append({
                    'index': index,
                    **created_account,
                })
            except PermissionDenied as e:
                errors.append({
                    'index': index,
                    'identifier': raw_account.get('email') or raw_account.get('username'),
                    'message': str(e),
                })
            except (serializers.ValidationError, ServiceValidationError) as e:
                detail = e.detail if hasattr(e, 'detail') else str(e)
                errors.append({
                    'index': index,
                    'identifier': raw_account.get('email') or raw_account.get('username'),
                    'message': str(detail),
                })
            except Exception as e:
                logger.error(f"Bulk account create failed at index {index}: {str(e)}", exc_info=True)
                errors.append({
                    'index': index,
                    'identifier': raw_account.get('email') or raw_account.get('username'),
                    'message': str(e),
                })

        response_data = {
            'created': created,
            'errors': errors,
            'created_count': len(created),
            'error_count': len(errors),
            'requested_count': len(raw_accounts),
        }

        if not created:
            return Response(
                ResponseBuilder.error(
                    message="No accounts were created",
                    data=response_data,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ResponseBuilder.success(
                data=response_data,
                message=f"Created {len(created)} of {len(raw_accounts)} accounts",
                status_code=status.HTTP_201_CREATED if not errors else 207,
            ),
            status=status.HTTP_201_CREATED if not errors else 207,
        )
