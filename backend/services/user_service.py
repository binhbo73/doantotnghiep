"""
User Service - Nghiệp vụ quản lý Account và Profile.
Xử lý các thao tác về Tài khoản người dùng.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from django.apps import apps
from django.db import transaction
from core.exceptions import BusinessLogicError, ValidationError, InvalidCredentialsError
from services.base_service import BaseService
from repositories.user_repository import UserRepository
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """
    User Management Service - Logic cho Tài khoản
    """
    
    repository_class = UserRepository
    
    def __init__(self):
        super().__init__()  # BaseService will initialize repository from repository_class
        self.Account = apps.get_model('users', 'Account')
        self.UserProfile = apps.get_model('users', 'UserProfile')

    @transaction.atomic
    def register_account(self, account_data: Dict) -> Any:
        """Đăng ký tài khoản mới"""
        try:
            # Extract department before creating account (department is not on Account anymore)
            department = account_data.pop('department', None)
            password = account_data.pop('password')
            
            # Create account WITHOUT department (it's now on UserProfile)
            account = self.Account(**account_data)
            account.set_password(password)
            account.save()
            
            # Create UserProfile (1-1 relationship) with department
            try:
                profile_data = {
                    'account': account,
                    'full_name': account.get_full_name() or account.username,
                }
                if department:
                    profile_data['department'] = department
                
                self.UserProfile.objects.create(**profile_data)
                logger.info(f"UserProfile created for: {account.username}")
            except Exception as e:
                logger.error(f"Error creating UserProfile: {str(e)}")
                raise BusinessLogicError(f"Không thể tạo Profile: {str(e)}")
            
            logger.info(f"User registered: {account.username}")
            return account
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            raise BusinessLogicError(f"Đăng ký thất bại: {str(e)}")

    def change_password(self, user_id: int, old_password: str, new_password: str):
        """Đổi mật khẩu bảo mật (kiểm tra mật khẩu cũ)"""
        try:
            user = self.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id}: {str(e)}")
            raise ValidationError(f"Không thể lấy thông tin tài khoản: {str(e)}")
        
        if not user.check_password(old_password):
            raise ValidationError("Mật khẩu hiện tại không chính xác.")
        
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])
        logger.info(f"User {user_id} changed password successfully")

    def update_account(self, user_id: int, account_data: Dict) -> Any:
        """Cập nhật thông tin account của user"""
        # ⚠️ Unpack dict to kwargs vì BaseService.update(pk, **data)
        return self.update(user_id, **account_data)

    def deactivate_account(self, user_id: int):
        """Khóa tài khoản người dùng"""
        user = self.get_by_id(user_id)
        user.status = 'blocked'
        user.is_active = False # Django standard
        user.save()
        logger.warning(f"Account {user_id} blocked")

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Lấy danh sách tất cả mã permission của user (từ Role)"""
        user = self.get_by_id(user_id)
        return user.get_permissions() if hasattr(user, 'get_permissions') else []
    
    @transaction.atomic
    def authenticate(self, email_or_username: str, password: str) -> Tuple[Any, Dict[str, str]]:
        """
        Authenticate user (login)
        
        Args:
            email_or_username: User email or username
            password: User password (plaintext)
            
        Returns:
            (user, tokens_dict) where tokens_dict = {'access': ..., 'refresh': ...}
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        try:
            # Try to find user by email or username
            user = self.repository.get_by_email_or_username(email_or_username)
            
            if not user:
                logger.warning(f"Login attempt with non-existent user: {email_or_username}")
                raise InvalidCredentialsError("Email/username hoặc mật khẩu không chính xác")
            
            if not user.is_active:
                logger.warning(f"Login attempt with inactive user: {user.id}")
                raise ValidationError("Tài khoản không active")
            
            # Check password
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for user: {user.id}")
                raise InvalidCredentialsError("Email/username hoặc mật khẩu không chính xác")
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            tokens = {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
            
            logger.info(f"User {user.id} logged in successfully")
            return user, tokens
            
        except (InvalidCredentialsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}", exc_info=True)
            raise BusinessLogicError(f"Lỗi xác thực: {str(e)}")
