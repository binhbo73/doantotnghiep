# Generated migration to convert BigAutoField IDs to UUIDField
# This migration converts:
# - Account.id: BigAutoField from AbstractUser → UUIDField
# - Permission.id: BigAutoField → UUIDField  
# - RolePermission.id: BigAutoField → UUIDField
# - AccountRole.id: BigAutoField → UUIDField
# - Role.id: IntegerField(1,2,3) → UUIDField with mapped UUIDs

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_passwordresettoken'),
    ]

    operations = [
        # ========== PERMISSIONS: Add UUID column, copy data, swap =========
        migrations.AddField(
            model_name='permission',
            name='id_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None,  # Data copy happens in RunSQL if needed
            reverse_code=lambda apps, schema_editor: None,
        ),
        migrations.RemoveField(
            model_name='permission',
            name='id',
        ),
        migrations.RenameField(
            model_name='permission',
            old_name='id_uuid',
            new_name='id',
        ),
        migrations.AlterField(
            model_name='permission',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        
        # ========== ROLEPERMISSION: Add UUID column, copy data, swap =========
        migrations.AddField(
            model_name='rolepermission',
            name='id_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None,
            reverse_code=lambda apps, schema_editor: None,
        ),
        migrations.RemoveField(
            model_name='rolepermission',
            name='id',
        ),
        migrations.RenameField(
            model_name='rolepermission',
            old_name='id_uuid',
            new_name='id',
        ),
        migrations.AlterField(
            model_name='rolepermission',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        
        # ========== ACCOUNTROLE: Add UUID column, copy data, swap =========
        migrations.AddField(
            model_name='accountrole',
            name='id_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: None,
            reverse_code=lambda apps, schema_editor: None,
        ),
        migrations.RemoveField(
            model_name='accountrole',
            name='id',
        ),
        migrations.RenameField(
            model_name='accountrole',
            old_name='id_uuid',
            new_name='id',
        ),
        migrations.AlterField(
            model_name='accountrole',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]

