"""
Pipeline Stages - Individual Processing Steps
==============================================

Each stage handles one responsibility:
1. ValidationStage - File validation
2. ParsingStage - Text extraction with page awareness
3. ChunkingStage - Splitting into chunks and embeddings
4. SummarizationStage - Generate chunk summaries
5. PersistenceStage - Save to DB and Qdrant
"""

import os
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone

from .base import PipelineStage, PipelineContext, StageExecutionError

logger = logging.getLogger(__name__)


class ValidationStage(PipelineStage):
    """Validate uploaded file."""
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.xlsx', '.csv'}
    MAX_FILE_SIZE_MB = 50
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Validate file type and size.
        
        Args:
            context: Pipeline context with file_path
        
        Returns:
            Updated context
        
        Raises:
            StageExecutionError: If validation fails
        """
        t_start = time.monotonic()
        file_path = context.file_path
        
        # Check file exists
        if not os.path.exists(file_path):
            raise StageExecutionError(f"File not found: {file_path}")
        
        # Check file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.ALLOWED_EXTENSIONS:
            raise StageExecutionError(
                f"File type {ext} not supported. "
                f"Allowed: {self.ALLOWED_EXTENSIONS}"
            )
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise StageExecutionError(
                f"File too large: {file_size_mb:.1f}MB "
                f"(max {self.MAX_FILE_SIZE_MB}MB)"
            )
        
        # Check read permissions
        if not os.access(file_path, os.R_OK):
            raise StageExecutionError(f"No read permission for file: {file_path}")
        
        context.metadata['file_extension'] = ext.lower()
        context.metadata['file_size_mb'] = round(file_size_mb, 2)
        
        self.logger.info(
            f"File validation passed: {file_size_mb:.2f}MB ({ext})"
        )
        self.logger.info(
            f"[UPLOAD_PROFILE] stage=validation document={context.document_id} "
            f"time={(time.monotonic() - t_start) * 1000:.1f}ms"
        )
        return context


class ParsingStage(PipelineStage):
    """Extract text from document with page awareness."""
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Parse document into text with page info.
        
        Args:
            context: Pipeline context with file_path
        
        Returns:
            Updated context with text_content
        
        Raises:
            StageExecutionError: If parsing fails
        """
        t_start = time.monotonic()
        try:
            from services.document.page_aware_parser import PageAwareParserEnhancer
            
            file_path = context.file_path
            file_ext = context.metadata.get('file_extension', '').lower()
            
            parser = PageAwareParserEnhancer()
            
            # Parse based on file type
            if file_ext == '.pdf':
                page_aware_text = parser.enhance_pdf(file_path)
            elif file_ext == '.docx':
                page_aware_text = parser.enhance_docx(file_path)
            elif file_ext == '.xlsx':
                page_aware_text = parser.enhance_excel(file_path)
            elif file_ext == '.csv':
                page_aware_text = parser.enhance_csv(file_path)
            else:
                page_aware_text = parser.enhance_text(file_path)
            
            if not page_aware_text or not getattr(page_aware_text, 'text', '').strip():
                raise StageExecutionError("Document contains no text")
            
            context.text_content = page_aware_text.text
            context.metadata['page_aware_text'] = page_aware_text
            context.metadata['page_count'] = getattr(page_aware_text, 'total_pages', 1)
            context.metadata['text_length'] = len(page_aware_text.text)
            context.metadata['parsed_at'] = datetime.now().isoformat()
            
            # Detailed logging
            page_count = context.metadata['page_count']
            text_length = context.metadata['text_length']
            word_count = len(page_aware_text.text.split()) if page_aware_text.text else 0
            self.logger.info(
                f"🚀 [PIPELINE START] Processing document: {os.path.basename(context.file_path)}\n"
                f"   📄 TOTAL PAGES DETECTED: {page_count} (Source of Truth)\n"
                f"   📝 Total length: {text_length} chars | {word_count} words\n"
                f"   📏 Strategy: {'RAPTOR (Hierarchical)' if page_count >= getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3) else 'FLAT (Standard)'}\n"
                f"   🔢 Document ID: {context.document_id}"
            )
            self.logger.info(
                f"[UPLOAD_PROFILE] stage=parsing document={context.document_id} "
                f"pages={page_count} chars={text_length} time={(time.monotonic() - t_start) * 1000:.1f}ms"
            )
            return context
        
        except StageExecutionError:
            raise
        except Exception as e:
            raise StageExecutionError(f"Parsing failed: {str(e)}") from e


class ChunkingStage(PipelineStage):
    """Split text into chunks with embeddings."""
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Chunk document and generate embeddings.
        
        Args:
            context: Pipeline context with text_content
        
        Returns:
            Updated context with chunks and embeddings
        
        Raises:
            StageExecutionError: If chunking fails
        """
        t_start = time.monotonic()
        try:
            from services.document.enhanced_chunker import (
                EnhancedDocumentChunker
            )
            from services.ai.embedding_client import EmbeddingClient
            from services.ai.qdrant_client import QdrantClient
            
            text = context.text_content
            if not text:
                raise StageExecutionError("No text content to chunk")
            
            # Initialize services
            t_client_start = time.monotonic()
            embedding_client = EmbeddingClient()
            qdrant_client = QdrantClient()
            client_init_ms = (time.monotonic() - t_client_start) * 1000
            
            t_chunker_start = time.monotonic()
            chunker = EnhancedDocumentChunker(
                base_chunker=None
            )
            chunker_init_ms = (time.monotonic() - t_chunker_start) * 1000
            
            # DECISION: Only apply RAPTOR logic (summaries + hierarchy) if document exceeds page threshold
            page_count = context.metadata.get('page_count', 1)
            raptor_threshold = getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3)
            should_apply_raptor = page_count >= raptor_threshold
            fast_upload_mode = getattr(settings, 'RAG_UPLOAD_FAST_MODE', True)
            defer_summaries = getattr(settings, 'RAG_DEFER_SUMMARY_ON_UPLOAD', True)
            build_raptor_on_upload = getattr(settings, 'RAG_BUILD_RAPTOR_ON_UPLOAD', False)
            generate_summaries = should_apply_raptor and not defer_summaries

            if not should_apply_raptor:
                self.logger.info(
                    f"ℹ️  [CHUNKING] Document has {page_count} pages (threshold: {raptor_threshold}). "
                    f"Applying Flat RAG (no RAPTOR)."
                )
            elif defer_summaries:
                self.logger.info(
                    f"ℹ️  [CHUNKING] RAPTOR eligible, but summaries are deferred during upload "
                    f"(fast_mode={fast_upload_mode})"
                )
            
            # Chunk and embed
            t_chunk_start = time.monotonic()
            chunks = chunker.chunk_and_embed_enhanced(
                text=text,
                document_id=context.document_id,
                embedding_client=embedding_client,
                qdrant_client=qdrant_client,
                metadata={
                    'file_type': context.metadata.get('file_extension', ''),
                    'page_count': page_count,
                    'word_count': len(text.split()) if text else 0,
                    'source_name': os.path.basename(context.file_path),
                    'raptor_applied': should_apply_raptor,
                },
                # If not applying RAPTOR, don't pass page_aware_text to skip hierarchy creation
                page_aware_text=context.metadata.get('page_aware_text') if should_apply_raptor else None,
                generate_summaries=generate_summaries,
                summary_mode='async'
            )
            chunk_ms = (time.monotonic() - t_chunk_start) * 1000
            
            if not chunks:
                raise StageExecutionError("No chunks generated")
            
            context.chunks = chunks
            context.metadata['chunk_count'] = len(chunks)
            context.metadata['avg_chunk_size'] = (
                len(text) // len(chunks) if chunks else 0
            )
            
            # Detailed logging with stats
            page_count = context.metadata.get('page_count', 1)
            text_length = context.metadata.get('text_length', 0)
            avg_chunk_size = context.metadata['avg_chunk_size']
            
            # Calculate page-wise distribution
            page_chunks = {}
            for chunk in chunks:
                page = chunk.get('page_number', 1)
                if page not in page_chunks:
                    page_chunks[page] = 0
                page_chunks[page] += 1
            
            page_distribution = ", ".join([f"Page {p}:{cnt}" for p, cnt in sorted(page_chunks.items())])
            
            # Pass decision to next stages via metadata
            context.metadata['raptor_applied'] = should_apply_raptor
            
            self.logger.info(
                f"✂️  [CHUNKING] Processing completed\n"
                f"   📊 Total chunks: {len(chunks)}\n"
                f"   📄 Pages processed: {page_count}\n"
                f"   🔗 RAPTOR Applied: {'YES' if should_apply_raptor else 'NO'}\n"
                f"   📏 Avg chunk size: {avg_chunk_size} chars\n"
                f"   📍 Chunk distribution per page: {page_distribution}\n"
                f"   🔢 Document ID: {context.document_id}"
            )
            self.logger.info(
                f"[UPLOAD_PROFILE] stage=chunking document={context.document_id} "
                f"clients={client_init_ms:.1f}ms chunker={chunker_init_ms:.1f}ms "
                f"process={chunk_ms:.1f}ms total={(time.monotonic() - t_start) * 1000:.1f}ms "
                f"summaries={'on' if generate_summaries else 'deferred'}"
            )
            return context
        
        except StageExecutionError:
            raise
        except Exception as e:
            raise StageExecutionError(f"Chunking failed: {str(e)}") from e


class SummarizationStage(PipelineStage):
    """Generate summaries for chunks (async - per chunk).
    
    NOTE: Summaries are now generated asynchronously PER-CHUNK during the ChunkingStage,
    not in batch. This stage is kept for backward compatibility but is essentially a no-op.
    """
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Skip summarization (now handled per-chunk in ChunkingStage).
        
        Args:
            context: Pipeline context with chunks
        
        Returns:
            Updated context (no changes to summaries)
        
        Note:
            Summaries are already queued asynchronously for each chunk
            during the ChunkingStage. This stage does nothing.
        """
        t_start = time.monotonic()
        total_chunks = len(context.chunks)
        
        # Log that we're skipping batch summarization (per-chunk is already queued)
        self.logger.info(
            f"📝 [SUMMARIZATION] Skipping batch summarization - "
            f"{total_chunks} chunks already queued for async per-chunk summary generation"
        )
        self.logger.info(
            f"[UPLOAD_PROFILE] stage=summarization document={context.document_id} "
            f"chunks={total_chunks} mode=async-deferred time={(time.monotonic() - t_start) * 1000:.1f}ms"
        )
        
        return context

    def can_skip(self, context: PipelineContext) -> bool:
        """Can skip if no chunks generated."""
        return len(context.chunks) == 0


class PersistenceStage(PipelineStage):
    """Save document and chunks to database."""

    def _update_document_indexing_metadata(self, document_id: str, **updates):
        from django.apps import apps

        Document = apps.get_model('documents', 'Document')
        doc = Document.objects.get(id=document_id)
        metadata = doc.metadata or {}
        metadata.update(updates)
        doc.metadata = metadata
        doc.save(update_fields=['metadata', 'updated_at'])
        return doc

    def _build_raptor_tree_sync(self, document_id: str):
        """Build RAPTOR tree in a background worker/thread."""
        try:
            from services.retrieval.raptor_tree import RaptorTreeBuilder
            from services.ai.embedding_client import EmbeddingClient
            from services.ai.qdrant_client import QdrantClient

            self.logger.info(f"[RAPTOR_BACKGROUND] Starting RAPTOR tree construction for {document_id}")
            self._update_document_indexing_metadata(
                document_id,
                raptor_status='building',
                raptor_ready=False,
                raptor_started_at=timezone.now().isoformat(),
            )
            builder = RaptorTreeBuilder(
                embedding_client=EmbeddingClient(),
                qdrant_client=QdrantClient(),
            )
            raptor_nodes = builder.build_tree(str(document_id))
            node_count = len(raptor_nodes or [])
            self._update_document_indexing_metadata(
                document_id,
                indexing_status='raptor_ready' if node_count else 'base_ready',
                raptor_status='ready' if node_count else 'skipped',
                raptor_ready=bool(node_count),
                raptor_node_count=node_count,
                raptor_ready_at=timezone.now().isoformat(),
            )
            self.logger.info(
                f"[RAPTOR_BACKGROUND] Completed RAPTOR tree for {document_id} "
                f"with {node_count} summary nodes"
            )
        except Exception as e:
            try:
                self._update_document_indexing_metadata(
                    document_id,
                    raptor_status='failed',
                    raptor_ready=False,
                    raptor_error=str(e)[:500],
                    raptor_failed_at=timezone.now().isoformat(),
                )
            except Exception:
                pass
            self.logger.error(f"[RAPTOR_BACKGROUND] Failed for {document_id}: {e}", exc_info=True)

    def _queue_raptor_tree_build(self, document_id: str):
        """Queue RAPTOR build without blocking upload completion."""
        t_start = time.monotonic()
        if getattr(settings, 'CELERY_ENABLED', False):
            try:
                from services.document.tasks import build_raptor_tree_task

                build_raptor_tree_task.delay(str(document_id))
                self.logger.info(
                    f"[RAPTOR_BACKGROUND] mode=celery-queued document={document_id} "
                    f"queue_time={(time.monotonic() - t_start) * 1000:.1f}ms"
                )
                return
            except Exception as e:
                self.logger.warning(f"[RAPTOR_BACKGROUND] Celery enqueue failed, using thread: {e}")

        thread = threading.Thread(
            target=self._build_raptor_tree_sync,
            args=(str(document_id),),
            daemon=True,
        )
        thread.start()
        self.logger.info(
            f"[RAPTOR_BACKGROUND] mode=thread-queued document={document_id} "
            f"queue_time={(time.monotonic() - t_start) * 1000:.1f}ms"
        )
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Persist to DB and Qdrant.
        
        Args:
            context: Pipeline context with all data
        
        Returns:
            Updated context with document saved
        
        Raises:
            StageExecutionError: If save fails
        """
        t_start = time.monotonic()
        try:
            from django.apps import apps
            from django.db import transaction
            from django.conf import settings
            
            Document = apps.get_model('documents', 'Document')
            raptor_build_document_id = None
            
            # Use transaction for atomicity
            with transaction.atomic():
                # Ensure metadata is JSON-serializable before saving.
                # Replace heavy PageAwareText objects with a small serializable summary.
                if 'page_aware_text' in context.metadata:
                    pa = context.metadata.get('page_aware_text')
                    try:
                        summary = {
                            'total_pages': getattr(pa, 'total_pages', None),
                            'text_preview': (getattr(pa, 'text', '') or '')[:200]
                        }
                        context.metadata['page_aware_text'] = summary
                    except Exception:
                        context.metadata.pop('page_aware_text', None)
                # Update or create document
                file_path = context.file_path
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                file_type = context.metadata.get('file_extension', '').lstrip('.') or 'unknown'

                if context.document_id:
                    try:
                        doc = Document.objects.get(id=context.document_id)
                    except Document.DoesNotExist:
                        doc = Document.objects.create(
                            id=context.document_id,
                            filename=file_name,
                            original_name=file_name,
                            storage_path=file_path,
                            file_type=file_type,
                            file_size=file_size,
                            uploader_id=context.user_id or None,
                            metadata=context.metadata,
                            embedding_model=getattr(settings, 'EMBEDDING_MODEL', getattr(settings, 'LLM_MODEL', '')),
                            chunking_strategy=context.metadata.get('strategy', 'token_window'),
                            status='processing',
                        )
                else:
                    doc = Document.objects.create(
                        filename=file_name,
                        original_name=file_name,
                        storage_path=file_path,
                        file_type=file_type,
                        file_size=file_size,
                        uploader_id=context.user_id or None,
                        metadata=context.metadata,
                        embedding_model=getattr(settings, 'EMBEDDING_MODEL', getattr(settings, 'LLM_MODEL', '')),
                        chunking_strategy=context.metadata.get('strategy', 'token_window'),
                        status='processing',
                    )
                    context.document_id = str(doc.id)
                
                # Update document metadata and status
                # IMPORTANT: Only store serializable data in JSONField
                db_metadata = doc.metadata or {}
                
                # Copy primitives from context.metadata
                for k, v in context.metadata.items():
                    if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                        db_metadata[k] = v

                # Decide upload indexing state before writing document metadata.
                raptor_applied = context.metadata.get('raptor_applied', False)
                build_raptor_on_upload = getattr(settings, 'RAG_BUILD_RAPTOR_ON_UPLOAD', False)
                
                db_metadata.update({
                    'page_count': context.metadata.get('page_count', 0),
                    'chunk_count': len(context.chunks),
                    'processed_at': datetime.now().timestamp(),
                    'last_stage': 'persistence',
                    'indexing_status': 'summary_pending' if raptor_applied else 'base_ready',
                    'base_ready': True,
                    'base_ready_at': timezone.now().isoformat(),
                    'summary_status': 'queued' if raptor_applied else 'not_required',
                    'raptor_status': 'queued' if raptor_applied and build_raptor_on_upload else 'not_required',
                    'raptor_ready': False,
                })
                doc.metadata = db_metadata
                doc.status = 'completed' if context.chunks else 'failed'
                
                # IMPORTANT: Only mark as hierarchical if RAPTOR was actually applied
                has_parent_nodes = any(bool(chunk.get('parent_node_id')) for chunk in context.chunks)
                doc.has_hierarchical_chunks = raptor_applied and has_parent_nodes
                doc.save()

                # ✅ STEP: Build Multi-Level RAPTOR Tree if threshold met
                if raptor_applied and build_raptor_on_upload:
                    raptor_build_document_id = str(doc.id)
                    self.logger.info(
                        f"[PERSISTENCE] RAPTOR tree build queued for {doc.id} "
                        f"after chunks and embeddings are persisted"
                    )
                elif raptor_applied:
                    self.logger.info(
                        f"[PERSISTENCE] RAPTOR tree build deferred for {doc.id} "
                        f"(RAG_BUILD_RAPTOR_ON_UPLOAD=False)"
                    )

            if raptor_build_document_id:
                self._queue_raptor_tree_build(raptor_build_document_id)
                
            context.metadata['persisted_at'] = datetime.now().isoformat()
            
            # Detailed persistence logging
            chunk_count = len(context.chunks)
            page_count = context.metadata.get('page_count', 1)
            text_length = context.metadata.get('text_length', 0)
            summary_count = context.metadata.get('summaries_generated', 0)
            
            # Check for RAPTOR/hierarchical structure
            has_parent_nodes = any(
                bool(chunk.get('parent_node_id') or chunk.get('parent_summary_id')) 
                for chunk in context.chunks
            )
            
            self.logger.info(
                f"💾 [PERSISTENCE COMPLETE]\n"
                f"   📄 Document: {context.document_id}\n"
                f"   📊 Chunks persisted: {chunk_count}\n"
                f"   📍 Pages: {page_count}\n"
                f"   💾 Text size: {text_length} chars\n"
                f"   📝 Summaries: {summary_count}/{chunk_count}\n"
                f"   🔗 RAPTOR Hierarchy: {'YES (with parent_node_id)' if has_parent_nodes else 'NO (flat structure)'}\n"
                f"   ✅ Status: completed"
            )
            self.logger.info(
                f"[UPLOAD_PROFILE] stage=persistence document={context.document_id} "
                f"chunks={chunk_count} summaries={summary_count} raptor={'yes' if raptor_applied else 'no'} "
                f"time={(time.monotonic() - t_start) * 1000:.1f}ms"
            )
            return context
        
        except Exception as e:
            raise StageExecutionError(f"Persistence failed: {str(e)}") from e

    def rollback(self, context: PipelineContext) -> None:
        """Rollback document if needed."""
        try:
            if context.document_id:
                from django.apps import apps
                Document = apps.get_model('documents', 'Document')
                
                doc = Document.objects.get(id=context.document_id)
                doc.is_deleted = True
                doc.save()
                
                self.logger.info(f"Rolled back document {context.document_id}")
        except Exception as e:
            self.logger.error(f"Rollback error: {e}")
