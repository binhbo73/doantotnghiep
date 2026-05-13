from __future__ import absolute_import

try:
    from celery import shared_task
except ImportError:
    shared_task = None

from django.apps import apps
from services.document.chunk_summary_service import ChunkSummaryService

if shared_task:
    @shared_task(bind=True)
    def summarize_chunk_task(self, chunk_id: str, chunk_text: str, document_id: str = None):
        """Celery task to generate and persist chunk summary."""
        service = ChunkSummaryService()
        try:
            summary = service.generate_summary_sync(chunk_text)
            if summary:
                DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                chunk = DocumentChunk.objects.get(id=chunk_id)
                chunk.summary = summary
                chunk.save(update_fields=['summary', 'updated_at'])
                return {'chunk_id': chunk_id, 'status': 'completed'}
            return {'chunk_id': chunk_id, 'status': 'empty_summary'}
        except Exception as e:
            return {'chunk_id': chunk_id, 'status': 'failed', 'error': str(e)}
