"""
Core Decorators - Tập hợp các decorator dùng chung cho toàn hệ thống.
"""
from core.permissions.decorators import (
    require_permission,
    require_role,
    require_any_permission,
    require_all_permissions,
    require_ownership,
    require_department_access
)

__all__ = [
    'require_permission',
    'require_role',
    'require_any_permission',
    'require_all_permissions',
    'require_ownership',
    'require_department_access',
]
