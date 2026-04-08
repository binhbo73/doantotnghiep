# Seed data script
# Usage: docker compose exec backend python manage.py shell < scripts/seed_data.py

from apps.users.models import Account, Role, Permission, RolePermission
from django.utils import timezone

def seed_permissions():
    """Create all permission codes"""
    permissions_data = [
        # User
        ('user_create', 'Create User', 'users', 'create'),
        ('user_read', 'Read User', 'users', 'read'),
        ('user_update', 'Update User', 'users', 'update'),
        ('user_delete', 'Delete User', 'users', 'delete'),
        ('user_change_role', 'Change User Role', 'users', 'change_role'),
        # Document
        ('document_create', 'Create Document', 'documents', 'create'),
        ('document_read', 'Read Document', 'documents', 'read'),
        ('document_update', 'Update Document', 'documents', 'update'),
        ('document_delete', 'Delete Document', 'documents', 'delete'),
        ('document_share', 'Share Document', 'documents', 'share'),
        ('document_download', 'Download Document', 'documents', 'download'),
        # Folder
        ('folder_create', 'Create Folder', 'folders', 'create'),
        ('folder_read', 'Read Folder', 'folders', 'read'),
        ('folder_update', 'Update Folder', 'folders', 'update'),
        ('folder_delete', 'Delete Folder', 'folders', 'delete'),
        # Permissions & Roles
        ('permission_manage', 'Manage Permissions', 'permissions', 'manage'),
        ('role_manage', 'Manage Roles', 'roles', 'manage'),
        # RAG
        ('rag_query', 'Query RAG', 'rag', 'query'),
        ('embedding_generate', 'Generate Embeddings', 'embeddings', 'generate'),
        # Audit
        ('audit_log_view', 'View Audit Logs', 'audit', 'view'),
        ('system_admin', 'System Administrator', 'system', 'admin'),
    ]
    
    created = 0
    for code, name, resource, action in permissions_data:
        perm, created_flag = Permission.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'resource': resource,
                'action': action,
                'description': f'{name} permission'
            }
        )
        if created_flag:
            created += 1
    
    print(f"✅ Permissions: {created} created")
    return created

def seed_roles():
    """Create default roles"""
    roles_data = {
        1: {
            'code': 'admin',
            'name': 'Administrator',
            'description': 'Full system access',
            'is_system_role': True,
            'permissions': ['system_admin', 'permission_manage', 'role_manage', 'user_create', 'user_delete']
        },
        2: {
            'code': 'manager',
            'name': 'Manager',
            'description': 'Department manager',
            'is_system_role': True,
            'permissions': ['document_create', 'document_read', 'document_update', 'document_delete', 'user_read', 'folder_create', 'rag_query']
        },
        3: {
            'code': 'user',
            'name': 'User',
            'description': 'Regular user',
            'is_system_role': True,
            'permissions': ['document_read', 'document_create', 'document_download', 'folder_read', 'rag_query']
        },
    }
    
    for role_id, role_info in roles_data.items():
        role, created = Role.objects.get_or_create(
            id=role_id,
            defaults={
                'code': role_info['code'],
                'name': role_info['name'],
                'description': role_info['description'],
                'is_system_role': role_info['is_system_role']
            }
        )
        
        # Assign permissions
        for perm_code in role_info['permissions']:
            try:
                perm = Permission.objects.get(code=perm_code)
                RolePermission.objects.get_or_create(role=role, permission=perm)
            except Permission.DoesNotExist:
                print(f"⚠️  Permission not found: {perm_code}")
        
        status = "created" if created else "already exists"
        print(f"✅ Role {role.name}: {status}")

print("=" * 60)
print("SEEDING DATABASE")
print("=" * 60)

seed_permissions()
seed_roles()

print("=" * 60)
print("✅ SEEDING COMPLETE!")
print("=" * 60)

