# Generated migration to remove department from Account

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),  # Adjust based on your latest migration
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='department',
        ),
    ]
