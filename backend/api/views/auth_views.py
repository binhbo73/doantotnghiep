"""
Auth Views - Các API endpoints liên quan đến Định danh người dùng.
Hỗ trợ: Login (JWT), Refresh, Logout, Register, Profile, Change Password.
"""
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from api.serializers.base import ResponseBuilder, LoginSerializer, ChangePasswordSerializer
from api.serializers.user_serializers import AccountSerializer, AccountCreateSerializer
from api.views.base import BaseViewSet
from services.user_service import UserService

import logging

logger = logging.getLogger(__name__)


class UserLoginView(TokenObtainPairView):
    """
    Login API - Trả về Access & Refresh Token chuẩn JWT
    """
    def post(self, request, *args, **kwargs):
        # DRF SimpleJWT handles validation & authentication
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response(
                ResponseBuilder.success(
                    data=response.data,
                    message="Đăng nhập thành công"
                ),
                status=status.HTTP_200_OK
            )
        return response


class UserRefreshTokenView(TokenRefreshView):
    """
    Refresh API - Làm mới Access Token từ Refresh Token
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response(
                ResponseBuilder.success(
                    data=response.data,
                    message="Làm mới token thành công"
                ),
                status=status.HTTP_200_OK
            )
        return response


class UserLogoutView(APIView):
    """
    Logout API - Vô hiệu hóa Refresh Token (hỗ trợ blacklist nếu config)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                ResponseBuilder.success(message="Đăng xuất thành công"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                ResponseBuilder.error(message=f"Đăng xuất thất bại: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(APIView):
    """
    Profile API - Lấy thông tin tài khoản hiện tại / Cập nhật Profile
    """
    permission_classes = [permissions.IsAuthenticated]
    user_service = UserService()

    def get(self, request):
        """Lấy thông tin User hiện tại"""
        user = request.user
        serializer = AccountSerializer(user)
        return Response(
            ResponseBuilder.success(data=serializer.data, message="Thành công"),
            status=status.HTTP_200_OK
        )

    def patch(self, request):
        """Cập nhật thông tin User (tên, avatar, điện thoại...)"""
        user_id = request.user.id
        updated_user = self.user_service.update_profile(user_id, request.data)
        serializer = AccountSerializer(updated_user)
        return Response(
            ResponseBuilder.updated(data=serializer.data, message="Cập nhật thành công"),
            status=status.HTTP_200_OK
        )


class RegisterAccountView(APIView):
    """
    Register API - Đăng ký tài khoản cho User mới
    """
    permission_classes = [permissions.AllowAny] # Cho phép đăng ký tự do hoặc Admins (tùy nghiệp vụ)
    user_service = UserService()

    def post(self, request):
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Call Service to perform password hashing and extra logic
        new_user = self.user_service.register_account(serializer.validated_data)
        result_serializer = AccountSerializer(new_user)
        return Response(
            ResponseBuilder.created(data=result_serializer.data, message="Đăng ký tài khoản thành công"),
            status=status.HTTP_201_CREATED
        )


class ChangePasswordView(APIView):
    """
    API đổi mật khẩu sau khi login
    """
    permission_classes = [permissions.IsAuthenticated]
    user_service = UserService()

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        self.user_service.change_password(
            user_id=request.user.id,
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password']
        )
        return Response(
            ResponseBuilder.success(message="Đổi mật khẩu thành công"),
            status=status.HTTP_200_OK
        )
