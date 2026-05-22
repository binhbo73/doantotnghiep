from __future__ import absolute_import
import os
import logging
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

logger = logging.getLogger(__name__)

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.imports = ('services.document.tasks',)
app.autodiscover_tasks()

@worker_ready.connect
def preload_embedding_on_worker_ready(sender=None, **kwargs):
    try:
        from django.conf import settings
        if not getattr(settings, 'EMBEDDING_PRELOAD_ENABLED', True):
            return
        app.send_task('services.document.tasks.warmup_embedding_model_task')
        logger.info("[EMBEDDING_WARMUP] queued celery warmup task")
    except Exception:
        logger.exception("[EMBEDDING_WARMUP] failed to queue celery warmup task")

@app.task(bind=True)
def debug_task(self):
    return f'Request: {self.request!r}'
