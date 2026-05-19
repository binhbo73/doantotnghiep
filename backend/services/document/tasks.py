from __future__ import absolute_import

import logging
import os
import time

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
from django.db import close_old_connections
from django.utils import timezone
from services.document.chunk_summary_service import ChunkSummaryService

logger = logging.getLogger(__name__)


def _update_document_indexing_metadata(document_id: str, **updates):
    Document = apps.get_model('documents', 'Document')
    doc = Document.objects.get(id=document_id)
    metadata = doc.metadata or {}
    metadata.update(updates)
    doc.metadata = metadata
    doc.save(update_fields=['metadata', 'updated_at'])
    return doc


def _resolve_storage_path(storage_path: str) -> str:
    if not storage_path:
        return storage_path

    candidates = [storage_path]
    if not os.path.isabs(storage_path):
        candidates.extend([
            os.path.join(str(settings.MEDIA_ROOT), storage_path),
            os.path.join(str(settings.BASE_DIR), storage_path),
            os.path.join(str(settings.BASE_DIR.parent), storage_path),
        ])

    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if os.path.exists(normalized):
            return normalized

    return storage_path


def _mark_document_failed(document_id: str, error: str, **metadata_updates):
    Document = apps.get_model('documents', 'Document')
    try:
        document = Document.objects.get(id=document_id)
        metadata = document.metadata or {}
        metadata.update(metadata_updates)
        metadata['processing_error'] = str(error)[:1000]
        metadata['processing_failed_at'] = timezone.now().isoformat()
        document.status = 'failed'
        document.metadata = metadata
        document.save(update_fields=['status', 'metadata', 'updated_at'])
    except Exception:
        logger.exception("[DocumentTask] Failed to mark document %s as failed", document_id)


def _json_safe_metadata(metadata: dict) -> dict:
    return {
        key: value
        for key, value in (metadata or {}).items()
        if isinstance(value, (str, int, float, bool, list, dict)) or value is None
    }


def process_document_assets_for_document(document_id: str, task_id: str = None) -> dict:
    """Process image assets for a completed document without changing document.status."""
    start_time = time.monotonic()
    Document = apps.get_model('documents', 'Document')
    DocumentAsset = apps.get_model('documents', 'DocumentAsset')

    document = Document.objects.get(id=document_id)

    if not getattr(settings, 'ASSET_PIPELINE_ENABLED', True):
        _update_document_indexing_metadata(
            document_id,
            asset_status='not_required',
            asset_ready=False,
            asset_reason='disabled',
            asset_count=0,
        )
        return {
            'document_id': str(document_id),
            'status': 'not_required',
            'reason': 'disabled',
        }

    storage_path = _resolve_storage_path(document.storage_path)
    if not storage_path or not os.path.exists(storage_path):
        raise FileNotFoundError(f"Document file not found: {document.storage_path}")

    metadata_updates = {
        'asset_status': 'processing',
        'asset_ready': False,
        'asset_started_at': timezone.now().isoformat(),
    }
    if task_id:
        metadata_updates['asset_task_id'] = task_id
    _update_document_indexing_metadata(document_id, **metadata_updates)

    try:
        from services.ai.qdrant_client import QdrantClient

        QdrantClient().delete_asset_embeddings(str(document_id))
    except Exception as cleanup_error:
        logger.warning(
            "[AssetTask] Failed to delete old asset embeddings for %s: %s",
            document_id,
            cleanup_error,
        )

    try:
        DocumentAsset.objects.filter(document_id=document_id).update(
            is_deleted=True,
            deleted_at=timezone.now(),
        )
    except Exception as cleanup_error:
        logger.warning(
            "[AssetTask] Failed to soft-delete old assets for %s: %s",
            document_id,
            cleanup_error,
        )

    from services.pipeline.asset_stage import AssetPipelineStage
    from services.pipeline.base import PipelineContext
    from services.pipeline.stages import ParsingStage, ValidationStage

    context = PipelineContext(
        file_path=storage_path,
        document_id=str(document.id),
        user_id=str(document.uploader_id or ''),
        metadata={
            'source_name': document.original_name,
            'file_type': document.file_type,
            'uploader_id': str(document.uploader_id or ''),
            'embedding_model': getattr(settings, 'EMBEDDING_MODEL', document.embedding_model or ''),
        },
    )

    for stage in [
        ValidationStage(name='asset_validation'),
        ParsingStage(name='asset_parsing'),
        AssetPipelineStage(name='asset_extraction'),
    ]:
        if stage.can_skip(context):
            logger.info("[AssetTask] Skipping stage %s for document %s", stage.name, document_id)
            continue

        stage_start = time.monotonic()
        context = stage.execute(context)
        context.add_timing(stage.name, (time.monotonic() - stage_start) * 1000)
        context.stages_executed.append(stage.name)

    elapsed_ms = (time.monotonic() - start_time) * 1000
    result_metadata = _json_safe_metadata(context.metadata)
    asset_status = result_metadata.get('asset_status')
    asset_error = result_metadata.get('asset_error')
    asset_count = int(result_metadata.get('asset_count') or 0)

    if asset_error:
        final_status = 'failed'
    elif asset_status in {'ready', 'not_required'}:
        final_status = asset_status
    elif asset_count > 0:
        final_status = 'ready'
    else:
        final_status = 'not_required'

    final_updates = {
        **result_metadata,
        'asset_status': final_status,
        'asset_ready': final_status == 'ready',
        'asset_finished_at': timezone.now().isoformat(),
        'asset_pipeline_metrics_ms': elapsed_ms,
    }
    if final_status == 'failed':
        final_updates['asset_failed_at'] = timezone.now().isoformat()
    elif final_status == 'ready':
        final_updates['asset_ready_at'] = timezone.now().isoformat()

    _update_document_indexing_metadata(document_id, **final_updates)

    logger.info(
        "[AssetTask] Completed document %s status=%s assets=%s elapsed=%.1fms",
        document_id,
        final_status,
        asset_count,
        elapsed_ms,
    )

    return {
        'document_id': str(document_id),
        'status': final_status,
        'asset_count': asset_count,
        'elapsed_ms': elapsed_ms,
    }

if shared_task:
    @shared_task(
        bind=True,
        time_limit=getattr(settings, 'CELERY_TASK_TIME_LIMIT', 1800),
        soft_time_limit=getattr(settings, 'CELERY_TASK_SOFT_TIME_LIMIT', 1500),
    )
    def process_document_task(self, document_id: str):
        """Run the document ingest pipeline outside the upload request."""
        close_old_connections()
        start_time = time.monotonic()
        Document = apps.get_model('documents', 'Document')

        try:
            document = Document.objects.get(id=document_id)
            if document.status == 'completed':
                logger.info("[DocumentTask] Document %s already completed; skipping", document_id)
                return {
                    'document_id': str(document_id),
                    'status': 'skipped',
                    'reason': 'already_completed',
                }

            storage_path = _resolve_storage_path(document.storage_path)
            if not storage_path or not os.path.exists(storage_path):
                raise FileNotFoundError(f"Document file not found: {document.storage_path}")

            document.status = 'processing'
            document.metadata = document.metadata or {}
            document.metadata.update({
                'celery_task_id': self.request.id,
                'processing_dispatch': 'celery',
                'processing_started_at': timezone.now().isoformat(),
            })
            document.save(update_fields=['status', 'metadata', 'updated_at'])

            from services.document_upload_service import DocumentUploadService

            DocumentUploadService()._process_document(document, storage_path)
            document.refresh_from_db()

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "[DocumentTask] Completed document %s status=%s elapsed=%.1fms",
                document_id,
                document.status,
                elapsed_ms,
            )
            return {
                'document_id': str(document_id),
                'status': document.status,
                'elapsed_ms': elapsed_ms,
                'chunk_count': (document.metadata or {}).get('chunk_count'),
            }
        except SoftTimeLimitExceeded:
            _mark_document_failed(
                document_id,
                'Document processing exceeded soft time limit',
                celery_task_id=getattr(self.request, 'id', None),
            )
            raise
        except Exception as e:
            _mark_document_failed(
                document_id,
                str(e),
                celery_task_id=getattr(self.request, 'id', None),
            )
            logger.exception("[DocumentTask] Failed document %s: %s", document_id, e)
            raise
        finally:
            close_old_connections()


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
        time_limit=getattr(settings, 'ASSET_TASK_TIME_LIMIT', 1800),
        soft_time_limit=getattr(settings, 'ASSET_TASK_SOFT_TIME_LIMIT', 1500),
    )
    def process_document_assets_task(self, document_id: str):
        """Celery task for image extraction, OCR, VL captions, and asset embeddings."""
        close_old_connections()
        try:
            return process_document_assets_for_document(
                document_id=str(document_id),
                task_id=getattr(self.request, 'id', None),
            )
        except SoftTimeLimitExceeded:
            try:
                _update_document_indexing_metadata(
                    document_id,
                    asset_status='timeout',
                    asset_ready=False,
                    asset_error='Asset processing exceeded soft time limit',
                    asset_failed_at=timezone.now().isoformat(),
                    asset_task_id=getattr(self.request, 'id', None),
                )
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                _update_document_indexing_metadata(
                    document_id,
                    asset_status='failed',
                    asset_ready=False,
                    asset_error=str(e)[:500],
                    asset_failed_at=timezone.now().isoformat(),
                    asset_task_id=getattr(self.request, 'id', None),
                )
            except Exception:
                pass
            logger.exception("[AssetTask] Failed document %s: %s", document_id, e)
            raise
        finally:
            close_old_connections()


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
