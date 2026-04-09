"""
Base Service Class
==================
Abstract base for all services

Pattern:
    class DocumentService(BaseService):
        repository_class = DocumentRepository
        
        def get_document(self, doc_id):
            doc = self.repository.get_by_id(doc_id)
            # Business logic here
            return doc
        
        def search_documents(self, query):
            results = self.repository.search(query)
            # Process results
            return results

Features:
- Auto-initializes repository
- Logging on all operations
- Exception handling
- Audit trail tracking
- Performance metrics (optional)
"""

import logging
from typing import Optional, List, Any, Tuple, Type
from django.apps import apps
from django.db.models import Model, QuerySet
from core.exceptions import NotFoundError, BusinessLogicError
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BaseService:
    """
    Abstract base service for business logic layer
    
    Responsibilities:
    1. Validate business rules
    2. Call repositories for data access
    3. Log operations
    4. Handle exceptions
    5. Return results
    
    Usage:
        class DocumentService(BaseService):
            repository_class = DocumentRepository
            
            def create_document(self, **kwargs):
                # Validate
                if not kwargs.get('original_name'):
                    raise ValidationError("name required")
                
                # Call repository
                doc = self.repository.create(**kwargs)
                
                # Log
                logger.info(f"Document created: {doc.id}")
                
                return doc
    """
    
    # Subclasses must define this
    repository_class: Optional[Type[BaseRepository]] = None
    
    def __init__(self):
        """Initialize service with repository"""
        if not self.repository_class:
            raise ValueError(
                f"{self.__class__.__name__} must define repository_class"
            )
        
        self.repository = self.repository_class()
        self.logger = logging.getLogger(f"services.{self.__class__.__name__}")
        
        # Initialize audit log repository for centralized audit logging
        # ALL services use this for audit trail (not ORM direct calls)
        from repositories.audit_log_repository import AuditLogRepository
        self.audit_log_repository = AuditLogRepository()
    
    # ============================================================================
    # COMMON OPERATIONS - Delegated to Repository
    # ============================================================================
    
    def get_by_id(self, pk: int) -> Model:
        """
        Get single item by ID
        
        Args:
            pk: Primary key
        
        Returns:
            Model instance
        
        Raises:
            NotFoundError: If not found
        """
        try:
            item = self.repository.get_by_id(pk)
            self.logger.debug(f"Retrieved item {pk}")
            return item
        except NotFoundError:
            self.logger.warning(f"Item {pk} not found")
            raise
        except Exception as e:
            self.logger.error(f"Error getting item {pk}: {str(e)}")
            raise
    
    def get_by_filter(self, **filters) -> Optional[Model]:
        """
        Get single item by filter
        
        Args:
            **filters: Filter kwargs (e.g., email='test@example.com')
        
        Returns:
            Model instance or None
        """
        try:
            item = self.repository.get_by_filter(**filters)
            if item:
                self.logger.debug(f"Retrieved item by filter: {filters}")
            return item
        except Exception as e:
            self.logger.error(f"Error getting item by filter {filters}: {str(e)}")
            return None
    
    def list(self, **filters) -> List[Model]:
        """
        List items with filters
        
        Args:
            **filters: Filter kwargs
        
        Returns:
            List of model instances
        """
        try:
            items = self.repository.list(**filters)
            self.logger.debug(f"Listed {len(items)} items with filters: {filters}")
            return items
        except Exception as e:
            self.logger.error(f"Error listing items: {str(e)}")
            return []
    
    def count(self, **filters) -> int:
        """
        Count items with filters
        
        Args:
            **filters: Filter kwargs
        
        Returns:
            Count
        """
        try:
            count = self.repository.count(**filters)
            self.logger.debug(f"Count: {count} items")
            return count
        except Exception as e:
            self.logger.error(f"Error counting items: {str(e)}")
            return 0
    
    def exists(self, **filters) -> bool:
        """
        Check if item exists with filters
        
        Args:
            **filters: Filter kwargs
        
        Returns:
            True if exists
        """
        try:
            exists = self.repository.exists(**filters)
            self.logger.debug(f"Item exists: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Error checking existence: {str(e)}")
            return False
    
    def create(self, **data) -> Model:
        """
        Create new item
        
        Args:
            **data: Item fields
        
        Returns:
            Created model instance
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            item = self.repository.create(**data)
            self.logger.info(f"Created item {item.id}")
            return item
        except Exception as e:
            self.logger.error(f"Error creating item: {str(e)}")
            raise
    
    def bulk_create(self, data_list: List[dict]) -> List[Model]:
        """
        Create multiple items
        
        Args:
            data_list: List of item field dicts
        
        Returns:
            List of created instances
        """
        try:
            items = self.repository.bulk_create(data_list)
            self.logger.info(f"Bulk created {len(items)} items")
            return items
        except Exception as e:
            self.logger.error(f"Error bulk creating items: {str(e)}")
            raise
    
    def update(self, pk: int, **data) -> Model:
        """
        Update item
        
        Args:
            pk: Primary key
            **data: Fields to update
        
        Returns:
            Updated model instance
        
        Raises:
            NotFoundError: If not found
        """
        try:
            item = self.repository.update(pk, **data)
            self.logger.info(f"Updated item {pk}")
            return item
        except NotFoundError:
            self.logger.warning(f"Item {pk} not found for update")
            raise
        except Exception as e:
            self.logger.error(f"Error updating item {pk}: {str(e)}")
            raise
    
    def bulk_update(self, updates: List[Tuple[int, dict]]) -> List[Model]:
        """
        Update multiple items
        
        Args:
            updates: List of (pk, data) tuples
        
        Returns:
            List of updated instances
        """
        try:
            items = self.repository.bulk_update(updates)
            self.logger.info(f"Bulk updated {len(items)} items")
            return items
        except Exception as e:
            self.logger.error(f"Error bulk updating items: {str(e)}")
            raise
    
    def delete(self, pk: int) -> bool:
        """
        Delete (soft) item
        
        Args:
            pk: Primary key
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If not found
        """
        try:
            result = self.repository.delete(pk)
            self.logger.info(f"Deleted item {pk}")
            return result
        except NotFoundError:
            self.logger.warning(f"Item {pk} not found for delete")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting item {pk}: {str(e)}")
            raise
    
    def bulk_delete(self, pks: List[int]) -> int:
        """
        Delete multiple items
        
        Args:
            pks: List of primary keys
        
        Returns:
            Number deleted
        """
        try:
            count = self.repository.bulk_delete(pks)
            self.logger.info(f"Bulk deleted {count} items")
            return count
        except Exception as e:
            self.logger.error(f"Error bulk deleting items: {str(e)}")
            raise
    
    def restore(self, pk: int) -> Model:
        """
        Restore (undo soft delete) item
        
        Args:
            pk: Primary key
        
        Returns:
            Restored instance
        """
        try:
            item = self.repository.restore(pk)
            self.logger.info(f"Restored item {pk}")
            return item
        except Exception as e:
            self.logger.error(f"Error restoring item {pk}: {str(e)}")
            raise
    
    def paginate(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: dict = None,
        ordering: str = None
    ) -> Tuple[List[Model], Any]:
        """
        Paginate items
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            filters: Filter kwargs
            ordering: Order by field (e.g., '-created_at')
        
        Returns:
            (items_list, page_object)
        """
        try:
            filters = filters or {}
            items, page_obj = self.repository.paginate(
                page=page,
                page_size=page_size,
                filters=filters,
                ordering=ordering
            )
            self.logger.debug(f"Paginated page {page} (size {page_size})")
            return items, page_obj
        except Exception as e:
            self.logger.error(f"Error paginating items: {str(e)}")
            raise
    
    # ============================================================================
    # LOGGING HELPERS
    # ============================================================================
    
    def log_action(
        self,
        action: str,
        resource_id: int = None,
        details: str = None,
        user_id: int = None
    ):
        """
        Log service action
        
        Args:
            action: Action name (e.g., 'CREATE', 'UPDATE', 'PROCESS')
            resource_id: Resource ID (optional)
            details: Additional details (optional)
            user_id: User ID (optional)
        
        Usage:
            self.log_action('PROCESS', doc_id, 'Started processing', user_id)
        """
        msg = f"{action}"
        if resource_id:
            msg += f" (ID: {resource_id})"
        if user_id:
            msg += f" [user: {user_id}]"
        if details:
            msg += f": {details}"
        
        self.logger.info(msg)
    
    def log_error(
        self,
        action: str,
        error: Exception,
        resource_id: int = None,
        user_id: int = None
    ):
        """
        Log error with context
        
        Args:
            action: Action that failed
            error: Exception instance
            resource_id: Resource ID (optional)
            user_id: User ID (optional)
        """
        msg = f"ERROR in {action}"
        if resource_id:
            msg += f" (ID: {resource_id})"
        if user_id:
            msg += f" [user: {user_id}]"
        msg += f": {str(error)}"
        
        self.logger.error(msg, exc_info=True)
    
    # ============================================================================
    # EXCEPTION HANDLING HELPERS
    # ============================================================================
    
    def ensure_exists(self, pk: int, message: str = None) -> Model:
        """
        Get item or raise NotFoundError
        
        Args:
            pk: Primary key
            message: Custom error message
        
        Returns:
            Model instance
        
        Raises:
            NotFoundError: If not found
        """
        try:
            return self.repository.get_by_id(pk)
        except NotFoundError:
            msg = message or f"Item {pk} not found"
            self.logger.warning(msg)
            raise NotFoundError(msg)
    
    def validate_business_rule(
        self,
        condition: bool,
        message: str
    ):
        """
        Validate business rule, raise if false
        
        Args:
            condition: Condition to check
            message: Error message if false
        
        Raises:
            BusinessLogicError: If condition is False
        
        Usage:
            self.validate_business_rule(
                doc.status == 'draft',
                "Document must be in draft status"
            )
        """
        if not condition:
            self.logger.warning(f"Business rule violated: {message}")
            raise BusinessLogicError(message)
    
    def audit_log_action(
        self,
        action: str,
        user_id: int = None,
        resource_id: str = None,
        resource_type: str = None,
        query_text: str = None,
        ip_address: str = None,
        user_agent: str = None,
        details: dict = None
    ) -> bool:
        """
        Log action to AuditLog model via Repository (NOT ORM direct call).
        
        Centralized audit logging for all services - avoids duplicating
        AuditLog.objects.create() calls everywhere.
        
        ✅ CORRECT: Uses AuditLogRepository
        ❌ NEVER: AuditLog.objects.create() direct ORM calls
        
        Args:
            action: Action name (LOGIN, CREATE_USER, UPDATE_ACCOUNT, etc.)
            user_id: User ID performing the action (optional)
            resource_id: ID of resource affected (optional)
            resource_type: Type of resource (User, Document, etc.) (optional)
            query_text: Description of action (optional)
            ip_address: Client IP (optional)
            user_agent: Client user agent (optional)
            details: Dict with additional details (optional)
        
        Returns:
            True if logged successfully, False otherwise
        
        Example:
            service.audit_log_action(
                action='CREATE_USER',
                user_id=request.user.id,
                resource_id=str(new_user.id),
                query_text=f"User {new_user.username} created",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        """
        try:
            # ✅ CORRECT: Use Repository for audit logging
            # Delegate to AuditLogRepository (single source of truth for audit logs)
            # Get account object if user_id provided
            account = None
            if user_id:
                account = self.repository.get_by_id(user_id) if hasattr(self, 'repository') else None
            
            return self.audit_log_repository.log_action(
                account=account,
                action=action,
                resource_id=str(resource_id) if resource_id else None,
                resource_type=resource_type,
                query_text=query_text,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {}
            )
        except Exception as e:
            self.logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
            # Don't raise - logging should never fail the main operation
            return False
    
    # ============================================================================
    # TEMPLATE METHODS - Override in subclasses
    # ============================================================================
    
    def before_create(self, **data):
        """
        Hook: called before create
        Override to add validation/transformation
        
        Args:
            **data: Fields to create
        
        Returns:
            Modified data dict
        
        Example:
            def before_create(self, **data):
                data['status'] = 'draft'  # Set default status
                return data
        """
        return data
    
    def after_create(self, item: Model):
        """
        Hook: called after create
        Override to do post-creation tasks
        
        Args:
            item: Created instance
        
        Example:
            def after_create(self, item):
                AuditLog.log_action(...)
                send_notification(...)
        """
        pass
    
    def before_update(self, pk: int, **data):
        """Hook: called before update"""
        return data
    
    def after_update(self, item: Model):
        """Hook: called after update"""
        pass
    
    def before_delete(self, pk: int):
        """Hook: called before delete"""
        pass
    
    def after_delete(self, pk: int):
        """Hook: called after delete"""
        pass
