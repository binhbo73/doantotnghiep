# Migration 0009 - Fix UUID conversions for Role and Account
# Migration 0008 was incomplete, so this fixes the remaining tables

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_bigint_to_uuid'),
    ]

    operations = [
        # Fix Roles table and related FKs - convert id from integer to UUID
        migrations.RunSQL(
            sql='''
                -- First, convert role_id in account_roles and role_permissions to UUID
                ALTER TABLE account_roles ADD COLUMN role_id_new UUID;
                ALTER TABLE role_permissions ADD COLUMN role_id_new UUID;
                
                -- Create mapping table to map old role IDs to new UUIDs
                -- Role IDs: 1->11111..., 2->22222..., 3->33333...
                UPDATE account_roles SET role_id_new = (
                    CASE role_id
                        WHEN 1 THEN '11111111-1111-1111-1111-111111111111'::uuid
                        WHEN 2 THEN '22222222-2222-2222-2222-222222222222'::uuid
                        WHEN 3 THEN '33333333-3333-3333-3333-333333333333'::uuid
                    END
                );
                UPDATE role_permissions SET role_id_new = (
                    CASE role_id
                        WHEN 1 THEN '11111111-1111-1111-1111-111111111111'::uuid
                        WHEN 2 THEN '22222222-2222-2222-2222-222222222222'::uuid
                        WHEN 3 THEN '33333333-3333-3333-3333-333333333333'::uuid
                    END
                );
                
                -- Drop old FK constraints
                ALTER TABLE account_roles DROP CONSTRAINT IF EXISTS account_roles_role_id_885a75d4_fk_roles_id;
                ALTER TABLE role_permissions DROP CONSTRAINT IF EXISTS role_permissions_role_id_216516f2_fk_roles_id;
                
                -- Drop old FK columns
                ALTER TABLE account_roles DROP COLUMN role_id;
                ALTER TABLE role_permissions DROP COLUMN role_id;
                
                -- Rename new columns
                ALTER TABLE account_roles RENAME COLUMN role_id_new TO role_id;
                ALTER TABLE role_permissions RENAME COLUMN role_id_new TO role_id;
                
                -- Make NOT NULL
                ALTER TABLE account_roles ALTER COLUMN role_id SET NOT NULL;
                ALTER TABLE role_permissions ALTER COLUMN role_id SET NOT NULL;
                
                -- Now convert roles table id
                ALTER TABLE roles ADD COLUMN id_new UUID;
                UPDATE roles SET id_new = (
                    CASE id
                        WHEN 1 THEN '11111111-1111-1111-1111-111111111111'::uuid
                        WHEN 2 THEN '22222222-2222-2222-2222-222222222222'::uuid
                        WHEN 3 THEN '33333333-3333-3333-3333-333333333333'::uuid
                    END
                );
                
                ALTER TABLE roles DROP CONSTRAINT roles_pkey CASCADE;
                ALTER TABLE roles DROP COLUMN id;
                ALTER TABLE roles RENAME COLUMN id_new TO id;
                ALTER TABLE roles ADD PRIMARY KEY (id);
                
                -- Recreate foreign keys
                ALTER TABLE account_roles 
                ADD CONSTRAINT account_roles_role_id_885a75d4_fk_roles_id 
                FOREIGN KEY (role_id) REFERENCES roles(id) DEFERRABLE INITIALLY DEFERRED;
                
                ALTER TABLE role_permissions 
                ADD CONSTRAINT role_permissions_role_id_216516f2_fk_roles_id 
                FOREIGN KEY (role_id) REFERENCES roles(id) DEFERRABLE INITIALLY DEFERRED;
            ''',
            reverse_sql='''
                -- Reverse not supported
            ''',
        ),
    ]
