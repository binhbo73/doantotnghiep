from typing import List, Dict, Any, Optional
import logging
import threading
import hashlib
import concurrent.futures
from django.apps import apps
from django.conf import settings

logger = logging.getLogger(__name__)


class RaptorTreeBuilder:
    """Hierarchical RAPTOR tree builder.

    Builds a multi-level tree of:
    - leaf chunks
    - page summaries
    - section summaries
    - document summary
    """

    def __init__(self, embedding_client=None, qdrant_client=None):
        self.DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client

    def _get_exact_page_count(self, document) -> int:
        """Get the parsed page count recorded from the original file metadata."""
        metadata = document.metadata or {}
        # The source of truth should be 'page_count' set in ParsingStage
        page_count = metadata.get('page_count') or metadata.get('pages')
        
        if page_count is not None:
            return int(page_count)
            
        # If not in metadata, try counting unique page_numbers in detail chunks
        unique_pages = document.chunks.filter(is_deleted=False, node_type='detail').values_list('page_number', flat=True).distinct()
        if unique_pages.exists():
            return unique_pages.count()
            
        return 0 # Return 0 instead of 1 to signal "not determined"

    def should_build(self, document) -> bool:
        """Decide whether RAPTOR should be applied to a document."""
        try:
            # Use the global threshold from settings
            threshold = getattr(settings, 'RAG_RAPTOR_THRESHOLD_PAGES', 3)
            
            page_cnt = self._get_exact_page_count(document)
            if page_cnt >= threshold:
                return True
                
            # Fallback for documents without explicit page count
            total_chunks = document.chunks.filter(is_deleted=False, node_type='detail').count()
            # If we have more than (threshold * 5) chunks, it's likely a long document
            return total_chunks > (threshold * 5)
        except Exception:
            return False

    def build_tree(self, document_id: str) -> List[Dict[str, Any]]:
        """Build hierarchical RAPTOR nodes and return created nodes."""
        created = []
        try:
            from django.apps import apps
            from django.conf import settings
            Document = apps.get_model('documents', 'Document')
            doc = Document.objects.get(pk=document_id)

            if not self.should_build(doc):
                logger.info(f"Skipping RAPTOR tree building for document {document_id} (below threshold)")
                return []

            page_cnt = self._get_exact_page_count(doc)
            logger.info(f"🏗️ Building RAPTOR tree for document {document_id} ({page_cnt} pages)")

            chunks_qs = doc.chunks.filter(is_deleted=False, node_type='detail').order_by('page_number', 'chunk_index')
            if not chunks_qs.exists():
                logger.info(f"No detail chunks for document {document_id}, skipping RAPTOR")
                return []

            # Build page summaries
            page_groups = {}
            for chunk in chunks_qs:
                # Use getattr without a default of 1 to see the real value
                page = getattr(chunk, 'page_number', None)
                
                if page is None:
                    logger.error(f"❌ [RAPTOR] Chunk {chunk.id} has NO page_number! This will break hierarchy.")
                    page = 0 # Use 0 to indicate error/unknown instead of 1
                
                page_groups.setdefault(page, []).append(chunk)

            logger.info(f"📊 [RAPTOR] Grouped chunks into {len(page_groups)} pages for summarization")
            
            # 🚀 Parallelized Page Summaries
            page_summaries = self._build_page_summaries_parallel(document_id, page_groups)
            created.extend(page_summaries)

            # 🚀 Parallelized Section Summaries
            section_summaries = self._build_section_summaries_parallel(document_id, page_summaries)
            created.extend(section_summaries)

            # Build document summary if sections exist
            document_summary = self._build_document_summary(document_id, section_summaries)
            if document_summary:
                created.append(document_summary)

            logger.info(
                f"Built RAPTOR tree for document {document_id} (parsed_pages={page_cnt}): "
                f"page={len(page_summaries)} section={len(section_summaries)} document={1 if document_summary else 0}"
            )
            return created

        except Exception as e:
            logger.error(f"Error building RAPTOR tree for {document_id}: {e}")
            return []

    def _build_page_summaries_parallel(self, document_id: str, page_groups: Dict[int, List[Any]]) -> List[Dict[str, Any]]:
        created = []
        
        def process_page(page, chunks):
            summary_text = self._compose_summary_text(chunks)
            if not summary_text:
                return None

            # Generate a content hash to identify unique summaries
            content_hash = hashlib.md5(summary_text.encode()).hexdigest()

            page_summary, created = self.DocumentChunk.objects.get_or_create(
                document_id=document_id,
                page_number=page,
                node_type='summary',
                metadata__raptor_level=1,
                defaults={
                    'content': summary_text[:4000],
                    'summary': summary_text[:4000],
                    'chunk_index': chunks[0].chunk_index if chunks else 0,
                    'metadata': {
                        'raptor_level': 1, 
                        'child_chunk_count': len(chunks),
                        'content_hash': content_hash
                    },
                }
            )

            if not created:
                logger.info(f"♻️  [RAPTOR] Page Summary for Page {page} already exists, skipping creation")
            else:
                logger.info(f"✅ [RAPTOR] Created Page Summary for Page {page}")

            for child in chunks:
                child.parent_node = page_summary
                child.save(update_fields=['parent_node'])

            # Generate embedding and store in Qdrant
            self._embed_and_store(page_summary)
            return {'summary_chunk_id': str(page_summary.id), 'page': page, 'child_count': len(chunks)}

        # Use up to 4 threads for RAPTOR generation
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_page = {executor.submit(process_page, p, c): p for p, c in page_groups.items()}
            for future in concurrent.futures.as_completed(future_to_page):
                res = future.result()
                if res:
                    created.append(res)
                    logger.info(f"✅ [RAPTOR] Finished Page Summary for Page {res['page']}")
        
        return sorted(created, key=lambda x: x['page'])

    def _build_section_summaries_parallel(self, document_id: str, page_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created = []
        if not page_summaries:
            return []

        page_summary_ids = [item['summary_chunk_id'] for item in page_summaries]
        page_summary_objs = list(self.DocumentChunk.objects.filter(id__in=page_summary_ids).order_by('page_number'))

        pages_per_section = 4
        section_groups = [page_summary_objs[i:i + pages_per_section] for i in range(0, len(page_summary_objs), pages_per_section)]

        def process_section(section_index, group):
            section_text = self._compose_summary_text(group)
            if not section_text:
                return None

            # Level 2 nodes were previously called 'section', changing to 'summary' 
            # with level 2 to avoid confusion with base page sections.
            section_summary, created = self.DocumentChunk.objects.get_or_create(
                document_id=document_id,
                page_number=getattr(group[0], 'page_number', 1),
                node_type='summary',
                metadata__raptor_level=2,
                defaults={
                    'content': section_text[:4000],
                    'summary': section_text[:4000],
                    'chunk_index': getattr(group[0], 'chunk_index', 0),
                    'metadata': {
                        'raptor_level': 2,
                        'child_summary_count': len(group),
                        'page_range': [getattr(group[0], 'page_number', 1), getattr(group[-1], 'page_number', 1)],
                    },
                }
            )

            if not created:
                logger.info(f"♻️  [RAPTOR] Section Summary {section_index} already exists")
            else:
                logger.info(f"✅ [RAPTOR] Created Section Summary {section_index}")

            for page_summary in group:
                page_summary.parent_node = section_summary
                page_summary.save(update_fields=['parent_node'])

            # Generate embedding and store in Qdrant
            self._embed_and_store(section_summary)
            return {
                'section_summary_id': str(section_summary.id),
                'section_index': section_index,
                'child_count': len(group),
                'page_number': section_summary.page_number
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_sec = {executor.submit(process_section, i, g): i for i, g in enumerate(section_groups, 1)}
            for future in concurrent.futures.as_completed(future_to_sec):
                res = future.result()
                if res:
                    created.append(res)
                    logger.info(f"✅ [RAPTOR] Finished Section Summary {res['section_index']}")

        return sorted(created, key=lambda x: x['page_number'])

    def _build_document_summary(self, document_id: str, section_summaries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not section_summaries:
            return None

        summary_ids = [item['section_summary_id'] for item in section_summaries]
        section_objs = list(self.DocumentChunk.objects.filter(id__in=summary_ids).order_by('page_number'))
        document_text = self._compose_summary_text(section_objs)
        if not document_text:
            return None

        document_summary, created = self.DocumentChunk.objects.get_or_create(
            document_id=document_id,
            node_type='summary',
            metadata__raptor_level=3,
            defaults={
                'content': document_text[:4000],
                'summary': document_text[:4000],
                'page_number': getattr(section_objs[0], 'page_number', 1),
                'chunk_index': getattr(section_objs[0], 'chunk_index', 0),
                'metadata': {
                    'raptor_level': 3,
                    'child_section_count': len(section_objs),
                    'page_range': [getattr(section_objs[0], 'page_number', 1), getattr(section_objs[-1], 'page_number', 1)],
                },
            }
        )

        if not created:
            logger.info(f"♻️  [RAPTOR] Global Document Summary already exists")
        else:
            logger.info(f"✅ [RAPTOR] Created Global Document Summary")

        for section in section_objs:
            section.parent_node = document_summary
            section.save(update_fields=['parent_node'])

        # Generate embedding and store in Qdrant
        self._embed_and_store(document_summary)

        logger.info(
            f"👑 [RAPTOR] Created Global Document Summary (Level 3)\n"
            f"   🆔 ID: {document_summary.id}\n"
            f"   👨‍👦 Parent of {len(section_objs)} sections"
        )

        return {
            'document_summary_id': str(document_summary.id),
            'child_count': len(section_objs),
        }

    def _embed_and_store(self, chunk_obj):
        """Helper to generate embedding and store in Qdrant for RAPTOR nodes."""
        if not self.embedding_client or not self.qdrant_client:
            logger.warning(f"Embedding or Qdrant client missing, skipping vector storage for node {chunk_obj.id}")
            return

        try:
            # 1. Generate embedding
            embedding = self.embedding_client.create_embedding(chunk_obj.content)
            if not embedding:
                return

            # 2. Store in Qdrant
            doc_obj = chunk_obj.document
            qdrant_payload = {
                'document_id': str(chunk_obj.document_id),
                'chunk_id': str(chunk_obj.id),
                'chunk_index': chunk_obj.chunk_index,
                'text': chunk_obj.content[:500],
                'node_type': chunk_obj.node_type,
                'raptor_level': chunk_obj.metadata.get('raptor_level', 0),
                'access_scope': getattr(doc_obj, 'access_scope', 'company'),
                'department_id': str(doc_obj.department_id) if getattr(doc_obj, 'department_id', None) else None,
            }
            
            vector_id = self.qdrant_client.add_embedding(
                embedding=embedding,
                chunk_id=str(chunk_obj.id),
                payload=qdrant_payload
            )
            
            # 3. Update chunk and create DocumentEmbedding
            chunk_obj.vector_id = vector_id
            chunk_obj.save(update_fields=['vector_id'])
            
            DocumentEmbedding = apps.get_model('documents', 'DocumentEmbedding')
            from django.utils import timezone
            import json
            embedding_json = json.dumps(embedding.tolist() if hasattr(embedding, 'tolist') else embedding)
            
            DocumentEmbedding.objects.create(
                chunk=chunk_obj,
                qdrant_vector_id=vector_id,
                embedding_vector=embedding_json, # Store for visibility
                embedding_dimension=len(embedding),
                embedding_model=getattr(self.embedding_client, 'model', 'bge-m3'),
                embedding_computed_at=timezone.now(),
            )
            logger.info(f"Stored RAPTOR node {chunk_obj.id} ({chunk_obj.node_type}) in Qdrant")
        except Exception as e:
            logger.error(f"Failed to embed and store RAPTOR node {chunk_obj.id}: {e}")

    def _compose_summary_text(self, chunks: List[Any]) -> str:
        parts = []
        for chunk in chunks:
            summary_text = getattr(chunk, 'summary', None)
            if summary_text:
                parts.append(summary_text)
            elif getattr(chunk, 'content', None):
                parts.append(chunk.content[:400])
        return ' '.join(parts).strip()
