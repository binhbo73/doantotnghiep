"""
DRF Permission Classes
======================
Django REST Framework permission classes for ViewSet integration

Usage:
    class DocumentViewSet(ModelViewSet):
        permission_classes = [IsAuthenticated, HasDocumentPermission]
        
        def check_object_permissions(self, request, obj):
            # DRF will call these permission classes
            super().check_object_permissions(request, obj)
"""

import logging
from rest_framework.permissions import BasePermission, IsAuthenticated
from core.constants import PermissionCodes, RoleIds, AccessScope
from .permission_manager import get_permission_manager

logger = logging.getLogger(__name__)


def get_user_permission_codes(user) -> set:
    """Return current DB-backed permission codes for a user."""
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    cached = getattr(user, '_rbac_permission_codes', None)
    if cached is not None:
        return cached

    try:
        from repositories.permission_repository import PermissionRepository
        codes = set(PermissionRepository().get_user_permission_codes(user.id))
        setattr(user, '_rbac_permission_codes', codes)
        return codes
    except Exception as e:
        logger.error(f"Error loading permission codes for user {getattr(user, 'id', None)}: {e}", exc_info=True)
        return set()


def user_has_permission(user, permission_code: str) -> bool:
    """Check a permission code with system_admin bypass."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    codes = get_user_permission_codes(user)
    return PermissionCodes.SYSTEM_ADMIN in codes or permission_code in codes


def user_has_any_permission(user, permission_codes) -> bool:
    """Check any permission code with system_admin bypass."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    codes = get_user_permission_codes(user)
    if PermissionCodes.SYSTEM_ADMIN in codes:
        return True
    return any(code in codes for code in permission_codes or [])


def user_has_all_permissions(user, permission_codes) -> bool:
    """Check all permission codes with system_admin bypass."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    codes = get_user_permission_codes(user)
    if PermissionCodes.SYSTEM_ADMIN in codes:
        return True
    return all(code in codes for code in permission_codes or [])


class HasAnyPermission(BasePermission):
    """
    Permission class that reads `required_permissions` from the view.
    Grants access when the user has at least one required permission.
    """

    message = "You don't have the required permission"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required = getattr(view, 'required_permissions', None)
        if required is None:
            single = getattr(view, 'required_permission_code', None)
            required = [single] if single else []

        if isinstance(required, str):
            required = [required]

        if not required:
            logger.warning(f"View {view.__class__.__name__} missing required_permissions")
            return False

        allowed = user_has_any_permission(request.user, required)
        if not allowed:
            self.message = f"You need one of these permissions: {', '.join(required)}"
            logger.warning(
                f"User {request.user.id} denied - missing any permission {required} "
                f"on {request.method} {request.path}"
            )
        return allowed


class HasAllPermissions(BasePermission):
    """
    Permission class that reads `required_permissions` from the view.
    Grants access only when the user has all required permissions.
    """

    message = "You don't have all required permissions"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required = getattr(view, 'required_permissions', [])
        if isinstance(required, str):
            required = [required]

        if not required:
            logger.warning(f"View {view.__class__.__name__} missing required_permissions")
            return False

        allowed = user_has_all_permissions(request.user, required)
        if not allowed:
            self.message = f"You need all these permissions: {', '.join(required)}"
            logger.warning(
                f"User {request.user.id} denied - missing all permissions {required} "
                f"on {request.method} {request.path}"
            )
        return allowed


class IsAuthenticatedUser(IsAuthenticated):
    """
    Custom authenticated permission
    
    DRF's IsAuthenticated extended with:
    - Logs authentication check
    - Checks user.is_active
    """
    
    message = "Authentication credentials were not provided."
    
    def has_permission(self, request, view):
        # Call parent's check
        if not super().has_permission(request, view):
            return False
        
        # Additional check: user must be active
        if not request.user.is_active:
            self.message = "Your account is not active"
            logger.warning(f"Inactive user {request.user.id} attempted access to {request.path}")
            return False
        
        return True


class IsAdmin(BasePermission):
    """Check if user has system administrator permission."""
    message = "Admin access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return user_has_permission(request.user, PermissionCodes.SYSTEM_ADMIN)


class IsManager(BasePermission):
    """Check if user has management-level permissions."""
    message = "Manager access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return user_has_any_permission(
            request.user,
            [
                PermissionCodes.USER_UPDATE,
                PermissionCodes.USER_CHANGE_ROLE,
                PermissionCodes.DEPARTMENT_READ,
                PermissionCodes.DEPARTMENT_UPDATE,
            ],
        )


class IsAdminOrManager(BasePermission):
    """Check if user has system or management permissions."""
    message = "Admin or Manager access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return user_has_any_permission(
            request.user,
            [
                PermissionCodes.SYSTEM_ADMIN,
                PermissionCodes.USER_UPDATE,
                PermissionCodes.USER_CHANGE_ROLE,
                PermissionCodes.DEPARTMENT_READ,
                PermissionCodes.DEPARTMENT_UPDATE,
            ],
        )


class HasDocumentPermission(BasePermission):
    """
    Permission: Check if user can access document
    
    For ViewSets with document_id in URL kwargs:
    - check_permissions() checks LIST/CREATE (calls has_permission)
    - check_object_permissions() checks RETRIEVE/UPDATE/DELETE (calls has_object_permission)
    
    Usage:
        class DocumentViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, HasDocumentPermission]
            
            def get_object(self):
                # DRF will call check_object_permissions(request, obj)
                return self.get_queryset().get(pk=self.kwargs['pk'])
    
    Returns:
        True: User can perform action
        False: User doesn't have permission
    """
    
    message = "You don't have permission to access this document"
    
    def has_permission(self, request, view):
        """Check LIST/CREATE actions"""
        # Allow authenticated users for general list
        # Specific document filtering happens in check_object_permission
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check RETRIEVE/UPDATE/DELETE actions
        
        Args:
            request: HTTP request
            view: ViewSet instance
            obj: Document instance being accessed
        
        Returns:
            True if user can access, False otherwise
        """
        try:
            perm_mgr = get_permission_manager()
            
            # Map HTTP method to action
            action_map = {
                'GET': 'read',
                'HEAD': 'read',
                'OPTIONS': 'read',
                'POST': 'write',
                'PUT': 'write',
                'PATCH': 'write',
                'DELETE': 'delete',
            }
            
            action = action_map.get(request.method, 'read')
            
            # Check document access
            if not perm_mgr.check_document_access(request.user.id, obj.id, action):
                logger.warning(
                    f"User {request.user.id} denied {action} access to document {obj.id}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking document permission: {str(e)}", exc_info=True)
            return False


class HasFolderPermission(BasePermission):
    """
    Permission: Check if user can access folder
    
    Usage:
        class FolderViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, HasFolderPermission]
    
    Returns:
        True: User can perform action
        False: User doesn't have permission
    """
    
    message = "You don't have permission to access this folder"
    
    def has_permission(self, request, view):
        """Check LIST/CREATE actions"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check RETRIEVE/UPDATE/DELETE actions on folder
        
        Args:
            request: HTTP request
            view: ViewSet instance
            obj: Folder instance
        
        Returns:
            True if user can access, False otherwise
        """
        try:
            perm_mgr = get_permission_manager()
            
            action_map = {
                'GET': 'read',
                'HEAD': 'read',
                'OPTIONS': 'read',
                'POST': 'write',
                'PUT': 'write',
                'PATCH': 'write',
                'DELETE': 'delete',
            }
            
            action = action_map.get(request.method, 'read')
            
            if not perm_mgr.check_folder_access(request.user.id, obj.id, action):
                logger.warning(
                    f"User {request.user.id} denied {action} access to folder {obj.id}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking folder permission: {str(e)}", exc_info=True)
            return False


class HasPermissionCode(BasePermission):
    """
    Permission: Check if user has specific permission code
    
    Usage:
        class AdminViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, HasPermissionCode]
            required_permission_code = PermissionCodes.USER_CREATE
        
        def create(self, request):
            # ViewSet must define required_permission_code
            ...
    """
    
    message = "You don't have the required permission"
    
    def has_permission(self, request, view):
        """
        Check if user has required permission code
        
        ViewSet should define: required_permission_code = "permission_code"
        """
        try:
            permission_code = getattr(view, 'required_permission_code', None)
            if not permission_code:
                logger.warning(f"ViewSet {view.__class__.__name__} missing required_permission_code")
                return False
            
            perm_mgr = get_permission_manager()
            if not perm_mgr.check_user_has_permission(request.user.id, permission_code):
                self.message = f"You need '{permission_code}' permission"
                logger.warning(
                    f"User {request.user.id} denied - missing permission {permission_code}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking permission code: {str(e)}", exc_info=True)
            return False


class HasRole(BasePermission):
    """
    Permission: Check if user has specific role
    
    Usage:
        class AdminViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, HasRole]
            required_role_id = RoleIds.ADMIN
        
        def get_permissions(self):
            if self.action == 'destroy':
                self.required_role_id = RoleIds.ADMIN
            return super().get_permissions()
    """
    
    message = "You don't have the required role"
    
    def has_permission(self, request, view):
        """
        Check if user has required role
        
        ViewSet should define: required_role_id = RoleIds.ADMIN
        """
        try:
            role_id = getattr(view, 'required_role_id', None)
            if role_id is None:
                logger.warning(f"ViewSet {view.__class__.__name__} missing required_role_id")
                return False
            
            perm_mgr = get_permission_manager()
            if not perm_mgr.check_user_has_role(request.user.id, role_id):
                role_name = {
                    RoleIds.ADMIN: "Admin",
                    RoleIds.MANAGER: "Manager",
                    RoleIds.USER: "User"
                }.get(role_id, f"Role {role_id}")
                
                self.message = f"You need {role_name} role"
                logger.warning(
                    f"User {request.user.id} denied - missing role {role_id}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking role: {str(e)}", exc_info=True)
            return False


class IsAdmin(BasePermission):
    """
    Permission: User must be Admin
    
    Usage:
        class SystemViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, IsAdmin]
    """
    
    message = "You must be an Admin to access this resource"
    
    def has_permission(self, request, view):
        try:
            if not user_has_permission(request.user, PermissionCodes.SYSTEM_ADMIN):
                logger.warning(f"User {request.user.id} attempted admin-only access")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking admin role: {str(e)}", exc_info=True)
            return False


class IsAdminOrManager(BasePermission):
    """
    Permission: User must be Admin or Manager
    
    Usage:
        class ManagementViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, IsAdminOrManager]
    """
    
    message = "You must be an Admin or Manager to access this resource"
    
    def has_permission(self, request, view):
        try:
            has_management_permission = user_has_any_permission(
                request.user,
                [
                    PermissionCodes.SYSTEM_ADMIN,
                    PermissionCodes.USER_UPDATE,
                    PermissionCodes.USER_CHANGE_ROLE,
                    PermissionCodes.DEPARTMENT_READ,
                    PermissionCodes.DEPARTMENT_UPDATE,
                ],
            )
            
            if not has_management_permission:
                logger.warning(f"User {request.user.id} attempted manager-level access")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking manager/admin roles: {str(e)}", exc_info=True)
            return False


class IsObjectOwner(BasePermission):
    """
    Permission: User must be the object owner
    
    Object must have 'uploader_id', 'created_by_id', or 'owner_id' field
    
    Usage:
        class DocumentViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, IsObjectOwner]
    """
    
    message = "You can only manage your own objects"
    
    def has_object_permission(self, request, view, obj):
        # Check for common owner fields
        owner_field_names = ['uploader_id', 'created_by_id', 'owner_id', 'user_id']
        
        for field_name in owner_field_names:
            if hasattr(obj, field_name):
                owner_id = getattr(obj, field_name)
                if owner_id == request.user.id:
                    return True
        
        logger.warning(
            f"User {request.user.id} attempted to access object they don't own: "
            f"{obj.__class__.__name__} {obj.id}"
        )
        return False


class CanModifyUser(BasePermission):
    """
    Permission: Check if user can modify target user
    
    Rules:
    - Admin can modify anyone
    - Manager can modify users in their department
    - User can only modify themselves
    
    Usage:
        class AccountViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, CanModifyUser]
            
            def get_object(self):
                # View will use check_object_permissions
                return Account.objects.get(pk=self.kwargs['pk'])
    """
    
    message = "You don't have permission to modify this user"
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user can modify target user 'obj'
        
        Args:
            request: HTTP request
            view: ViewSet
            obj: Target Account instance
        """
        try:
            # Users with user_update can modify managed user records.
            if user_has_permission(request.user, PermissionCodes.USER_UPDATE):
                return True
            
            # User can modify themselves
            if obj.id == request.user.id:
                return True
            
            logger.warning(
                f"User {request.user.id} attempted to modify user {obj.id} without permission"
            )
            return False
            
        except Exception as e:
            logger.error(f"Error checking modify user permission: {str(e)}", exc_info=True)
            return False


# ============================================================
# UTILITY FUNCTIONS - Avoid repeating permission checks in views
# ============================================================

def is_admin_or_manager(user) -> bool:
    """
    ✅ UTILITY: Check if user is admin or manager (centralized)
    
    This function eliminates repeated inline permission checks like:
        is_admin = request.user.account_roles.filter(
            role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
            is_deleted=False
        ).exists()
    
    Usage:
        if not is_admin_or_manager(request.user):
            return Response(..., status=403)
    
    Args:
        user: User/Account instance
    
    Returns:
        bool: True if admin or manager, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    return user_has_any_permission(
        user,
        [
            PermissionCodes.SYSTEM_ADMIN,
            PermissionCodes.USER_UPDATE,
            PermissionCodes.USER_CHANGE_ROLE,
            PermissionCodes.DEPARTMENT_READ,
            PermissionCodes.DEPARTMENT_UPDATE,
        ],
    )


def is_admin(user) -> bool:
    """
    ✅ UTILITY: Check if user is admin (centralized)
    
    Usage:
        if not is_admin(request.user):
            return Response(..., status=403)
    
    Args:
        user: User/Account instance
    
    Returns:
        bool: True if admin, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    return user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)


# ============================================================================
# CONVENIENCE EXPORTS
# ============================================================================

__all__ = [
    'IsAuthenticatedUser',
    'HasDocumentPermission',
    'HasFolderPermission',
    'HasPermissionCode',
    'HasAnyPermission',
    'HasAllPermissions',
    'HasRole',
    'IsAdmin',
    'IsAdminOrManager',
    'IsObjectOwner',
    'CanModifyUser',
    'get_user_permission_codes',
    'user_has_permission',
    'user_has_any_permission',
    'user_has_all_permissions',
]
