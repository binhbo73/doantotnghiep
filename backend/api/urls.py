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
from api.views.user_management_views import (
    UserListView,
    UserDetailView,
    UserStatusChangeView,
    UserDeleteView,
    UserRolesView,
    UserRoleAssignView,
    UserRoleUpdateView,
    UserDepartmentChangeView,
    AdminCreateAccountView
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
    re_path(rf"^auth/account/(?P<user_id>{UUID_PATTERN})/?$", UserProfileView.as_view(), name="auth_account_update"),
    re_path(r"^auth/change-password/?$", ChangePasswordView.as_view(), name="auth_change_password"),
    
    # ============================================================
    # PASSWORD RESET ENDPOINTS (Phase 1)
    # ============================================================
    re_path(r"^auth/forgot-password/?$", ForgotPasswordView.as_view(), name="auth_forgot_password"),
    re_path(r"^auth/reset-password/?$", ResetPasswordView.as_view(), name="auth_reset_password"),
    re_path(rf"^accounts/(?P<id>{UUID_PATTERN})/reset-password/?$", AdminResetPasswordView.as_view(), name="account_admin_reset_password"),
    
    # ============================================================
    # ACCOUNT MANAGEMENT ENDPOINTS (Phase 1)
    # Account: Tài khoản đăng nhập (authentication, status, roles, department)
    # ============================================================
    # List all accounts (admin only)
    re_path(r"^accounts/?$", UserListView.as_view(), name="account_list"),
    
    # Admin: Create new account + send email
    re_path(r"^accounts/create/?$", AdminCreateAccountView.as_view(), name="account_create"),
    
    # Get single account detail (GET) / Update account (PATCH) 
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/?$", UserDetailView.as_view(), name="account_detail"),
    
    # Change account status (block/unblock)
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/change-status/?$", UserStatusChangeView.as_view(), name="account_change_status"),
    
    # Get account roles (GET) / Assign role to account (POST)
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/roles/?$", UserRolesView.as_view(), name="account_roles_list"),
    
    # Assign role to account (also handled by POST on /roles endpoint)
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/roles/?$", UserRoleAssignView.as_view(), name="account_role_assign"),
    
    # Update/Delete role assignment
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/roles/(?P<role_id>{UUID_PATTERN})/?$", UserRoleUpdateView.as_view(), name="account_role_update"),
    
    # Change account department
    re_path(rf"^accounts/(?P<user_id>{UUID_PATTERN})/department/?$", UserDepartmentChangeView.as_view(), name="account_change_department"),
]
