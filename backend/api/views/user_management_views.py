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
from core.constants import RoleIds, AccountStatus

import logging

logger = logging.getLogger(__name__)


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
    """Check if user has admin role"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check if user has ADMIN (id=1) or MANAGER (id=2) role
        return request.user.account_roles.filter(
            role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
            is_deleted=False
        ).exists()


class IsAdminOrOwner(permissions.BasePermission):
    """Check if user is admin OR viewing own profile"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access any user
        if request.user.account_roles.filter(
            role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
            is_deleted=False
        ).exists():
            return True
        
        # Owner can access own profile
        return obj.id == request.user.id


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
    pagination_class = UserPagination
    user_service = UserService()
    
    def get(self, request):
        try:
            # Extract query parameters
            search_query = request.query_params.get('search', '').strip()
            status_filter = request.query_params.get('status', '').strip()
            dept_filter = request.query_params.get('department_id', '').strip()
            
            # Validate status if provided
            if status_filter and status_filter not in ['active', 'blocked', 'inactive']:
                return Response(
                    ResponseBuilder.error(
                        message=f"Invalid status: {status_filter}. Must be active, blocked, or inactive"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ✅ FIXED: Use SERVICE instead of ORM direct query
            # Service handles all business logic including filtering, searching, etc.
            users_list = self.user_service.list_users(
                search=search_query,
                department_id=dept_filter,
                status=status_filter
            )
            
            # Pagination
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(users_list, request)
            
            # ✅ FIXED: Use UserProfileListSerializer for UserProfile objects
            serializer = UserProfileListSerializer(paginated_queryset, many=True)
            
            page_size = paginator.page_size
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
            # ✅ FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check: admin or own account
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                is_deleted=False
            ).exists()
            
            is_own = request.user.id == account_id
            
            if not (is_admin or is_own):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to view this account"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ✅ FIXED: Add audit log for GET operation
            try:
                from apps.operations.models import AuditLog
                action_desc = f"User {request.user.username} viewed account detail {user.username}"
                AuditLog.log_action(
                    account=request.user,
                    action='VIEW_ACCOUNT_DETAIL',
                    resource_id=str(account_id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.warning(f"Failed to log view_account_detail action: {str(e)}")
            
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
        # Check admin permission
        is_admin = request.user.account_roles.filter(
            role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
            is_deleted=False
        ).exists()
        
        if not is_admin:
            return Response(
                ResponseBuilder.error(message="You don't have permission to delete accounts"),
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # ✅ FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent self-deletion
            if request.user.id == account_id:
                return Response(
                    ResponseBuilder.error(message="Cannot delete your own account"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # ✅ FIXED: Use SERVICE for deactivate instead of direct save
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()
    
    @transaction.atomic
    def post(self, request, account_id):
        try:
            # ✅ FIXED: Use SERVICE instead of ORM direct
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception as e:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent admin from blocking themselves
            if request.user.id == account_id:
                return Response(
                    ResponseBuilder.error(message="Cannot change your own account status"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Validate request
            serializer = UserStatusChangeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            # ✅ FIXED: Use SERVICE to change status instead of direct save
            updated_user = self.user_service.change_account_status(account_id, new_status, reason)
            
            # Log status change via Service (which uses AuditLogRepository)
            try:
                self.user_service.audit_log_action(
                    action='CHANGE_USER_STATUS',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Status changed for account {account_id}: {user.status if 'user' in locals() else 'unknown'} → {new_status}. Reason: {reason}",
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
            # ✅ FIXED: Use SERVICE instead of direct ORM
            self.user_service = UserService()
            try:
                user = self.user_service.get_by_id(account_id)
            except Exception:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {account_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                is_deleted=False
            ).exists()
            
            if not (is_admin or request.user.id == account_id):
                return Response(
                    ResponseBuilder.error(message="You don't have permission"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ✅ FIXED: Get detailed roles via Service method (NOT direct ORM)
            try:
                roles_data = self.user_service.get_user_roles_detailed(account_id)
            except ValidationError as e:
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ✅ FIXED: Add audit log for GET operation
            try:
                from apps.operations.models import AuditLog
                action_desc = f"User {request.user.username} viewed roles for account {account_id}"
                AuditLog.log_action(
                    account=request.user,
                    action='VIEW_ACCOUNT_ROLES',
                    resource_id=str(account_id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.warning(f"Failed to log view_account_roles action: {str(e)}")
            
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
            # Check admin permission
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                is_deleted=False
            ).exists()
            
            if not is_admin:
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
            # ✅ CORRECT: ar already has role via FK - no ORM needed!
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
    
    @transaction.atomic
    def delete(self, request, account_id, role_id):
        try:
            # Call Service (NOT ORM)
            self.user_service = UserService()
            self.user_service.remove_role_from_user(account_id, role_id)
            
            # ✅ CORRECT: No ORM calls needed for success response
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
            
            # ✅ CORRECT: ar already has role via FK - no ORM needed!
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
            
            # ✅ CORRECT: Use Service for ALL role replacement logic (NOT ORM direct calls)
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
            
            # ✅ CORRECT: Get data from Service response (NOT ORM)
            new_role = new_ar.role
            account = new_ar.account
            
            # Log action via Service
            try:
                self.user_service.audit_log_action(
                    action='REPLACE_ROLE',
                    user_id=request.user.id,
                    resource_id=str(account_id),
                    query_text=f"Role replaced for account {account_id}: {role_id} → {new_role_id}. Notes: {notes}",
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
            
            # ✅ CORRECT: No ORM calls needed for response
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
    Admin endpoint để tạo account mới cho user.
    - GET /api/accounts/create: Danh sách account active
    - POST /api/accounts/create: Tạo account mới + tự động generate temp password + gửi email
    
    Chỉ admin mới có quyền truy cập.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """GET: List all active accounts"""
        try:
            from services.user_service import UserService
            
            self.user_service = UserService()
            
            # ✅ FIXED: Use SERVICE instead of direct ORM
            accounts = self.user_service.list_users(status='active')
            
            # Convert model instances to dict for response
            paginator = UserPagination()
            page = paginator.paginate_queryset(accounts, request)
            if page is not None:
                # ✅ FIXED: Use UserProfileListSerializer for UserProfile objects (not UserListSerializer)
                serializer = UserProfileListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            # ✅ FIXED: Use UserProfileListSerializer for UserProfile objects
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
            
            # Step 1: Extract & resolve department (optional)
            # ✅ CORRECT: Use Service to resolve department (NOT ORM direct calls)
            department_id = request.data.get('department_id')
            
            try:
                if department_id:
                    department = self.user_service.department_repository.get_by_id(department_id)
                    if not department:
                        return Response(
                            ResponseBuilder.error(message=f"Department '{department_id}' not found"),
                            status=status.HTTP_404_NOT_FOUND
                        )
                else:
                    # Get or create default department via Service
                    department = self.user_service.resolve_or_create_default_department()
            except Exception as e:
                logger.error(f"Error resolving department: {str(e)}")
                return Response(
                    ResponseBuilder.error(message="Error resolving department"),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Step 2: Extract account fields
            username = request.data.get('username', '').strip()
            email = request.data.get('email', '').strip()
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()
            
            # Generate temporary password
            temp_password = self._generate_temporary_password()
            
            # Step 3: Call Service to create account
            from core.constants import RoleIds
            account_data = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': temp_password
            }
            
            user = self.user_service.register_account_admin(
                account_data=account_data,
                department=department,
                role_id=RoleIds.USER
            )
            
            # Step 4: Send email
            try:
                from services.email_service import EmailService
                email_sent = EmailService.send_account_creation_email(user, temp_password)
                email_status = "sent" if email_sent else "failed"
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                email_status = "error"
            
            # Step 5: Log action via Service (which uses AuditLogRepository)
            try:
                self.user_service.audit_log_action(
                    action='CREATE_ACCOUNT',
                    user_id=request.user.id,
                    resource_id=str(user.id),
                    query_text=f"Admin created account: {username} ({email}). Email status: {email_status}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
            except Exception as e:
                logger.error(f"Failed to log account creation: {str(e)}")
            
            return Response(
                ResponseBuilder.created(
                    data={
                        'id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'status': user.status,
                        'department_id': str(department.id) if department else None,
                        'department_name': department.name if department else None,
                        'created_at': user.created_at,
                        'email_sent': email_status == "sent"
                    },
                    message=f"Account '{username}' created successfully. Email: {email_status}"
                ),
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error creating account: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
