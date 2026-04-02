"""
Request Logging Middleware
==========================
Adds request_id to all requests and logs request/response details

Features:
- Generate unique request_id (UUID) for each request
- Attach request_id to request object (request.request_id)
- Log request details (method, path, user)
- Log response details (status, duration)
- Attach request_id to response headers (X-Request-ID)

Usage:
    In settings.py:
    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        'core.middleware.RequestLoggingMiddleware',  # Add here
        ...
    ]

Result log:
    [2024-01-15 10:30:45] request_id=abc-123-def | GET /api/documents/ | user=john | status=200 | duration=45ms
"""

import logging
import uuid
import time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests with unique request_id
    
    Adds:
    - request.request_id (UUID)
    - X-Request-ID response header
    
    Logs:
    - Request: method, path, user, time
    - Response: status code, response time
    """
    
    def process_request(self, request):
        """
        Generate request_id and attach to request
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        
        # Store start time for duration calculation
        request._start_time = time.time()
        
        # Log request
        user_id = request.user.id if request.user and request.user.is_authenticated else 'anonymous'
        
        log_message = (
            f"request_id={request_id} | "
            f"{request.method} {request.path} | "
            f"user={user_id}"
        )
        
        # Include query params for GET requests
        if request.GET:
            log_message += f" | params={dict(request.GET)}"
        
        logger.info(log_message)
        
        return None
    
    def process_response(self, request, response):
        """
        Log response and attach request_id to headers
        """
        try:
            # Calculate request duration
            if hasattr(request, '_start_time'):
                duration_ms = (time.time() - request._start_time) * 1000
            else:
                duration_ms = 0
            
            # Get request_id
            request_id = getattr(request, 'request_id', 'unknown')
            
            # Log response
            log_message = (
                f"request_id={request_id} | "
                f"{request.method} {request.path} | "
                f"status={response.status_code} | "
                f"duration={duration_ms:.1f}ms"
            )
            
            # Log at appropriate level based on status code
            if 200 <= response.status_code < 300:
                logger.debug(log_message)
            elif 300 <= response.status_code < 400:
                logger.info(log_message)
            elif 400 <= response.status_code < 500:
                logger.warning(log_message)
            else:
                logger.error(log_message)
            
            # Attach request_id to response headers
            response['X-Request-ID'] = request_id
            
        except Exception as e:
            logger.error(f"Error in RequestLoggingMiddleware.process_response: {str(e)}")
        
        return response
    
    def process_exception(self, request, exception):
        """
        Log exceptions
        """
        try:
            request_id = getattr(request, 'request_id', 'unknown')
            
            logger.error(
                f"request_id={request_id} | "
                f"{request.method} {request.path} | "
                f"exception={exception.__class__.__name__}: {str(exception)}",
                exc_info=True
            )
        except Exception as e:
            logger.error(f"Error logging exception: {str(e)}")
        
        return None
