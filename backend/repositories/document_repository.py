"""
DocumentRepository - Specific queries for Document model.
Queries: search, filter by folder, by department, by status, etc.
"""
from typing import List, Optional, Dict, Tuple
from django.db.models import Q, Count, Prefetch
from apps.documents.models import Document, DocumentChunk, Folder
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository):
    """
    Repository cho Document model.
    Optimize queries: select_related + prefetch chunks
    """
    
    model_class = Document
    default_select_related = ['uploader', 'department', 'folder']  # FK
    default_prefetch_related = ['tags']  # M2M
    
    # ============================================================
    # DOCUMENT-SPECIFIC QUERIES
    # ============================================================
    
    def get_by_original_name(self, original_name: str) -> Optional[Document]:
        """
        Get document by original filename.
        
        Example:
            doc = repo.get_by_original_name("report.pdf")
        """
        try:
            return self.get_base_queryset().get(original_name=original_name)
        except Document.DoesNotExist:
            return None
    
    def list_by_folder(self, folder_id) -> List[Document]:
        """
        Get all documents in a folder.
        
        Example:
            docs = repo.list_by_folder(folder_id)
        """
        return self.list(folder_id=folder_id)
    
    def list_by_department(self, department_id) -> List[Document]:
        """
        Get all documents in a department.
        
        Example:
            docs = repo.list_by_department(dept_id)
        """
        return self.list(department_id=department_id)
    
    def list_by_uploader(self, user_id) -> List[Document]:
        """
        Get all documents uploaded by specific user.
        
        Example:
            docs = repo.list_by_uploader(user_id)
        """
        return self.list(uploader_id=user_id)
    
    def list_by_status(self, status: str) -> List[Document]:
        """
        Get documents by processing status (pending, processing, completed, failed).
        
        Example:
            completed = repo.list_by_status('completed')
        """
        return self.list(status=status)
    
    def search(self, query: str) -> List[Document]:
        """
        Search documents by original name or description.
        
        Example:
            results = repo.search("annual report")
        """
        try:
            queryset = self.get_base_queryset().filter(
                Q(original_name__icontains=query) |
                Q(description__icontains=query)
            )
            return list(queryset)
        except Exception as e:
            logger.error(f"Error searching documents: {e}", exc_info=True)
            return []
    
    def list_pending_processing(self) -> List[Document]:
        """
        Get documents pending embedding (status = pending or processing).
        
        Example:
            pending = repo.list_pending_processing()
        """
        try:
            queryset = self.get_base_queryset().filter(
                status__in=['pending', 'processing']
            ).order_by('created_at')
            return list(queryset)
        except Exception as e:
            logger.error(f"Error listing pending documents: {e}", exc_info=True)
            return []
    
    def list_failed_processing(self) -> List[Document]:
        """
        Get documents with failed embedding (for retry).
        
        Example:
            failed = repo.list_failed_processing()
        """
        return self.list(status='failed')
    
    # ============================================================
    # DOCUMENT WITH CHUNKS
    # ============================================================
    
    def get_document_with_chunks(self, doc_id) -> Optional[Document]:
        """
        Get document with all chunks loaded (optimized query).
        
        Example:
            doc = repo.get_document_with_chunks(doc_id)
            # doc.chunks.all() won't trigger additional query
        """
        try:
            queryset = self.get_base_queryset().prefetch_related(
                Prefetch(
                    'chunks',
                    queryset=DocumentChunk.objects.filter(is_deleted=False)
                )
            )
            return queryset.get(pk=doc_id)
        except Document.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting document with chunks: {e}", exc_info=True)
            return None
    
    def get_document_chunk_count(self, doc_id) -> int:
        """
        Get number of chunks for a document.
        
        Example:
            count = repo.get_document_chunk_count(doc_id)
        """
        try:
            return DocumentChunk.objects.filter(
                document_id=doc_id,
                is_deleted=False
            ).count()
        except Exception as e:
            logger.error(f"Error getting chunk count: {e}", exc_info=True)
            return 0
    
    # ============================================================
    # PERMISSIONS CHECK
    # ============================================================
    
    def check_user_can_read(self, doc_id, user_id) -> bool:
        """
        Check if user can read a document.
        Uses access_scope: personal/department/company.
        
        Example:
            can_read = repo.check_user_can_read(doc_id, user_id)
        """
        try:
            from apps.users.models import Account
            doc = self.get_by_id(doc_id)
            user = Account.objects.get(pk=user_id)
            
            # Check access scope
            if doc.access_scope == 'personal':
                return doc.uploader_id == user_id
            elif doc.access_scope == 'department':
                return doc.department_id == user.department_id
            else:  # company
                return True
        except Exception as e:
            logger.warning(f"Error checking document read access: {e}")
            return False
    
    def check_user_can_write(self, doc_id, user_id) -> bool:
        """
        Check if user can write/edit a document (owner only by default).
        
        Example:
            can_write = repo.check_user_can_write(doc_id, user_id)
        """
        try:
            doc = self.get_by_id(doc_id)
            return doc.uploader_id == user_id  # Only owner can edit
        except Exception as e:
            logger.warning(f"Error checking document write access: {e}")
            return False
    
    def check_user_can_delete(self, doc_id, user_id) -> bool:
        """
        Check if user can delete a document (owner or admin).
        
        Example:
            can_delete = repo.check_user_can_delete(doc_id, user_id)
        """
        try:
            from apps.users.models import Account, RoleIds
            doc = self.get_by_id(doc_id)
            user = Account.objects.get(pk=user_id)
            
            # Owner can delete
            if doc.uploader_id == user_id:
                return True
            
            # Admin can delete
            if user.has_role(RoleIds.ADMIN):
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking document delete access: {e}")
            return False
    
    # ============================================================
    # BULK OPERATIONS
    # ============================================================
    
    def mark_as_completed(self, doc_ids: List) -> int:
        """
        Mark multiple documents as successfully embedded.
        
        Example:
            count = repo.mark_as_completed([id1, id2, id3])
        """
        try:
            count = 0
            for doc_id in doc_ids:
                doc = self.get_by_id(doc_id)
                doc.status = 'completed'
                doc.save()
                count += 1
            
            logger.info(f"Marked {count} documents as completed")
            return count
        except Exception as e:
            logger.error(f"Error marking documents as completed: {e}", exc_info=True)
            return 0
    
    def mark_as_failed(self, doc_ids: List, error_message: str = None) -> int:
        """
        Mark multiple documents as failed during embedding.
        
        Example:
            count = repo.mark_as_failed([id1, id2], "Timeout after 30s")
        """
        try:
            count = 0
            for doc_id in doc_ids:
                doc = self.get_by_id(doc_id)
                doc.status = 'failed'
                if error_message:
                    doc.metadata['error'] = error_message
                doc.save()
                count += 1
            
            logger.warning(f"Marked {count} documents as failed: {error_message}")
            return count
        except Exception as e:
            logger.error(f"Error marking documents as failed: {e}", exc_info=True)
            return 0
    
    # ============================================================
    # STATISTICS
    # ============================================================
    
    def get_statistics(self, department_id: Optional[int] = None) -> Dict:
        """
        Get document statistics.
        
        Example:
            stats = repo.get_statistics(department_id=dept_id)
            # {
            #   'total': 100,
            #   'pending': 10,
            #   'processing': 5,
            #   'completed': 80,
            #   'failed': 5,
            #   'total_size_kb': 5000
            # }
        """
        from django.db.models import Sum
        try:
            queryset = self.get_base_queryset()
            
            if department_id:
                queryset = queryset.filter(department_id=department_id)
            
            stats = queryset.aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(status='pending')),
                processing=Count('id', filter=Q(status='processing')),
                completed=Count('id', filter=Q(status='completed')),
                failed=Count('id', filter=Q(status='failed')),
                total_size_bytes=Sum('file_size'),
            )
            
            # Convert to KB for backward compatibility or as requested
            stats['total_size_kb'] = (stats['total_size_bytes'] or 0) // 1024
            
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return {}
