"""
Core Permissions Package
========================
ACL (Access Control Logic) for documents/folders
"""

from .permission_manager import PermissionManager, get_permission_manager

__all__ = [
    'PermissionManager',
    'get_permission_manager',
]
