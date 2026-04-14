from django.urls import path, include, re_path
from rest_framework import routers
from api.views.auth_views import (
    UserLoginView, 
    UserRefreshTokenView, 
    UserLogoutView, 
    UserProfileView, 
    RegisterAccountView, 
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    AdminResetPasswordView
)
from api.views.user_profile_views import (
    UserProfileSelfView,
    UserProfileAvatarView,
)
from api.views.user_profile_admin_views import (
    UserProfileAdminListView,
    UserProfileAdminDetailView,
)
from api.views.user_management_views import (
    UserListView,
    UserDetailView,
    UserStatusChangeView,
    UserRolesView,
    UserRoleUpdateView,
    UserDepartmentChangeView,
    AdminCreateAccountView
)
from api.views.iam_views import (
    PermissionListView,
    RoleManagementView,
    RolePermissionsView,
    CheckUserPermissionView
)

# UUID regex pattern for URL routing
UUID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

# Root API router
router = routers.DefaultRouter()
# router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    # Router endpoints (ViewSets)
    path("", include(router.urls)),
    
    # ============================================================
    # AUTH ENDPOINTS (Phase 0)
    # ============================================================
    re_path(r"^auth/login/?$", UserLoginView.as_view(), name="auth_login"),
    re_path(r"^auth/refresh/?$", UserRefreshTokenView.as_view(), name="auth_refresh"),
    re_path(r"^auth/logout/?$", UserLogoutView.as_view(), name="auth_logout"),
    re_path(r"^auth/register/?$", RegisterAccountView.as_view(), name="auth_register"),
    re_path(r"^auth/account/?$", UserProfileView.as_view(), name="auth_account"),
    re_path(rf"^auth/account/(?P<account_id>{UUID_PATTERN})/?$", UserProfileView.as_view(), name="auth_account_update"),
    re_path(r"^auth/change-password/?$", ChangePasswordView.as_view(), name="auth_change_password"),
    
    # ============================================================
    # PASSWORD RESET ENDPOINTS (Phase 1)
    # ============================================================
    re_path(r"^auth/forgot-password/?$", ForgotPasswordView.as_view(), name="auth_forgot_password"),
    re_path(r"^auth/reset-password/?$", ResetPasswordView.as_view(), name="auth_reset_password"),
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/reset-password/?$", AdminResetPasswordView.as_view(), name="account_admin_reset_password"),
    
    # ============================================================
    # USER PROFILE ENDPOINTS (Phase 2 - Self-Service)
    # User can manage their own profile (personal info, avatar)
    # ============================================================
    # GET /api/v1/users/me - Get own profile
    # PATCH /api/users/me - Update own profile (full_name, address, birthday, metadata)
    re_path(r"^users/me/?$", UserProfileSelfView.as_view(), name="user_profile_self"),
    
    # POST /api/v1/users/me/avatar - Upload avatar
    re_path(r"^users/me/avatar/?$", UserProfileAvatarView.as_view(), name="user_profile_avatar"),
    
    # ============================================================
    # USER PROFILE ADMIN ENDPOINTS (Phase 3 - Admin Personnel Management)
    # Admin can manage all user profile information
    # ============================================================
    # GET /api/v1/users/ - List all users (search, filter, pagination)
    re_path(r"^users/?$", UserProfileAdminListView.as_view(), name="user_profile_admin_list"),
    
    # GET /api/v1/users/{user_id}/ - Get user profile details
    # PATCH /api/v1/users/{user_id}/ - Update user profile
    re_path(rf"^users/(?P<user_id>{UUID_PATTERN})/?$", UserProfileAdminDetailView.as_view(), name="user_profile_admin_detail"),
    
    # ============================================================
    # ACCOUNT MANAGEMENT ENDPOINTS (Phase 1)
    # Account: Tài khoản đăng nhập (authentication, status, roles, department)
    # ============================================================
    # List all accounts (admin only)
    re_path(r"^accounts/?$", UserListView.as_view(), name="account_list"),
    
    # Admin: Create new account + send email
    re_path(r"^accounts/create/?$", AdminCreateAccountView.as_view(), name="account_create"),
    
    # Get single account detail (GET) / Update account (PATCH) 
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/?$", UserDetailView.as_view(), name="account_detail"),
    
    # Change account status (block/unblock)
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/change-status/?$", UserStatusChangeView.as_view(), name="account_change_status"),
    
    # Get account roles (GET) / Assign role to account (POST)
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/roles/?$", UserRolesView.as_view(), name="account_roles"),
    
    # Update/Delete role assignment
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/roles/(?P<role_id>{UUID_PATTERN})/?$", UserRoleUpdateView.as_view(), name="account_role_update"),
    
    # Change account department
    re_path(rf"^accounts/(?P<account_id>{UUID_PATTERN})/department/?$", UserDepartmentChangeView.as_view(), name="account_change_department"),
    
    # ============================================================
    # IAM ENDPOINTS (Phase 3 - Role & Permission Management)
    # ============================================================
    # GET /api/v1/iam/permissions - List all permission codes (paginated)
    # PUT /api/v1/iam/permissions/{permission_id} - Update permission
    # DELETE /api/v1/iam/permissions/{permission_id} - Delete permission (soft delete)
    re_path(r"^iam/permissions/?$", PermissionListView.as_view(), name="iam_permissions"),
    re_path(rf"^iam/permissions/(?P<permission_id>{UUID_PATTERN})/?$", PermissionListView.as_view(), name="iam_permission_detail"),
    
    # API-06/07/08/09: GET|POST|PUT|DELETE /api/v1/iam/roles - Role management
    re_path(r"^iam/roles/?$", RoleManagementView.as_view(), name="iam_roles"),
    re_path(rf"^iam/roles/(?P<role_id>{UUID_PATTERN})/?$", RoleManagementView.as_view(), name="iam_role_detail"),
    
    # API-10/11/12: GET|POST|DELETE /api/v1/iam/roles/{role_id}/permissions
    re_path(rf"^iam/roles/(?P<role_id>{UUID_PATTERN})/permissions/?$", RolePermissionsView.as_view(), name="iam_role_permissions"),
    re_path(rf"^iam/roles/(?P<role_id>{UUID_PATTERN})/permissions/(?P<permission_id>{UUID_PATTERN})/?$", RolePermissionsView.as_view(), name="iam_role_permission_detail"),
    
    # POST /api/v1/iam/users/{user_id}/check-permission - Check user permission
    re_path(rf"^iam/users/(?P<user_id>{UUID_PATTERN})/check-permission/?$", CheckUserPermissionView.as_view(), name="iam_check_user_permission"),
]
