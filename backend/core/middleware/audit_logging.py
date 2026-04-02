"""
Audit Logging Middleware
=======================
Auto-logs all mutations (POST, PUT, PATCH, DELETE) to AuditLog model

Features:
- Intercepts POST/PUT/PATCH/DELETE requests
- Captures request data
- Logs to AuditLog model with:
  - account_id
  - action (CREATE, UPDATE, DELETE, UPLOAD, etc.)
  - resource_type (Document, User, Folder, etc.)
  - resource_id
  - query_text (description)
  - ip_address
  - user_agent
  - timestamp
- Handles DRF ViewSet actions
- Skips sensitive endpoints (like login, password change)

Usage:
    In settings.py:
    MIDDLEWARE = [
        'core.middleware.RequestLoggingMiddleware',
        'core.middleware.AuditLoggingMiddleware',  # After RequestLoggingMiddleware
        ...
    ]

Result:
    AuditLog entry created with full mutation details
"""

import logging
import json
from django.utils.deprecation import MiddlewareMixin
from django.apps import apps
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to auto-log all mutations to AuditLog
    
    Sensitivity:
    - Logs: POST, PUT, PATCH, DELETE methods
    - Skips: Login, password change, authentication endpoints
    - Attaches: request_id, user, IP, user_agent
    
    Performance:
    - Minimal overhead (early skip for safe methods)
    - Async logging in future (currently sync)
    """
    
    # HTTP methods that trigger audit logging
    AUDIT_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    # Paths to skip audit logging (authentication sensitive)
    SKIP_PATHS = {
        '/api/auth/login/',
        '/api/auth/logout/',
        '/api/auth/refresh/',
        '/api/auth/change-password/',
        '/api/users/change-password/',
        '/token/',
        '/token/refresh/',
    }
    
    def process_request(self, request: HttpRequest):
        """
        Store request body for later use (since it can only be read once)
        """
        if request.method in self.AUDIT_METHODS:
            try:
                # Store the body for later use in process_response
                if request.content_type and 'application/json' in request.content_type:
                    try:
                        request._body_data = json.loads(request.body)
                    except json.JSONDecodeError:
                        request._body_data = {}
                else:
                    request._body_data = {}
            except Exception as e:
                logger.debug(f"Error parsing request body: {str(e)}")
                request._body_data = {}
        
        return None
    
    def process_response(self, request: HttpRequest, response):
        """
        Log mutation to AuditLog after successful response
        """
        # Only audit mutation methods
        if request.method not in self.AUDIT_METHODS:
            return response
        
        # Skip sensitive paths
        if any(request.path.startswith(skip_path) for skip_path in self.SKIP_PATHS):
            return response
        
        # Only log successful mutations (status 200-399)
        if not (200 <= response.status_code < 400):
            return response
        
        # Only log if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return response
        
        try:
            self._log_audit(request, response)
        except Exception as e:
            logger.error(f"Error in audit logging: {str(e)}", exc_info=True)
        
        return response
    
    def _log_audit(self, request: HttpRequest, response):
        """
        Internal method to log audit entry
        """
        try:
            AuditLog = apps.get_model('operations', 'AuditLog')
        except LookupError:
            logger.debug("AuditLog model not found, skipping audit logging")
            return
        
        # Extract audit info from request
        action = self._get_action_from_method_path(request.method, request.path)
        resource_type, resource_id = self._extract_resource_from_path(request.path)
        request_id = getattr(request, 'request_id', None)
        
        # Build query_text (description)
        query_text = f"{request.method} {request.path}"
        if action:
            query_text = f"{action} {resource_type or 'Unknown'}"
        
        # Get IP address
        ip_address = self._get_client_ip(request)
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        
        # Create AuditLog entry
        try:
            audit_log = AuditLog(
                account=request.user,
                action=action or 'MUTATION',
                resource_type=resource_type or 'Unknown',
                resource_id=resource_id,
                query_text=query_text,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_data=getattr(request, '_body_data', {}),
                response_status=response.status_code,
            )
            audit_log.save()
            
            logger.debug(
                f"AuditLog created: {action} {resource_type} {resource_id} "
                f"by user {request.user.id}"
            )
            
        except Exception as e:
            logger.error(f"Error creating AuditLog: {str(e)}", exc_info=True)
    
    def _get_action_from_method_path(self, method: str, path: str) -> str:
        """
        Infer action from HTTP method and path
        
        Examples:
        - POST /api/documents/ → CREATE
        - POST /api/documents/1/upload-chunk/ → UPLOAD
        - PUT /api/documents/1/ → UPDATE
        - PATCH /api/documents/1/ → UPDATE
        - DELETE /api/documents/1/ → DELETE
        """
        if method == 'POST':
            if 'upload' in path.lower():
                return 'UPLOAD'
            elif 'create' in path.lower():
                return 'CREATE'
            elif 'import' in path.lower():
                return 'IMPORT'
            else:
                return 'CREATE'
        
        elif method in ('PUT', 'PATCH'):
            return 'UPDATE'
        
        elif method == 'DELETE':
            return 'DELETE'
        
        return 'MUTATION'
    
    def _extract_resource_from_path(self, path: str) -> tuple:
        """
        Extract resource type and ID from API path
        
        Examples:
        - /api/documents/ → (documents, None)
        - /api/documents/123/ → (documents, 123)
        - /api/users/45/roles/ → (roles, 45)
        - /api/folders/10/permissions/ → (permissions, 10)
        
        Returns:
            (resource_type, resource_id)
        """
        try:
            parts = path.strip('/').split('/')
            
            # Skip 'api' prefix
            if parts and parts[0] == 'api':
                parts = parts[1:]
            
            if not parts:
                return None, None
            
            # Resource type is usually the first meaningful part
            resource_type = parts[0] if parts else None
            
            # Resource ID might be in second position (if it exists and is numeric)
            resource_id = None
            if len(parts) > 1:
                # Check if it's a number or a UUID string
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                if parts[1].isdigit() or re.match(uuid_pattern, parts[1].lower()):
                    resource_id = parts[1]
            
            return resource_type, resource_id
            
        except Exception as e:
            logger.debug(f"Error extracting resource from path {path}: {str(e)}")
            return None, None
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Extract client IP address from request
        
        Handles:
        - X-Forwarded-For (proxy)
        - X-Real-IP (proxy)
        - REMOTE_ADDR (direct)
        """
        # X-Forwarded-For (used by proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get first IP (actual client)
            return x_forwarded_for.split(',')[0].strip()
        
        # X-Real-IP (alternative proxy header)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip
        
        # Direct connection
        remote_addr = request.META.get('REMOTE_ADDR', '')
        return remote_addr[:45]  # Limit to 45 chars (IP field length)
