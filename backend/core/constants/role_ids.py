"""
Role IDs - Constants for role identifiers used throughout the system
"""


class RoleIds:
    """
    Fixed role IDs for system-defined roles.
    
    These are well-known role IDs that should be consistent across the system.
    Used for permission checks, decorators, etc.
    
    Example:
        @require_role([RoleIds.ADMIN])
        def delete(self, request):
            pass
    
    Note:
        These should match the roles created in database migrations.
        If roles are changed, update these constants.
    """
    
    # Common role codes (use these for code-based checks)
    ADMIN = 'admin'
    MANAGER = 'manager'
    USER = 'user'
    VIEWER = 'viewer'
    
    # Convenience lists
    ADMIN_ROLES = ['admin', 'manager']
    EDITOR_ROLES = ['admin', 'manager', 'user']
    ALL_ROLES = ['admin', 'manager', 'user', 'viewer']


# Alternative: If using UUID-based role IDs
class RoleUUIDs:
    """
    Fixed role UUIDs - use if roles are stored with fixed UUIDs.
    
    This pattern is useful when you need to reference roles by ID
    and want them to be consistent across environments.
    
    Example:
        # In migration, create role with explicit ID:
        Role.objects.create(
            id='550e8400-e29b-41d4-a716-446655440000',
            code='admin',
            name='Administrator'
        )
    
    Then reference:
        @require_role([RoleUUIDs.ADMIN_ID])
    """
    
    # Set these if your roles have fixed UUIDs
    ADMIN_ID = None  # Set to actual UUID if used
    MANAGER_ID = None
    USER_ID = None
    VIEWER_ID = None
