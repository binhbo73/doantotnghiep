from __future__ import absolute_import
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.imports = ('services.document.tasks',)
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    return f'Request: {self.request!r}'
