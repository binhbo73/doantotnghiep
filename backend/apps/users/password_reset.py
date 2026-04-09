"""
Password Reset Service - Business logic for password reset operations.

Uses PasswordResetTokenRepository for all ORM operations.
Service layer should NOT call ORM directly.
"""
import logging
from django.apps import apps

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service để xử lý password reset logic"""
    
    # Token expiration time (24 hours)
    TOKEN_EXPIRY_HOURS = 24
    
    # Token length
    TOKEN_LENGTH = 32
    
    @staticmethod
    def get_repository():
        """Get PasswordResetTokenRepository instance (lazy import to avoid circular deps)"""
        from repositories.password_reset_token_repository import PasswordResetTokenRepository
        return PasswordResetTokenRepository()
    
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
        
        ✅ Uses Repository - no ORM calls in Service layer
        """
        try:
            repo = PasswordResetService.get_repository()
            return repo.generate_token(
                account=account,
                is_admin_action=is_admin_action,
                generated_by=generated_by,
                token_length=PasswordResetService.TOKEN_LENGTH,
                expiry_hours=PasswordResetService.TOKEN_EXPIRY_HOURS
            )
            
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
        
        ✅ Uses Repository - no ORM calls in Service layer
        """
        try:
            repo = PasswordResetService.get_repository()
            reset_token_obj = repo.get_by_token(token)
            
            if not reset_token_obj:
                raise PermissionError("Token không hợp lệ")
            
            # Check if already used
            if reset_token_obj.is_used:
                raise PermissionError("Token đã được sử dụng rồi")
            
            # Check if expired
            if not reset_token_obj.is_valid():
                raise PermissionError("Token đã hết hạn (24 giờ)")
            
            return reset_token_obj.account
            
        except PermissionError:
            raise
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
        
        ✅ Uses Repository - no ORM calls in Service layer
        """
        try:
            repo = PasswordResetService.get_repository()
            return repo.mark_as_used(token)
            
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
        
        ✅ Uses Repository - no ORM calls in Service layer
        """
        try:
            repo = PasswordResetService.get_repository()
            return repo.invalidate_account_tokens(account)
            
        except Exception as e:
            logger.error(f"Failed to invalidate tokens: {str(e)}")
            raise
