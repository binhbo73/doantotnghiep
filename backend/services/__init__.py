"""
Services Package
================
Business Logic Layer - orchestrates repositories, permissions, AI clients

Architecture:
    ViewSet → Service → Repository → Database
              ↓
         PermissionManager
              ↓
           Logging

Services use:
- Repositories for data access
- PermissionManager for ACL
- External clients (Llama, Qdrant)
- AuditLog for mutations
"""

from .base_service import BaseService
from .permission_service import PermissionService
from .document_service import DocumentService
from .user_service import UserService
from .task_service import TaskService
from .chat_service import ChatService

__all__ = [
    'BaseService',
    'PermissionService',
    'DocumentService',
    'UserService',
    'TaskService',
    'ChatService',
]
