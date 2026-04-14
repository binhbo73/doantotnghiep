"""
Permission Decorators - Declarative permissions for views.

Usage:
    @require_role([RoleIds.ADMIN, RoleIds.MANAGER])
    def post(self, request):
        # Only ADMIN or MANAGER can access
        pass
    
    @require_permission(['users.create', 'users.edit'])
    def put(self, request, pk):
        # User must have at least one of these permissions
        pass
    
    @require_authenticated
    def get(self, request):
        # User must be authenticated
        pass
"""

from functools import wraps
from rest_framework import status
from rest_framework.response import Response
from api.serializers.base import ResponseBuilder
from core.exceptions import PermissionDeniedError
import logging

logger = logging.getLogger(__name__)


def require_authenticated(view_func):
    """
    Decorator to require user to be authenticated.
    
    Usage:
        @require_authenticated
        def get(self, request):
            pass
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response(
                ResponseBuilder.error(
                    message="Authentication required",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ),
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(self, request, *args, **kwargs)
    return wrapper


def require_role(allowed_roles):
    """
    Decorator to require user to have specific role(s).
    
    Args:
        allowed_roles: List of role IDs
        
    Usage:
        from core.constants import RoleIds
        
        @require_role([RoleIds.ADMIN, RoleIds.MANAGER])
        def delete(self, request, pk):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        message="Authentication required",
                        status_code=status.HTTP_401_UNAUTHORIZED
                    ),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check roles from JWT token (cached)
            # First try to get from JWT token claims
            user_roles = None
            if hasattr(request, 'auth') and request.auth:
                # From JWT token payload
                user_roles = request.auth.get('roles', []) if request.auth else None
            
            # Fallback: get from user object (for non-JWT auth)
            if not user_roles:
                try:
                    user_roles = [
                        ar.role.id
                        for ar in request.user.account_roles.filter(is_deleted=False)
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get roles for user: {str(e)}")
                    user_roles = []
            
            # Convert to list of IDs if needed
            if isinstance(user_roles, list) and user_roles and isinstance(user_roles[0], dict):
                # JWT token format: [{'id': '...', 'name': '...', 'code': '...'}]
                role_ids = [r.get('id') for r in user_roles]
            else:
                role_ids = user_roles if isinstance(user_roles, list) else []
            
            # Check if user has at least one of the required roles
            has_permission = False
            for role_id in allowed_roles:
                if str(role_id) in [str(r) for r in role_ids]:
                    has_permission = True
                    break
            
            if not has_permission:
                logger.warning(
                    f"User {request.user.id} denied access - required roles {allowed_roles}, has {role_ids}"
                )
                return Response(
                    ResponseBuilder.error(
                        message="Permission denied - insufficient role",
                        status_code=status.HTTP_403_FORBIDDEN
                    ),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(allowed_permissions):
    """
    Decorator to require user to have specific permission(s).
    
    Args:
        allowed_permissions: List of permission codes (e.g., ['users.create', 'users.edit'])
        
    Usage:
        @require_permission(['documents.create', 'documents.edit'])
        def post(self, request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        message="Authentication required",
                        status_code=status.HTTP_401_UNAUTHORIZED
                    ),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get permissions from JWT token (cached)
            user_permissions = None
            if hasattr(request, 'auth') and request.auth:
                user_permissions = request.auth.get('permissions', []) if request.auth else None
            
            # Fallback: get from user object
            if not user_permissions:
                try:
                    from repositories.permission_repository import PermissionRepository
                    perm_repo = PermissionRepository()
                    user_permissions = list(perm_repo.get_user_permission_codes(request.user.id))
                except Exception as e:
                    logger.warning(f"Failed to get permissions for user: {str(e)}")
                    user_permissions = []
            
            # Check if user has at least one of the required permissions
            has_permission = any(perm in user_permissions for perm in allowed_permissions)
            
            if not has_permission:
                logger.warning(
                    f"User {request.user.id} denied access - required permissions {allowed_permissions}, has {user_permissions}"
                )
                return Response(
                    ResponseBuilder.error(
                        message="Permission denied - insufficient permissions",
                        status_code=status.HTTP_403_FORBIDDEN
                    ),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_owner_or_admin(owner_param='user_id'):
    """
    Decorator to require user to be owner or admin.
    
    Args:
        owner_param: Name of the URL parameter containing owner ID
        
    Usage:
        @require_owner_or_admin(owner_param='pk')
        def put(self, request, pk):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Check authentication
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        message="Authentication required",
                        status_code=status.HTTP_401_UNAUTHORIZED
                    ),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get owner ID from URL parameters
            owner_id = kwargs.get(owner_param)
            
            # Check if user is owner
            is_owner = str(request.user.id) == str(owner_id)
            
            # Check if user is admin
            is_admin = False
            user_roles = None
            if hasattr(request, 'auth') and request.auth:
                user_roles = request.auth.get('roles', []) if request.auth else None
            
            if not user_roles:
                try:
                    from core.constants import RoleIds
                    user_roles = [
                        ar.role.id
                        for ar in request.user.account_roles.filter(is_deleted=False)
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get roles for user: {str(e)}")
                    user_roles = []
            
            # Convert to list of IDs if needed
            if isinstance(user_roles, list) and user_roles and isinstance(user_roles[0], dict):
                role_ids = [r.get('id') for r in user_roles]
            else:
                role_ids = user_roles if isinstance(user_roles, list) else []
            
            # Check admin roles
            from core.constants import RoleIds
            for role_id in [RoleIds.ADMIN, RoleIds.MANAGER]:
                if str(role_id) in [str(r) for r in role_ids]:
                    is_admin = True
                    break
            
            if not (is_owner or is_admin):
                logger.warning(
                    f"User {request.user.id} denied access to resource owned by {owner_id}"
                )
                return Response(
                    ResponseBuilder.error(
                        message="Permission denied - you can only access your own resources",
                        status_code=status.HTTP_403_FORBIDDEN
                    ),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator
