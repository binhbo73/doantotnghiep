"""
Password Reset Token Repository - Data access layer for PasswordResetToken model.

Encapsulates all ORM operations for password reset tokens.
Used by PasswordResetService for business logic.
"""
import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PasswordResetTokenRepository(BaseRepository):
    """Repository for password reset token operations"""
    
    # Set model_class for BaseRepository
    model_class = None  # Will be set in __init__
    
    def __init__(self):
        from apps.users.models import PasswordResetToken
        self.model_class = PasswordResetToken
        super().__init__()
    
    def generate_token(self, account, is_admin_action=False, generated_by=None, token_length=32, expiry_hours=24):
        """
        Generate a new password reset token for account.
        
        Args:
            account: Account object
            is_admin_action: Boolean, if True => admin reset
            generated_by: Admin Account object (if is_admin_action=True)
            token_length: Length of token
            expiry_hours: Expiration time in hours
        
        Returns:
            str: Reset token
        
        Raises:
            Exception: If token creation fails
        """
        try:
            # Generate random token and ensure uniqueness
            token = secrets.token_urlsafe(token_length)
            while self.model_class.objects.filter(token=token).exists():
                token = secrets.token_urlsafe(token_length)
            
            # Calculate expiration
            expires_at = timezone.now() + timedelta(hours=expiry_hours)
            
            # Create token record
            reset_token = self.model_class.objects.create(
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
    
    def get_by_token(self, token):
        """
        Retrieve password reset token by token string.
        
        Args:
            token: Token string
        
        Returns:
            PasswordResetToken object or None
        """
        try:
            return self.model_class.objects.select_related('account').get(token=token)
        except self.model_class.DoesNotExist:
            logger.warning(f"Invalid password reset token: {token[:10]}...")
            return None
        except Exception as e:
            logger.error(f"Error retrieving reset token: {str(e)}")
            raise
    
    def mark_as_used(self, token):
        """
        Mark token as used after successful password reset.
        
        Args:
            token: Token string
        
        Returns:
            bool: True if success
        
        Raises:
            Exception: If token not found
        """
        try:
            reset_token_obj = self.model_class.objects.get(token=token)
            reset_token_obj.is_used = True
            reset_token_obj.used_at = timezone.now()
            reset_token_obj.save(update_fields=['is_used', 'used_at'])
            
            logger.info(f"Password reset token marked as used for {reset_token_obj.account.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark token as used: {str(e)}")
            raise
    
    def invalidate_account_tokens(self, account):
        """
        Invalidate all active tokens for an account (when admin resets).
        
        Args:
            account: Account object
        
        Returns:
            int: Number of tokens invalidated
        """
        try:
            # Mark all active tokens as used
            count = self.model_class.objects.filter(
                account=account,
                is_used=False
            ).update(is_used=True, used_at=timezone.now())
            
            logger.info(f"Invalidated {count} active reset tokens for {account.email}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to invalidate tokens: {str(e)}")
            raise
    
    def cleanup_expired_tokens(self):
        """
        Delete expired password reset tokens (optional cleanup).
        
        Returns:
            int: Number of tokens deleted
        """
        try:
            expired_count, _ = self.model_class.objects.filter(
                expires_at__lt=timezone.now()
            ).delete()
            
            logger.info(f"Cleaned up {expired_count} expired password reset tokens")
            return expired_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {str(e)}")
            raise
