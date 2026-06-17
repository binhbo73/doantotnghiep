import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_passwordresettoken_soft_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepartmentDeletionOperation',
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
                        related_name='department_deletion_operations',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'root_department',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='deletion_operations',
                        to='users.department',
                    ),
                ),
            ],
            options={
                'db_table': 'department_deletion_operations',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='departmentdeletionoperation',
            index=models.Index(fields=['root_department', 'status'], name='department__root_de_b510d1_idx'),
        ),
        migrations.AddIndex(
            model_name='departmentdeletionoperation',
            index=models.Index(fields=['created_at'], name='department__created_790a55_idx'),
        ),
    ]
