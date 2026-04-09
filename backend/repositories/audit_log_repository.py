"""
AuditLogRepository - Specific queries for AuditLog model.
Centralized audit logging to replace scattered AuditLog.objects.create() calls.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from apps.operations.models import AuditLog
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class AuditLogRepository(BaseRepository):
    """
    Repository cho AuditLog model.
    
    Purpose:
    - Replace ALL direct AuditLog.objects.create() calls in services
    - Provide centralized audit logging with consistent error handling
    - Enable audit log filtering, archival, and search across entire system
    
    Usage:
    # OLD (WRONG): Service directly calls ORM
    AuditLog.objects.create(account=user, action='LOGIN', ...)
    
    # NEW (CORRECT): Service uses Repository
    audit_repo.log_action(account=user, action='LOGIN', ...)
    
    Key Usage:
    1. BaseService.audit_log_action() → calls AuditLogRepository.log_action()
    2. DocumentService audit logging → calls AuditLogRepository.log_action()
    3. PermissionService audit logging → calls AuditLogRepository.log_action()
    4. All custom audit logging → goes through this repository
    """
    
    model_class = AuditLog
    default_select_related = ['account']
    default_prefetch_related = []
    
    def log_action(
        self,
        account: Optional[Any] = None,
        action: str = '',
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        query_text: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
        status: str = 'success'
    ) -> bool:
        """
        Create audit log entry for an action.
        
        Args:
            account: User/Account performing the action (optional)
            action: Action code (e.g., 'LOGIN', 'UPDATE_PROFILE', 'DELETE_DOCUMENT')
            resource_id: ID of resource being acted upon
            resource_type: Type of resource (e.g., 'document', 'user', 'role')
            query_text: Human-readable description of action
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional metadata/context (dict)
            status: Action result (success, failed, pending)
        
        Returns:
            True if successful, False if failed
        
        Example:
            # In service
            self.audit_repo.log_action(
                account=user,
                action='CHANGE_PASSWORD',
                resource_id=None,
                query_text=f"User {user.username} changed password",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                status='success'
            )
        
        Note:
            - Never raises exceptions; logs errors and returns False
            - Designed for "fire and forget" audit logging
            - Thread-safe for concurrent use
            - Handles None values gracefully
        """
        try:
            # Prepare data - all fields optional
            log_data = {
                'account': account,
                'action': action or 'UNKNOWN',
                'resource_id': resource_id,
                'resource_type': resource_type,
                'query_text': query_text,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'details': details or {},
                'status': status,
            }
            
            # Remove None values for cleaner audit logs
            log_data = {k: v for k, v in log_data.items() if v is not None}
            
            # Create audit log
            self.create(**log_data)
            return True
            
        except Exception as e:
            # Never fail service logic for audit logging error
            logger.error(
                f"Failed to create audit log: action={action}, resource={resource_id}, error={e}",
                exc_info=True
            )
            return False
    
    def get_user_actions(self, account_id: str, limit: int = 100) -> list:
        """
        Get recent actions by user.
        
        Args:
            account_id: User/Account ID
            limit: Number of recent actions to return
        
        Returns:
            List of AuditLog entries ordered by newest first
        
        Example:
            actions = audit_repo.get_user_actions(user_id, limit=50)
        """
        try:
            return list(
                self.get_base_queryset()
                    .filter(account_id=account_id)
                    .order_by('-created_at')[:limit]
            )
        except Exception as e:
            logger.error(f"Error getting user actions: {e}")
            return []
    
    def get_resource_actions(self, resource_id: str, limit: int = 100) -> list:
        """
        Get all actions on a specific resource.
        
        Args:
            resource_id: Resource ID (document, account, role, etc.)
            limit: Number of actions to return
        
        Returns:
            List of AuditLog entries ordered by newest first
        """
        try:
            return list(
                self.get_base_queryset()
                    .filter(resource_id=resource_id)
                    .order_by('-created_at')[:limit]
            )
        except Exception as e:
            logger.error(f"Error getting resource actions: {e}")
            return []
    
    def get_action_history(self, action: str, limit: int = 100) -> list:
        """
        Get all occurrences of a specific action.
        
        Args:
            action: Action code (e.g., 'LOGIN', 'UPDATE_PROFILE')
            limit: Number of records to return
        
        Returns:
            List of AuditLog entries ordered by newest first
        """
        try:
            return list(
                self.get_base_queryset()
                    .filter(action=action)
                    .order_by('-created_at')[:limit]
            )
        except Exception as e:
            logger.error(f"Error getting action history: {e}")
            return []
    
    def get_failed_actions(self, limit: int = 100) -> list:
        """
        Get all failed actions (for security review).
        
        Args:
            limit: Number of failed actions to return
        
        Returns:
            List of failed AuditLog entries
        """
        try:
            return list(
                self.get_base_queryset()
                    .filter(status='failed')
                    .order_by('-created_at')[:limit]
            )
        except Exception as e:
            logger.error(f"Error getting failed actions: {e}")
            return []
