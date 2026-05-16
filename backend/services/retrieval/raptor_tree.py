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

    def _is_spreadsheet_document(self, document) -> bool:
        metadata = document.metadata or {}
        file_type = (getattr(document, 'file_type', '') or '').lower()
        mime_type = (getattr(document, 'mime_type', '') or '').lower()
        return (
            file_type in {'xlsx', 'xls', 'csv'}
            or 'spreadsheet' in mime_type
            or mime_type == 'text/csv'
            or bool(metadata.get('spreadsheet'))
        )

    def _should_build_spreadsheet(self, document) -> bool:
        if not getattr(settings, 'RAG_SPREADSHEET_RAPTOR_ENABLED', True):
            return False

        metadata = document.metadata or {}
        spreadsheet = metadata.get('spreadsheet') or {}
        sheet_count = int(
            metadata.get('spreadsheet_sheet_count')
            or spreadsheet.get('sheet_count')
            or self._get_exact_page_count(document)
            or 0
        )
        total_rows = int(
            metadata.get('spreadsheet_total_rows')
            or spreadsheet.get('total_non_empty_rows')
            or 0
        )
        total_chunks = int(
            metadata.get('chunk_count')
            or document.chunks.filter(is_deleted=False, node_type='detail').count()
            or 0
        )

        return (
            sheet_count >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_SHEETS', 3))
            or total_rows >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_ROWS', 200))
            or total_chunks >= int(getattr(settings, 'RAG_SPREADSHEET_RAPTOR_MIN_CHUNKS', 12))
        )

    def should_build(self, document) -> bool:
        """Decide whether RAPTOR should be applied to a document."""
        try:
            if self._is_spreadsheet_document(document):
                return self._should_build_spreadsheet(document)

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
                        **self._summary_metadata_for_chunks(chunks),
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

        max_workers = max(1, int(getattr(settings, 'RAG_RAPTOR_BUILD_WORKERS', 1)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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
            section_text = self._compose_summary_text(group, use_llm=True)
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
                        **self._summary_metadata_for_chunks(group),
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

        max_workers = max(1, int(getattr(settings, 'RAG_RAPTOR_BUILD_WORKERS', 1)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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
        document_text = self._compose_summary_text(section_objs, use_llm=True)
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
                    **self._summary_metadata_for_chunks(section_objs),
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
                'sheet_name': chunk_obj.metadata.get('sheet_name'),
                'row_start': chunk_obj.metadata.get('row_start'),
                'row_end': chunk_obj.metadata.get('row_end'),
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

    def _compose_summary_text(self, chunks: List[Any], use_llm: bool = False) -> str:
        """Compose summary text from child chunks/summaries.
        
        P1#6: Khi use_llm=True (level >= 2), dung LLM de synthesize summary
        thay vi chi concatenate thuan tuy. Concatenation tao ra chuoi dai cac cau
        roi rac, khong co tinh mach lac. LLM synthesis cho summary chat luong cao hon.
        """
        if self._is_table_chunk_group(chunks):
            return self._compose_table_summary_text(chunks)

        parts = []
        for chunk in chunks:
            summary_text = getattr(chunk, 'summary', None)
            if summary_text:
                parts.append(summary_text)
            elif getattr(chunk, 'content', None):
                parts.append(chunk.content[:400])
        
        combined = ' '.join(parts).strip()
        
        # P1#6: LLM synthesis cho level >= 2 section/document summaries
        if use_llm and len(combined) > 500:
            try:
                synthesized = self._llm_synthesize_summary(combined)
                if synthesized:
                    return synthesized
            except Exception as e:
                logger.warning(f'LLM synthesis failed, using concatenation: {e}')
        
        return combined

    def _is_table_chunk_group(self, chunks: List[Any]) -> bool:
        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', None) or {}
            content = getattr(chunk, 'content', '') or ''
            if metadata.get('content_format') == 'spreadsheet_markdown' or '| Excel row |' in content:
                return True
        return False

    def _summary_metadata_for_chunks(self, chunks: List[Any]) -> Dict[str, Any]:
        sheet_names = []
        row_starts = []
        row_ends = []
        content_formats = set()

        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', None) or {}
            sheet_name = metadata.get('sheet_name')
            if sheet_name and sheet_name not in sheet_names:
                sheet_names.append(sheet_name)
            for key, target in (('row_start', row_starts), ('row_end', row_ends)):
                value = metadata.get(key)
                if value is not None:
                    try:
                        target.append(int(value))
                    except (TypeError, ValueError):
                        pass
            if metadata.get('content_format'):
                content_formats.add(metadata['content_format'])

        summary_metadata: Dict[str, Any] = {}
        if sheet_names:
            summary_metadata['sheet_name'] = sheet_names[0] if len(sheet_names) == 1 else ', '.join(sheet_names[:5])
            summary_metadata['sheet_names'] = sheet_names[:20]
        if row_starts:
            summary_metadata['row_start'] = min(row_starts)
        if row_ends:
            summary_metadata['row_end'] = max(row_ends)
        if content_formats:
            summary_metadata['content_format'] = 'spreadsheet_summary' if 'spreadsheet_markdown' in content_formats else sorted(content_formats)[0]
        return summary_metadata

    def _split_markdown_row(self, line: str) -> List[str]:
        cells = [cell.strip().replace('\\|', '|') for cell in (line or '').strip().strip('|').split('|')]
        return cells

    def _compose_table_summary_text(self, chunks: List[Any]) -> str:
        """Create a deterministic, table-aware summary for spreadsheet chunks."""
        metadata = self._summary_metadata_for_chunks(chunks)
        sheet_label = metadata.get('sheet_name') or 'spreadsheet'
        row_start = metadata.get('row_start')
        row_end = metadata.get('row_end')
        row_label = f"rows {row_start}-{row_end}" if row_start and row_end else "rows unknown"

        columns = []
        row_summaries = []
        for chunk in chunks:
            content = getattr(chunk, 'content', '') or ''
            for line in content.splitlines():
                if not line.startswith('|'):
                    continue
                cells = self._split_markdown_row(line)
                if len(cells) < 2:
                    continue
                if cells[0].lower() == 'excel row':
                    columns = cells
                    continue
                if cells[0].isdigit():
                    values = [cell for cell in cells[1:] if cell]
                    if values:
                        row_summaries.append(f"row {cells[0]}: {'; '.join(values[:6])}")
                if len(row_summaries) >= 10:
                    break
            if len(row_summaries) >= 10:
                break

        column_text = f"Columns: {', '.join(columns)}." if columns else ""
        rows_text = " | ".join(row_summaries[:10])
        summary = (
            f"Spreadsheet summary for sheet {sheet_label}, {row_label}. "
            f"{column_text} Key rows: {rows_text}"
        ).strip()
        return summary[:4000]
    
    def _llm_synthesize_summary(self, text: str) -> str:
        """Goi LLM de synthesize summary tu concatenated child summaries.
        
        Fix: Tang timeout len 300s (tuong thich voi Qwen3-4B tren CPU)
        va giam prompt text xuong 1500 chars de tranh timeout.
        """
        try:
            from services.ai.llama_client import LlamaClient
            
            llama = LlamaClient(timeout=300)
            prompt = (
                "Tong hop cac tom tat sau thanh 1-3 cau tieng Viet, toi da 250 ky tu. "
                "Chi giu y chinh, ten rieng, ngay thang, so lieu, dieu kien va hanh dong quan trong. "
                "Khong suy dien, khong them thong tin ngoai noi dung.\n\n"
                + text[:900] + "\n\n"
                "Tom tat tong hop:"
            )
            summary = llama.complete(
                prompt=prompt,
                max_tokens=96,
                temperature=0.2,
                timeout=300,
            )
            if summary and len(summary.strip()) > 20:
                return summary.strip()[:4000]
        except Exception as e:
            logger.warning(f'LLM synthesis error: {e}')
        return None
