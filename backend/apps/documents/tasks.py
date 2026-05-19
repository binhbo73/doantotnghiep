from __future__ import absolute_import, unicode_literals
from services.document.tasks import (
    build_raptor_tree_task,
    process_document_assets_task,
    process_document_task,
    summarize_chunk_task,
)

# Export tasks so celery autodiscover can find them
__all__ = (
    'process_document_task',
    'process_document_assets_task',
    'summarize_chunk_task',
    'build_raptor_tree_task',
)
