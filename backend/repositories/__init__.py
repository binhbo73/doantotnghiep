"""
Repository Layer - Data Access Abstraction Layer.
Tất cả database queries đi qua repository để:
1. Centralize soft delete logic
2. Optimize queries (select_related, prefetch_related)
3. Implement caching
4. Pagination support
"""
from .base_repository import BaseRepository
from .user_repository import UserRepository
from .document_repository import DocumentRepository
from .permission_repository import PermissionRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'DocumentRepository',
    'PermissionRepository',
]
