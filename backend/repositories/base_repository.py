"""
BaseRepository - Abstract base class cho tất cả repositories.
Cung cấp generic CRUD methods + soft delete + pagination + optimization.

Mô hình:
- Tất cả query mặc định exclude is_deleted=True
- Tất cả delete() gọi soft delete (set is_deleted=True)
- Tất cả create/update tự động update timestamps
- Tất cả list queries support pagination
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Model, QuerySet, Q
from django.core.paginator import Paginator, Page
from core.exceptions import NotFoundError, ValidationError, DatabaseError
import logging


logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """
    Abstract base repository - implement generic CRUD operations.
    Subclasses phải override properties: model_class, default_select_related, default_prefetch_related
    """
    
    # Subclasses MUST override these
    model_class: Model = None
    default_select_related: List[str] = []  # FK/OneToOne relations để load cùng lúc
    default_prefetch_related: List[str] = []  # M2M/Reverse FK relations để prefetch
    
    def __init__(self):
        """Initialize repository"""
        if self.model_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'model_class'"
            )
    
    # ============================================================
    # BASE QUERYSET METHODS
    # ============================================================
    
    def get_base_queryset(self) -> QuerySet:
        """
        Get base queryset với default optimizations.
        Mặc định:
        - Exclude soft deleted records (is_deleted=False)
        - Apply select_related + prefetch_related
        """
        queryset = self.model_class.objects.filter(is_deleted=False)
        
        # Apply optimizations
        if self.default_select_related:
            queryset = queryset.select_related(*self.default_select_related)
        
        if self.default_prefetch_related:
            queryset = queryset.prefetch_related(*self.default_prefetch_related)
        
        return queryset
    
    def get_all_including_deleted(self) -> QuerySet:
        """Get tất cả records (cả deleted - admin only)"""
        queryset = self.model_class.objects.all()
        if self.default_select_related:
            queryset = queryset.select_related(*self.default_select_related)
        if self.default_prefetch_related:
            queryset = queryset.prefetch_related(*self.default_prefetch_related)
        return queryset
    
    # ============================================================
    # CREATE (CREATE)
    # ============================================================
    
    def create(self, **data) -> Model:
        """
        Create new record.
        
        Args:
            **data: Field values
        
        Returns:
            Created model instance
        
        Raises:
            ValidationError: If data invalid
            DatabaseError: If save failed
        
        Example:
            repo.create(name="John", email="john@example.com")
        """
        try:
            instance = self.model_class(**data)
            instance.full_clean()  # Validate before save
            instance.save()
            logger.info(
                f"Created {self.model_class.__name__} with id={instance.pk}",
                extra={"model": self.model_class.__name__}
            )
            return instance
        except ValidationError as e:
            logger.warning(f"Validation error during create: {e}")
            raise ValidationError(str(e), detail=e.error_list if hasattr(e, 'error_list') else [])
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create {self.model_class.__name__}")
    
    def bulk_create(self, data_list: List[Dict]) -> List[Model]:
        """
        Create multiple records efficiently.
        
        Args:
            data_list: List of dicts with field values
        
        Returns:
            List of created instances
        
        Note:
            - full_clean() không được gọi trên mỗi record (vì performance)
            - Don't use nếu validation quan trọng
        """
        try:
            instances = [self.model_class(**data) for data in data_list]
            created = self.model_class.objects.bulk_create(instances, batch_size=1000)
            logger.info(f"Bulk created {len(created)} {self.model_class.__name__} records")
            return created
        except Exception as e:
            logger.error(f"Error bulk creating {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to bulk create {self.model_class.__name__}")
    
    # ============================================================
    # READ (SELECT)
    # ============================================================
    
    def get_by_id(self, pk: Any) -> Model:
        """
        Get single record by primary key.
        
        Args:
            pk: Primary key value
        
        Returns:
            Model instance
        
        Raises:
            NotFoundError: If not found
        
        Example:
            user = repo.get_by_id(123)
        """
        try:
            return self.get_base_queryset().get(pk=pk)
        except self.model_class.DoesNotExist:
            raise NotFoundError(f"{self.model_class.__name__} with id={pk} not found")
        except Exception as e:
            logger.error(f"Error fetching {self.model_class.__name__} by id: {e}", exc_info=True)
            raise DatabaseError(f"Failed to fetch {self.model_class.__name__}")
    
    def get_by_filter(self, **filters) -> Optional[Model]:
        """
        Get single record by filter (returns first if multiple).
        
        Args:
            **filters: Django ORM filter kwargs
        
        Returns:
            Model instance or None
        
        Example:
            user = repo.get_by_filter(email="john@example.com")
        """
        try:
            return self.get_base_queryset().filter(**filters).first()
        except Exception as e:
            logger.error(f"Error fetching {self.model_class.__name__} by filter: {e}", exc_info=True)
            raise DatabaseError(f"Failed to fetch {self.model_class.__name__}")
    
    def list(self, **filters) -> List[Model]:
        """
        Get list of records matching filters.
        
        Args:
            **filters: Django ORM filter kwargs
        
        Returns:
            List of model instances
        
        Example:
            users = repo.list(status='active', department_id=dept_id)
        """
        try:
            queryset = self.get_base_queryset().filter(**filters)
            return list(queryset)
        except Exception as e:
            logger.error(f"Error listing {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to list {self.model_class.__name__}")
    
    def count(self, **filters) -> int:
        """
        Count records matching filters.
        
        Args:
            **filters: Django ORM filter kwargs
        
        Returns:
            Record count
        """
        try:
            return self.get_base_queryset().filter(**filters).count()
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to count {self.model_class.__name__}")
    
    def exists(self, **filters) -> bool:
        """
        Check if record exists matching filters.
        
        Args:
            **filters: Django ORM filter kwargs
        
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.get_base_queryset().filter(**filters).exists()
        except Exception as e:
            logger.error(f"Error checking existence: {e}", exc_info=True)
            return False
    
    # ============================================================
    # PAGINATE
    # ============================================================
    
    def paginate(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict] = None,
        ordering: Optional[str] = None,
    ) -> Tuple[List[Model], Page]:
        """
        Get paginated list of records.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            filters: Optional filter dict
            ordering: Optional ordering field (prefix - for desc)
        
        Returns:
            Tuple of (items_list, Page object)
        
        Example:
            items, page = repo.paginate(page=2, page_size=20, filters={'status': 'active'})
            print(page.paginator.count)  # Total count
            print(page.has_next)  # Is there next page?
        """
        try:
            queryset = self.get_base_queryset()
            
            # Apply filters
            if filters:
                queryset = queryset.filter(**filters)
            
            # Apply ordering
            if ordering:
                queryset = queryset.order_by(ordering)
            else:
                # Default ordering by -created_at if model has it
                if hasattr(self.model_class, 'created_at'):
                    queryset = queryset.order_by('-created_at')
            
            # Paginate
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            items = list(page_obj.object_list)
            
            logger.debug(
                f"Paginated {self.model_class.__name__}: page={page}, size={page_size}, total={paginator.count}"
            )
            
            return items, page_obj
        except Exception as e:
            logger.error(f"Error paginating {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to paginate {self.model_class.__name__}")
    
    # ============================================================
    # UPDATE
    # ============================================================
    
    def update(self, pk: Any, **data) -> Model:
        """
        Update single record by ID.
        
        Args:
            pk: Primary key
            **data: Fields to update
        
        Returns:
            Updated model instance
        
        Raises:
            NotFoundError: If not found
            DatabaseError: If update failed
        
        Example:
            user = repo.update(123, name="Jane", status="active")
        """
        try:
            instance = self.get_by_id(pk)
            
            # Update fields
            for field, value in data.items():
                setattr(instance, field, value)
            
            instance.full_clean()  # Validate before save
            instance.save()
            
            logger.info(
                f"Updated {self.model_class.__name__} with id={pk}",
                extra={"model": self.model_class.__name__}
            )
            
            return instance
        except (NotFoundError, ValidationError) as e:
            raise
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update {self.model_class.__name__}")
    
    def bulk_update(self, pk_data_list: List[Tuple[Any, Dict]]) -> List[Model]:
        """
        Update multiple records efficiently.
        
        Args:
            pk_data_list: List of (pk, update_dict) tuples
        
        Returns:
            List of updated instances
        
        Example:
            updates = [(1, {'status': 'inactive'}), (2, {'status': 'active'})]
            results = repo.bulk_update(updates)
        """
        try:
            updated_instances = []
            for pk, data in pk_data_list:
                instance = self.get_by_id(pk)
                for field, value in data.items():
                    setattr(instance, field, value)
                updated_instances.append(instance)
            
            # Bulk save
            self.model_class.objects.bulk_update(updated_instances, batch_size=1000)
            logger.info(f"Bulk updated {len(updated_instances)} {self.model_class.__name__} records")
            
            return updated_instances
        except Exception as e:
            logger.error(f"Error bulk updating {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to bulk update {self.model_class.__name__}")
    
    # ============================================================
    # DELETE (SOFT DELETE)
    # ============================================================
    
    def delete(self, pk: Any) -> bool:
        """
        Soft delete single record by ID.
        Sets is_deleted=True and deleted_at=now().
        
        Args:
            pk: Primary key
        
        Returns:
            True if deleted, False if already deleted
        
        Raises:
            NotFoundError: If not found
        
        Example:
            repo.delete(123)
        """
        try:
            instance = self.get_by_id(pk)
            instance.delete()  # Calls soft delete
            logger.info(
                f"Soft deleted {self.model_class.__name__} with id={pk}",
                extra={"model": self.model_class.__name__}
            )
            return True
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to delete {self.model_class.__name__}")
    
    def bulk_delete(self, pk_list: List[Any]) -> int:
        """
        Soft delete multiple records efficiently.
        
        Args:
            pk_list: List of primary keys
        
        Returns:
            Count of deleted records
        
        Example:
            count = repo.bulk_delete([1, 2, 3])
        """
        try:
            instances = self.get_base_queryset().filter(pk__in=pk_list)
            deleted_count = 0
            for instance in instances:
                instance.delete()
                deleted_count += 1
            
            logger.info(f"Bulk soft deleted {deleted_count} {self.model_class.__name__} records")
            return deleted_count
        except Exception as e:
            logger.error(f"Error bulk deleting {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to bulk delete {self.model_class.__name__}")
    
    def restore(self, pk: Any) -> Model:
        """
        Restore soft-deleted record (undo soft delete).
        
        Args:
            pk: Primary key
        
        Returns:
            Restored model instance
        
        Example:
            user = repo.restore(123)
        """
        try:
            # Get from all_records (including deleted)
            instance = self.get_all_including_deleted().get(pk=pk)
            instance.restore()
            logger.info(f"Restored {self.model_class.__name__} with id={pk}")
            return instance
        except self.model_class.DoesNotExist:
            raise NotFoundError(f"{self.model_class.__name__} with id={pk} not found")
        except Exception as e:
            logger.error(f"Error restoring {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to restore {self.model_class.__name__}")
    
    def hard_delete(self, pk: Any) -> bool:
        """
        Permanently delete record from database (use with caution!).
        
        Args:
            pk: Primary key
        
        Returns:
            True if deleted
        
        Note:
            - This is PERMANENT deletion
            - Use only for cleanup/archival
            - Prefer soft delete for normal operations
        """
        try:
            instance = self.get_all_including_deleted().get(pk=pk)
            instance.hard_delete()
            logger.warning(
                f"HARD deleted (permanent) {self.model_class.__name__} with id={pk}",
                extra={"model": self.model_class.__name__}
            )
            return True
        except self.model_class.DoesNotExist:
            raise NotFoundError(f"{self.model_class.__name__} with id={pk} not found")
        except Exception as e:
            logger.error(f"Error hard deleting {self.model_class.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to hard delete {self.model_class.__name__}")
