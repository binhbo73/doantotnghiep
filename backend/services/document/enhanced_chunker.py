"""
Enhanced Document Chunker (RAPTOR Phase 1-3)
=============================================
Adds page-aware chunking and chunk summarization.

Features:
1. Page-aware chunking (tracks actual page numbers)
2. Chunk summarization (sync/async)
3. Contextual chunk metadata
4. Hierarchical support (parent-child chunks)

Integration points:
- DocumentUploadService calls chunk_and_embed()
- page_aware_text: Optional PageAwareText from parser
- summary_service: ChunkSummaryService for summaries
"""

import logging
import threading
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from core.exceptions import DocumentProcessingError
from services.document.page_aware_parser import PageAwareText

logger = logging.getLogger(__name__)


class EnhancedDocumentChunker:
    """
    Wraps existing DocumentChunker with page-aware + summary features.
    
    Usage:
        chunker = EnhancedDocumentChunker()
        
        # With page-aware parsing
        chunks = chunker.chunk_and_embed_enhanced(
            text=raw_text,
            document_id=doc_id,
            embedding_client=embedding,
            qdrant_client=qdrant,
            page_aware_text=page_aware,  # Optional PageAwareText object
            generate_summaries=True,
            summary_mode='sync'  # or 'async'
        )
    """
    
    def __init__(self, base_chunker=None):
        """
        Initialize with optional base chunker.
        
        Args:
            base_chunker: Existing DocumentChunker instance (optional)
        """
        self.logger = logging.getLogger(__name__)
        if base_chunker is None:
            from services.document.chunker import DocumentChunker
            self.base_chunker = DocumentChunker()
        else:
            self.base_chunker = base_chunker
        
        # Initialize summary service
        try:
            from services.document.chunk_summary_service import ChunkSummaryService
            self.summary_service = ChunkSummaryService()
        except Exception as e:
            self.logger.warning(f"ChunkSummaryService not available: {e}")
            self.summary_service = None
    
    def chunk_and_embed_enhanced(
        self,
        text: str,
        document_id: str,
        embedding_client,
        qdrant_client,
        metadata: Dict[str, Any] = None,
        page_aware_text: Optional[PageAwareText] = None,
        structured_document=None,
        generate_summaries: bool = True,
        summary_mode: str = 'sync',  # 'sync' or 'async'
    ) -> List[Dict[str, Any]]:
        """
        Enhanced chunking with page awareness + summarization.
        
        Args:
            text: Raw document text
            document_id: Document ID
            embedding_client: For generating embeddings
            qdrant_client: For storing vectors
            metadata: Additional metadata
            page_aware_text: PageAwareText with page boundaries (optional)
            generate_summaries: Whether to generate summaries
            summary_mode: 'sync' (blocking) or 'async' (background)
        
        Returns:
            List of chunk dictionaries with metadata + embeddings
        """
        try:
            t_total_start = time.monotonic()
            # Step 1: Use hierarchical chunking if page-aware, else fallback to regular chunking
            should_raptor = False
            t_chunking_start = time.monotonic()

            # CRITICAL: Log which chunking path we're taking
            if structured_document:
                self.logger.info(
                    f"🚀 [CHUNKING_PATH] Using STRUCTURED DOCUMENT chunking for {document_id}"
                )
            elif page_aware_text:
                self.logger.info(
                    f"📄 [CHUNKING_PATH] Using PAGE-AWARE chunking for {document_id}"
                )
            else:
                self.logger.info(
                    f"📝 [CHUNKING_PATH] Using PLAIN TEXT chunking for {document_id}"
                )

            if structured_document:
                page_count = len(getattr(structured_document, 'pages', []) or []) or (
                    page_aware_text.total_pages if page_aware_text else 1
                )
                threshold = getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3)
                should_raptor = page_count >= threshold

                if hasattr(self.base_chunker, 'chunk_structured_document'):
                    chunks = self.base_chunker.chunk_structured_document(
                        structured_document,
                        metadata,
                    )

                    # Log metadata capture
                    if chunks:
                        sample_meta = chunks[0].get('metadata', {})
                        self.logger.info(
                            f"✅ [STRUCTURED_CHUNKS_CREATED] {len(chunks)} chunks with Mineru metadata:\n"
                            f"   📦 Block types: {sample_meta.get('block_type')}\n"
                            f"   🗺️  Heading path: {sample_meta.get('heading_path')}\n"
                            f"   📍 BBox: {bool(sample_meta.get('bbox'))}\n"
                            f"   📊 Reading order: {sample_meta.get('reading_order_start')}-{sample_meta.get('reading_order_end')}\n"
                            f"   🏗️  Parse backend: {sample_meta.get('parse_backend')}"
                        )

                    logger.info(
                        f"Created {len(chunks)} structured block-first chunks "
                        f"for document {document_id} (pages={page_count})"
                    )
                else:
                    logger.warning(
                        f"chunk_structured_document not available on "
                        f"{type(self.base_chunker).__name__}, "
                        f"falling back to page-aware / text chunking"
                    )
                    if page_aware_text:
                        chunks = self.base_chunker.chunk_by_pages(
                            page_aware_text, metadata
                        )
                        logger.info(
                            f"Created {len(chunks)} fallback page-aware chunks "
                            f"for document {document_id}"
                        )
                    else:
                        chunks = self.base_chunker.chunk_text(text, metadata)
                        logger.info(
                            f"Created {len(chunks)} fallback text chunks "
                            f"for document {document_id}"
                        )
            elif page_aware_text:
                page_count = page_aware_text.total_pages
                threshold = getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3)
                should_raptor = page_count >= threshold
                logger.info(f"📊 Document has {page_count} pages. RAPTOR threshold is {threshold}. Should RAPTOR: {should_raptor}")

                # HIERARCHICAL: Split by pages, then chunk within each page
                chunks = self.base_chunker.chunk_by_pages(page_aware_text, metadata)
                logger.info(
                    f"Created {len(chunks)} hierarchical chunks (by pages) for document {document_id}"
                )
            else:
                # FALLBACK: Regular chunking on full text
                chunks = self.base_chunker.chunk_text(text, metadata)
                logger.info(f"Created {len(chunks)} base chunks for document {document_id}")
            chunking_ms = (time.monotonic() - t_chunking_start) * 1000
            
            # Step 2: Skip page enrichment if already done by chunk_by_pages()
            # (page_number is already accurate from hierarchical chunking)
            if page_aware_text and not structured_document:
                chunks = self._enrich_chunks_with_pages(chunks, page_aware_text)
            
            # Step 3: Generate embeddings + store in DB
            t_embed_store_start = time.monotonic()
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            Document = apps.get_model('documents', 'Document')
            
            doc_obj = Document.objects.get(pk=document_id)
            
            chunks_with_embeddings = []
            prev_chunk_obj = None
            db_chunk_index = 0
            text_preview_chars = int(getattr(settings, 'RAG_QDRANT_TEXT_PREVIEW_CHARS', 1000))

            # Group chunks by page for page-aware persistence/RAPTOR processing.
            page_groups = {}
            if page_aware_text:
                for idx, chunk_dict in enumerate(chunks):
                    # Check if 'page_number' exists in chunk, otherwise use the sequence logic
                    chunk_metadata = chunk_dict.get('metadata') or {}
                    p_num = chunk_dict.get('page_number') or chunk_metadata.get('page_number')
                    if p_num is None:
                        # Fallback: estimate from chunk sequence if missing
                        logger.warning(f"⚠️ Chunk {idx} missing page_number, estimating...")
                        p_num = (idx // 5) + 1 # Rough fallback
                    
                    page_groups.setdefault(p_num, []).append(chunk_dict)
                
                logger.info(f"📦 [CHUNKING] Grouped into {len(page_groups)} pages")
            else:
                logger.warning("❗ No page_aware_text provided. All chunks will be assigned to Page 1 (General).")
                page_groups[1] = chunks

            for page_number in sorted(page_groups.keys()):
                page_chunks = page_groups[page_number]

                # RAPTOR tree construction owns parent-child links. Page
                # containers are legacy nodes and should stay opt-in so they
                # do not become orphaned after RAPTOR re-parents detail chunks.
                page_container = None
                create_page_containers = bool(
                    getattr(settings, 'RAG_CREATE_PAGE_CONTAINERS_ON_UPLOAD', False)
                )
                if page_aware_text and should_raptor and create_page_containers:
                    page_container_content = "\n".join(chunk['text'] for chunk in page_chunks)
                    content_hash = hashlib.md5(page_container_content.encode()).hexdigest()
                    
                    # 🚀 NEW: Generate embedding for the whole page/section node
                    section_embedding = None
                    
                    # ✅ IDEMPOTENCY FIX: Check if a section node for this page already exists
                    existing_section = DocumentChunk.objects.filter(
                        document_id=document_id,
                        page_number=page_number,
                        node_type='section'
                    ).first()

                    if existing_section:
                        page_container = existing_section
                        logger.info(f"♻️  [PAGE {page_number}] Using existing section node")
                    else:
                        page_container = DocumentChunk.objects.create(
                            document_id=document_id,
                            content=page_container_content[:4000],
                            chunk_index=db_chunk_index,
                            token_count=self.base_chunker._estimate_token_count(page_container_content),
                            page_number=page_number,
                            node_type='section',
                            vector_id=None, # Will be set by DocumentEmbedding
                            metadata={
                                'hierarchy_level': 1,
                                'page_container': True,
                                'page_number': page_number,
                                'child_chunk_count': len(page_chunks),
                                'strategy': self.base_chunker.strategy_name,
                                'page_aware': True,
                                'content_hash': content_hash
                            },
                            prev_chunk=prev_chunk_obj,
                        )
                    
                        if getattr(settings, 'RAG_VECTORIZE_PAGE_SECTIONS', False):
                            section_embedding = self.base_chunker._generate_embedding(
                                page_container_content[:4000],
                                embedding_client,
                            )
                            section_vector_id = qdrant_client.add_embedding(
                                embedding=section_embedding,
                                chunk_id=str(page_container.id),
                                payload={
                                    'document_id': str(document_id),
                                    'chunk_id': str(page_container.id),
                                    'page_number': page_number,
                                    'text_preview': page_container_content[:text_preview_chars],
                                    'node_type': 'section',
                                    'hierarchy_level': 1,
                                }
                            )

                            page_container.vector_id = section_vector_id
                            page_container.save(update_fields=['vector_id'])

                            from apps.documents.models import DocumentEmbedding
                            import json
                            section_embedding_json = json.dumps(section_embedding.tolist() if hasattr(section_embedding, 'tolist') else section_embedding)

                            DocumentEmbedding.objects.create(
                                chunk=page_container,
                                embedding_vector=section_embedding_json,
                                qdrant_vector_id=section_vector_id,
                                embedding_model=getattr(settings, 'EMBEDDING_MODEL', 'bge-m3'),
                                embedding_dimension=len(section_embedding) if section_embedding else 1024,
                                embedding_computed_at=timezone.now(),
                            )

                        logger.info(
                            f"📂 [PAGE {page_number}] Created & Vectorized Parent Node\n"
                            f"   🆔 ID: {page_container.id}\n"
                            f"   👶 Children expected: {len(page_chunks)} chunks"
                        )
                        # RAPTOR tree building creates page/section/document summaries.
                        # Queue section summaries separately only when explicitly enabled.
                        queue_section_summaries = getattr(
                            settings,
                            'RAG_QUEUE_SECTION_SUMMARIES_ON_UPLOAD',
                            False,
                        )
                        if generate_summaries and queue_section_summaries and self.summary_service:
                            try:
                                if summary_mode == 'async':
                                    self.summary_service.queue_summary_async(
                                        chunk_id=str(page_container.id),
                                        chunk_text=page_container_content[:4000],
                                        document_id=document_id
                                    )
                                else:
                                    logger.info(
                                        f"[SUMMARY_PROFILE] skipped_async_queue chunk_id={page_container.id} "
                                        f"mode={summary_mode}"
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to queue summary for section {page_container.id}: {e}")

                    if prev_chunk_obj:
                        prev_chunk_obj.next_chunk = page_container
                        prev_chunk_obj.save(update_fields=['next_chunk'])

                    prev_chunk_obj = page_container
                    db_chunk_index += 1

                # P1#5: Batch embed all chunk texts for this page. Optionally add a
                # compact contextual prefix for embeddings only; DB/citations keep raw text.
                page_chunk_texts = [
                    self._build_contextual_embedding_text(c['text'], c, metadata)
                    for c in page_chunks
                ]
                page_embeddings = self.base_chunker.batch_generate_embeddings(
                    page_chunk_texts, embedding_client
                )
                
                for page_idx, chunk_dict in enumerate(page_chunks):
                    try:
                        chunk_text = chunk_dict['text']
                        chunk_metadata = chunk_dict.get('metadata') or {}
                        page_number = chunk_dict.get('page_number') or chunk_metadata.get('page_number') or page_number or 1
                        
                        # ✅ IDEMPOTENCY FIX: Check if this detail chunk already exists
                        chunk_content_hash = hashlib.md5(chunk_text.encode()).hexdigest()
                        persisted_metadata = {
                            **chunk_metadata,
                            'start_char': chunk_dict.get('start_char', chunk_metadata.get('start_char', 0)),
                            'end_char': chunk_dict.get('end_char', chunk_metadata.get('end_char', 0)),
                            'line_start': chunk_dict.get('line_start', chunk_metadata.get('line_start')),
                            'line_end': chunk_dict.get('line_end', chunk_metadata.get('line_end')),
                            'hierarchy_level': 2,
                            'page_container_id': str(page_container.id) if page_container else None,
                            'content_hash': chunk_content_hash,
                            'source': 'enhanced_chunker'
                        }
                        
                        chunk_obj, created = DocumentChunk.objects.get_or_create(
                            document_id=document_id,
                            page_number=page_number,
                            chunk_index=db_chunk_index,
                            node_type='detail',
                            metadata__content_hash=chunk_content_hash,
                            defaults={
                                'content': chunk_text,
                                'token_count': chunk_dict.get('token_count', self.base_chunker._estimate_token_count(chunk_text)),
                                'parent_node': page_container,
                                'prev_chunk': prev_chunk_obj,
                                'metadata': persisted_metadata
                            }
                        )

                        if not created:
                            logger.info(f"♻️  [CHUNK {db_chunk_index}] Already exists, skipping creation")
                            vector_id = chunk_obj.vector_id
                        else:
                            # Generate embedding ONLY for new chunks
                            embedding = page_embeddings[page_idx] if page_idx < len(page_embeddings) else self.base_chunker._generate_embedding(chunk_text, embedding_client)
                            if not embedding:
                                logger.warning(f"⚠️ Failed to generate embedding for chunk {db_chunk_index}")
                                continue

                            # Link sequential chunks
                            if prev_chunk_obj:
                                prev_chunk_obj.next_chunk = chunk_obj
                                prev_chunk_obj.save(update_fields=['next_chunk'])

                            # Store in Qdrant
                            vector_id = qdrant_client.add_embedding(
                                embedding=embedding,
                                chunk_id=str(chunk_obj.id),
                                payload={
                                    'document_id': str(document_id),
                                    'chunk_id': str(chunk_obj.id),
                                    'page_number': page_number,
                                    'page_index': chunk_dict.get('page_index', page_idx),
                                    'sheet_name': persisted_metadata.get('sheet_name'),
                                    'row_start': persisted_metadata.get('row_start'),
                                    'row_end': persisted_metadata.get('row_end'),
                                    'text_preview': chunk_text[:text_preview_chars],
                                    'node_type': 'detail',
                                    'metadata': persisted_metadata,
                                }
                            )
                            
                            chunk_obj.vector_id = vector_id
                            chunk_obj.save(update_fields=['vector_id'])
                            
                            # Store embedding in SQL for visibility/audit
                            from apps.documents.models import DocumentEmbedding
                            import json
                            embedding_json = json.dumps(embedding.tolist() if hasattr(embedding, 'tolist') else embedding)
                            
                            DocumentEmbedding.objects.create(
                                chunk=chunk_obj,
                                qdrant_vector_id=vector_id,
                                embedding_vector=embedding_json,
                                embedding_dimension=len(embedding) if hasattr(embedding, '__len__') else 1024,
                                embedding_model=getattr(embedding_client, 'model', 'bge-m3'),
                                embedding_computed_at=timezone.now(),
                            )

                            # Detail chunk summaries are optional. Final answers cite
                            # detail chunks directly; RAPTOR uses page/section summaries.
                            summarize_detail_chunks = getattr(
                                settings,
                                'RAG_SUMMARIZE_DETAIL_CHUNKS_ON_UPLOAD',
                                False,
                            )
                            if generate_summaries and summarize_detail_chunks and self.summary_service:
                                try:
                                    if summary_mode == 'async':
                                        self.summary_service.queue_summary_async(
                                            chunk_id=str(chunk_obj.id),
                                            chunk_text=chunk_text,
                                            document_id=document_id
                                        )
                                    else:
                                        logger.info(
                                            f"[SUMMARY_PROFILE] skipped_async_queue chunk_id={chunk_obj.id} "
                                            f"mode={summary_mode}"
                                        )
                                except Exception as summary_err:
                                    logger.warning(f"Failed to queue summary for chunk {chunk_obj.id}: {summary_err}")

                        # Add to the tracking list for the orchestrator
                        chunks_with_embeddings.append({
                            'chunk_id': str(chunk_obj.id),
                            'vector_id': vector_id,
                            'page_number': page_number,
                            'page_index': chunk_dict.get('page_index', page_idx),
                            'parent_node_id': str(page_container.id) if page_container else None,
                            'text': chunk_text,
                            'metadata': chunk_obj.metadata or persisted_metadata,
                        })

                        prev_chunk_obj = chunk_obj
                        db_chunk_index += 1

                    except Exception as e:
                        logger.error(f"❌ Error processing chunk index {db_chunk_index}: {e}", exc_info=True)
                        continue

            # ✅ REMOVED: Redundant RAPTOR thread. 
            # Building RAPTOR tree is now handled exclusively in PersistenceStage 
            # to ensure base chunks are fully saved first and avoid race conditions.

            logger.info(
                f"Enhanced chunking completed: {len(chunks_with_embeddings)} chunks with embeddings, "
                f"page_aware={page_aware_text is not None}, summaries={generate_summaries}"
            )
            logger.info(
                f"[UPLOAD_PROFILE] stage=enhanced_chunker document={document_id} "
                f"chunking={chunking_ms:.1f}ms embed_store={(time.monotonic() - t_embed_store_start) * 1000:.1f}ms "
                f"total={(time.monotonic() - t_total_start) * 1000:.1f}ms"
            )
            
            return chunks_with_embeddings
        
        except Exception as e:
            logger.error(f"Error in enhanced chunk_and_embed: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Enhanced chunking failed: {str(e)}")

    def _build_contextual_embedding_text(
        self,
        chunk_text: str,
        chunk_dict: Dict[str, Any],
        document_metadata: Dict[str, Any],
    ) -> str:
        """Add stable document/page context to the embedding input only."""
        if not getattr(settings, 'RAG_CONTEXTUAL_EMBEDDING_PREFIX_ENABLED', True):
            return chunk_text

        chunk_metadata = chunk_dict.get('metadata') or {}
        parts = []
        source_name = (document_metadata or {}).get('source_name')
        if source_name:
            parts.append(f"File: {source_name}")
        page = chunk_dict.get('page_number') or chunk_metadata.get('page_number')
        if page:
            parts.append(f"Page: {page}")
        sheet_name = chunk_metadata.get('sheet_name')
        if sheet_name:
            parts.append(f"Sheet: {sheet_name}")
        row_start = chunk_metadata.get('row_start')
        row_end = chunk_metadata.get('row_end')
        if row_start:
            row_text = f"Rows: {row_start}"
            if row_end and row_end != row_start:
                row_text += f"-{row_end}"
            parts.append(row_text)
        heading_path = chunk_metadata.get('heading_path') or []
        if heading_path:
            if isinstance(heading_path, (list, tuple)):
                parts.append("Section: " + " > ".join(str(item) for item in heading_path if item))
            else:
                parts.append(f"Section: {heading_path}")
        block_type = chunk_metadata.get('block_type')
        if block_type:
            parts.append(f"Block: {block_type}")

        if not parts:
            return chunk_text

        max_prefix_chars = int(getattr(settings, 'RAG_CONTEXTUAL_EMBEDDING_PREFIX_CHARS', 360))
        prefix = " | ".join(parts)[:max_prefix_chars]
        return f"{prefix}\n\n{chunk_text}"
    
    def _enrich_chunks_with_pages(
        self,
        chunks: List[Dict[str, Any]],
        page_aware_text: PageAwareText
    ) -> List[Dict[str, Any]]:
        """
        Add actual page numbers to chunks based on character positions.
        
        Args:
            chunks: List of chunk dictionaries (with 'text', 'start_char', 'end_char')
            page_aware_text: PageAwareText with page mapping
        
        Returns:
            Enhanced chunks with 'page_number' field
        """
        for chunk in chunks:
            start_char = chunk.get('start_char', 0)
            end_char = chunk.get('end_char', 0)
            
            # Get page range for this chunk
            start_page, end_page = page_aware_text.get_page_range(start_char, end_char)
            
            # For multi-page chunks, use the starting page
            # (better than averaging since most chunks are single-page)
            chunk['page_number'] = start_page
            chunk['page_range'] = (start_page, end_page)
        
        logger.debug(f"Enriched {len(chunks)} chunks with page numbers from page_aware_text")
        return chunks
    
    def _generate_chunk_summaries(
        self,
        document_id: str,
        chunk_ids: List[str],
        chunks: List[Dict[str, Any]],
        mode: str = 'sync',
    ):
        """
        Generate summaries for chunks.
        
        Args:
            document_id: Parent document ID
            chunk_ids: List of chunk IDs
            chunks: List of chunk dictionaries (with 'text' field)
            mode: 'sync' for blocking, 'async' for background
        """
        try:
            if not self.summary_service:
                logger.warning("ChunkSummaryService not available, skipping summaries")
                return
            
            logger.info(f"📝 [SUMMARY_GENERATION] Starting {mode} mode for {len(chunks)} chunks")
            
            if mode == 'sync':
                # Generate summaries immediately
                generated = 0
                failed = 0
                page_stats = {}
                
                for idx, chunk_dict in enumerate(chunks):
                    try:
                        page_num = chunk_dict.get('page_number', 1)
                        if page_num not in page_stats:
                            page_stats[page_num] = {'success': 0, 'failed': 0}
                        
                        summary = self.summary_service.generate_summary_sync(chunk_dict['text'])
                        if summary:
                            # Update chunk in DB
                            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                            chunk = DocumentChunk.objects.get(id=chunk_dict['chunk_id'])
                            chunk.summary = summary
                            chunk.save(update_fields=['summary', 'updated_at'])
                            generated += 1
                            page_stats[page_num]['success'] += 1
                            
                            logger.debug(
                                f"  ✅ Chunk {idx} (Page {page_num}): {summary[:50]}..."
                            )
                        else:
                            failed += 1
                            page_stats[page_num]['failed'] += 1
                    
                    except Exception as e:
                        failed += 1
                        page_num = chunk_dict.get('page_number', 1)
                        if page_num not in page_stats:
                            page_stats[page_num] = {'success': 0, 'failed': 0}
                        page_stats[page_num]['failed'] += 1
                        logger.warning(f"  ❌ Chunk {idx} (Page {page_num}): Error - {str(e)}")
                
                page_dist = ", ".join([f"Page {p}:{s['success']}" for p, s in sorted(page_stats.items())])
                logger.info(
                    f"✅ [SUMMARY_SYNC_COMPLETE]\n"
                    f"   ✔️  Generated: {generated}/{len(chunks)}\n"
                    f"   ❌ Failed: {failed}\n"
                    f"   📊 Per-page: {page_dist}"
                )
            
            elif mode == 'async':
                # Queue summaries for background processing only when explicitly requested.
                for chunk_dict in chunks:
                    try:
                        self.summary_service.queue_summary_async(
                            chunk_id=chunk_dict['chunk_id'],
                            chunk_text=chunk_dict['text'],
                            document_id=document_id
                        )
                    except Exception as e:
                        logger.warning(f"Error queuing summary for chunk {chunk_dict['chunk_id']}: {e}")
                
                logger.info(f"⏳ [SUMMARY_ASYNC] Queued {len(chunks)} chunks for background processing")
        
        except Exception as e:
            logger.error(f"Error in _generate_chunk_summaries: {str(e)}")
    
    def get_chunk_with_context(
        self,
        chunk_id: str,
        context_mode: str = 'local'  # 'local', 'section', 'document'
    ) -> Dict[str, Any]:
        """
        Get chunk with contextual information for RAG.
        
        Args:
            chunk_id: DocumentChunk ID
            context_mode: What context to include
                - 'local': Just the chunk
                - 'section': Chunk + surrounding chunks on same page
                - 'document': Chunk + document summary
        
        Returns:
            Chunk with context
        """
        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            chunk = DocumentChunk.objects.get(id=chunk_id)
            
            result = {
                'id': str(chunk.id),
                'content': chunk.content,
                'summary': chunk.summary,
                'page_number': chunk.page_number,
                'chunk_index': chunk.chunk_index,
            }
            
            if context_mode == 'local':
                # Just return the chunk
                pass
            
            elif context_mode == 'section':
                # Get surrounding chunks on same page
                surrounding_chunks = DocumentChunk.objects.filter(
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    is_deleted=False
                ).order_by('chunk_index').values_list('id', 'content', 'summary')
                
                result['context'] = {
                    'page_chunks': [
                        {'id': str(c[0]), 'content': c[1], 'summary': c[2]}
                        for c in surrounding_chunks
                    ]
                }
            
            elif context_mode == 'document':
                # Get document summary
                document = chunk.document
                result['context'] = {
                    'document_name': document.original_name,
                    'document_summary': document.metadata.get('summary', ''),
                    'total_chunks': document.chunks.filter(is_deleted=False).count(),
                }
            
            return result
        
        except DocumentChunk.DoesNotExist:
            raise DocumentProcessingError(f"Chunk {chunk_id} not found")
        except Exception as e:
            logger.error(f"Error getting chunk with context: {str(e)}")
            raise
