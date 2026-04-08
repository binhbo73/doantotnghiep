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
from core.constants import RoleIds
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.apps import apps

import logging

logger = logging.getLogger(__name__)


class UserLoginView(TokenObtainPairView):
    """
    Login API - Trả về Access & Refresh Token chuẩn JWT
    
    Theo Roadmap API-01:
    - Check account.status != 'blocked' và account.is_deleted == False
    - Ghi AuditLog(action='LOGIN')
    - Trả về permission_codes trong response
    
    Request body:
    {
        "username": "admin",  OR "email": "admin@example.com"
        "password": "password123"
    }
    """
    def post(self, request, *args, **kwargs):
        try:
            # Validate input (username + email flexible)
            email = request.data.get('email', '').strip()
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            
            if not (username or email):
                return Response(
                    ResponseBuilder.error(message="Username hoặc email bắt buộc"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not password:
                return Response(
                    ResponseBuilder.error(message="Mật khẩu bắt buộc"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            User = get_user_model()
            
            # Find account by username or email
            user = None
            if username:
                try:
                    user = User.objects.get(is_deleted=False, username=username)
                except User.DoesNotExist:
                    pass
            
            if not user and email:
                try:
                    user = User.objects.get(is_deleted=False, email=email)
                except User.DoesNotExist:
                    pass
            
            if not user:
                identifier = username or email
                logger.warning(f"Login attempt with non-existent user: {identifier}")
                return Response(
                    ResponseBuilder.error(message="Username/email hoặc mật khẩu không chính xác"),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # ⚠️ CHECK: Quy tắc 1 - Account status không được 'blocked' (Roadmap)
            if user.status == 'blocked':
                logger.warning(f"Login attempt with blocked account: {user.id}")
                return Response(
                    ResponseBuilder.error(message="Tài khoản đã bị khóa"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if user.status == 'inactive' or not user.is_active:
                logger.warning(f"Login attempt with inactive account: {user.id}")
                return Response(
                    ResponseBuilder.error(message="Tài khoản không hoạt động"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ⚠️ CHECK: Password validation
            if not user.check_password(password):
                logger.warning(f"Login attempt with wrong password for user: {user.username}")
                return Response(
                    ResponseBuilder.error(message="Username/email hoặc mật khẩu không chính xác"),
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # ✅ Generate JWT tokens (KHÔNG dùng super().post())
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last_login timestamp
            try:
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                logger.info(f"Updated last_login for user: {user.username}")
            except Exception as e:
                logger.warning(f"Failed to update last_login: {str(e)}")
            
            # ⚠️ GHI AUDIT LOG (Roadmap: "Ghi AuditLog(action='LOGIN')")
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=user,
                    action='LOGIN',
                    query_text=f"User {user.username} logged in",
                    request=request
                )
            except Exception as e:
                logger.error(f"Failed to log login action: {str(e)}")
            
            # ⚠️ TRUY VẤN PERMISSION CODES (Roadmap: "trả về permission_codes array")
            try:
                permission_codes = user.get_permissions() if hasattr(user, 'get_permissions') else []
                roles = [{"id": ar.role.id, "code": ar.role.code, "name": ar.role.name} 
                        for ar in user.account_roles.filter(is_deleted=False).select_related('role')]
            except Exception as e:
                logger.warning(f"Failed to fetch permissions: {str(e)}")
                permission_codes = []
                roles = []
            
            # Wrap response data
            # Get department from UserProfile (not Account)
            department_id = None
            try:
                user_profile = user.user_profile
                if user_profile and user_profile.department_id:
                    department_id = str(user_profile.department_id)
            except:
                pass
            
            enhanced_data = {
                "access": access_token,
                "refresh": refresh_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.get_full_name() or user.username,
                    "department_id": department_id,
                    "roles": roles,
                    "permission_codes": permission_codes,  # ✅ CLI trả về permissions
                }
            }
            
            return Response(
                ResponseBuilder.success(
                    data=enhanced_data,
                    message="Đăng nhập thành công"
                ),
                status=status.HTTP_200_OK
            )
            
        except serializers.ValidationError as e:
            logger.warning(f"Login validation error: {str(e)}")
            return Response(
                ResponseBuilder.error(message=f"Lỗi xác thực: {e.detail}"),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi đăng nhập: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


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
                    
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    
                    # Kiểm tra user.is_deleted hoặc user.status == 'blocked'
                    if user.is_deleted or user.status == 'blocked':
                        logger.warning(f"Refresh token denied for deleted/blocked user: {user.id}")
                        return Response(
                            ResponseBuilder.error(message="Tài khoản không còn hoạt động"),
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    
                    if user.status == 'inactive' or not user.is_active:
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

    def get(self, request, user_id=None):
        """Lấy thông tin account - own hoặc admin access"""
        # Nếu có user_id từ URL, check admin permission
        if user_id:
            is_admin = request.user.account_roles.filter(
                role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],  # ADMIN, MANAGER
                is_deleted=False
            ).exists()
            if not is_admin:
                return Response(
                    ResponseBuilder.error(message="Không có quyền xem account khác"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                User = get_user_model()
                user = User.objects.get(id=user_id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"Account {user_id} không tồn tại"),
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get current user
            user = request.user
        
        serializer = AccountSerializer(user)
        return Response(
            ResponseBuilder.success(data=serializer.data, message="Thành công"),
            status=status.HTTP_200_OK
        )

    def patch(self, request, user_id=None):
        """
        Cập nhật thông tin Account
        
        ⚠️ Ghi AuditLog(action='UPDATE_ACCOUNT')
        """
        try:
            # Nếu có user_id từ URL, check admin permission
            if user_id:
                is_admin = request.user.account_roles.filter(
                    role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],  # ADMIN, MANAGER
                    is_deleted=False
                ).exists()
                if not is_admin:
                    return Response(
                        ResponseBuilder.error(message="Không có quyền cập nhật account khác"),
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                try:
                    User = get_user_model()
                    target_user = User.objects.get(id=user_id, is_deleted=False)
                except User.DoesNotExist:
                    return Response(
                        ResponseBuilder.error(message=f"Account {user_id} không tồn tại"),
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                update_user_id = user_id
                target_account = target_user
            else:
                # Update own account
                update_user_id = request.user.id
                target_account = request.user
            
            updated_user = self.user_service.update_account(update_user_id, request.data)
            
            # ⚠️ GHI AUDIT LOG (Roadmap: "Ghi AuditLog khi update account")
            try:
                from apps.operations.models import AuditLog
                action_desc = f"Admin {request.user.username} updated account {updated_user.username}" if user_id else f"User {request.user.username} updated own account"
                AuditLog.log_action(
                    account=request.user,
                    action='UPDATE_ACCOUNT',
                    resource_id=str(update_user_id),
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
    
    def delete(self, request, user_id=None):
        """
        Xóa account (Soft-delete)
        
        ⚠️ Ghi AuditLog(action='DEACTIVATE_ACCOUNT')
        """
        try:
            # Nếu có user_id từ URL, check admin permission
            if user_id:
                is_admin = request.user.account_roles.filter(
                    role_id__in=[RoleIds.ADMIN, RoleIds.MANAGER],  # ADMIN, MANAGER
                    is_deleted=False
                ).exists()
                if not is_admin:
                    return Response(
                        ResponseBuilder.error(message="Không có quyền xóa account khác"),
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                try:
                    User = get_user_model()
                    user = User.objects.get(id=user_id, is_deleted=False)
                except User.DoesNotExist:
                    return Response(
                        ResponseBuilder.error(message=f"Account {user_id} không tồn tại"),
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Delete own account
                user = request.user
            
            # Soft delete
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
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
                    data={"deleted_at": user.deleted_at}
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
            # Step 1: Extract & resolve department BEFORE serializer validation
            department_id = request.data.get('department_id')
            Department = apps.get_model('users', 'Department')
            department = None
            
            # Strategy 1: Nếu có department_id → tìm department (accept any string format)
            if department_id:
                try:
                    # Thử UUID trực tiếp
                    department = Department.objects.get(id=department_id, is_deleted=False)
                except (Department.DoesNotExist, ValueError):
                    # Không tìm được, return error
                    return Response(
                        ResponseBuilder.error(
                            message=f"Department '{department_id}' không tồn tại"
                        ),
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Strategy 2: Nếu không có department_id → tìm default company department  
            if not department:
                try:
                    department = Department.objects.filter(
                        parent_id__isnull=True,
                        is_deleted=False
                    ).first()
                    
                    if not department:
                        # Tạo default department
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
            
            # Step 2: Validate account fields via serializer (WITHOUT department)
            # Make a copy of request data without department_id
            data_for_serializer = request.data.copy()
            data_for_serializer.pop('department_id', None)
            # Don't pass department to serializer - it's not on Account model anymore
            
            serializer = AccountCreateSerializer(data=data_for_serializer)
            serializer.is_valid(raise_exception=True)
            
            # Step 3: Get or create the account
            from core.constants import RoleIds
            Role = apps.get_model('users', 'Role')
            
            try:
                default_role = Role.objects.get(id=RoleIds.USER)
            except Role.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message="Role mặc định không tồn tại"),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Call Service để tạo account
            validated_data = serializer.validated_data
            validated_data['department'] = department
            
            new_user = self.user_service.register_account(validated_data)
            
            # Step 4: Gán default role
            AccountRole = apps.get_model('users', 'AccountRole')
            AccountRole.objects.create(
                account=new_user,
                role=default_role,
                notes="Auto-assigned default user role"
            )
            logger.info(f"Default role {default_role.code} assigned to {new_user.username}")
            
            # Step 5: GHI AUDIT LOG
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
            User = get_user_model()
            
            # Get first non-deleted user with this email
            user = User.objects.filter(email=email, is_deleted=False).first()
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
            
            # Update password
            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])
            
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
        except Exception as e:
            logger.error(f"Reset password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminResetPasswordView(APIView):
    """
    POST /accounts/{id}/reset-password
    
    Admin reset password cho user mà không cần biết password cũ
    
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
        "message": "Mật khẩu của user đã được đặt lại",
        "data": {
            "user_id": 123,
            "email": "user@example.com",
            "notification_sent": true
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, id=None):
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
                    ResponseBuilder.error(message="Chỉ admin mới có quyền reset password cho user khác"),
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get target user
            if not id:
                return Response(
                    ResponseBuilder.error(message="User ID bắt buộc"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            User = get_user_model()
            try:
                target_user = User.objects.get(id=id, is_deleted=False)
            except User.DoesNotExist:
                return Response(
                    ResponseBuilder.error(message=f"User {id} không tồn tại"),
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
            
            # Update password
            target_user.set_password(new_password)
            target_user.save(update_fields=['password', 'updated_at'])
            
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
                        'notification_sent': notification_sent
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
        except Exception as e:
            logger.error(f"Admin reset password error: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(message=f"Lỗi: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
