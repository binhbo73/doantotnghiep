"""
Migration: Fix permission levels from 'admin' to 'delete' in DocumentPermission and FolderPermission

This migration updates:
1. DocumentPermission.permission choices: 'admin' → 'delete'
2. FolderPermission.permission choices: 'admin' → 'delete'
3. Data migration: Update existing 'admin' records to 'delete'
"""

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_alter_document_file_type_alter_document_mime_type'),
    ]

    operations = [
        # Update DocumentPermission field
        migrations.AlterField(
            model_name='documentpermission',
            name='permission',
            field=models.CharField(
                choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
                default='read',
                help_text='Permission level (read, write, delete)',
                max_length=50,
            ),
        ),
        
        # Update FolderPermission field
        migrations.AlterField(
            model_name='folderpermission',
            name='permission',
            field=models.CharField(
                choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
                default='read',
                help_text='Permission level (read, write, delete)',
                max_length=50,
            ),
        ),
        
        # Data migration: Convert existing 'admin' records to 'delete'
        migrations.RunPython(
            code=lambda apps, schema_editor: (
                apps.get_model('documents', 'DocumentPermission')
                .objects.filter(permission='admin', is_deleted=False)
                .update(permission='delete'),
                apps.get_model('documents', 'FolderPermission')
                .objects.filter(permission='admin', is_deleted=False)
                .update(permission='delete'),
                print("✅ Migrated 'admin' permissions to 'delete'"),
            ),
            reverse_code=lambda apps, schema_editor: (
                # Reverse: convert 'delete' back to 'admin'
                apps.get_model('documents', 'DocumentPermission')
                .objects.filter(permission='delete', is_deleted=False)
                .update(permission='admin'),
                apps.get_model('documents', 'FolderPermission')
                .objects.filter(permission='delete', is_deleted=False)
                .update(permission='admin'),
                print("⏮️  Reversed: migrated 'delete' permissions back to 'admin'"),
            ),
        ),
    ]
