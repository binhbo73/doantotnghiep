from django.urls import path, include
from rest_framework import routers
from api.views.auth_views import (
    UserLoginView, 
    UserRefreshTokenView, 
    UserLogoutView, 
    UserProfileView, 
    RegisterAccountView, 
    ChangePasswordView
)

# Root API router
router = routers.DefaultRouter()
# router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    # Router endpoints (ViewSets)
    path("", include(router.urls)),
    
    # Custom endpoints (Auth & User lifecycle)
    path("auth/login/", UserLoginView.as_view(), name="auth_login"),
    path("auth/refresh/", UserRefreshTokenView.as_view(), name="auth_refresh"),
    path("auth/logout/", UserLogoutView.as_view(), name="auth_logout"),
    path("auth/register/", RegisterAccountView.as_view(), name="auth_register"),
    path("auth/profile/", UserProfileView.as_view(), name="auth_profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth_change_password"),
]
