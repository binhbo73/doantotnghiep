"""
AuditService - Centralized audit logging for all important actions
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
from repositories.audit_log_repository import AuditLogRepository
import logging
import json

logger = logging.getLogger(__name__)
User = get_user_model()


class AuditService:
    """
    Service for logging important system actions to AuditLog table.
    
    Actions to log:
    - LOGIN, LOGOUT
    - CREATE, UPDATE, DELETE (any resource)
    - CHANGE_ROLE
    - GRANT_ACL, REVOKE_ACL
    - UPLOAD, DOWNLOAD
    - QUERY
    
    Usage:
        audit_service = AuditService()
        audit_service.log(
            action='CREATE_DOCUMENT',
            account=request.user,
            resource_id=str(doc.id),
            resource_type='documents',
            metadata={'filename': doc.name}
        )
    """
    
    def __init__(self):
        self.repo = AuditLogRepository()
    
    def log(self, action: str, account, resource_id: str = None, 
            resource_type: str = None, query_text: str = None,
            metadata: dict = None, ip_address: str = None, user_agent: str = None,
            status: str = 'success', http_method: str = None, path: str = None,
            status_code: int = None):
        """
        Log an audit action to database.
        
        Args:
            action (str): Action type (e.g., 'CREATE_ROLE')
            account: User performing action
            resource_id (str): ID of affected resource
            resource_type (str): Type of affected resource (e.g., 'roles', 'documents')
            metadata (dict): Additional data (optional)
            ip_address (str): Client IP address (optional)
        
        Returns:
            AuditLog instance or None if error
        """
        try:
            from apps.operations.models import AuditLog
            
            # Create audit log entry (only pass valid fields accepted by AuditLog model)
            audit_log = AuditLog.objects.create(
                action=action,
                account=account,
                resource_id=resource_id,
                resource_type=resource_type,
                status=status,
                http_method=http_method,
                path=path,
                status_code=status_code,
                metadata=json.loads(json.dumps(metadata or {}, default=str)),
                query_text=query_text,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                f"Audit: {action} by {account.username} - "
                f"{resource_type}({resource_id})"
            )
            
            return audit_log
            
        except Exception as e:
            # Log errors but don't fail the main operation
            username = getattr(account, 'username', 'system')
            logger.error(
                f"Failed to create audit log: {str(e)} "
                f"(Action: {action}, User: {username})"
            )
            return None
    
    # Convenience methods for common actions
    
    def log_login(self, account, ip_address: str = None):
        """Log user login"""
        return self.log(
            action='LOGIN',
            account=account,
            ip_address=ip_address
        )
    
    def log_logout(self, account, ip_address: str = None):
        """Log user logout"""
        return self.log(
            action='LOGOUT',
            account=account,
            ip_address=ip_address
        )
    
    def log_role_change(self, account, user_id: str, old_roles: list, 
                       new_roles: list):
        """Log role assignment change"""
        return self.log(
            action='CHANGE_ROLE',
            account=account,
            resource_id=user_id,
            resource_type='accounts',
            metadata={
                'old_roles': old_roles,
                'new_roles': new_roles
            }
        )
    
    def log_permission_grant(self, account, resource_id: str, 
                            resource_type: str, subject_id: str,
                            subject_type: str, permission: str):
        """Log ACL permission grant"""
        return self.log(
            action='GRANT_ACL',
            account=account,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata={
                'subject_id': subject_id,
                'subject_type': subject_type,
                'permission': permission
            }
        )
    
    def log_permission_revoke(self, account, resource_id: str,
                             resource_type: str, subject_id: str,
                             subject_type: str):
        """Log ACL permission revoke"""
        return self.log(
            action='REVOKE_ACL',
            account=account,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata={
                'subject_id': subject_id,
                'subject_type': subject_type
            }
        )
    
    def log_upload(self, account, document_id: str, filename: str, size: int):
        """Log document upload"""
        return self.log(
            action='UPLOAD',
            account=account,
            resource_id=document_id,
            resource_type='documents',
            metadata={
                'resource_name': filename,
                'resource_label': f"Tài liệu: {filename}",
                'context_label': 'Tải lên tài liệu',
                'document_name': filename,
                'filename': filename,
                'size': size
            }
        )
    
    def log_download(self, account, document_id: str, filename: str):
        """Log document download"""
        return self.log(
            action='DOWNLOAD',
            account=account,
            resource_id=document_id,
            resource_type='documents',
            metadata={
                'resource_name': filename,
                'resource_label': f"Tài liệu: {filename}",
                'context_label': 'Tải xuống tài liệu',
                'document_name': filename,
                'filename': filename
            }
        )
    
    def log_query(self, account, query_text: str, result_count: int = 0):
        """Log semantic search / chat query"""
        return self.log(
            action='QUERY',
            account=account,
            metadata={
                'query': query_text,
                'result_count': result_count
            }
        )
