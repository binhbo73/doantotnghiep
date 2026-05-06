"""
Clean Database Script - Xóa hết dữ liệu trước seed
Usage: python manage.py shell < scripts/clean_database.py
OR: docker-compose exec backend python manage.py shell < scripts/clean_database.py

Lưu ý: Xóa theo thứ tự foreign keys để tránh lỗi
"""

import os
import sys
import django

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.db import connection
from django.apps import apps

print("\n" + "=" * 80)
print("🗑️  CLEANING DATABASE - XÓA TẤT CẢ DỮ LIỆU")
print("=" * 80)

# Thứ tự xóa (tính đến foreign keys)
tables_to_delete = [
    # 1. Xóa tables có foreign keys đến account/role/department
    'account_roles',
    'role_permissions',
    'document_permissions',
    'folder_permissions',
    'user_document_cache',
    'document_embeddings',
    'document_chunks',
    'documents_tags',
    'conversations_attached_documents',
    'conversations_attached_folders',
    'messages',
    'conversations',
    'human_feedback',
    'password_reset_tokens',
    'async_tasks',
    'audit_logs',
    
    # 2. Xóa main tables
    'users',  # UserProfile table
    'documents',
    'folders',
    'tags',
    'permissions',
    'roles',
    'accounts',
    'departments',
    'users_company',
    
    # 3. Xóa auth tables
    'django_admin_log',
    'auth_group_permissions',
    'auth_group',
    'auth_permission',
    'django_session',
    'django_content_type',
]

with connection.cursor() as cursor:
    # Disable foreign key checks
    cursor.execute("SET session_replication_role = 'replica';")
    
    deleted_count = 0
    for table in tables_to_delete:
        try:
            # DELETE instead of TRUNCATE - keeps table structure, only removes data
            cursor.execute(f"DELETE FROM {table};")
            rows_deleted = cursor.rowcount
            deleted_count += 1
            print(f"  ✅ Cleared: {table:40} ({rows_deleted:5} rows deleted)")
        except Exception as e:
            print(f"  ⚠️  Skipped: {table:40} (not exist or error: {str(e)[:30]})")
    
    # Re-enable foreign key checks
    cursor.execute("SET session_replication_role = 'origin';")
    
    # Reset sequences (keep them but reset to 1)
    try:
        cursor.execute("""
            SELECT SETVAL('accounts_id_seq', 1, false);
        """)
        cursor.execute("""
            SELECT SETVAL('auth_permission_id_seq', 1, false);
        """)
        cursor.execute("""
            SELECT SETVAL('django_migrations_id_seq', 1, false);
        """)
    except:
        pass  # Some sequences might not exist
    
    connection.commit()

print(f"\n✅ Total tables cleared: {deleted_count}")

# Verify deletion
print("\n📊 VERIFYING DELETION...")

from apps.users.models import Account, Role, Permission, RolePermission, AccountRole, Department, UserProfile
from apps.documents.models import Document, Folder
from apps.operations.models import Conversation, Message

counts = {
    'Accounts': Account.objects.count(),
    'Departments': Department.objects.count(),
    'Roles': Role.objects.count(),
    'Permissions': Permission.objects.count(),
    'RolePermissions': RolePermission.objects.count(),
    'AccountRoles': AccountRole.objects.count(),
    'Users': UserProfile.objects.count(),
    'Documents': Document.objects.count(),
    'Folders': Folder.objects.count(),
    'Conversations': Conversation.objects.count(),
    'Messages': Message.objects.count(),
}

all_empty = True
for name, count in counts.items():
    status = "✅ Empty" if count == 0 else "⚠️  Still has data"
    print(f"  {status}: {name:20} = {count:5}")
    if count > 0:
        all_empty = False

print("\n" + "=" * 80)
if all_empty:
    print("✨ DATABASE CLEAN & READY FOR SEEDING")
else:
    print("⚠️  WARNING: Some tables still have data")
print("=" * 80 + "\n")
