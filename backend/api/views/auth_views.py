"""
Auth Views - Các API endpoints liên quan đến Định danh người dùng.
Hỗ trợ: Login (JWT), Refresh, Logout, Register, Profile, Change Password.
"""
from rest_framework import status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from api.serializers.base import ResponseBuilder, LoginSerializer, ChangePasswordSerializer
from api.serializers.user_serializers import AccountSerializer, AccountCreateSerializer
from api.views.base import BaseViewSet
from services.user_service import UserService
from core.constants import RoleIds, AccountStatus
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.apps import apps
from django.core.exceptions import ValidationError

import logging

logger = logging.getLogger(__name__)


class UserLoginView(TokenObtainPairView):
    """
    Login API - Trả về Access & Refresh Token chuẩn JWT
    
    Request body:
    {
        "username": "admin",  OR "email": "admin@example.com"
        "password": "password123"
    }
    
    Response:
    {
        "success": true,
        "status_code": 200,
        "message": "Đăng nhập thành công",
        "data": {
            "user": {...},
            "access_token": "...",
            "refresh_token": "...",
            "permissions": [...],
            "roles": [...],
            "department_id": "..."
        }
    }
    
    💡 NOTE: All business logic (validation, status checks, audit logging, etc.)
              is in UserService.authenticate() - View is just HTTP handler!
    """
    
    def post(self, request, *args, **kwargs):
        """Handle login request - Call service + format response"""
        try:
            # Get email/username/password from request
            email = request.data.get('email', '').strip()
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            
            # One of email or username must be provided
            email_or_username = email or username
            
            # Call UserService.authenticate() - ALL LOGIC IS HERE!
            service = UserService()
            result = service.authenticate(email_or_username, password, request=request)
            
            # Return success response with all result data
            return Response(
                ResponseBuilder.success(
                    data=result,
                    message="Đăng nhập thành công"
                ),
                status=status.HTTP_200_OK
            )
            
        # Exception handler will catch all exceptions and format response
        # (InvalidCredentialsError, AccountBlockedError, ValidationError, etc.)
        # But we can add specific handling here if needed
        except Exception as e:
            # Exceptions are caught by global exception handler
            raise


class UserRefreshTokenView(TokenRefreshView):
    """
    Refresh API - Làm mới Access Token từ Refresh Token
    
    Theo Roadmap API-02:
    - Kiểm tra lại user.is_deleted và user.status (case: user bị block sau login)
    """
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code != 200:
                return response
            
            # ⚠️ RE-CHECK: User status có thay đổi không (blocked/deleted)
            try:
                refresh_token_str = request.data.get('refresh')
                if refresh_token_str:
                    refresh_token = RefreshToken(refresh_token_str)
                    user_id = refresh_token.get('user_id')
                    
                    # ✅ FIXED: Use SERVICE instead of ORM direct
                    user_service = UserService()
                    try:
                        user = user_service.get_by_id(user_id)
                    except Exception:
                        logger.warning(f"User {user_id} not found during token refresh")
                        return Response(
                            ResponseBuilder.error(message="Người dùng không tồn tại"),
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    
                    # Kiểm tra user.is_deleted hoặc user.status == AccountStatus.BLOCKED
                    if user.is_deleted or user.status == AccountStatus.BLOCKED:
                        logger.warning(f"Refresh token denied for deleted/blocked user: {user.id}")
                        return Response(
                            ResponseBuilder.error(message="Tài khoản không còn hoạt động"),
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    
                    if user.status == AccountStatus.INACTIVE or not user.is_active:
                        return Response(
                            ResponseBuilder.error(message="Tài khoản không hoạt động"),
                            status=status.HTTP_403_FORBIDDEN
                        )
            except Exception as e:
                logger.warning(f"Failed to validate user on refresh: {str(e)}")
                # Continue anyway, let client handle it
            
            return Response(
                ResponseBuilder.success(
                    data=response.data,
                    message="Làm mới token thành công"
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Refresh token error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message="Làm mới token thất bại"),
                status=status.HTTP_400_BAD_REQUEST
            )


class UserLogoutView(APIView):
    """
    Logout API - Vô hiệu hóa Refresh Token (hỗ trợ blacklist nếu config)
    
    Theo Roadmap API-03:
    - Ghi AuditLog(action='LOGOUT')
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if not refresh_token:
                return Response(
                    ResponseBuilder.error(message="Refresh token bắt buộc"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ⚠️ Note: Token blacklist app chưa installed
            # Logout logic: client abandon token, token auto-invalid qua rotation
            # Token sẽ expire sau REFRESH_TOKEN_LIFETIME (7 days)
            
            # ⚠️ GHI AUDIT LOG (Roadmap: "Ghi AuditLog(action='LOGOUT')")
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='LOGOUT',
                    query_text=f"User {request.user.username} logged out",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log logout action: {str(e)}")
            
            return Response(
                ResponseBuilder.success(message="Đăng xuất thành công"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message="Đăng xuất thất bại"),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserProfileView(APIView):
    """
    Account API - GET/PATCH/DELETE account
    
    GET    /auth/account           - Lấy thông tin account của chính user
    PATCH  /auth/account           - Cập nhật account của chính user
    DELETE /auth/account           - Xóa account của chính user (soft-delete)
    
    GET    /auth/account/{id}      - Lấy account khác (admin only)
    PATCH  /auth/account/{id}      - Cập nhật account khác (admin only)
    DELETE /auth/account/{id}      - Xóa account khác (admin only)
    """
    permission_classes = [permissions.IsAuthenticated]
    user_service = UserService()

    def get(self, request, account_id=None):
        """Lấy thông tin account - own hoặc admin access"""
        try:
            # Nếu có account_id từ URL, check admin permission
            if account_id:
                is_admin = request.user.account_roles.filter(
                    role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                    is_deleted=False
                ).exists()
                if not is_admin:
                    return Response(
                        ResponseBuilder.error(message="Không có quyền xem account khác"),
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # ✅ FIXED: Use SERVICE instead of ORM direct
                try:
                    user = self.user_service.get_by_id(account_id)
                except Exception as e:
                    return Response(
                        ResponseBuilder.error(message=f"Account {account_id} không tồn tại"),
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Get current user
                user = request.user
            
            # ✅ FIXED: Add audit log for GET operation
            try:
                from apps.operations.models import AuditLog
                action_desc = f"Admin {request.user.username} viewed account {user.username}" if account_id else f"User {request.user.username} viewed own account"
                AuditLog.log_action(
                    account=request.user,
                    action='VIEW_ACCOUNT',
                    resource_id=str(user.id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.warning(f"Failed to log view_account action: {str(e)}")
            
            serializer = AccountSerializer(user)
            return Response(
                ResponseBuilder.success(data=serializer.data, message="Thành công"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error getting account: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Error: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @transaction.atomic
    def patch(self, request, account_id=None):
        """
        Cập nhật thông tin Account
        
        ⚠️ Ghi AuditLog(action='UPDATE_ACCOUNT')
        """
        try:
            # Nếu có account_id từ URL, check admin permission
            if account_id:
                is_admin = request.user.account_roles.filter(
                    role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                    is_deleted=False
                ).exists()
                if not is_admin:
                    return Response(
                        ResponseBuilder.error(message="Không có quyền cập nhật account khác"),
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # ✅ FIXED: Use SERVICE instead of ORM direct
                try:
                    target_account = self.user_service.get_by_id(account_id)
                except Exception as e:
                    return Response(
                        ResponseBuilder.error(message=f"Account {account_id} không tồn tại"),
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                update_account_id = account_id
            else:
                # Update own account
                update_account_id = request.user.id
                target_account = request.user
            
            # ✅ FIXED: Validate input with serializer first
            serializer = AccountSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            # ✅ FIXED: Use SERVICE for update
            updated_user = self.user_service.update_account(update_account_id, serializer.validated_data)
            
            # ⚠️ GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                action_desc = f"Admin {request.user.username} updated account {updated_user.username}" if account_id else f"User {request.user.username} updated own account"
                AuditLog.log_action(
                    account=request.user,
                    action='UPDATE_ACCOUNT',
                    resource_id=str(update_account_id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log update_account action: {str(e)}")
            
            serializer = AccountSerializer(updated_user)
            return Response(
                ResponseBuilder.updated(data=serializer.data, message="Cập nhật thành công"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Update account error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Cập nhật thất bại: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @transaction.atomic
    def delete(self, request, account_id=None):
        """
        Xóa account (Soft-delete)
        
        ⚠️ Ghi AuditLog(action='DEACTIVATE_ACCOUNT')
        """
        try:
            # Nếu có account_id từ URL, check admin permission
            if account_id:
                is_admin = request.user.account_roles.filter(
                    role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],
                    is_deleted=False
                ).exists()
                if not is_admin:
                    return Response(
                        ResponseBuilder.error(message="Không có quyền xóa account khác"),
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # ✅ FIXED: Use SERVICE instead of ORM direct
                try:
                    user = self.user_service.get_by_id(account_id)
                except Exception as e:
                    return Response(
                        ResponseBuilder.error(message=f"Account {account_id} không tồn tại"),
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Delete own account
                user = request.user
            
            # ✅ FIXED: Use SERVICE for deactivate instead of direct save
            self.user_service.deactivate_account(user.id)
            
            # ⚠️ GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                action_desc = f"Account {user.username} deleted by admin {request.user.username}" if user_id else f"User {user.username} self-deleted their account"
                AuditLog.log_action(
                    account=request.user if user_id else user,
                    action='DEACTIVATE_ACCOUNT',
                    resource_id=str(user.id),
                    query_text=action_desc,
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log deactivate action: {str(e)}")
            
            return Response(
                ResponseBuilder.success(
                    message="Tài khoản đã bị xóa (có thể khôi phục)",
                    data={"user_id": str(user.id)}
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Account delete error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Xóa tài khoản thất bại: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RegisterAccountView(APIView):
    """
    Register API - Đăng ký tài khoản cho User mới
    
    Theo Roadmap API-05 (tạm thời đạo vào register):
    - Bắt buộc gán ít nhất 1 Role và 1 Department
    - Phải tạo cả Account và UserProfile trong cùng 1 transaction
    - Validate: username, email unique
    - Ghi AuditLog(action='CREATE_USER')
    """
    permission_classes = [permissions.AllowAny]  # Cho phép đăng ký tự do hoặc Admins (tùy nghiệp vụ)
    user_service = UserService()

    @transaction.atomic
    def post(self, request):
        try:
            # Step 1: Resolve department via Service (NOT ORM)
            department_id = request.data.get('department_id')
            self.user_service = UserService()
            
            try:
                department = self.user_service.resolve_or_create_default_department(department_id)
            except ValidationError as e:
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Step 2: Validate account fields via serializer
            data_for_serializer = request.data.copy()
            data_for_serializer.pop('department_id', None)
            
            serializer = AccountCreateSerializer(data=data_for_serializer)
            serializer.is_valid(raise_exception=True)
            
            # Step 3: Get default role via Service (NOT ORM direct call)
            # ❌ WRONG: Role.objects.get(id=RoleIds.USER)
            # ✅ RIGHT: Service → Repository layer
            validated_data = serializer.validated_data
            validated_data['department'] = department
            
            # Note: UserService.register_account() handles default role assignment
            # If no role specified, user still gets created but needs admin intervention to assign roles
            
            # Step 4: Call Service để tạo account (with department already resolved)
            new_user = self.user_service.register_account(validated_data)
            
            # Step 5: Gán default role via Service (if needed)
            try:
                from core.constants import RoleIds
                self.user_service.assign_role_to_user(
                    user_id=new_user.id,
                    role_id=RoleIds.USER,
                    notes="Auto-assigned default user role",
                    granted_by=None
                )
                logger.info(f"Default role {default_role.code} assigned to {new_user.username}")
            except Exception as e:
                logger.error(f"Failed to assign default role: {str(e)}")
            
            # Step 6: GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=new_user,
                    action='CREATE_USER',
                    query_text=f"User {new_user.username} registered",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log register action: {str(e)}")
            
            result_serializer = AccountSerializer(new_user)
            return Response(
                ResponseBuilder.created(data=result_serializer.data, message="Đăng ký tài khoản thành công"),
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Register error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Đăng ký thất bại: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ChangePasswordView(APIView):
    """
    API đổi mật khẩu sau khi login
    
    ⚠️ Yêu cầu xác thực (JWT token)
    ⚠️ Ghi AuditLog(action='CHANGE_PASSWORD')
    """
    permission_classes = [permissions.IsAuthenticated]
    user_service = UserService()

    def post(self, request):
        try:
            serializer = ChangePasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            try:
                self.user_service.change_password(
                    user_id=request.user.id,
                    old_password=serializer.validated_data['old_password'],
                    new_password=serializer.validated_data['new_password']
                )
            except Exception as e:
                logger.error(f"Service change_password error: {str(e)}", exc_info=True)
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ⚠️ GHI AUDIT LOG (Roadmap: "Ghi AuditLog(action='CHANGE_PASSWORD')")
            try:
                from apps.operations.models import AuditLog
                ip_address = self._get_client_ip(request)
                AuditLog.log_action(
                    account=request.user,
                    action='CHANGE_PASSWORD',
                    resource_type='Account',
                    resource_id=str(request.user.id),
                    query_text=f"User {request.user.username} changed password",
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception as e:
                logger.error(f"Failed to log change_password action: {str(e)}")
            
            return Response(
                ResponseBuilder.success(message="Đổi mật khẩu thành công"),
                status=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            logger.warning(f"Change password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi xác thực: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Change password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Đổi mật khẩu thất bại: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================
# PASSWORD RESET ENDPOINTS (Phase 1)
# ============================================================

class ForgotPasswordView(APIView):
    """
    POST /auth/forgot-password
    
    Người dùng quên password → gửi email link reset
    
    Request body:
    {
        "email": "user@example.com"
    }
    
    Response:
    {
        "success": true,
        "status_code": 200,
        "message": "Email reset password đã được gửi",
        "data": null
    }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            from api.serializers.user_serializers import ForgotPasswordSerializer
            from apps.users.password_reset import PasswordResetService
            from services.email_service import EmailService
            
            serializer = ForgotPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            email = serializer.validated_data['email']
            
            # Call Service (NOT ORM)
            from services.user_service import UserService
            self.user_service = UserService()
            user = self.user_service.get_by_email(email)
            if not user:
                # Don't reveal if email exists (security best practice)
                logger.info(f"Forgot password attempt with non-existent email: {email}")
                return Response(
                    ResponseBuilder.success(
                        message="Nếu email tồn tại, bạn sẽ nhận được email hướng dẫn reset password"
                    ),
                    status=status.HTTP_200_OK
                )
            
            # Generate reset token
            reset_token = PasswordResetService.generate_reset_token(
                account=user,
                is_admin_action=False
            )
            
            # Send email
            email_sent = EmailService.send_password_reset_email(user, reset_token)
            
            if not email_sent:
                logger.error(f"Failed to send reset password email to {email}")
                return Response(
                    ResponseBuilder.error(
                        message="Gửi email thất bại. Vui lòng thử lại sau."
                    ),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # ⚠️ GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=user,
                    action='FORGOT_PASSWORD',
                    query_text=f"User {user.username} requested password reset",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log forgot_password action: {str(e)}")
            
            logger.info(f"Password reset email sent to {email}")
            
            return Response(
                ResponseBuilder.success(
                    message="Email hướng dẫn reset password đã được gửi. Vui lòng kiểm tra inbox."
                ),
                status=status.HTTP_200_OK
            )
            
        except serializers.ValidationError as e:
            logger.warning(f"Forgot password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi xác thực: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResetPasswordView(APIView):
    """
    POST /auth/reset-password
    
    Click link từ email → reset password mới
    
    Request body:
    {
        "token": "reset-token-from-email",
        "new_password": "new_password_123",
        "confirm_password": "new_password_123"
    }
    
    Response:
    {
        "success": true,
        "status_code": 200,
        "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập.",
        "data": null
    }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            from api.serializers.user_serializers import ResetPasswordSerializer
            from apps.users.password_reset import PasswordResetService
            
            serializer = ResetPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            # Verify token and get user
            try:
                user = PasswordResetService.verify_reset_token(token)
            except PermissionError as e:
                logger.warning(f"Invalid reset password token: {str(e)}")
                return Response(
                    ResponseBuilder.error(message=str(e)),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call Service (NOT ORM)
            from services.user_service import UserService
            self.user_service = UserService()
            self.user_service.reset_user_password(user.id, new_password)
            
            # Mark token as used
            try:
                PasswordResetService.use_reset_token(token)
            except Exception as e:
                logger.error(f"Failed to mark token as used: {str(e)}")
            
            # ⚠️ GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=user,
                    action='RESET_PASSWORD',
                    query_text=f"User {user.username} reset password",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log reset_password action: {str(e)}")
            
            logger.info(f"Password reset successfully for user: {user.email}")
            
            return Response(
                ResponseBuilder.success(
                    message="Đặt lại mật khẩu thành công. Vui lòng đăng nhập với mật khẩu mới."
                ),
                status=status.HTTP_200_OK
            )
            
        except serializers.ValidationError as e:
            logger.warning(f"Reset password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi xác thực: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            logger.warning(f"Reset password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Reset password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminResetPasswordView(APIView):
    """
    POST /accounts/{account_id}/reset-password
    
    Admin reset password cho account mà không cần biết password cũ
    
    Permission: Admin only (role_id = 1 or 2)
    
    Request body:
    {
        "new_password": "new_password_123",
        "confirm_password": "new_password_123",
        "send_email": true  (optional, default=true)
    }
    
    Response:
    {
        "success": true,
        "status_code": 200,
        "message": "Mật khẩu của account đã được đặt lại",
        "data": {
            "account_id": 123,
            "email": "user@example.com",
            "notification_sent": true
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, account_id=None):
        try:
            from api.serializers.user_serializers import AdminResetPasswordSerializer
            from apps.users.password_reset import PasswordResetService
            from services.email_service import EmailService
            
            # Check admin permission
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],  # ADMIN, MANAGER
                is_deleted=False
            ).exists()
            
            if not is_admin:
                logger.warning(f"Non-admin user {request.user.username} tried to reset password for others")
                return Response(
                    ResponseBuilder.error(message="Chỉ admin mới có quyền reset password cho account khác"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get target account
            if not account_id:
                return Response(
                    ResponseBuilder.error(message="Account ID bắt buộc"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get target account
            from services.user_service import UserService
            self.user_service = UserService()
            target_user = self.user_service.get_by_id(account_id)
            if not target_user:
                return Response(
                    ResponseBuilder.error(message=f"Account {account_id} không tồn tại"),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Admin can't reset own password (use change-password instead)
            if target_user.id == request.user.id:
                return Response(
                    ResponseBuilder.error(
                        message="Bạn không thể reset password của chính mình.\nHãy sử dụng /auth/change-password"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AdminResetPasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_password = serializer.validated_data['new_password']
            send_email = serializer.validated_data.get('send_email', True)
            
            # Call Service (NOT ORM)
            target_user = self.user_service.admin_reset_user_password(account_id, new_password)
            
            # Invalidate all existing reset tokens
            try:
                PasswordResetService.invalidate_all_tokens(target_user)
            except Exception as e:
                logger.warning(f"Failed to invalidate tokens: {str(e)}")
            
            # Send notification email with new password
            notification_sent = False
            if send_email:
                notification_sent = EmailService.send_admin_password_reset_email(
                    target_user, 
                    new_password=new_password
                )
            
            # ⚠️ GHI AUDIT LOG
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='ADMIN_RESET_PASSWORD',
                    resource_id=str(target_user.id),
                    query_text=f"Admin {request.user.username} reset password for {target_user.username}",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log admin_reset_password action: {str(e)}")
            
            logger.warning(
                f"Admin {request.user.username} reset password for {target_user.email} "
                f"(notification_sent={notification_sent})"
            )
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'user_id': target_user.id,
                        'email': target_user.email,
                        'username': target_user.username,
                        'notification_sent': notification_sent,
                        'note': 'Hãy yêu cầu user đổi mật khẩu sau khi đăng nhập' if not send_email else 'Email thông báo đã được gửi'
                    },
                    message="Mật khẩu của user đã được đặt lại thành công"
                ),
                status=status.HTTP_200_OK
            )
            
        except serializers.ValidationError as e:
            logger.warning(f"Admin reset password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi xác thực: {str(e.detail)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            logger.warning(f"Admin reset password validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Admin reset password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
