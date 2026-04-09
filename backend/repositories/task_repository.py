"""
Task Repository - Data access layer for AsyncTask model.

Responsibility:
- Create, read, update tasks
- Update task status and progress
- Track task lifecycle (pending → running → completed/failed)
"""
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.apps import apps
from repositories.base_repository import BaseRepository

import logging

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository):
    """
    Repository for AsyncTask model.
    
    Encapsulates all data access operations for background tasks.
    """
    
    model_class = None  # Will be set in __init__
    
    def __init__(self):
        """Initialize with AsyncTask model"""
        self.AsyncTask = apps.get_model('operations', 'AsyncTask')
        self.model_class = self.AsyncTask
        super().__init__()
    
    # ============================================================
    # TASK CREATION
    # ============================================================
    
    def create_task(
        self,
        task_type: str,
        account_id: int,
        document_id: int = None,
        metadata: Dict = None,
    ) -> 'AsyncTask':
        """
        Create new async task (pending status)
        
        Args:
            task_type: Type of task (e.g., 'document_processing')
            account_id: Account that created task
            document_id: Optional document ID
            metadata: Additional task metadata
        
        Returns:
            Created AsyncTask instance
        """
        try:
            task = self.create(
                type=task_type,
                account_id=account_id,
                document_id=document_id,
                status='pending',
                metadata=metadata or {},
                progress_percentage=0
            )
            logger.info(f"Task created: {task_type} (ID: {task.id}) for Account {account_id}")
            return task
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise
    
    # ============================================================
    # TASK RETRIEVAL
    # ============================================================
    
    def get_task_by_id(self, task_id: int) -> Optional['AsyncTask']:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
        
        Returns:
            AsyncTask instance or None
        """
        try:
            return self.get_by_id(task_id)
        except Exception:
            return None
    
    def get_user_tasks(
        self,
        account_id: int,
        status: str = None,
        limit: int = 100
    ) -> List['AsyncTask']:
        """
        Get all tasks for a specific user/account
        
        Args:
            account_id: Account ID
            status: Filter by status (pending, running, completed, failed)
            limit: Maximum results
        
        Returns:
            List of AsyncTask instances
        """
        filters = {'account_id': account_id}
        if status:
            filters['status'] = status
        
        return self.get_base_queryset().filter(**filters).order_by('-created_at')[:limit]
    
    def get_pending_tasks(self, limit: int = 50) -> List['AsyncTask']:
        """Get all pending tasks (for background worker)"""
        return self.get_base_queryset().filter(status='pending').order_by('created_at')[:limit]
    
    def get_running_tasks(self, limit: int = 50) -> List['AsyncTask']:
        """Get all running tasks"""
        return self.get_base_queryset().filter(status='running').order_by('-started_at')[:limit]
    
    # ============================================================
    # TASK STATUS UPDATES
    # ============================================================
    
    def start_task(self, task_id: int) -> 'AsyncTask':
        """
        Mark task as running
        
        Args:
            task_id: Task ID
        
        Returns:
            Updated AsyncTask instance
        """
        task = self.get_by_id(task_id)
        task.status = 'running'
        task.started_at = timezone.now()
        task.save(update_fields=['status', 'started_at'])
        logger.debug(f"Task {task_id} started")
        return task
    
    def update_progress(
        self,
        task_id: int,
        percentage: int,
        message: str = None
    ) -> 'AsyncTask':
        """
        Update task progress
        
        Args:
            task_id: Task ID
            percentage: Progress 0-100
            message: Optional status message
        
        Returns:
            Updated AsyncTask instance
        """
        task = self.get_by_id(task_id)
        task.progress_percentage = min(100, max(0, percentage))
        if message:
            metadata = task.metadata or {}
            metadata['last_status_msg'] = message
            task.metadata = metadata
        task.save(update_fields=['progress_percentage', 'metadata'])
        return task
    
    def complete_task(
        self,
        task_id: int,
        result: Dict = None
    ) -> 'AsyncTask':
        """
        Mark task as completed
        
        Args:
            task_id: Task ID
            result: Optional result data
        
        Returns:
            Updated AsyncTask instance
        """
        task = self.get_by_id(task_id)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.progress_percentage = 100
        if result:
            task.result_data = result
        task.save(update_fields=['status', 'completed_at', 'progress_percentage', 'result_data'])
        logger.info(f"Task {task_id} completed successfully")
        return task
    
    def fail_task(
        self,
        task_id: int,
        error_msg: str
    ) -> 'AsyncTask':
        """
        Mark task as failed with error message
        
        Args:
            task_id: Task ID
            error_msg: Error message/reason
        
        Returns:
            Updated AsyncTask instance
        """
        task = self.get_by_id(task_id)
        task.status = 'failed'
        task.completed_at = timezone.now()
        task.error_message = error_msg
        task.save(update_fields=['status', 'completed_at', 'error_message'])
        logger.error(f"Task {task_id} failed: {error_msg}")
        return task
    
    # ============================================================
    # TASK STATUS QUERIES
    # ============================================================
    
    def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """
        Get current task status for API response
        
        Args:
            task_id: Task ID
        
        Returns:
            Dict with status info: id, status, progress, error, is_finished
        """
        task = self.get_by_id(task_id)
        return {
            'id': task.id,
            'status': task.status,
            'progress': task.progress_percentage,
            'error': task.error_message,
            'is_finished': task.status in ['completed', 'failed']
        }
    
    def is_task_running(self, task_id: int) -> bool:
        """Check if task is currently running"""
        task = self.get_by_id(task_id)
        return task.status == 'running' if task else False
    
    def get_failed_tasks(self, limit: int = 50) -> List['AsyncTask']:
        """Get failed tasks for admin review"""
        return self.get_base_queryset().filter(status='failed').order_by('-completed_at')[:limit]
