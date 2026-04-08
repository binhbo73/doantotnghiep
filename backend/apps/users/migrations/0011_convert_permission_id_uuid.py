# Migration 0011 - Convert permission_id FK in role_permissions to UUID
# After migration 0008, the permission_id column stayed bigint despite permissions.id being UUID

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_convert_account_uuid'),
    ]

    operations = [
        # Step 1: Drop FK constraint to permissions (if it exists - it's missing as discovered)
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions DROP CONSTRAINT IF EXISTS role_permissions_permission_id_ad343843_fk_permissions_id CASCADE;",
        ),

        # Step 2: Add new UUID column
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions ADD COLUMN permission_id_new UUID;",
        ),

        # Step 3: Create UUID mapping for permissions table
        # Map old permission IDs to the new UUIDs
        migrations.RunSQL(
            sql='''UPDATE role_permissions rp 
                   SET permission_id_new = p.id 
                   FROM permissions p 
                   WHERE p.id::text::bigint = rp.permission_id;''',
        ),

        # Step 4: Drop old column and rename new one
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions DROP COLUMN permission_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions RENAME COLUMN permission_id_new TO permission_id;",
        ),

        # Step 5: Add FK constraint
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions ADD CONSTRAINT role_permissions_permission_id_ad343843_fk_permissions_id FOREIGN KEY (permission_id) REFERENCES permissions(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
    ]
