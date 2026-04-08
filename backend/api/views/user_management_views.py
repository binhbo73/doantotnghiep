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
from rest_framework import serializers

from api.serializers.base import ResponseBuilder
from api.serializers.user_serializers import (
    UserListSerializer, UserDetailSerializer, UserStatusChangeSerializer,
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
            User = get_user_model()
            
            # Base queryset - exclude deleted users
            queryset = User.objects.filter(is_deleted=False)
            
            # Search by text
            search_query = request.query_params.get('search', '').strip()
            if search_query:
                queryset = queryset.filter(
                    Q(username__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query)
                )
                logger.info(f"User search: {search_query} - {queryset.count()} results")
            
            # Filter by status
            status_filter = request.query_params.get('status', '').strip()
            if status_filter:
                if status_filter not in ['active', 'blocked', 'inactive']:
                    return Response(
                        ResponseBuilder.error(
                            message=f"Invalid status: {status_filter}. Must be active, blocked, or inactive"
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                queryset = queryset.filter(status=status_filter)
            
            # Filter by department (from UserProfile, not Account)
            dept_filter = request.query_params.get('department_id', '').strip()
            if dept_filter:
                queryset = queryset.filter(user_profile__department_id=dept_filter)
            
            # Optimize queries
            queryset = queryset.prefetch_related(
                'account_roles__role',
                'user_profile'
            ).order_by('-date_joined')
            
            # Pagination
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            
            serializer = UserListSerializer(paginated_queryset, many=True)
            
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
    GET /api/users/{id}/ - Get detailed information about an account
    DELETE /api/users/{id}/ - Soft-delete an account
    GET: Accessible by: admin OR the account owner
    DELETE: Accessible by: admin only
    """
    permission_classes = [IsAdminOrOwner]
    
    def get(self, request, user_id):
        try:
            User = get_user_model()
            
            try:
                user = User.objects.select_related('user_profile').prefetch_related(
                    'account_roles__role__role_permissions__permission'
                ).get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check: admin or own profile
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                is_deleted=False
            ).exists()
            
            is_own = request.user.id == user_id
            
            if not (is_admin or is_own):
                return Response(
                    ResponseBuilder.error(message="You don't have permission to view this user"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = UserDetailSerializer(user)
            return Response(
                ResponseBuilder.success(data=serializer.data, message="User detail retrieved"),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting user detail: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def delete(self, request, user_id):
        """Delete (soft-delete) an account - requires admin permission"""
        # Check admin permission
        permission_classes = [IsAdmin]
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
            User = get_user_model()
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent self-deletion
            if request.user.id == user_id:
                return Response(
                    ResponseBuilder.error(message="Cannot delete your own account"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Soft delete
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
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
    POST /api/users/{id}/change-status
    Block/Unblock user account by changing status.
    Only admin can do this.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def post(self, request, user_id):
        try:
            User = get_user_model()
            
            # Get user
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent admin from blocking themselves
            if request.user.id == user_id:
                return Response(
                    ResponseBuilder.error(message="Cannot change your own account status"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Validate request
            serializer = UserStatusChangeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            old_status = user.status
            user.status = new_status
            user.save(update_fields=['status', 'updated_at'])
            
            # Log status change
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='CHANGE_USER_STATUS',
                    query_text=f"Status changed for user {user.username}: {old_status} → {new_status}. Reason: {reason}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log status change: {str(e)}")
            
            # If blocking user, invalidate tokens (in real app, would use blacklist)
            if new_status == 'blocked':
                logger.warning(f"User {user.username} blocked. Invalidating tokens...")
                # Note: Token invalidation would happen via blacklist app (not installed)
                # For now, tokens will fail on validation when user is checked
            
            serializer = UserDetailSerializer(user)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message=f"User status changed to '{new_status}'"
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


class UserDeleteView(APIView):
    """
    DELETE /api/users/{id}/
    Soft-delete user account (set is_deleted=True).
    Only admin can do this. Admin cannot delete own account.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def delete(self, request, user_id):
        try:
            User = get_user_model()
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prevent self-deletion
            if request.user.id == user_id:
                return Response(
                    ResponseBuilder.error(message="Cannot delete your own account"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Soft delete
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
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
                    data={"user_id": user.id, "deleted_at": user.deleted_at}
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}", exc_info=True)
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
    GET /api/users/{id}/roles - List all roles assigned to an account
    POST /api/users/{id}/roles - Assign a role to an account
    GET: Accessible by: admin OR the account owner
    POST: Accessible by: admin only
    """
    permission_classes = [IsAdminOrOwner]
    
    def get(self, request, user_id):
        try:
            User = get_user_model()
            
            try:
                user = User.objects.prefetch_related(
                    'account_roles__role__role_permissions__permission'
                ).get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Permission check
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                is_deleted=False
            ).exists()
            
            if not (is_admin or request.user.id == user_id):
                return Response(
                    ResponseBuilder.error(message="You don't have permission"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get roles
            roles_data = []
            for ar in user.account_roles.filter(is_deleted=False).select_related('role'):
                role = ar.role
                permissions = list(
                    role.role_permissions.filter(is_deleted=False)
                    .values_list('permission__code', flat=True)
                )
                roles_data.append({
                    'id': str(role.id),
                    'code': role.code,
                    'name': role.name,
                    'permissions': permissions,
                    'assigned_at': ar.created_at
                })
            
            return Response(
                ResponseBuilder.success(
                    data=roles_data,
                    message=f"Retrieved {len(roles_data)} roles for user"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def post(self, request, user_id):
        """Assign a role to account (POST method on same endpoint)"""
        try:
            User = get_user_model()
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
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
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate request
            serializer = RoleAssignmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            role_id = serializer.validated_data['role_id']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                role = Role.objects.get(id=role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if role already assigned
            if user.account_roles.filter(role_id=role_id, is_deleted=False).exists():
                return Response(
                    ResponseBuilder.error(message=f"User already has role '{role.code}'"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Assign role
            ar = AccountRole.objects.create(
                account=user,
                role=role,
                granted_by=request.user,
                notes=notes
            )
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='ASSIGN_ROLE',
                    query_text=f"Role '{role.code}' assigned to user {user.username}. Notes: {notes}",
                    request=request
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
                    message=f"Role '{role.code}' assigned to user {user.username}"
                ),
                status=status.HTTP_201_CREATED
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserRoleAssignView(APIView):
    """
    POST /api/users/{id}/roles
    Assign a role to user (add to existing roles).
    Only admin can do this.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def post(self, request, user_id):
        try:
            User = get_user_model()
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate request
            serializer = RoleAssignmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            role_id = serializer.validated_data['role_id']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                role = Role.objects.get(id=role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if role already assigned
            if user.account_roles.filter(role_id=role_id, is_deleted=False).exists():
                return Response(
                    ResponseBuilder.error(message=f"User already has role '{role.code}'"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Assign role
            ar = AccountRole.objects.create(
                account=user,
                role=role,
                granted_by=request.user,
                notes=notes
            )
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='ASSIGN_ROLE',
                    query_text=f"Role '{role.code}' assigned to user {user.username}. Notes: {notes}",
                    request=request
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
                    message=f"Role '{role.code}' assigned to user {user.username}"
                ),
                status=status.HTTP_201_CREATED
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class UserRoleRemoveView(APIView):
    """
    DELETE /api/users/{id}/roles/{role_id}
    Remove a role from user.
    Only admin can do this. Cannot remove last role.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def delete(self, request, user_id, role_id):
        try:
            User = get_user_model()
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                role = Role.objects.get(id=role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Find the account-role mapping
            try:
                ar = AccountRole.objects.get(
                    account_id=user_id,
                    role_id=role_id,
                    is_deleted=False
                )
            except AccountRole.DoesNotExist:
                return Response(
                    ResponseBuilder.error(
                        message=f"User does not have role '{role.code}'"
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if this is the last role
            role_count = user.account_roles.filter(is_deleted=False).count()
            if role_count <= 1:
                return Response(
                    ResponseBuilder.error(message="Cannot remove user's only role"),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Soft-delete the account-role mapping
            ar.is_deleted = True
            ar.deleted_at = timezone.now()
            ar.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='REMOVE_ROLE',
                    query_text=f"Role '{role.code}' removed from user {user.username}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log role removal: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    message=f"Role '{role.code}' removed from user {user.username}"
                ),
                status=status.HTTP_200_OK
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
    PATCH /api/accounts/{id}/roles/{role_id}
    Update role assignment info (notes, etc.) for a particular role.
    Only admin can do this.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def patch(self, request, user_id, role_id):
        try:
            User = get_user_model()
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                role = Role.objects.get(id=role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Find the account-role mapping
            try:
                ar = AccountRole.objects.get(
                    account_id=user_id,
                    role_id=role_id,
                    is_deleted=False
                )
            except AccountRole.DoesNotExist:
                return Response(
                    ResponseBuilder.error(
                        message=f"Account with ID {user_id} does not have role with ID {role_id}"
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate request
            serializer = RoleUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Update notes if provided
            new_notes = serializer.validated_data.get('notes', '')
            old_notes = ar.notes or ''
            
            if new_notes != old_notes:
                ar.notes = new_notes
                ar.save(update_fields=['notes', 'updated_at'])
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='UPDATE_ROLE',
                    query_text=f"Role '{role.code}' updated for user {user.username}. Old notes: {old_notes} → New notes: {new_notes}",
                    request=request
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
                    message=f"Role '{role.code}' updated for user {user.username}"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating role: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def put(self, request, user_id, role_id):
        """Replace single active role - only 1 role active per account"""
        try:
            User = get_user_model()
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Account with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get old role (from URL parameter)
            try:
                old_role = Role.objects.get(id=role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check account has old role (must be active)
            try:
                old_ar = AccountRole.objects.get(
                    account_id=user_id,
                    role_id=role_id,
                    is_deleted=False
                )
            except AccountRole.DoesNotExist:
                return Response(
                    ResponseBuilder.error(
                        message=f"Account with ID {user_id} does not have role '{old_role.code}' (only active roles can be replaced)"
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate request
            if 'new_role_id' not in request.data:
                return Response(
                    ResponseBuilder.error(message="Field 'new_role_id' is required"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            new_role_id = request.data.get('new_role_id')
            notes = request.data.get('notes', '')
            
            # Get new role
            try:
                new_role = Role.objects.get(id=new_role_id, is_deleted=False)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Role with ID {new_role_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check not same role
            if role_id == new_role_id:
                return Response(
                    ResponseBuilder.error(
                        message=f"New role must be different from current role '{old_role.code}'"
                    ),
                    status=status.HTTP_409_CONFLICT
                )
            
            # Soft-delete OLD role (make it inactive)
            old_ar.is_deleted = True
            old_ar.deleted_at = timezone.now()
            old_ar.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
            # Smart logic: Try to restore OLDEST deleted role OR create new
            # 🔴 CRITICAL: Use .all_records() to bypass SoftDeleteManager auto-filtering!
            # The manager automatically filters is_deleted=False, so we MUST use:
            # - Model.objects.all_records() to get deleted records
            # - NOT Model.objects (which filters is_deleted=False by default)
            logger.info(f"[PUT] Looking for deleted role {new_role_id} for account {user_id}")
            
            deleted_new_ars = AccountRole.objects.all_records().filter(
                account_id=user_id,
                role_id=new_role_id,
                is_deleted=True
            ).order_by('id')
            
            logger.info(f"[PUT] Found {deleted_new_ars.count()} deleted records for role {new_role_id}")
            
            if deleted_new_ars.exists():
                # RESTORE the oldest deleted role (reuse record, update flags)
                deleted_new_ar = deleted_new_ars.first()
                logger.info(f"[PUT] Restoring deleted record id={deleted_new_ar.id} of role {new_role_id}")
                
                deleted_new_ar.is_deleted = False
                deleted_new_ar.deleted_at = None
                deleted_new_ar.granted_by = request.user
                if notes:
                    deleted_new_ar.notes = notes
                deleted_new_ar.save(update_fields=['is_deleted', 'deleted_at', 'granted_by', 'notes', 'updated_at'])
                
                # HARD DELETE other deleted records for this role (cleanup)
                other_deleted = deleted_new_ars.exclude(id=deleted_new_ar.id)
                other_count = other_deleted.delete()[0]
                if other_count > 0:
                    logger.info(f"[PUT] Cleaned up {other_count} duplicate deleted records for role {new_role_id}")
                
                new_ar = deleted_new_ar
                action_type = 'RESTORE'
                logger.info(f"[PUT] Action: RESTORE (id={deleted_new_ar.id})")
            else:
                # CREATE new role assignment (never existed before)
                logger.info(f"[PUT] Creating NEW record for role {new_role_id}")
                new_ar = AccountRole.objects.create(
                    account=user,
                    role=new_role,
                    granted_by=request.user,
                    notes=notes
                )
                action_type = 'CREATE'
                logger.info(f"[PUT] Action: CREATE (id={new_ar.id})")
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='REPLACE_ROLE',
                    query_text=f"Role replaced for account {user.username}: '{old_role.code}' → '{new_role.code}' ({action_type}). Notes: {notes}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log role replacement: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'old_role_id': old_role.id,
                        'old_role_code': old_role.code,
                        'new_role_id': new_role.id,
                        'new_role_code': new_role.code,
                        'new_role_name': new_role.name,
                        'notes': notes,
                        'action': action_type,
                        'replaced_at': new_ar.created_at if action_type == 'CREATE' else new_ar.updated_at
                    },
                    message=f"Role replaced for account {user.username}: '{old_role.code}' → '{new_role.code}' ({action_type})"
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
    PATCH /api/users/{id}/department
    Transfer user to a different department.
    Only admin can do this.
    
    Note: Department info is on UserProfile, not Account.
    """
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def patch(self, request, user_id):
        try:
            User = get_user_model()
            Department = apps.get_model('users', 'Department')
            UserProfile = apps.get_model('users', 'UserProfile')
            
            try:
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User with ID {user_id} not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate request
            serializer = DepartmentChangeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_dept_id = serializer.validated_data['department_id']
            reason = serializer.validated_data.get('reason', '')
            
            try:
                new_department = Department.objects.get(id=new_dept_id, is_deleted=False)
            except Department.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Department with ID '{new_dept_id}' not found"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get or create UserProfile
            try:
                user_profile = user.user_profile
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(
                    account=user,
                    full_name=user.get_full_name() or user.username
                )
            
            old_department = user_profile.department
            old_dept_name = old_department.name if old_department else "None"
            
            # Update department on UserProfile, not Account
            user_profile.department = new_department
            user_profile.save(update_fields=['department', 'updated_at'])
            
            # Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='CHANGE_USER_DEPARTMENT',
                    query_text=f"User {user.username} department changed: {old_dept_name} → {new_department.name}. Reason: {reason}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log department change: {str(e)}")
            
            serializer = UserDetailSerializer(user)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message=f"User transferred to department '{new_department.name}'"
                ),
                status=status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            return Response(
                ResponseBuilder.error(message=f"Validation error: {str(e.detail)}"),
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
            User = get_user_model()
            
            # Get all active accounts
            accounts = User.objects.filter(
                is_deleted=False,
                status=AccountStatus.ACTIVE
            ).select_related().order_by('-created_at')
            
            # Pagination
            paginator = UserPagination()
            page = paginator.paginate_queryset(accounts, request)
            if page is not None:
                serializer = UserListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = UserListSerializer(accounts, many=True)
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
            User = get_user_model()
            
            # Step 1: Extract & resolve department (optional, same logic as RegisterAccountView)
            department_id = request.data.get('department_id')
            Department = apps.get_model('users', 'Department')
            department = None
            
            # Strategy 1: Nếu có department_id → tìm department
            if department_id:
                try:
                    department = Department.objects.get(id=department_id, is_deleted=False)
                except (Department.DoesNotExist, ValueError):
                    return Response(
                        ResponseBuilder.error(
                            message=f"Department '{department_id}' không tồn tại"
                        ),
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Strategy 2: Nếu không có department_id → tìm hoặc tạo default company department
            if not department:
                try:
                    department = Department.objects.filter(
                        parent_id__isnull=True,
                        is_deleted=False
                    ).first()
                    
                    if not department:
                        import uuid as uuid_module
                        department = Department.objects.create(
                            id=uuid_module.uuid4(),
                            name="Company",
                            parent=None,
                            is_deleted=False
                        )
                        logger.info(f"Created default department: {department.id}")
                    else:
                        logger.info(f"Auto-assigned default department: {department.name}")
                except Exception as e:
                    logger.error(f"Error finding/creating default department: {str(e)}")
                    return Response(
                        ResponseBuilder.error(message="Không thể xác định department"),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Step 2: Validate account fields
            username = request.data.get('username', '').strip()
            email = request.data.get('email', '').strip()
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()
            
            # Validation
            errors = {}
            
            if not username:
                errors['username'] = "Username is required"
            elif len(username) < 3:
                errors['username'] = "Username must be at least 3 characters"
            elif User.objects.filter(username=username, is_deleted=False).exists():
                errors['username'] = f"Username '{username}' already exists"
            
            if not email:
                errors['email'] = "Email is required"
            elif '@' not in email:
                errors['email'] = "Invalid email format"
            elif User.objects.filter(email=email, is_deleted=False).exists():
                errors['email'] = f"Email '{email}' already registered"
            
            if errors:
                return Response(
                    ResponseBuilder.error(message="Validation failed", data=errors),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate temporary password
            temp_password = self._generate_temporary_password()
            
            # Step 3: Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=temp_password,
                status=AccountStatus.ACTIVE
            )
            
            # Step 4: Create UserProfile (1-1 relationship) with department - GIỐNG RegisterAccountView
            try:
                UserProfile = apps.get_model('users', 'UserProfile')
                profile_data = {
                    'account': user,
                    'full_name': user.get_full_name() or user.username,
                }
                if department:
                    profile_data['department'] = department
                
                user_profile = UserProfile.objects.create(**profile_data)
                logger.info(f"UserProfile created for: {user.username} in department: {department.name}")
            except Exception as e:
                logger.error(f"Error creating UserProfile: {str(e)}")
                # Không fail - user vẫn được tạo nhưng không có profile
            
            # Step 5: Assign default role (User role)
            try:
                Role = apps.get_model('users', 'Role')
                AccountRole = apps.get_model('users', 'AccountRole')
                
                default_role = Role.objects.get(code='user', is_deleted=False)
                AccountRole.objects.create(
                    account=user,
                    role=default_role,
                    granted_by=request.user,
                    notes="Created by admin"
                )
            except Exception as e:
                logger.warning(f"Failed to assign default role: {str(e)}")
            
            # Step 6: Send email
            try:
                from services.email_service import EmailService
                email_sent = EmailService.send_account_creation_email(user, temp_password)
                email_status = "sent" if email_sent else "failed"
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                email_status = "error"
            
            # Step 7: Log action
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='CREATE_ACCOUNT',
                    query_text=f"Admin created account: {username} ({email}) in department {department.name}. Email status: {email_status}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log account creation: {str(e)}")
            
            return Response(
                ResponseBuilder.created(
                    data={
                        'id': user.id,
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
                    message=f"Account '{username}' created successfully in department '{department.name if department else 'None'}'. Email sent: {email_status == 'sent'}"
                ),
                status=status.HTTP_201_CREATED
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
