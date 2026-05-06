"""
Production Seed Data Script with Proper Account-User Mapping
Usage: python manage.py shell < scripts/seed_production_data.py
OR: docker-compose exec backend python manage.py shell < scripts/seed_production_data.py

Requirements:
1. 11 Accounts (1 admin, 4 managers, 5 employees)
2. Account → creates User (UserProfile)
3. 3 Roles: admin, manager, user
4. 5 Departments: IT, HR, DevOps, Sale, Manager
5. Permissions mapped to real API endpoints
6. Role-Permission assignments

Chú ý: Each role has specific permissions based on actual backend APIs
"""

import os
import sys
import django

# Ensure Django settings are configured
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from apps.users.models import Account, Role, Permission, RolePermission, AccountRole, Department, UserProfile
from django.utils import timezone
import uuid

print("\n" + "=" * 80)
print("🌟 PRODUCTION DATABASE SEEDING - 11 ACCOUNTS WITH PROPER STRUCTURE")
print("=" * 80)

# ============================================================================
# 1. CREATE PERMISSIONS (From actual API endpoints)
# ============================================================================
print("\n📋 [STEP 1/5] CREATING PERMISSIONS (from APIs)...")

permissions_data = [
    # User Management APIs
    ('user_create', 'Create User', 'users', 'create', 'POST /api/users - Create new account'),
    ('user_read', 'Read User', 'users', 'read', 'GET /api/users - View user list and details'),
    ('user_update', 'Update User', 'users', 'update', 'PUT /api/users/{id} - Update user info'),
    ('user_delete', 'Delete User', 'users', 'delete', 'DELETE /api/users/{id} - Delete user account'),
    ('user_change_role', 'Change User Role', 'users', 'change_role', 'POST /api/users/{id}/roles - Assign/remove roles'),
    ('user_change_status', 'Change User Status', 'users', 'change_status', 'PATCH /api/users/{id}/status - Block/unblock user'),
    
    # Document Management APIs
    ('document_create', 'Create Document', 'documents', 'create', 'POST /api/documents - Upload/create documents'),
    ('document_read', 'Read Document', 'documents', 'read', 'GET /api/documents - View document list and content'),
    ('document_update', 'Update Document', 'documents', 'update', 'PUT /api/documents/{id} - Update document metadata'),
    ('document_delete', 'Delete Document', 'documents', 'delete', 'DELETE /api/documents/{id} - Delete documents'),
    ('document_share', 'Share Document', 'documents', 'share', 'POST /api/documents/{id}/share - Share with users/roles'),
    ('document_download', 'Download Document', 'documents', 'download', 'GET /api/documents/{id}/download - Download file'),
    ('document_write', 'Write Document', 'documents', 'write', 'Full document write access (includes update)'),
    
    # Folder Management APIs
    ('folder_create', 'Create Folder', 'folders', 'create', 'POST /api/folders - Create new folder'),
    ('folder_read', 'Read Folder', 'folders', 'read', 'GET /api/folders - View folder structure'),
    ('folder_update', 'Update Folder', 'folders', 'update', 'PUT /api/folders/{id} - Update folder'),
    ('folder_delete', 'Delete Folder', 'folders', 'delete', 'DELETE /api/folders/{id} - Delete folder'),
    
    # Department Management APIs
    ('department_read', 'Read Department', 'departments', 'read', 'GET /api/departments - View department list'),
    ('department_update', 'Update Department', 'departments', 'update', 'PUT /api/departments/{id} - Update department'),
    ('department_manage', 'Manage Department', 'departments', 'manage', 'Full department management'),
    
    # Permission & Role Management APIs
    ('permission_manage', 'Manage Permissions', 'permissions', 'manage', 'POST/DELETE /api/permissions - Create/edit permissions'),
    ('role_manage', 'Manage Roles', 'roles', 'manage', 'POST/PUT/DELETE /api/roles - Create/edit/delete roles'),
    
    # Chat & Conversation APIs
    ('chat_create', 'Create Chat', 'chat', 'create', 'POST /api/conversations - Start new chat'),
    ('chat_read', 'Read Chat', 'chat', 'read', 'GET /api/conversations - View conversations'),
    ('chat_send', 'Send Message', 'chat', 'send', 'POST /api/messages - Send chat message'),
    
    # RAG & AI Features APIs
    ('rag_query', 'Query RAG System', 'rag', 'query', 'POST /api/rag/query - Query documents with LLM'),
    ('embedding_generate', 'Generate Embeddings', 'embeddings', 'generate', 'POST /api/documents/{id}/embed - Generate vector embeddings'),
    
    # Audit & System APIs
    ('audit_log_view', 'View Audit Logs', 'audit', 'view', 'GET /api/audit-logs - View system activity logs'),
    ('system_admin', 'System Administrator', 'system', 'admin', 'Full system access - all permissions'),
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
        print(f"    ✅ {code:30} | {resource:15} | {action:20}")

print(f"  ✅ Total: {len(created_perms)} permissions created/verified")

# ============================================================================
# 2. CREATE ROLES WITH APPROPRIATE PERMISSIONS
# ============================================================================
print("\n👥 [STEP 2/5] CREATING 3 ROLES WITH PERMISSIONS...")

roles_data = {
    'admin': {
        'name': 'Administrator',
        'description': 'Full system access - manage everything',
        'is_system_role': True,
        'permissions': [
            # Admin can do everything
            'system_admin', 'permission_manage', 'role_manage',
            'user_create', 'user_read', 'user_update', 'user_delete', 'user_change_role', 'user_change_status',
            'document_create', 'document_read', 'document_update', 'document_delete', 'document_share', 'document_download', 'document_write',
            'folder_create', 'folder_read', 'folder_update', 'folder_delete',
            'department_read', 'department_update', 'department_manage',
            'chat_create', 'chat_read', 'chat_send',
            'rag_query', 'embedding_generate',
            'audit_log_view'
        ]
    },
    'manager': {
        'name': 'Manager',
        'description': 'Department manager - manage documents and team members',
        'is_system_role': True,
        'permissions': [
            # Managers can manage their team and documents
            'user_read', 'user_update', 'user_change_role',  # Manage team members
            'document_create', 'document_read', 'document_update', 'document_delete', 'document_share', 'document_download', 'document_write',
            'folder_create', 'folder_read', 'folder_update', 'folder_delete',
            'department_read',
            'chat_create', 'chat_read', 'chat_send',
            'rag_query', 'embedding_generate',
            'audit_log_view'
        ]
    },
    'user': {
        'name': 'User',
        'description': 'Regular user - basic document and query access',
        'is_system_role': True,
        'permissions': [
            # Regular users can only read and create basic items
            'user_read',  # Can see user list
            'document_read', 'document_create', 'document_download',  # Read and create
            'folder_read',
            'chat_create', 'chat_read', 'chat_send',
            'rag_query',  # Can query RAG
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
    perm_count = 0
    for perm_code in role_info['permissions']:
        if perm_code in created_perms:
            RolePermission.objects.get_or_create(
                role=role,
                permission=created_perms[perm_code]
            )
            perm_count += 1
    
    status = "✅ Created" if created else "⚠️  Updated"
    print(f"    {status}: {role.name:20} | {perm_count:3} permissions assigned")

print(f"  ✅ Total: {len(created_roles)} roles ready")

# ============================================================================
# 3. CREATE DEPARTMENTS (5 departments as required)
# ============================================================================
print("\n🏢 [STEP 3/5] CREATING 5 DEPARTMENTS...")

departments_data = [
    {'name': 'IT', 'code': 'it', 'description': 'Information Technology Department'},
    {'name': 'HR', 'code': 'hr', 'description': 'Human Resources Department'},
    {'name': 'DevOps', 'code': 'devops', 'description': 'DevOps & Infrastructure Department'},
    {'name': 'Sale', 'code': 'sale', 'description': 'Sales Department'},
    {'name': 'Manager', 'code': 'mgmt', 'description': 'Management Department'},
]

created_depts = {}
for dept_info in departments_data:
    dept, created = Department.objects.get_or_create(
        name=dept_info['name'],
        defaults={
            'description': dept_info['description'],
            'parent': None  # All departments are top-level
        }
    )
    created_depts[dept_info['name']] = dept
    status = "✅ Created" if created else "⚠️  Exists"
    print(f"    {status}: {dept.name:15} | {dept.description}")

print(f"  ✅ Total: {len(created_depts)} departments created")

# ============================================================================
# 4. CREATE 11 ACCOUNTS (1 Admin + 4 Managers + 5 Employees)
# ============================================================================
print("\n👤 [STEP 4/5] CREATING 11 ACCOUNTS WITH USER PROFILES...")

test_accounts = [
    # 1 ADMIN
    {
        'username': 'admin',
        'email': 'admin@company.com',
        'first_name': 'Tổng',
        'last_name': 'Quản Lý',
        'password': 'Admin@123456',
        'department': None,  # Admin không có department
        'roles': ['admin'],
        'status': 'active'
    },
    
    # 4 MANAGERS (1 per department, except Manager department)
    {
        'username': 'manager_it',
        'email': 'manager.it@company.com',
        'first_name': 'Quản Lý',
        'last_name': 'IT',
        'password': 'Manager@123456',
        'department': 'IT',
        'roles': ['manager'],
        'status': 'active'
    },
    {
        'username': 'manager_hr',
        'email': 'manager.hr@company.com',
        'first_name': 'Quản Lý',
        'last_name': 'HR',
        'password': 'Manager@123456',
        'department': 'HR',
        'roles': ['manager'],
        'status': 'active'
    },
    {
        'username': 'manager_devops',
        'email': 'manager.devops@company.com',
        'first_name': 'Quản Lý',
        'last_name': 'DevOps',
        'password': 'Manager@123456',
        'department': 'DevOps',
        'roles': ['manager'],
        'status': 'active'
    },
    {
        'username': 'manager_sale',
        'email': 'manager.sale@company.com',
        'first_name': 'Quản Lý',
        'last_name': 'Sale',
        'password': 'Manager@123456',
        'department': 'Sale',
        'roles': ['manager'],
        'status': 'active'
    },
    
    # 5 EMPLOYEES (distributed across 5 departments)
    {
        'username': 'employee_it_1',
        'email': 'emp.it1@company.com',
        'first_name': 'Nhân Viên',
        'last_name': 'IT 1',
        'password': 'Employee@123456',
        'department': 'IT',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'employee_hr_1',
        'email': 'emp.hr1@company.com',
        'first_name': 'Nhân Viên',
        'last_name': 'HR 1',
        'password': 'Employee@123456',
        'department': 'HR',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'employee_devops_1',
        'email': 'emp.devops1@company.com',
        'first_name': 'Nhân Viên',
        'last_name': 'DevOps 1',
        'password': 'Employee@123456',
        'department': 'DevOps',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'employee_sale_1',
        'email': 'emp.sale1@company.com',
        'first_name': 'Nhân Viên',
        'last_name': 'Sale 1',
        'password': 'Employee@123456',
        'department': 'Sale',
        'roles': ['user'],
        'status': 'active'
    },
    {
        'username': 'employee_mgmt_1',
        'email': 'emp.mgmt1@company.com',
        'first_name': 'Nhân Viên',
        'last_name': 'Manager 1',
        'password': 'Employee@123456',
        'department': 'Manager',
        'roles': ['user'],
        'status': 'active'
    },
]

created_accounts = {}
account_counter = {'total': 0, 'created': 0}

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
        account_counter['created'] += 1
    
    account_counter['total'] += 1
    created_accounts[acc_info['username']] = account
    
    # ========================================
    # CREATE USER PROFILE (Maps Account to Department)
    # ========================================
    dept = None
    if acc_info['department']:
        dept = created_depts.get(acc_info['department'])
    
    user_profile, profile_created = UserProfile.objects.get_or_create(
        account=account,
        defaults={
            'full_name': f"{acc_info['first_name']} {acc_info['last_name']}",
            'department': dept
        }
    )
    
    # Update profile if department changed
    if not profile_created and user_profile.department != dept:
        user_profile.department = dept
        user_profile.save()
    
    # ========================================
    # ASSIGN ROLES
    # ========================================
    for role_code in acc_info['roles']:
        if role_code in created_roles:
            AccountRole.objects.get_or_create(
                account=account,
                role=created_roles[role_code],
                defaults={'granted_by': account}
            )
    
    # Print account info
    status = "✅ Created" if created else "⚠️  Exists"
    dept_name = acc_info['department'] if acc_info['department'] else 'N/A'
    roles_str = ', '.join(acc_info['roles'])
    print(f"    {status}: {acc_info['username']:20} | Dept: {dept_name:15} | Role: {roles_str:15} | Pass: {acc_info['password']}")

print(f"  ✅ Total: {account_counter['total']} accounts ({account_counter['created']} created)")

# ============================================================================
# 5. VERIFY DATA
# ============================================================================
print("\n✅ [STEP 5/5] VERIFYING DATA...")

# Verify permissions
perm_count = Permission.objects.filter(is_deleted=False).count()
print(f"    📋 Permissions: {perm_count} total")

# Verify roles
role_count = Role.objects.filter(is_deleted=False).count()
role_perm_count = RolePermission.objects.filter(is_deleted=False).count()
print(f"    👥 Roles: {role_count} total | {role_perm_count} role-permission mappings")

# Verify departments
dept_count = Department.objects.filter(is_deleted=False).count()
print(f"    🏢 Departments: {dept_count} total")

# Verify accounts and profiles
account_count = Account.objects.filter(is_deleted=False).count()
profile_count = UserProfile.objects.filter(is_deleted=False).count()
account_roles = AccountRole.objects.filter(is_deleted=False).count()
print(f"    👤 Accounts: {account_count} total | User Profiles: {profile_count} | Account-Role mappings: {account_roles}")

# ============================================================================
# PRINT SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("✨ SEEDING COMPLETE!")
print("=" * 80)
print("""
📊 SUMMARY:
  • Permissions: All API-based permissions created
  • Roles: admin, manager, user (with appropriate permissions)
  • Departments: IT, HR, DevOps, Sale, Manager
  • Accounts: 11 total (1 admin + 4 managers + 5 employees)
  • User Profiles: Automatically created with department assignment

🔐 TEST CREDENTIALS:
  Admin:
    - Username: admin_tong
    - Password: Admin@123456

  Managers (1 per department):
    - manager_it / Manager@123456
    - manager_hr / Manager@123456
    - manager_devops / Manager@123456
    - manager_sale / Manager@123456

  Employees (5 total):
    - employee_it_1 / Employee@123456
    - employee_hr_1 / Employee@123456
    - employee_devops_1 / Employee@123456
    - employee_sale_1 / Employee@123456
    - employee_mgmt_1 / Employee@123456

📋 NOTE:
  ✓ Documents & Folders: You'll create these separately via API
  ✓ All permissions are mapped to actual backend APIs
  ✓ Role permissions are appropriate for each role
  ✓ Department hierarchy is flat (all departments are top-level)
""")
print("=" * 80 + "\n")
