"""
Auth Validation Middleware - Validate user status on every request.

Purpose:
- Check if authenticated user is still active (not blocked/deleted)
- Invalidate tokens for blocked/deleted users
- Return 401 if user no longer has access

This prevents blocked users from accessing API with old tokens.
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
import logging

logger = logging.getLogger(__name__)


class AuthValidationMiddleware(MiddlewareMixin):
    """
    Validate user status on every request.
    
    If user is authenticated (has JWT token):
    1. Check if user.is_deleted = True → 401
    2. Check if user.status = 'blocked' → 401
    3. Check if user.status = 'inactive' → 401
    4. Check if user.is_active = False → 401
    
    This ensures that even if a user has a valid JWT token,
    we re-validate their account status on every request.
    """
    
    def process_request(self, request):
        """
        Check user status before view is executed.
        Skip for unauthenticated requests and health checks.
        """
        
        # Skip unauthenticated requests
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        # Skip health check
        if request.path in ['/health', '/health/']:
            return None
        
        try:
            # Extract JWT token
            auth = JWTAuthentication()
            user_auth = auth.authenticate(request)
            
            if user_auth is None:
                return None
            
            user, validated_token = user_auth
            
            # ✅ Check 1: User not deleted
            if user.is_deleted:
                logger.warning(f"Deleted user {user.username} attempted access with token")
                return JsonResponse({
                    'success': False,
                    'status_code': 401,
                    'message': 'Account has been deleted'
                }, status=401)
            
            # ✅ Check 2: User account is active
            if not user.is_active:
                logger.warning(f"Inactive user {user.username} attempted access with token")
                return JsonResponse({
                    'success': False,
                    'status_code': 401,
                    'message': 'Account is not active'
                }, status=401)
            
            # ✅ Check 3: User status check (blocked or inactive)
            if hasattr(user, 'status'):
                if user.status == 'blocked':
                    logger.warning(f"Blocked user {user.username} attempted access with token")
                    return JsonResponse({
                        'success': False,
                        'status_code': 401,
                        'message': 'Account has been blocked'
                    }, status=401)
                
                if user.status == 'inactive':
                    logger.warning(f"Inactive user {user.username} attempted access with token")
                    return JsonResponse({
                        'success': False,
                        'status_code': 401,
                        'message': 'Account is inactive'
                    }, status=401)
            
            # ✅ All checks passed, allow request to continue
            return None
        
        except (InvalidToken, AuthenticationFailed):
            # Invalid token - let DRF's authentication handle it
            return None
        except Exception as e:
            # Log any unexpected errors but don't block the request
            logger.error(f"Error in AuthValidationMiddleware: {str(e)}", exc_info=True)
            return None
