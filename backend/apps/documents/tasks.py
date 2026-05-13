from __future__ import absolute_import, unicode_literals
from services.document.tasks import summarize_chunk_task

# Export tasks so celery autodiscover can find them
__all__ = ('summarize_chunk_task',)
