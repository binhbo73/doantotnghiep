import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_document_version_lineage'),
        ('users', '0015_department_deletion_operation'),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderDeletionOperation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('snapshot', models.JSONField(default=dict)),
                (
                    'status',
                    models.CharField(
                        choices=[('deleted', 'Deleted'), ('restored', 'Restored')],
                        db_index=True,
                        default='deleted',
                        max_length=20,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('restored_at', models.DateTimeField(blank=True, null=True)),
                (
                    'deleted_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='folder_deletion_operations',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'root_folder',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='deletion_operations',
                        to='documents.folder',
                    ),
                ),
            ],
            options={
                'db_table': 'folder_deletion_operations',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='folderdeletionoperation',
            index=models.Index(fields=['root_folder', 'status'], name='folder_dele_root_fo_68adca_idx'),
        ),
        migrations.AddIndex(
            model_name='folderdeletionoperation',
            index=models.Index(fields=['created_at'], name='folder_dele_created_2453bd_idx'),
        ),
    ]
