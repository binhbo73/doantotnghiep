"""
Permission Decorators
====================
Decorators for ViewSet methods to enforce permission checks

Usage:
    class DocumentViewSet(ModelViewSet):
        @require_permission(PermissionCodes.DOCUMENT_READ)
        def list(self, request):
            ...
        
        @require_document_access(action='write')
        def partial_update(self, request, pk=None):
            ...
        
        @require_role(RoleIds.ADMIN)
        def destroy(self, request, pk=None):
            ...
"""

import logging
from functools import wraps
from django.apps import apps
from rest_framework.response import Response
from rest_framework import status as http_status
from core.constants import PermissionCodes, RoleIds
from core.exceptions import PermissionDeniedError, UnauthorizedError
from api.serializers.base import ResponseBuilder
from .permission_manager import get_permission_manager

logger = logging.getLogger(__name__)


def require_permission(permission_code: str):
    """
    Decorator: Require specific permission via RBAC
    
    Args:
        permission_code: Permission code (e.g., PermissionCodes.DOCUMENT_READ)
    
    Raises:
        PermissionDeniedError if user doesn't have permission
    
    Example:
        @require_permission(PermissionCodes.DOCUMENT_DELETE)
        def destroy(self, request, pk=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Check user is authenticated
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            
            # Check permission
            perm_mgr = get_permission_manager()
            if not perm_mgr.check_user_has_permission(request.user.id, permission_code):
                logger.warning(
                    f"User {request.user.id} denied - missing permission {permission_code} "
                    f"on {request.method} {request.path}"
                )
                return Response(
                    ResponseBuilder.error(
                        f"You don't have permission '{permission_code}' required for this action",
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            # Permission granted, call original method
            return func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_role(role_id: int):
    """
    Decorator: Require specific role
    
    Args:
        role_id: Role ID (e.g., RoleIds.ADMIN)
    
    Raises:
        PermissionDeniedError if user doesn't have role
    
    Example:
        @require_role(RoleIds.ADMIN)
        def destroy(self, request, pk=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Check user is authenticated
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            
            # Check role
            perm_mgr = get_permission_manager()
            if not perm_mgr.check_user_has_role(request.user.id, role_id):
                role_name = {
                    RoleIds.ADMIN: "Admin",
                    RoleIds.MANAGER: "Manager",
                    RoleIds.USER: "User"
                }.get(role_id, f"Role {role_id}")
                
                logger.warning(
                    f"User {request.user.id} denied - missing role {role_id} "
                    f"on {request.method} {request.path}"
                )
                return Response(
                    ResponseBuilder.error(
                        f"This action requires {role_name} role",
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            # Role granted, call original method
            return func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_document_access(action: str = 'read'):
    """
    Decorator: Require document access (read/write/delete)
    
    Extracts document_id from:
    1. kwargs['pk'] (ViewSet detail route)
    2. request.data.get('document_id')
    3. request.query_params.get('document_id')
    
    Args:
        action: 'read', 'write', 'delete', 'share'
    
    Raises:
        PermissionDeniedError if user doesn't have document access
    
    Example:
        @require_document_access(action='write')
        def partial_update(self, request, pk=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Check user is authenticated
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            
            # Extract document_id
            document_id = kwargs.get('pk') or request.data.get('document_id') or request.query_params.get('document_id')
            
            if not document_id:
                logger.warning(f"No document_id found for access check on {request.path}")
                return Response(
                    ResponseBuilder.error(
                        "document_id is required",
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # Check document access
            perm_mgr = get_permission_manager()
            try:
                if not perm_mgr.check_document_access(request.user.id, document_id, action):
                    logger.warning(
                        f"User {request.user.id} denied {action} access to document {document_id} "
                        f"on {request.method} {request.path}"
                    )
                    return Response(
                        ResponseBuilder.error(
                            f"You don't have permission to {action} this document",
                            status_code=http_status.HTTP_403_FORBIDDEN,
                            request_id=getattr(request, 'request_id', None)
                        ),
                        status=http_status.HTTP_403_FORBIDDEN
                    )
            except Exception as e:
                logger.error(f"Error checking document access: {str(e)}")
                return Response(
                    ResponseBuilder.error(
                        "Error checking document access",
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Access granted, call original method
            return func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_folder_access(action: str = 'read'):
    """
    Decorator: Require folder access
    
    Extracts folder_id from:
    1. kwargs['folder_id']
    2. request.data.get('folder_id')
    3. request.query_params.get('folder_id')
    
    Args:
        action: 'read', 'write', 'delete'
    
    Raises:
        PermissionDeniedError if user doesn't have folder access
    
    Example:
        @require_folder_access(action='write')
        def partial_update(self, request, folder_id=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Check user is authenticated
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            
            # Extract folder_id
            folder_id = kwargs.get('folder_id') or request.data.get('folder_id') or request.query_params.get('folder_id')
            
            if not folder_id:
                logger.warning(f"No folder_id found for access check on {request.path}")
                return Response(
                    ResponseBuilder.error(
                        "folder_id is required",
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # Check folder access
            perm_mgr = get_permission_manager()
            if not perm_mgr.check_folder_access(request.user.id, folder_id, action):
                logger.warning(
                    f"User {request.user.id} denied {action} access to folder {folder_id} "
                    f"on {request.method} {request.path}"
                )
                return Response(
                    ResponseBuilder.error(
                        f"You don't have permission to {action} this folder",
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            # Access granted, call original method
            return func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def is_authenticated():
    """
    Decorator: Require user to be authenticated
    
    Example:
        @is_authenticated()
        def get_profile(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """
    Convenience decorator: Require Admin role
    
    Example:
        @require_admin()
        def statistics(self, request):
            ...
    """
    return require_role(RoleIds.ADMIN)


def require_manager_or_above():
    """
    Convenience decorator: Require Manager or Admin role
    
    Example:
        @require_manager_or_above()
        def department_report(self, request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                return Response(
                    ResponseBuilder.error(
                        "Authentication required",
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_401_UNAUTHORIZED
                )
            
            perm_mgr = get_permission_manager()
            has_admin = perm_mgr.check_user_has_role(request.user.id, RoleIds.ADMIN)
            has_manager = perm_mgr.check_user_has_role(request.user.id, RoleIds.MANAGER)
            
            if not (has_admin or has_manager):
                logger.warning(
                    f"User {request.user.id} denied - requires Manager or Admin role "
                    f"on {request.method} {request.path}"
                )
                return Response(
                    ResponseBuilder.error(
                        "This action requires Manager or Admin role",
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        request_id=getattr(request, 'request_id', None)
                    ),
                    status=http_status.HTTP_403_FORBIDDEN
                )
            
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
