from __future__ import absolute_import

try:
    from celery import shared_task
except ImportError:
    shared_task = None
try:
    from celery.exceptions import SoftTimeLimitExceeded
except Exception:
    SoftTimeLimitExceeded = Exception

from django.apps import apps
from django.conf import settings
from django.utils import timezone
from services.document.chunk_summary_service import ChunkSummaryService


def _update_document_indexing_metadata(document_id: str, **updates):
    Document = apps.get_model('documents', 'Document')
    doc = Document.objects.get(id=document_id)
    metadata = doc.metadata or {}
    metadata.update(updates)
    doc.metadata = metadata
    doc.save(update_fields=['metadata', 'updated_at'])
    return doc

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


    @shared_task(
        bind=True,
        time_limit=getattr(settings, 'RAG_RAPTOR_TASK_TIME_LIMIT', 1800),
        soft_time_limit=getattr(settings, 'RAG_RAPTOR_TASK_SOFT_TIME_LIMIT', 1500),
    )
    def build_raptor_tree_task(self, document_id: str):
        """Celery task to build RAPTOR summaries after chunks/embeddings are persisted."""
        try:
            from services.ai.embedding_client import EmbeddingClient
            from services.ai.qdrant_client import QdrantClient
            from services.retrieval.raptor_tree import RaptorTreeBuilder

            _update_document_indexing_metadata(
                document_id,
                raptor_status='building',
                raptor_ready=False,
                raptor_started_at=timezone.now().isoformat(),
            )

            builder = RaptorTreeBuilder(
                embedding_client=EmbeddingClient(),
                qdrant_client=QdrantClient(),
            )
            nodes = builder.build_tree(str(document_id))
            node_count = len(nodes or [])
            _update_document_indexing_metadata(
                document_id,
                indexing_status='raptor_ready' if node_count else 'base_ready',
                raptor_status='ready' if node_count else 'skipped',
                raptor_ready=bool(node_count),
                raptor_node_count=node_count,
                raptor_ready_at=timezone.now().isoformat(),
            )
            return {
                'document_id': str(document_id),
                'status': 'completed',
                'summary_nodes': node_count,
            }
        except SoftTimeLimitExceeded:
            try:
                _update_document_indexing_metadata(
                    document_id,
                    raptor_status='timeout',
                    raptor_ready=False,
                    raptor_error='RAPTOR build exceeded soft time limit',
                    raptor_failed_at=timezone.now().isoformat(),
                )
            except Exception:
                pass
            return {
                'document_id': str(document_id),
                'status': 'timeout',
                'error': 'RAPTOR build exceeded soft time limit',
            }
        except Exception as e:
            try:
                _update_document_indexing_metadata(
                    document_id,
                    raptor_status='failed',
                    raptor_ready=False,
                    raptor_error=str(e)[:500],
                    raptor_failed_at=timezone.now().isoformat(),
                )
            except Exception:
                pass
            return {'document_id': str(document_id), 'status': 'failed', 'error': str(e)}
