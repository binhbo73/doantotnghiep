# Test configuration
import os
import django
from django.conf import settings

def pytest_configure():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    django.setup()
