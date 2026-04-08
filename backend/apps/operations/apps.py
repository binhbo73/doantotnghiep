from django.apps import AppConfig

class OperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Models explicitly use UUIDField
    name = 'apps.operations'
