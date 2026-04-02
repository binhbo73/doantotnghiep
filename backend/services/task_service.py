"""
Task Service - Quản lý các tác vụ xử lý ngầm (AsyncTask).
Theo dõi trạng thái: pending, running, completed, failed.
"""
import logging
from typing import Optional, Any, Dict
from django.apps import apps
from django.utils import timezone
from core.exceptions import BusinessLogicError

logger = logging.getLogger(__name__)


class TaskService:
    """
    Quản lý lifecycle của một AsyncTask.
    Giúp Frontend có thể theo dõi tiến độ qua API.
    """
    
    def __init__(self):
        self.AsyncTask = apps.get_model('operations', 'AsyncTask')

    def create_task(
        self, 
        task_type: str, 
        account_id: int, 
        document_id: int = None,
        metadata: Dict = None
    ) -> Any:
        """Tạo bản ghi tác vụ mới (pending)"""
        try:
            task = self.AsyncTask.objects.create(
                type=task_type,
                status='pending',
                account_id=account_id,
                document_id=document_id,
                metadata=metadata or {},
                progress_percentage=0
            )
            logger.info(f"Task created: {task_type} (ID: {task.id}) for Account {account_id}")
            return task
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise

    def start_task(self, task_id: int):
        """Đánh dấu bắt đầu chạy (running)"""
        task = self.AsyncTask.objects.get(pk=task_id)
        task.status = 'running'
        task.started_at = timezone.now()
        task.save()
        logger.debug(f"Task {task_id} started")

    def update_progress(self, task_id: int, percentage: int, message: str = None):
        """Cập nhật tiến độ xử lý (0-100%)"""
        task = self.AsyncTask.objects.get(pk=task_id)
        task.progress_percentage = min(100, max(0, percentage))
        if message:
            task.metadata['last_status_msg'] = message
        task.save()

    def complete_task(self, task_id: int, result: Dict = None):
        """Hoàn thành tác vụ (completed)"""
        task = self.AsyncTask.objects.get(pk=task_id)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.progress_percentage = 100
        if result:
            task.result_data = result
        task.save()
        logger.info(f"Task {task_id} completed successfully")

    def fail_task(self, task_id: int, error_msg: str):
        """Thất bại (failed) và ghi nhận nguyên nhân"""
        task = self.AsyncTask.objects.get(pk=task_id)
        task.status = 'failed'
        task.completed_at = timezone.now()
        task.error_message = error_msg
        task.save()
        logger.error(f"Task {task_id} failed: {error_msg}")

    def get_task_status(self, task_id: int) -> Dict:
        """Lấy trạng thái hiện tại (dùng cho API polling)"""
        task = self.AsyncTask.objects.get(pk=task_id)
        return {
            'id': task.id,
            'status': task.status,
            'progress': task.progress_percentage,
            'error': task.error_message,
            'is_finished': task.status in ['completed', 'failed']
        }
