import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_department_managers'),
    ]

    operations = [
        migrations.AddField(
            model_name='passwordresettoken',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='passwordresettoken',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='passwordresettoken',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name='passwordresettoken',
            index=models.Index(fields=['is_deleted'], name='users_passw_is_dele_4e21bc_idx'),
        ),
    ]
