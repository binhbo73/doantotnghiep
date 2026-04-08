"""
Password Reset Utilities - Generate tokens, send emails, and verify tokens.
"""
import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.apps import apps

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service để xử lý password reset logic"""
    
    # Token expiration time (24 hours)
    TOKEN_EXPIRY_HOURS = 24
    
    # Token length
    TOKEN_LENGTH = 32
    
    @staticmethod
    def generate_reset_token(account, is_admin_action=False, generated_by=None) -> str:
        """
        Tạo password reset token mới cho account.
        
        Args:
            account: Account object
            is_admin_action: Boolean, if True => admin reset password
            generated_by: Admin Account object (if is_admin_action=True)
        
        Returns:
            str: Reset token
        
        Raises:
            Exception: If token creation fails
        """
        try:
            PasswordResetToken = apps.get_model('users', 'PasswordResetToken')
            
            # Generate random token
            token = secrets.token_urlsafe(PasswordResetService.TOKEN_LENGTH)
            
            # หา token ที่ไม่duplicate
            while PasswordResetToken.objects.filter(token=token).exists():
                token = secrets.token_urlsafe(PasswordResetService.TOKEN_LENGTH)
            
            # Calculate expiration
            expires_at = timezone.now() + timedelta(hours=PasswordResetService.TOKEN_EXPIRY_HOURS)
            
            # Create token record
            reset_token = PasswordResetToken.objects.create(
                account=account,
                token=token,
                expires_at=expires_at,
                is_admin_action=is_admin_action,
                generated_by=generated_by if is_admin_action else None
            )
            
            logger.info(
                f"Password reset token created for {account.email} "
                f"(admin_action={is_admin_action})"
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate password reset token: {str(e)}")
            raise
    
    @staticmethod
    def verify_reset_token(token: str):
        """
        Xác minh password reset token.
        
        Args:
            token: Reset token string
        
        Returns:
            Account object if token is valid, None otherwise
        
        Raises:
            PermissionError: Nếu token expired hoặc đã được sử dụng
        """
        try:
            PasswordResetToken = apps.get_model('users', 'PasswordResetToken')
            
            # Find token
            reset_token_obj = PasswordResetToken.objects.select_related('account').get(token=token)
            
            # Check if already used
            if reset_token_obj.is_used:
                raise PermissionError("Token đã được sử dụng rồi")
            
            # Check if expired
            if not reset_token_obj.is_valid():
                raise PermissionError("Token đã hết hạn (24 giờ)")
            
            return reset_token_obj.account
            
        except PasswordResetToken.DoesNotExist:
            logger.warning(f"Invalid password reset token attempted: {token[:10]}...")
            raise PermissionError("Token không hợp lệ")
        except Exception as e:
            logger.error(f"Failed to verify reset token: {str(e)}")
            raise
    
    @staticmethod
    def use_reset_token(token: str) -> bool:
        """
        Mark token as used sau khi reset password thành công.
        
        Args:
            token: Reset token string
        
        Returns:
            bool: True if success
        
        Raises:
            Exception: If token not found
        """
        try:
            PasswordResetToken = apps.get_model('users', 'PasswordResetToken')
            
            reset_token_obj = PasswordResetToken.objects.get(token=token)
            reset_token_obj.is_used = True
            reset_token_obj.used_at = timezone.now()
            reset_token_obj.save(update_fields=['is_used', 'used_at'])
            
            logger.info(f"Password reset token marked as used for {reset_token_obj.account.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark token as used: {str(e)}")
            raise
    
    @staticmethod
    def invalidate_all_tokens(account) -> int:
        """
        Vô hiệu hóa tất cả active tokens của account (khi admin reset).
        
        Args:
            account: Account object
        
        Returns:
            int: Số tokens bị vô hiệu hóa
        """
        try:
            PasswordResetToken = apps.get_model('users', 'PasswordResetToken')
            
            # Mark all active tokens as used
            count = PasswordResetToken.objects.filter(
                account=account,
                is_used=False
            ).update(is_used=True, used_at=timezone.now())
            
            logger.info(f"Invalidated {count} active reset tokens for {account.email}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to invalidate tokens: {str(e)}")
            raise
