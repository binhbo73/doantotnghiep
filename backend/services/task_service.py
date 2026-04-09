"""
Task Service - Quản lý các tác vụ xử lý ngầm (AsyncTask).
Theo dõi trạng thái: pending, running, completed, failed.

Pattern:
    ✅ CORRECT: Service → TaskRepository → ORM → Database
    ❌ NEVER: Service → ORM directly
"""
import logging
from typing import Optional, Any, Dict
from django.apps import apps
from django.utils import timezone
from core.exceptions import BusinessLogicError
from repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    """
    Quản lý lifecycle của một AsyncTask.
    Giúp Frontend có thể theo dõi tiến độ qua API.
    
    ✅ CORRECT DATA FLOW:
    View → TaskService → TaskRepository → ORM → AsyncTask Model
    """
    
    def __init__(self):
        """Initialize with TaskRepository (NOT ORM direct)"""
        self.task_repository = TaskRepository()

    def create_task(
        self, 
        task_type: str, 
        account_id: int, 
        document_id: int = None,
        metadata: Dict = None
    ) -> Any:
        """
        Tạo bản ghi tác vụ mới (pending)
        
        ✅ CORRECT: Calls Repository (not ORM)
        """
        return self.task_repository.create_task(
            task_type=task_type,
            account_id=account_id,
            document_id=document_id,
            metadata=metadata
        )

    def start_task(self, task_id: int) -> Any:
        """Đánh dấu bắt đầu chạy (running)"""
        return self.task_repository.start_task(task_id)

    def update_progress(self, task_id: int, percentage: int, message: str = None) -> Any:
        """Cập nhật tiến độ xử lý (0-100%)"""
        return self.task_repository.update_progress(task_id, percentage, message)

    def complete_task(self, task_id: int, result: Dict = None) -> Any:
        """Hoàn thành tác vụ (completed)"""
        return self.task_repository.complete_task(task_id, result)

    def fail_task(self, task_id: int, error_msg: str) -> Any:
        """Thất bại (failed) và ghi nhận nguyên nhân"""
        return self.task_repository.fail_task(task_id, error_msg)

    def get_task_status(self, task_id: int) -> Dict:
        """Lấy trạng thái hiện tại (dùng cho API polling)"""
        return self.task_repository.get_task_status(task_id)
