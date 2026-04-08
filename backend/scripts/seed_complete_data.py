"""
Complete Seed Data Script with Test Accounts
Usage: python manage.py shell < scripts/seed_complete_data.py
OR: docker-compose exec backend python manage.py shell < scripts/seed_complete_data.py

This script creates:
1. Permissions (all resource:action combinations)
2. Departments (organizational hierarchy)
3. Roles (Admin, Manager, User)
4. Test Accounts (admin, manager, user accounts for testing)
5. Role Assignments
"""

from apps.users.models import Account, Role, Permission, RolePermission, AccountRole, Department, UserProfile
from core.constants import RoleIds
from django.utils import timezone
import uuid

print("\n" + "=" * 70)
print("🔄 COMPLETE DATABASE SEEDING")
print("=" * 70)

# ============================================================================
# 1. CREATE PERMISSIONS
# ============================================================================
print("\n📋 [1/5] CREATING PERMISSIONS...")

permissions_data = [
    # User Management
    ('user_create', 'Create User', 'users', 'create', 'Create new user account'),
    ('user_read', 'Read User', 'users', 'read', 'View user information'),
    ('user_update', 'Update User', 'users', 'update', 'Update user information'),
    ('user_delete', 'Delete User', 'users', 'delete', 'Delete user account'),
    ('user_change_role', 'Change User Role', 'users', 'change_role', 'Assign/remove roles from user'),
    ('user_change_status', 'Change User Status', 'users', 'change_status', 'Block/unblock user'),
    
    # Document Management
    ('document_create', 'Create Document', 'documents', 'create', 'Upload/create documents'),
    ('document_read', 'Read Document', 'documents', 'read', 'View document content'),
    ('document_update', 'Update Document', 'documents', 'update', 'Modify document'),
    ('document_delete', 'Delete Document', 'documents', 'delete', 'Delete documents'),
    ('document_share', 'Share Document', 'documents', 'share', 'Share document with others'),
    ('document_download', 'Download Document', 'documents', 'download', 'Download document files'),
    
    # Folder Management
    ('folder_create', 'Create Folder', 'folders', 'create', 'Create folders'),
    ('folder_read', 'Read Folder', 'folders', 'read', 'View folders'),
    ('folder_update', 'Update Folder', 'folders', 'update', 'Modify folders'),
    ('folder_delete', 'Delete Folder', 'folders', 'delete', 'Delete folders'),
    
    # Role & Permission Management
    ('permission_manage', 'Manage Permissions', 'permissions', 'manage', 'Create/edit permissions'),
    ('role_manage', 'Manage Roles', 'roles', 'manage', 'Create/edit roles'),
    
    # RAG & AI Features
    ('rag_query', 'Query RAG System', 'rag', 'query', 'Query documents via RAG'),
    ('embedding_generate', 'Generate Embeddings', 'embeddings', 'generate', 'Generate embeddings for documents'),
    ('chat_create', 'Create Chat', 'chat', 'create', 'Start chat conversation'),
    
    # Audit & System
    ('audit_log_view', 'View Audit Logs', 'audit', 'view', 'View system audit logs'),
    ('system_admin', 'System Administrator', 'system', 'admin', 'Full system access'),
]

created_perms = {}
for code, name, resource, action, description in permissions_data:
    perm, created = Permission.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'resource': resource,
            'action': action,
            'description': description
        }
    )
    created_perms[code] = perm
    if created:
        print(f"  ✅ {code}")

print(f"  → Total: {len(created_perms)} permissions ready")

# ============================================================================
# 2. CREATE ROLES WITH UUID
# ============================================================================
print("\n👥 [2/5] CREATING ROLES...")

roles_data = {
    'admin': {
        'name': 'Administrator',
        'description': 'Full system access - manage everything',
        'is_system_role': True,
        'permissions': [
            'system_admin', 'permission_manage', 'role_manage',
            'user_create', 'user_read', 'user_update', 'user_delete', 'user_change_role', 'user_change_status',
            'document_create', 'document_read', 'document_update', 'document_delete', 'document_share', 'document_download',
            'folder_create', 'folder_read', 'folder_update', 'folder_delete',
            'rag_query', 'embedding_generate', 'chat_create',
            'audit_log_view'
        ]
    },
    'manager': {
        'name': 'Manager',
        'description': 'Department manager - manage documents and team members',
        'is_system_role': True,
        'permissions': [
            'user_read', 'user_update',
            'document_create', 'document_read', 'document_update', 'document_delete', 'document_share', 'document_download',
            'folder_create', 'folder_read', 'folder_update', 'folder_delete',
            'rag_query', 'embedding_generate', 'chat_create'
        ]
    },
    'user': {
        'name': 'User',
        'description': 'Regular user - basic document and query access',
        'is_system_role': True,
        'permissions': [
            'document_read', 'document_create', 'document_download',
            'folder_read',
            'rag_query', 'chat_create'
        ]
    },
}

created_roles = {}
for code, role_info in roles_data.items():
    role, created = Role.objects.get_or_create(
        code=code,
        defaults={
            'name': role_info['name'],
            'description': role_info['description'],
            'is_system_role': role_info['is_system_role']
        }
    )
    created_roles[code] = role
    
    # Assign permissions to role
    for perm_code in role_info['permissions']:
        if perm_code in created_perms:
            RolePermission.objects.get_or_create(
                role=role,
                permission=created_perms[perm_code]
            )
    
    status = "✅ Created" if created else "⚠️  Exists"
    perm_count = len(role_info['permissions'])
    print(f"  {status}: {role.name} ({perm_count} permissions)")

# ============================================================================
# 3. CREATE DEPARTMENTS
# ============================================================================
print("\n🏢 [3/5] CREATING DEPARTMENTS...")

departments_data = [
    {'name': 'Công ty mẹ', 'description': 'Parent organization', 'parent': None},
    {'name': 'Phòng IT', 'description': 'IT Department', 'parent': 'Công ty mẹ'},
    {'name': 'Phòng HR', 'description': 'Human Resources', 'parent': 'Công ty mẹ'},
    {'name': 'Phòng Kinh doanh', 'description': 'Business Development', 'parent': 'Công ty mẹ'},
    {'name': 'Team Phát triển', 'description': 'Development Team', 'parent': 'Phòng IT'},
    {'name': 'Team QA', 'description': 'Quality Assurance Team', 'parent': 'Phòng IT'},
]

created_depts = {}
for dept_info in departments_data:
    parent_name = dept_info.get('parent')
    parent = created_depts.get(parent_name) if parent_name else None
    
    dept, created = Department.objects.get_or_create(
        name=dept_info['name'],
        defaults={
            'description': dept_info['description'],
            'parent': parent
        }
    )
    created_depts[dept_info['name']] = dept
    status = "✅ Created" if created else "⚠️  Exists"
    print(f"  {status}: {dept.name}")

# ============================================================================
# 4. CREATE TEST ACCOUNTS
# ============================================================================
print("\n👤 [4/5] CREATING TEST ACCOUNTS...")

test_accounts = [
    {
        'username': 'admin',
        'email': 'admin@example.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'password': 'admin123',
        'department': 'Công ty mẹ',
        'roles': ['admin'],
        'status': 'active'
    },
    {
        'username': 'manager1',
        'email': 'manager1@example.com',
        'first_name': 'Quản lý',
        'last_name': 'IT',
        'password': 'manager123',
        'department': 'Phòng IT',
        'roles': ['manager'],
        'status': 'active'
    },
    {
        'username': 'manager2',
        'email': 'manager2@example.com',
        'first_name': 'Quản lý',
        'last_name': 'HR',
        'password': 'manager123',
        'department': 'Phòng HR',
        'roles': ['manager'],
        'status': 'active'
    },
    {
        'username': 'user1',
        'email': 'user1@example.com',
        'first_name': 'Như Quân',
        'last_name': 'Phần Mềm',
        'password': 'user123',
        'department': 'Team Phát triển',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'user2',
        'email': 'user2@example.com',
        'first_name': 'Thái',
        'last_name': 'Test',
        'password': 'user123',
        'department': 'Team QA',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'user3',
        'email': 'user3@example.com',
        'first_name': 'Lâm',
        'last_name': 'Phân Tích',
        'password': 'user123',
        'department': 'Team Phát triển',
        'roles': ['user'],
        'status': 'active'
    },
]

created_accounts = {}
for acc_info in test_accounts:
    account, created = Account.objects.get_or_create(
        username=acc_info['username'],
        defaults={
            'email': acc_info['email'],
            'first_name': acc_info['first_name'],
            'last_name': acc_info['last_name'],
            'status': acc_info['status'],
            'is_staff': 'admin' in acc_info['roles'],
            'is_superuser': 'admin' in acc_info['roles'],
        }
    )
    
    if created:
        account.set_password(acc_info['password'])
        account.save()
    
    created_accounts[acc_info['username']] = account
    
    # Assign department via UserProfile
    if acc_info['username'] not in ['admin']:  # admin không cần department
        dept = created_depts.get(acc_info['department'])
        if dept:
            user_profile, _ = UserProfile.objects.get_or_create(
                account=account,
                defaults={
                    'full_name': f"{acc_info['first_name']} {acc_info['last_name']}",
                    'department': dept
                }
            )
            if not created and user_profile.department != dept:
                user_profile.department = dept
                user_profile.save()
    else:
        # Create UserProfile for admin without department
        UserProfile.objects.get_or_create(
            account=account,
            defaults={
                'full_name': f"{acc_info['first_name']} {acc_info['last_name']}"
            }
        )
    
    # Assign roles
    for role_code in acc_info['roles']:
        if role_code in created_roles:
            AccountRole.objects.get_or_create(
                account=account,
                role=created_roles[role_code],
                defaults={'granted_by': account}
            )
    
    status = "✅ Created" if created else "⚠️  Exists"
    roles_str = ', '.join(acc_info['roles'])
    print(f"  {status}: {acc_info['username']:15} ({roles_str:25}) - Pass: {acc_info['password']}")

# ============================================================================
# 5. SUMMARY & VERIFICATION
# ============================================================================
print("\n" + "=" * 70)
print("✅ SEEDING COMPLETE!")
print("=" * 70)

summary = {
    'Permissions': Permission.objects.filter(is_deleted=False).count(),
    'Roles': Role.objects.filter(is_deleted=False).count(),
    'Departments': Department.objects.filter(is_deleted=False).count(),
    'Accounts': Account.objects.filter(is_deleted=False).count(),
    'Account-Roles': AccountRole.objects.filter(is_deleted=False).count(),
}

print("\n📊 DATABASE SUMMARY:")
for key, count in summary.items():
    print(f"  • {key}: {count}")

print("\n🔐 TEST ACCOUNTS (for testing):")
print(f"  {'Username':<15} {'Email':<25} {'Password':<12} {'Role':<12}")
print(f"  {'-'*15} {'-'*25} {'-'*12} {'-'*12}")
for username, account in created_accounts.items():
    roles = account.get_roles().values_list('role__name', flat=True)
    role_str = ', '.join(roles) if roles else 'N/A'
    acc_info = next((a for a in test_accounts if a['username'] == username), None)
    if acc_info:
        print(f"  {username:<15} {acc_info['email']:<25} {acc_info['password']:<12} {role_str:<12}")

print("\n" + "=" * 70)
print("💡 READY FOR API TESTING!")
print("=" * 70 + "\n")
