# Generated migration to convert AuditLog resource_id from UUID to CharField
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='resource_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='ID of affected resource (document/folder/user) - can be UUID or integer string',
                max_length=255,
                null=True
            ),
        ),
    ]
