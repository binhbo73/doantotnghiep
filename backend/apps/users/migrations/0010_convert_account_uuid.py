# Migration 0010 - Convert Account IDs from BigInt to UUID
# Use intermediate UUID columns with UUID generation via md5 mapping

from django.db import migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_fix_uuid_role_account'),
    ]

    operations = [
        # Step 1: Drop all FK constraints that reference accounts.id
        migrations.RunSQL(
            sql="ALTER TABLE account_roles DROP CONSTRAINT IF EXISTS account_roles_account_id_4e93ab4d_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles DROP CONSTRAINT IF EXISTS account_roles_granted_by_id_bd74608c_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_manager_id_326f7904_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions DROP CONSTRAINT IF EXISTS role_permissions_granted_by_id_efd9f563_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_account_id_a9cd56bd_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_generated_by_id_813b1fab_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE users DROP CONSTRAINT IF EXISTS users_account_id_b2e5bd98_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_account_id_b9a5f2e4_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_account_id_7af5bb85_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE human_feedback DROP CONSTRAINT IF EXISTS human_feedback_account_id_c89f3a2f_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE user_document_cache DROP CONSTRAINT IF EXISTS user_document_cache_account_id_6d688353_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_created_by_id_bc2c5343_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_uploader_id_a983b60c_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_groups DROP CONSTRAINT IF EXISTS accounts_groups_account_id_13c99fce_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user_permissions DROP CONSTRAINT IF EXISTS accounts_user_permissions_account_id_362b3798_fk_accounts_id CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_c564eba6_fk_accounts_id CASCADE;",
        ),

        # Step 2a: Create UUID mapping table to preserve account ID relationships
        migrations.RunSQL(
            sql='''CREATE TEMPORARY TABLE account_uuid_mapping AS 
                   SELECT id, gen_random_uuid() as new_id FROM accounts;'''
        ),

        # Step 2b: Add new UUID columns to FK tables
        migrations.RunSQL(
            sql="ALTER TABLE account_roles ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles ADD COLUMN granted_by_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE departments ADD COLUMN manager_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions ADD COLUMN granted_by_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens ADD COLUMN generated_by_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE users ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE conversations ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE human_feedback ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE user_document_cache ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tags ADD COLUMN created_by_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE documents ADD COLUMN uploader_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_groups ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user_permissions ADD COLUMN account_id_new UUID;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE django_admin_log ADD COLUMN user_id_new UUID;",
        ),

        # Step 3: Update new columns with values from mapping
        migrations.RunSQL(
            sql='''UPDATE account_roles ar SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE ar.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE account_roles ar SET granted_by_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE ar.granted_by_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE departments d SET manager_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE d.manager_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE role_permissions rp SET granted_by_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE rp.granted_by_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE password_reset_tokens prt SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE prt.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE password_reset_tokens prt SET generated_by_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE prt.generated_by_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE users u SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE u.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE audit_logs al SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE al.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE conversations c SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE c.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE human_feedback hf SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE hf.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE user_document_cache udc SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE udc.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE tags t SET created_by_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE t.created_by_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE documents d SET uploader_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE d.uploader_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE accounts_groups ag SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE ag.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE accounts_user_permissions aup SET account_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE aup.account_id = aum.id;'''
        ),
        migrations.RunSQL(
            sql='''UPDATE django_admin_log dal SET user_id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE dal.user_id = aum.id;'''
        ),

        # Step 4: Drop old columns and rename new ones
        migrations.RunSQL(
            sql="ALTER TABLE account_roles DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles DROP COLUMN granted_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles RENAME COLUMN granted_by_id_new TO granted_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE departments DROP COLUMN manager_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE departments RENAME COLUMN manager_id_new TO manager_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions DROP COLUMN granted_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions RENAME COLUMN granted_by_id_new TO granted_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens DROP COLUMN generated_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens RENAME COLUMN generated_by_id_new TO generated_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE users DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE users RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE conversations DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE conversations RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE human_feedback DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE human_feedback RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE user_document_cache DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE user_document_cache RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tags DROP COLUMN created_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tags RENAME COLUMN created_by_id_new TO created_by_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE documents DROP COLUMN uploader_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE documents RENAME COLUMN uploader_id_new TO uploader_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_groups DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_groups RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user_permissions DROP COLUMN account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user_permissions RENAME COLUMN account_id_new TO account_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE django_admin_log DROP COLUMN user_id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE django_admin_log RENAME COLUMN user_id_new TO user_id;",
        ),

        # Step 5: Convert accounts table itself
        migrations.RunSQL(
            sql="ALTER TABLE accounts ADD COLUMN id_new UUID;",
        ),
        migrations.RunSQL(
            sql='''UPDATE accounts a SET id_new = aum.new_id 
                   FROM account_uuid_mapping aum WHERE a.id = aum.id;'''
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts DROP CONSTRAINT accounts_pkey CASCADE;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts DROP COLUMN id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts RENAME COLUMN id_new TO id;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts ADD PRIMARY KEY (id);",
        ),

        # Step 6: Recreate all FK constraints with UUID type
        migrations.RunSQL(
            sql="ALTER TABLE account_roles ADD CONSTRAINT account_roles_account_id_4e93ab4d_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE account_roles ADD CONSTRAINT account_roles_granted_by_id_bd74608c_fk_accounts_id FOREIGN KEY (granted_by_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE departments ADD CONSTRAINT departments_manager_id_326f7904_fk_accounts_id FOREIGN KEY (manager_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE role_permissions ADD CONSTRAINT role_permissions_granted_by_id_efd9f563_fk_accounts_id FOREIGN KEY (granted_by_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens ADD CONSTRAINT password_reset_tokens_account_id_a9cd56bd_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE password_reset_tokens ADD CONSTRAINT password_reset_tokens_generated_by_id_813b1fab_fk_accounts_id FOREIGN KEY (generated_by_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE users ADD CONSTRAINT users_account_id_b2e5bd98_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_account_id_b9a5f2e4_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE conversations ADD CONSTRAINT conversations_account_id_7af5bb85_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE human_feedback ADD CONSTRAINT human_feedback_account_id_c89f3a2f_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE user_document_cache ADD CONSTRAINT user_document_cache_account_id_6d688353_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tags ADD CONSTRAINT tags_created_by_id_bc2c5343_fk_accounts_id FOREIGN KEY (created_by_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE documents ADD CONSTRAINT documents_uploader_id_a983b60c_fk_accounts_id FOREIGN KEY (uploader_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_groups ADD CONSTRAINT accounts_groups_account_id_13c99fce_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user_permissions ADD CONSTRAINT accounts_user_permissions_account_id_362b3798_fk_accounts_id FOREIGN KEY (account_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE django_admin_log ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_accounts_id FOREIGN KEY (user_id) REFERENCES accounts(id) DEFERRABLE INITIALLY DEFERRED;",
        ),
    ]
