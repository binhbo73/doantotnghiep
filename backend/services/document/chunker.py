"""
Document Chunker
================
Split documents into chunks + generate embeddings

Features:
- Token-window chunking (word-span based)
- Stable overlap between chunks
- Metadata preservation (char/token spans)
- Reranking via flashrank
- Embedding generation via LLM
- Batch processing

Configuration (from settings.py):
    CHUNK_TOKEN_SIZE = 320  # token-like units per chunk
    CHUNK_TOKEN_OVERLAP = 64  # token-like units overlap
    CHUNK_SIZE = 512  # legacy fallback
    CHUNK_OVERLAP = 100  # legacy fallback
    FLASHRANK_TOPK = 10  # rerank top K results

Usage:
    chunker = DocumentChunker()

    chunks = chunker.chunk_text(
        text="Long document text...",
        metadata={'document_id': 1, 'source': 'pdf'}
    )
"""

import logging
import re
from bisect import bisect_right
from typing import List, Dict, Any, Optional, Tuple
from django.conf import settings
from django.apps import apps
from core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


# ============================================================================
# VIETNAMESE DOCUMENT STRUCTURE PATTERNS
# ============================================================================
# These regex patterns detect Vietnamese legal/administrative document
# structure elements that should serve as chunk boundaries.

_VI_HEADING_PATTERNS = [
    # Chương I, CHƯƠNG 1, Chương 1: Tiêu đề
    re.compile(r'(?i)^\s*chương\s+[IVXLCDM\d]+[.:\s]', re.UNICODE),
    # Điều 1, Điều 15:
    re.compile(r'(?i)^\s*điều\s+\d+[.:\s]', re.UNICODE),
    # Mục 1, Mục 1.1:
    re.compile(r'(?i)^\s*mục\s+[\d.]+[.:\s]', re.UNICODE),
    # Phần I, Phần thứ nhất
    re.compile(r'(?i)^\s*phần\s+(thứ\s+)?[IVXLCDM\d]+[.:\s]', re.UNICODE),
    # Khoản 1:
    re.compile(r'(?i)^\s*khoản\s+\d+[.:\s]', re.UNICODE),
    # I. / 1. / 1.1. / a) / (a) style headings
    re.compile(r'^\s*(?:[IVXLCDM]+|\d+(?:\.\d+)*)[.)]\s+[A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]', re.UNICODE),
    # Markdown-style headings: ### Tiêu đề
    re.compile(r'^#{1,6}\s+\S', re.UNICODE),
]

# Common Vietnamese document type indicators for auto-detection
_DOC_TYPE_PATTERNS = [
    ('regulation', re.compile(
        r'(?i)(nghị\s*định|thông\s*tư|quyết\s*định|quy\s*chế|quy\s*định\s*(?:chung|về|số)|'
        r'nội\s*quy|văn\s*bản\s*quy\s*phạm|điều\s*lệ)'
    )),
    ('contract', re.compile(
        r'(?i)(hợp\s*đồng|bên\s+(?:A|B|mua|bán|thuê|cho\s*thuê)|'
        r'điều\s*khoản\s*\d+\s*:|phụ\s*lục\s*hợp\s*đồng|'
        r'thanh\s*lý|biên\s*bản\s*(?:bàn\s*giao|nghiệm\s*thu|thanh\s*lý))'
    )),
    ('handbook', re.compile(
        r'(?i)(sổ\s*tay|hướng\s*dẫn|quy\s*trình|cẩm\s*nang|'
        r'manual|handbook|guide|hướng\s*dẫn\s*sử\s*dụng)'
    )),
    ('report', re.compile(
        r'(?i)(báo\s*cáo|tổng\s*kết|báo\s*cáo\s*(?:tài\s*chính|thường\s*niên|'
        r'kết\s*quả\s*kinh\s*doanh)|bảng\s*cân\s*đối|báo\s*cáo\s*thống\s*kê)'
    )),
    ('technical', re.compile(
        r'(?i)(thông\s*số\s*kỹ\s*thuật|hướng\s*dẫn\s*kỹ\s*thuật|'
        r'bản\s*vẽ|sơ\s*đồ|đặc\s*tả\s*kỹ\s*thuật|datasheet|specification)'
    )),
]


class DocumentChunker:
    # ✅ P1#4: Lazy-loaded BGE-M3/XLM-RoBERTa tokenizer cho đếm token chính xác
    _tokenizer = None
    """
    Document chunker - splits text into semantic chunks + generates embeddings
    
    Strategy:
    1. Use file-type-aware chunk profiles
    2. Build token-like spans from original text (word-based)
    3. Snap chunk ends to paragraph/sentence boundaries when possible
    4. Preserve exact character spans to avoid content loss
    5. Generate embeddings for each chunk
    6. Rerank for quality (optional)
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        Initialize chunker
        
        Args:
            chunk_size: Token-like units per chunk
            chunk_overlap: Overlap token-like units between chunks
        """
        self.chunk_size = chunk_size or getattr(
            settings,
            'CHUNK_TOKEN_SIZE',
            getattr(settings, 'CHUNK_SIZE', 320)
        )
        self.chunk_overlap = chunk_overlap or getattr(
            settings,
            'CHUNK_TOKEN_OVERLAP',
            getattr(settings, 'CHUNK_OVERLAP', 64)
        )
        self.table_chunk_max_tokens = int(getattr(
            settings,
            'RAG_TABLE_CHUNK_MAX_TOKENS',
            max(1600, self.chunk_size * 4),
        ))

        if self.chunk_size <= 0:
            raise DocumentProcessingError("chunk_size must be > 0")
        if self.chunk_overlap < 0:
            raise DocumentProcessingError("chunk_overlap must be >= 0")
        if self.chunk_overlap >= self.chunk_size:
            # Avoid zero/negative stride causing infinite loops
            self.chunk_overlap = max(0, self.chunk_size // 4)

        self.strategy_name = f"token_window_{self.chunk_size}_{self.chunk_overlap}"
        
        logger.info(
            f"DocumentChunker initialized: "
            f"strategy={self.strategy_name}, chunk_size={self.chunk_size}, overlap={self.chunk_overlap}"
        )
    
    @classmethod
    def _get_tokenizer(cls):
        """Lazy-load BGE-M3/XLM-RoBERTa tokenizer để đếm token chính xác."""
        if cls._tokenizer is None:
            try:
                from transformers import AutoTokenizer
                model_name = getattr(settings, 'EMBEDDING_MODEL', 'BAAI/bge-m3')
                cls._tokenizer = AutoTokenizer.from_pretrained(
                    model_name, use_fast=True
                )
                logger.info(f"✅ BGE-M3 tokenizer loaded: {model_name}")
            except Exception as e:
                logger.warning(
                    f"Không thể load BGE-M3 tokenizer: {e}. "
                    f"Dùng heuristic word_count * 1.5 thay thế."
                )
                cls._tokenizer = None
        return cls._tokenizer

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text using heuristics.
        
        ✅ P1#4: Dùng BGE-M3/XLM-RoBERTa tokenizer thật để đếm token chính xác.
        - Base: word count
        - Multiplier: 1.5x for Vietnamese/Asian languages and complex text
        - Add buffer for punctuation and special chars
        - Handle long texts by truncating before encoding to avoid sequence length errors
        """
        if not text:
            return 0
        
        # BGE-M3 max_length is 8192 tokens
        # For safety, we'll estimate and truncate at ~6000 chars (conservative estimate)
        # This prevents the "Token indices sequence length is longer than the specified maximum" error
        MAX_ENCODE_CHARS = 6000
        
        # P1#4: Dung BGE-M3/XLM-RoBERTa tokenizer that neu co
        tokenizer = self._get_tokenizer()
        if tokenizer is not None:
            try:
                # Only encode a truncated portion to avoid exceeding model limits
                text_truncated = text[:MAX_ENCODE_CHARS]
                encoding = tokenizer.encode(text_truncated, add_special_tokens=False, max_length=8192)
                
                # If text was truncated, estimate remaining tokens
                if len(text) > MAX_ENCODE_CHARS:
                    # Estimate tokens for remaining text using heuristic
                    remaining_text = text[MAX_ENCODE_CHARS:]
                    word_count_remaining = len(remaining_text.split())
                    estimated_remaining = int(word_count_remaining * 1.5)
                    return max(1, len(encoding) + estimated_remaining)
                
                return max(1, len(encoding))
            except Exception as e:
                logger.warning('Tokenizer encode failed (%s), using heuristic fallback', str(e))
        
        # Fallback heuristic - always used for long texts
        word_count = len(text.split())
        estimated_tokens = int(word_count * 1.5)
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', text))
        estimated_tokens += min(special_chars, word_count // 2)
        return max(1, estimated_tokens)
    
    # ============================================================================
    # TEXT CHUNKING
    # ============================================================================
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        structured_document=None,
    ) -> List[Dict[str, Any]]:
        """
        Split text into semantic chunks
        
        Args:
            text: Document text
            metadata: Metadata to attach to each chunk
                (e.g., {'document_id': 1, 'source': 'pdf'})
        
        Returns:
            List of chunk dicts: {
                'text': str,
                'start_char': int,
                'end_char': int,
                'metadata': dict,
                'sequence': int,
            }
        
        Example:
            chunks = chunker.chunk_text(
                "Large document...",
                {'document_id': 123}
            )
            
            for i, chunk in enumerate(chunks):
                print(f"Chunk {i}: {len(chunk['text'])} chars")
        """
        try:
            if not text or len(text.strip()) == 0:
                raise DocumentProcessingError("Empty text cannot be chunked")
            
            merged_metadata = metadata or {}
            file_type = (merged_metadata.get('file_type') or '').lower()
            structured_document = structured_document or merged_metadata.get('structured_document')
            doc_text = getattr(structured_document, 'text', '') or ''
            self._apply_chunk_profile(file_type, doc_text=doc_text)

            if self._is_spreadsheet_file_type(file_type):
                return self._chunk_spreadsheet_text(text, merged_metadata)

            word_spans = self._build_word_spans(text, merged_metadata)

            # Fallback to char windows when text has no word spans (edge cases)
            if not word_spans:
                return self._chunk_by_character_windows(text, merged_metadata)

            breakpoints = self._build_structural_breakpoints(text, word_spans)
            window_indices = self._build_token_windows(len(word_spans), breakpoints)
            result_chunks = []
            for seq, (start_token, end_token) in enumerate(window_indices):
                raw_start_char = word_spans[start_token][0]
                start_char = self._clean_chunk_start(text, raw_start_char) if seq > 0 else raw_start_char
                end_char = word_spans[end_token - 1][1]
                chunk_text = text[start_char:end_char]
                if (
                    seq > 0
                    and start_char < raw_start_char
                    and self._estimate_token_count(chunk_text) > self._max_clean_chunk_tokens()
                ):
                    start_char = raw_start_char
                    chunk_text = text[start_char:end_char]

                result_chunks.append({
                    'text': chunk_text,
                    'start_char': start_char,
                    'end_char': end_char,
                    'token_start': start_token,
                    'token_end': end_token,
                    'token_count': self._estimate_token_count(chunk_text),
                    'metadata': merged_metadata,
                    'sequence': seq,
                })
            
            logger.info(
                f"Chunked text into {len(result_chunks)} chunks "
                f"(avg {len(text) // len(result_chunks) if result_chunks else 0} chars, strategy={self.strategy_name})"
            )
            
            return result_chunks
        
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to chunk text: {str(e)}")
    
    def chunk_by_pages(
        self,
        page_aware_text,
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hierarchical chunking: Split by pages, then chunk within each page.
        
        Each chunk belongs to exactly ONE page (no cross-page chunks).
        
        Args:
            page_aware_text: PageAwareText object with page boundaries
            metadata: Document metadata
            
        Returns:
            List of chunks with accurate page_number and page_index
            
        Example:
            Doc 10 pages
            Page 1 (2000 tokens) → 10 chunks (200 tokens each)
            Page 2 (1500 tokens) → 8 chunks (200 tokens each)
            ...
            Each chunk has page_number set correctly
        """
        try:
            if not page_aware_text:
                raise DocumentProcessingError("page_aware_text is required for page-aware chunking")
            
            text = page_aware_text.text
            boundaries = page_aware_text.boundaries
            total_pages = page_aware_text.total_pages
            
            if not text or len(text.strip()) == 0:
                raise DocumentProcessingError("Empty text cannot be chunked")
            
            merged_metadata = metadata or {}
            page_aware_metadata = getattr(page_aware_text, 'metadata', {}) or {}
            if page_aware_metadata:
                merged_metadata = {
                    **merged_metadata,
                    'page_aware_metadata': page_aware_metadata,
                }
            file_type = (merged_metadata.get('file_type') or '').lower()
            self._apply_chunk_profile(file_type, doc_text=text)
            if self._is_spreadsheet_file_type(file_type):
                return self._chunk_spreadsheet_text(text, merged_metadata)
            
            logger.info(
                f"🔍 [CHUNK_BY_PAGES] Starting hierarchical chunking\n"
                f"   📄 Total pages: {total_pages}\n"
                f"   💾 Total text length: {len(text)} chars"
            )
            
            all_chunks = []
            global_sequence = 0
            page_chunk_stats = {}
            
            # Process each page
            for page_idx, boundary in enumerate(boundaries):
                page_number = boundary.page_number
                page_start = boundary.char_start
                page_end = boundary.char_end or len(text)
                
                # Extract page text
                page_text = text[page_start:page_end]
                
                if not page_text or len(page_text.strip()) < 10:
                    logger.debug(f"⏭️  Skipping empty page {page_number}")
                    continue
                
                page_length = len(page_text)
                page_words = len(page_text.split())
                
                # Chunk this page
                page_chunks = self._chunk_page(
                    page_text,
                    page_number,
                    page_start,
                    merged_metadata
                )
                
                # Track stats
                page_chunk_stats[page_number] = {
                    'count': len(page_chunks),
                    'chars': page_length,
                    'words': page_words,
                }
                
                # Log page processing
                logger.info(
                    f"📌 [PAGE {page_number}] Processed\n"
                    f"   ✂️  Chunks: {len(page_chunks)}\n"
                    f"   📝 Content: {page_length} chars | {page_words} words"
                )
                
                # Add global sequence and page sequence
                for idx, chunk in enumerate(page_chunks):
                    chunk['sequence'] = global_sequence
                    chunk['page_index'] = idx  # Chunk index within this page
                    all_chunks.append(chunk)
                    global_sequence += 1
            
            # Format summary without backslash in f-string
            summary_parts = [f"Page {p}:{s['count']} chunks" for p, s in sorted(page_chunk_stats.items())]
            summary_str = ", ".join(summary_parts)
            
            logger.info(
                f"✅ [HIERARCHY COMPLETE] {len(all_chunks)} total chunks from {total_pages} pages\n"
                f"   📊 Summary: {summary_str}"
            )
            
            return all_chunks
        
        except Exception as e:
            logger.error(f"Error in hierarchical chunking: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to chunk by pages: {str(e)}")

    def chunk_structured_document(
        self,
        structured_document,
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk a structured document by blocks first, then token windows.

        This preserves tables, images, and equations as atomic evidence where
        possible, and carries MinerU-like metadata into DocumentChunk.metadata.
        """
        try:
            if not structured_document:
                raise DocumentProcessingError("structured_document is required")

            merged_metadata = metadata or {}
            file_type = (merged_metadata.get('file_type') or '').lower()
            doc_text = getattr(structured_document, 'text', '') or ''
            self._apply_chunk_profile(file_type, doc_text=doc_text)

            blocks = [
                block for block in structured_document.blocks(include_discarded=False)
                if self._structured_block_text(block)
            ]
            if not blocks:
                return self.chunk_text(
                    getattr(structured_document, 'text', '') or '',
                    merged_metadata,
                    structured_document=structured_document,
                )

            chunks: List[Dict[str, Any]] = []
            sequence = 0
            text_buffer: List[str] = []
            buffer_blocks: List[Any] = []
            buffer_page = None
            buffer_heading_path: List[str] = []

            def flush_text_buffer():
                nonlocal sequence, text_buffer, buffer_blocks, buffer_page, buffer_heading_path
                text = "\n\n".join(part for part in text_buffer if part).strip()
                if not text:
                    text_buffer = []
                    buffer_blocks = []
                    return

                block_metadata = self._merge_structured_block_metadata(buffer_blocks)
                base_meta = {
                    **merged_metadata,
                    **block_metadata,
                    'block_type': block_metadata.get('block_type') or 'paragraph',
                    'block_types': block_metadata.get('block_types') or ['paragraph'],
                    'heading_path': buffer_heading_path or block_metadata.get('heading_path') or [],
                    'parse_backend': getattr(structured_document, 'parse_backend', 'local_page_aware'),
                    'structured_chunk': True,
                }

                for sub_chunk in self._split_structured_text_if_needed(
                    text=text,
                    metadata=base_meta,
                    page_number=buffer_page or block_metadata.get('page_number') or 1,
                    sequence_start=sequence,
                ):
                    chunks.append(sub_chunk)
                    sequence += 1

                text_buffer = []
                buffer_blocks = []
                buffer_page = None
                buffer_heading_path = []

            for block in blocks:
                block_type = self._get_block_attr(block, 'type') or 'paragraph'
                block_text = self._structured_block_text(block)
                if not block_text:
                    continue

                page_number = int(self._get_block_attr(block, 'page_idx', 0) or 0) + 1
                heading_path = list(self._get_block_attr(block, 'heading_path', []) or [])

                if block_type in {'table', 'image', 'chart'}:
                    flush_text_buffer()
                    atomic_chunks = self._chunk_atomic_structured_block(
                        block=block,
                        text=block_text,
                        metadata=merged_metadata,
                        sequence_start=sequence,
                        parse_backend=getattr(structured_document, 'parse_backend', 'local_page_aware'),
                    )
                    chunks.extend(atomic_chunks)
                    sequence += len(atomic_chunks)
                    continue

                if block_type == 'equation':
                    # Equations are semantically tied to nearby prose. Keep
                    # them in the text buffer unless the buffer is already full.
                    if text_buffer and self._estimate_token_count("\n\n".join(text_buffer + [block_text])) > self.chunk_size:
                        flush_text_buffer()
                    text_buffer.append(block_text)
                    buffer_blocks.append(block)
                    buffer_page = buffer_page or page_number
                    buffer_heading_path = heading_path or buffer_heading_path
                    continue

                if block_type == 'title':
                    # Parser backends sometimes mark list labels and short
                    # clause starts as titles. Treat only real section headings
                    # as hard boundaries; otherwise keep the label with the
                    # following content so retrieval gets a complete thought.
                    if (
                        text_buffer
                        and self._is_structural_title_boundary(block_text)
                        and self._buffer_has_substantive_content(buffer_blocks, text_buffer)
                    ):
                        flush_text_buffer()
                    text_buffer.append(block_text)
                    buffer_blocks.append(block)
                    buffer_page = page_number
                    buffer_heading_path = heading_path
                    continue

                if (
                    buffer_page is not None
                    and page_number != buffer_page
                    and self._buffer_has_substantive_content(buffer_blocks, text_buffer)
                ):
                    flush_text_buffer()

                projected = "\n\n".join(text_buffer + [block_text])
                if (
                    text_buffer
                    and self._estimate_token_count(projected) > self.chunk_size
                    and self._buffer_has_substantive_content(buffer_blocks, text_buffer)
                ):
                    flush_text_buffer()

                text_buffer.append(block_text)
                buffer_blocks.append(block)
                buffer_page = buffer_page or page_number
                buffer_heading_path = heading_path or buffer_heading_path

            flush_text_buffer()
            chunks = self._merge_adjacent_small_structured_chunks(chunks)
            self._repair_contextless_chunk_starts(chunks)
            self._renumber_chunks(chunks)

            logger.info(
                f"Structured chunking produced {len(chunks)} chunks "
                f"from {len(blocks)} blocks (strategy={self.strategy_name})"
            )
            return chunks
        except Exception as e:
            logger.error(f"Error in structured chunking: {e}", exc_info=True)
            raise DocumentProcessingError(f"Failed to chunk structured document: {e}")

    def _get_block_attr(self, block, name: str, default=None):
        if isinstance(block, dict):
            return block.get(name, default)
        return getattr(block, name, default)

    def _structured_block_text(self, block) -> str:
        block_type = self._get_block_attr(block, 'type') or ''
        if hasattr(block, 'content_text'):
            raw_text = block.content_text()
        elif isinstance(block, dict):
            raw_text = (
                block.get('html')
                or block.get('latex')
                or block.get('caption')
                or block.get('text')
                or ''
            )
        else:
            raw_text = str(block or '')

        return self._normalize_structured_block_text(raw_text, block_type)

    def _normalize_structured_block_text(self, text: str, block_type: str = '') -> str:
        """Normalize prose extracted from structured/PDF parsers.

        Tables and HTML blocks keep their line structure. Prose blocks get
        layout line-wraps removed, including PDF word splits like
        ``kế t\noán`` and ``l\n\niên``.
        """
        if not text:
            return ''

        normalized = str(text).replace('\r\n', '\n').replace('\r', '\n').strip()
        if not normalized:
            return ''

        block_kind = (block_type or '').lower()
        if block_kind in {'table', 'image', 'chart', 'equation'} or self._looks_like_table_text(normalized):
            normalized = re.sub(r'[ \t]+', ' ', normalized)
            normalized = re.sub(r'\n{3,}', '\n\n', normalized)
            return normalized.strip()

        normalized = re.sub(r'[ \t]*\n+[ \t]*', ' ', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized)
        return normalized.strip()

    @staticmethod
    def _looks_like_table_text(text: str) -> bool:
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return False
        table_like = sum(
            1 for line in lines[:8]
            if line.startswith('|') or '<table' in line.lower() or '</tr>' in line.lower()
        )
        return table_like >= 2

    def _is_structural_title_boundary(self, text: str) -> bool:
        """Return True for headings that should start a new chunk."""
        clean = re.sub(r'\s+', ' ', (text or '').strip())
        if not clean:
            return False

        if clean.endswith(':'):
            return False

        # Numbered list items such as 1., 23.1.1 or 19.7 are content, not
        # chunk boundaries, even when the parser labels them as titles.
        if re.match(r'^\d+(?:\.\d+)*[.)]\s+', clean):
            return False

        if any(pattern.match(clean) for pattern in _VI_HEADING_PATTERNS):
            return True

        letters = [ch for ch in clean if ch.isalpha()]
        if len(letters) >= 8:
            upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
            if upper_ratio >= 0.75:
                return True

        return False

    def _buffer_has_substantive_content(self, blocks: List[Any], text_parts: List[str]) -> bool:
        """True when the current structured buffer has real body content.

        Heading-only buffers should stay attached to following content, even if
        another heading arrives or the first body block would push the token
        estimate over the normal chunk target.
        """
        if not text_parts:
            return False

        non_title_blocks = [
            block for block in blocks
            if (self._get_block_attr(block, 'type') or '').lower() != 'title'
        ]
        if non_title_blocks:
            return True

        text = "\n\n".join(part for part in text_parts if part).strip()
        if not text:
            return False

        min_tokens = self._min_meaningful_chunk_tokens()
        return self._estimate_token_count(text) >= min_tokens

    def _min_meaningful_chunk_tokens(self) -> int:
        configured = int(getattr(settings, 'RAG_MIN_MEANINGFUL_CHUNK_TOKENS', 0) or 0)
        if configured > 0:
            return configured
        validator_min = int(getattr(settings, 'CHUNK_VALIDATOR_MIN_TOKENS', 20))
        proportional = int(max(validator_min, self.chunk_size * 0.15))
        return max(20, min(96, proportional))

    def _min_meaningful_chunk_chars(self) -> int:
        configured = int(getattr(settings, 'RAG_MIN_MEANINGFUL_CHUNK_CHARS', 0) or 0)
        if configured > 0:
            return configured
        validator_min = int(getattr(settings, 'CHUNK_VALIDATOR_MIN_CHARS', 50))
        return max(120, min(320, validator_min * 3))

    def _merge_adjacent_small_structured_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge heading-only and tiny structured chunks into adjacent context.

        This keeps RAG evidence units meaningful without changing source text:
        the operation only changes chunk boundaries.
        """
        if len(chunks) <= 1:
            return chunks

        result: List[Dict[str, Any]] = []
        index = 0
        while index < len(chunks):
            current = chunks[index]

            if (
                self._should_merge_small_chunk(current)
                and index + 1 < len(chunks)
                and self._can_merge_chunks(current, chunks[index + 1])
            ):
                result.append(self._merge_chunk_pair(current, chunks[index + 1]))
                index += 2
                continue

            if (
                self._should_merge_small_chunk(current)
                and result
                and self._can_merge_chunks(result[-1], current)
            ):
                result[-1] = self._merge_chunk_pair(result[-1], current)
                index += 1
                continue

            result.append(current)
            index += 1

        # A single pass can leave a small merged heading before content when
        # there were multiple adjacent title blocks. One extra bounded pass
        # handles that without accidentally building giant chunks.
        if len(result) < len(chunks):
            second_pass: List[Dict[str, Any]] = []
            index = 0
            while index < len(result):
                current = result[index]
                if (
                    self._should_merge_small_chunk(current)
                    and index + 1 < len(result)
                    and self._can_merge_chunks(current, result[index + 1])
                ):
                    second_pass.append(self._merge_chunk_pair(current, result[index + 1]))
                    index += 2
                else:
                    second_pass.append(current)
                    index += 1
            result = second_pass

        return result

    def _should_merge_small_chunk(self, chunk: Dict[str, Any]) -> bool:
        if not chunk or self._is_atomic_chunk(chunk):
            return False

        text = (chunk.get('text') or '').strip()
        if not text:
            return False

        metadata = chunk.get('metadata') or {}
        token_count = int(chunk.get('token_count') or self._estimate_token_count(text))
        if token_count < self._min_meaningful_chunk_tokens():
            return True
        if len(text) < self._min_meaningful_chunk_chars():
            return True
        if metadata.get('block_type') == 'title' and self._is_structural_title_boundary(text):
            return True
        return False

    @staticmethod
    def _is_atomic_chunk(chunk: Dict[str, Any]) -> bool:
        metadata = chunk.get('metadata') or {}
        if metadata.get('atomic_block') or metadata.get('table_preserved'):
            return True
        block_type = metadata.get('block_type')
        block_types = metadata.get('block_types') or []
        if block_type in {'table', 'image', 'chart', 'equation'}:
            return True
        return any(item in {'table', 'image', 'chart', 'equation'} for item in block_types)

    def _can_merge_chunks(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        left_text = (left.get('text') or '').strip()
        right_text = (right.get('text') or '').strip()
        if not left_text or not right_text:
            return False

        merged_text = f"{left_text}\n\n{right_text}"
        merged_tokens = self._estimate_token_count(merged_text)
        max_merge_tokens = int(getattr(
            settings,
            'RAG_MAX_MERGED_CHUNK_TOKENS',
            max(self.chunk_size, int(self.chunk_size * 1.25)),
        ))
        if merged_tokens > max_merge_tokens:
            return False

        left_meta = left.get('metadata') or {}
        right_meta = right.get('metadata') or {}
        left_page = left.get('page_number') or left_meta.get('page_number')
        right_page = right.get('page_number') or right_meta.get('page_number')
        if left_page and right_page and abs(int(left_page) - int(right_page)) > 1:
            return False

        if self._is_atomic_chunk(left) or self._is_atomic_chunk(right):
            return self._can_merge_atomic_context(left, right)

        return True

    def _can_merge_atomic_context(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        """Allow tiny captions/header fragments to stay attached to tables.

        Tables remain atomic by default. The only exception is a very small
        adjacent non-atomic chunk that looks like table context, such as a
        markdown header row extracted separately from the table body.
        """
        left_is_table = self._is_table_chunk(left)
        right_is_table = self._is_table_chunk(right)
        if left_is_table == right_is_table:
            return False

        table_chunk = left if left_is_table else right
        context_chunk = right if left_is_table else left
        if self._is_atomic_chunk(context_chunk):
            return False

        context_text = (context_chunk.get('text') or '').strip()
        if not context_text:
            return False

        context_tokens = int(context_chunk.get('token_count') or self._estimate_token_count(context_text))
        if context_tokens > self._min_meaningful_chunk_tokens():
            return False
        if len(context_text) > self._min_meaningful_chunk_chars():
            return False

        if not self._looks_like_table_context(context_text):
            return False

        table_text = (table_chunk.get('text') or '').strip()
        merged_tokens = self._estimate_token_count(f"{context_text}\n\n{table_text}")
        max_table_merge_tokens = int(getattr(
            settings,
            'RAG_MAX_TABLE_CONTEXT_MERGE_TOKENS',
            max(self.table_chunk_max_tokens, self.chunk_size),
        ))
        return merged_tokens <= max_table_merge_tokens

    @staticmethod
    def _is_table_chunk(chunk: Dict[str, Any]) -> bool:
        metadata = chunk.get('metadata') or {}
        block_type = metadata.get('block_type')
        block_types = metadata.get('block_types') or []
        return bool(
            metadata.get('table_preserved')
            or block_type == 'table'
            or 'table' in block_types
        )

    @staticmethod
    def _looks_like_table_context(text: str) -> bool:
        clean = re.sub(r'\s+', ' ', (text or '').strip())
        if not clean:
            return False
        if '|' in clean:
            cells = [part.strip() for part in clean.split('|') if part.strip()]
            return len(cells) >= 2
        return clean.endswith(':') or bool(re.match(r'^(bảng|table)\s+\d+', clean, flags=re.IGNORECASE))

    def _merge_chunk_pair(
        self,
        left: Dict[str, Any],
        right: Dict[str, Any],
    ) -> Dict[str, Any]:
        left_text = (left.get('text') or '').strip()
        right_text = (right.get('text') or '').strip()
        merged_text = f"{left_text}\n\n{right_text}".strip()

        left_meta = left.get('metadata') or {}
        right_meta = right.get('metadata') or {}
        left_pages = self._chunk_page_range(left)
        right_pages = self._chunk_page_range(right)
        page_range = [
            min(left_pages[0], right_pages[0]),
            max(left_pages[1], right_pages[1]),
        ]

        block_types = []
        for value in (left_meta.get('block_types') or [left_meta.get('block_type')]):
            if value and value not in block_types:
                block_types.append(value)
        for value in (right_meta.get('block_types') or [right_meta.get('block_type')]):
            if value and value not in block_types:
                block_types.append(value)

        merged_from_sequences = []
        for item in (
            left_meta.get('merged_from_sequences'),
            [left.get('sequence')],
            right_meta.get('merged_from_sequences'),
            [right.get('sequence')],
        ):
            if isinstance(item, (list, tuple)):
                for value in item:
                    if value is not None and value not in merged_from_sequences:
                        merged_from_sequences.append(value)

        metadata = {
            **left_meta,
            **right_meta,
            'block_type': block_types[0] if len(block_types) == 1 else 'mixed',
            'block_types': block_types,
            'page_number': page_range[0],
            'page_range': page_range,
            'merged_small_chunk': True,
            'merged_from_sequences': merged_from_sequences,
        }

        if left_meta.get('heading_path') or right_meta.get('heading_path'):
            metadata['heading_path'] = right_meta.get('heading_path') or left_meta.get('heading_path') or []

        for key, fn in (
            ('reading_order_start', min),
            ('line_start', min),
            ('start_char', min),
        ):
            values = [v for v in (left.get(key), right.get(key), left_meta.get(key), right_meta.get(key)) if v is not None]
            if values:
                metadata[key] = fn(values)
        for key, fn in (
            ('reading_order_end', max),
            ('line_end', max),
            ('end_char', max),
        ):
            values = [v for v in (left.get(key), right.get(key), left_meta.get(key), right_meta.get(key)) if v is not None]
            if values:
                metadata[key] = fn(values)

        return {
            **left,
            'text': merged_text,
            'start_char': min(left.get('start_char', 0) or 0, right.get('start_char', 0) or 0),
            'end_char': max(left.get('end_char', 0) or 0, right.get('end_char', 0) or 0),
            'token_start': left.get('token_start', 0),
            'token_end': right.get('token_end', left.get('token_end', 0)),
            'token_count': self._estimate_token_count(merged_text),
            'page_number': page_range[0],
            'page_range': page_range,
            'metadata': metadata,
        }

    @staticmethod
    def _chunk_page_range(chunk: Dict[str, Any]) -> List[int]:
        metadata = chunk.get('metadata') or {}
        page_range = chunk.get('page_range') or metadata.get('page_range')
        if isinstance(page_range, (list, tuple)) and len(page_range) >= 2:
            return [int(page_range[0] or 1), int(page_range[1] or page_range[0] or 1)]
        page = chunk.get('page_number') or metadata.get('page_number') or 1
        return [int(page), int(page)]

    @staticmethod
    def _renumber_chunks(chunks: List[Dict[str, Any]]) -> None:
        for sequence, chunk in enumerate(chunks):
            chunk['sequence'] = sequence

    def _merge_structured_block_metadata(self, blocks: List[Any]) -> Dict[str, Any]:
        if not blocks:
            return {}

        block_types = []
        bboxes = []
        reading_orders = []
        heading_path = []
        page_numbers = []
        line_starts = []
        line_ends = []

        for block in blocks:
            block_type = self._get_block_attr(block, 'type')
            if block_type and block_type not in block_types:
                block_types.append(block_type)
            bbox = self._get_block_attr(block, 'bbox')
            if bbox:
                bboxes.append(bbox)
            reading_order = self._get_block_attr(block, 'reading_order')
            if reading_order is not None:
                reading_orders.append(reading_order)
            block_heading_path = self._get_block_attr(block, 'heading_path') or []
            if block_heading_path:
                heading_path = list(block_heading_path)
            page_numbers.append(int(self._get_block_attr(block, 'page_idx', 0) or 0) + 1)
            metadata = self._get_block_attr(block, 'metadata', {}) or {}
            if metadata.get('line_start'):
                line_starts.append(metadata.get('line_start'))
            if metadata.get('line_end'):
                line_ends.append(metadata.get('line_end'))

        return {
            'block_type': block_types[0] if len(block_types) == 1 else 'mixed',
            'block_types': block_types,
            'bbox': bboxes[0] if len(bboxes) == 1 else None,
            'bboxes': bboxes,
            'reading_order_start': min(reading_orders) if reading_orders else None,
            'reading_order_end': max(reading_orders) if reading_orders else None,
            'heading_path': heading_path,
            'page_number': min(page_numbers) if page_numbers else 1,
            'page_range': [min(page_numbers), max(page_numbers)] if page_numbers else [1, 1],
            'line_start': min(line_starts) if line_starts else None,
            'line_end': max(line_ends) if line_ends else None,
        }

    def _split_structured_text_if_needed(
        self,
        text: str,
        metadata: Dict[str, Any],
        page_number: int,
        sequence_start: int,
    ) -> List[Dict[str, Any]]:
        token_count = self._estimate_token_count(text)
        if token_count <= self.chunk_size:
            return [{
                'text': text,
                'start_char': 0,
                'end_char': len(text),
                'token_start': 0,
                'token_end': token_count,
                'token_count': token_count,
                'page_number': page_number,
                'metadata': {
                    **metadata,
                    'page_number': page_number,
                },
                'sequence': sequence_start,
            }]

        sub_chunks = self.chunk_text(text, metadata)
        for offset, chunk in enumerate(sub_chunks):
            if offset > 0:
                self._prepend_split_context(chunk, text, metadata)
            chunk['page_number'] = page_number
            chunk['sequence'] = sequence_start + offset
            chunk['metadata'] = {
                **(chunk.get('metadata') or {}),
                **metadata,
                'page_number': page_number,
                'structured_split': True,
            }
        return sub_chunks

    def _chunk_atomic_structured_block(
        self,
        block,
        text: str,
        metadata: Dict[str, Any],
        sequence_start: int,
        parse_backend: str,
    ) -> List[Dict[str, Any]]:
        block_type = self._get_block_attr(block, 'type') or 'paragraph'
        page_number = int(self._get_block_attr(block, 'page_idx', 0) or 0) + 1
        block_meta = self._merge_structured_block_metadata([block])
        block_specific = self._get_block_attr(block, 'metadata', {}) or {}
        base_metadata = {
            **metadata,
            **block_meta,
            **block_specific,
            'block_type': block_type,
            'block_types': [block_type],
            'heading_path': self._get_block_attr(block, 'heading_path', []) or [],
            'parse_backend': parse_backend,
            'structured_chunk': True,
            'atomic_block': True,
            'table_id': self._get_block_attr(block, 'table_id'),
            'image_id': self._get_block_attr(block, 'image_id'),
        }

        if block_type == 'table':
            return self._chunk_structured_table_block(
                text=text,
                metadata=base_metadata,
                page_number=page_number,
                sequence_start=sequence_start,
            )

        token_count = self._estimate_token_count(text)
        if token_count <= self.chunk_size:
            return [{
                'text': text,
                'start_char': 0,
                'end_char': len(text),
                'token_start': 0,
                'token_end': token_count,
                'token_count': token_count,
                'page_number': page_number,
                'metadata': {
                    **base_metadata,
                    'page_number': page_number,
                },
                'sequence': sequence_start,
            }]

        chunks = self._split_structured_text_if_needed(text, base_metadata, page_number, sequence_start)
        for chunk in chunks:
            chunk['metadata']['atomic_block_split'] = True
        return chunks

    def _prepend_split_context(
        self,
        chunk: Dict[str, Any],
        source_text: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Prefix continuation chunks with nearby section context for RAG.

        Sliding-window overlap can legitimately start a continuation in the
        middle of a sentence. Prefixing the nearest heading keeps each stored
        chunk self-contained without mutating the extracted source text itself.
        """
        chunk_text = (chunk.get('text') or '').lstrip()
        if not chunk_text:
            return

        start_char = int(chunk.get('start_char') or 0)
        prefix = self._split_context_prefix(source_text, start_char, metadata)
        if not prefix or chunk_text.startswith(prefix):
            return
        prefix_lines = prefix.splitlines()
        while prefix_lines and chunk_text.startswith(prefix_lines[-1]):
            prefix_lines.pop()
        prefix = "\n".join(prefix_lines).strip()
        if not prefix:
            return

        chunk['text'] = f"{prefix}\n\n{chunk_text}"
        chunk['token_count'] = self._estimate_token_count(chunk['text'])
        chunk_metadata = chunk.get('metadata') or {}
        chunk_metadata.update({
            'context_prefix_added': True,
            'context_prefix': prefix,
        })
        chunk['metadata'] = chunk_metadata

    def _split_context_prefix(
        self,
        source_text: str,
        start_char: int,
        metadata: Dict[str, Any],
    ) -> str:
        heading_path = [
            str(item).strip()
            for item in (metadata.get('heading_path') or [])
            if self._is_context_prefix_line(str(item).strip())
        ]

        before = source_text[:max(0, start_char)]
        nearby_headings: List[str] = []
        for raw_line in before.splitlines():
            line = re.sub(r'\s+', ' ', raw_line).strip()
            if not line or len(line) > 180:
                continue
            if self._is_context_prefix_line(line):
                if line not in nearby_headings:
                    nearby_headings.append(line)

        prefix_lines = (heading_path + nearby_headings)[-3:]
        if not prefix_lines:
            first_lines = [
                re.sub(r'\s+', ' ', line).strip()
                for line in source_text.splitlines()
                if line.strip()
            ]
            prefix_lines = first_lines[:2]

        cleaned: List[str] = []
        for line in prefix_lines:
            if line and line not in cleaned:
                cleaned.append(line)
        return "\n".join(cleaned).strip()

    @staticmethod
    def _looks_like_section_context(text: str) -> bool:
        clean = re.sub(r'\s+', ' ', (text or '').strip())
        if not clean:
            return False
        if re.match(r'(?i)^(chương|điều|mục|phần|khoản)\s+[IVXLCDM\d]+', clean):
            return True
        letters = [ch for ch in clean if ch.isalpha()]
        if len(letters) >= 8:
            upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
            return upper_ratio >= 0.75
        return False

    def _is_context_prefix_line(self, text: str) -> bool:
        clean = re.sub(r'\s+', ' ', (text or '').strip())
        if not clean or len(clean) > 180:
            return False
        if re.match(r'^\d+\.\d+(?:\.\d+)*[.)]?\s+\S', clean):
            return True
        if re.match(r'^\d+[.)]\s+', clean):
            return False
        return self._is_structural_title_boundary(clean) or self._looks_like_section_context(clean)

    def _repair_contextless_chunk_starts(self, chunks: List[Dict[str, Any]]) -> None:
        for index, chunk in enumerate(chunks):
            text = (chunk.get('text') or '').lstrip()
            if not text or not self._has_contextless_start(text):
                continue

            metadata = chunk.get('metadata') or {}
            prefix = self._chunk_context_prefix_from_neighbors(chunks, index)
            if not prefix:
                prefix = self._metadata_context_prefix(metadata)
            if not prefix:
                prefix = self._context_from_chunk_text(text)
            if not prefix or text.startswith(prefix):
                continue

            chunk['text'] = f"{prefix}\n\n{text}"
            chunk['token_count'] = self._estimate_token_count(chunk['text'])
            metadata.update({
                'context_prefix_added': True,
                'context_prefix': prefix,
                'context_prefix_reason': 'contextless_start',
            })
            chunk['metadata'] = metadata

    @staticmethod
    def _has_contextless_start(text: str) -> bool:
        clean = re.sub(r'\s+', ' ', (text or '').strip())
        if not clean:
            return False
        if re.match(r'^(chương|điều|mục|phần|khoản)\b', clean, flags=re.IGNORECASE):
            return False
        if re.match(r'^\d+(?:\.\d+)*[.)]\s+', clean):
            return False
        if re.match(r'^[A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]{2,}\b', clean):
            return False
        first_word_match = re.match(r'^([\wÀ-ỹ]+)', clean, flags=re.UNICODE)
        if not first_word_match:
            return False
        first = first_word_match.group(1)
        broken_fragments = {'n', 'vị', 'rong', 'hực', 'ịnh', 'định', 'ủa', 'ác', 'ững', 'nghề'}
        if first.lower() in broken_fragments:
            return True
        return first[:1].islower()

    def _metadata_context_prefix(self, metadata: Dict[str, Any]) -> str:
        lines = [
            str(item).strip()
            for item in (metadata.get('heading_path') or [])
            if self._is_context_prefix_line(str(item).strip())
        ]
        return "\n".join(lines[-3:]).strip()

    def _chunk_context_prefix_from_neighbors(
        self,
        chunks: List[Dict[str, Any]],
        index: int,
    ) -> str:
        for prev_index in range(index - 1, max(-1, index - 4), -1):
            prev_text = (chunks[prev_index].get('text') or '').strip()
            candidates = self._extract_context_lines(prev_text)
            if candidates:
                return "\n".join(candidates[-3:]).strip()
        return ''

    def _context_from_chunk_text(self, text: str) -> str:
        candidates = self._extract_context_lines(text[:900])
        return "\n".join(candidates[:2]).strip()

    def _extract_context_lines(self, text: str) -> List[str]:
        candidates: List[str] = []
        for raw_line in (text or '').splitlines():
            line = re.sub(r'\s+', ' ', raw_line).strip()
            if self._is_context_prefix_line(line) and line not in candidates:
                candidates.append(line)
        inline_patterns = [
            r'(?i)\b(chương\s+[IVXLCDM\d]+(?:\s+[^.;:\n]{0,80})?)',
            r'(?i)\b(điều\s+\d+[.:]?\s+[^.;:\n]{0,120})',
            r'\b(\d+\.\d+(?:\.\d+)*[.)]?\s+[^.;:\n]{0,120})',
        ]
        compact = re.sub(r'\s+', ' ', text or '')
        for pattern in inline_patterns:
            for match in re.finditer(pattern, compact):
                candidate = match.group(1).strip()
                if self._is_context_prefix_line(candidate) and candidate not in candidates:
                    candidates.append(candidate)
        return candidates

    def _chunk_structured_table_block(
        self,
        text: str,
        metadata: Dict[str, Any],
        page_number: int,
        sequence_start: int,
    ) -> List[Dict[str, Any]]:
        token_count = self._estimate_token_count(text)
        if token_count <= self.table_chunk_max_tokens:
            return [{
                'text': text,
                'start_char': 0,
                'end_char': len(text),
                'token_start': 0,
                'token_end': token_count,
                'token_count': token_count,
                'page_number': page_number,
                'metadata': {
                    **metadata,
                    'page_number': page_number,
                    'content_format': metadata.get('content_format') or 'table_markdown',
                    'table_split': False,
                    'table_preserved': True,
                },
                'sequence': sequence_start,
            }]

        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return []

        # Markdown tables keep the first two lines as repeated header when possible.
        header = lines[:2] if len(lines) >= 2 and all(line.strip().startswith('|') for line in lines[:2]) else lines[:1]
        data_lines = lines[len(header):] or lines
        chunks = []
        current_rows = []
        header_text = "\n".join(header).strip()
        sequence = sequence_start
        row_start = 1

        for row_idx, row in enumerate(data_lines, start=1):
            candidate_rows = current_rows + [row]
            candidate_text = "\n".join([header_text] + candidate_rows).strip()
            if current_rows and self._estimate_token_count(candidate_text) > self.chunk_size:
                chunk_text = "\n".join([header_text] + current_rows).strip()
                chunks.append({
                    'text': chunk_text,
                    'start_char': 0,
                    'end_char': len(chunk_text),
                    'token_start': 0,
                    'token_end': self._estimate_token_count(chunk_text),
                    'token_count': self._estimate_token_count(chunk_text),
                    'page_number': page_number,
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
                        'content_format': metadata.get('content_format') or 'table_markdown',
                        'table_split': True,
                        'table_preserved': False,
                        'row_start': row_start,
                        'row_end': row_idx - 1,
                    },
                    'sequence': sequence,
                })
                sequence += 1
                row_start = row_idx
                current_rows = [row]
            else:
                current_rows = candidate_rows

        if current_rows:
            chunk_text = "\n".join([header_text] + current_rows).strip()
            chunks.append({
                'text': chunk_text,
                'start_char': 0,
                'end_char': len(chunk_text),
                'token_start': 0,
                'token_end': self._estimate_token_count(chunk_text),
                'token_count': self._estimate_token_count(chunk_text),
                'page_number': page_number,
                'metadata': {
                    **metadata,
                    'page_number': page_number,
                    'content_format': metadata.get('content_format') or 'table_markdown',
                    'table_split': True,
                    'table_preserved': False,
                    'row_start': row_start,
                    'row_end': row_start + len(current_rows) - 1,
                },
                'sequence': sequence,
            })

        return chunks
    
    def _chunk_page(
        self,
        page_text: str,
        page_number: int,
        page_char_offset: int,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Chunk a single page using token window strategy.
        
        All chunks returned have page_number = page_number (guaranteed single page per chunk).
        
        Args:
            page_text: Text of this page
            page_number: Actual page number (1-indexed)
            page_char_offset: Character offset of page start in full document
            metadata: Document metadata
            
        Returns:
            List of chunks with page_number, no cross-page chunks
        """
        try:
            if not page_text or len(page_text.strip()) == 0:
                return []
            
            word_spans = self._build_word_spans(page_text, metadata)
            page_aware_metadata = metadata.get('page_aware_metadata') or {}
            toc_pages = {
                int(page)
                for page in (page_aware_metadata.get('toc_pages') or [])
                if str(page).isdigit() or isinstance(page, int)
            }
            is_toc_page = bool(page_aware_metadata.get('layout_role') == 'toc') or page_number in toc_pages
            
            # Fallback for pages with no word spans
            if not word_spans:
                return self._chunk_page_by_characters(
                    page_text,
                    page_number,
                    page_char_offset,
                    metadata
                )
            
            breakpoints = self._build_structural_breakpoints(page_text, word_spans)
            window_indices = self._build_token_windows(len(word_spans), breakpoints)
            
            page_chunks = []
            for seq, (start_token, end_token) in enumerate(window_indices):
                raw_start_char = word_spans[start_token][0]
                start_char = self._clean_chunk_start(page_text, raw_start_char) if seq > 0 else raw_start_char
                end_char = word_spans[end_token - 1][1]
                chunk_text = page_text[start_char:end_char]
                if (
                    seq > 0
                    and start_char < raw_start_char
                    and self._estimate_token_count(chunk_text) > self._max_clean_chunk_tokens()
                ):
                    start_char = raw_start_char
                    chunk_text = page_text[start_char:end_char]
                token_count = self._estimate_token_count(chunk_text)
                
                chunk_dict = {
                    'text': chunk_text,
                    'start_char': page_char_offset + start_char,  # Global offset
                    'end_char': page_char_offset + end_char,      # Global offset
                    'token_start': start_token,
                    'token_end': end_token,
                    'token_count': token_count,
                    'page_number': page_number,
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
                        'is_toc': is_toc_page,
                        'layout_role': 'toc' if is_toc_page else metadata.get('layout_role'),
                    },
                }
                page_chunks.append(chunk_dict)
                
                # Log individual chunk
                logger.debug(
                    f"  📌 Page {page_number} Chunk {seq}: "
                    f"{token_count} tokens | {len(chunk_text)} chars | "
                    f"Position: [{page_char_offset + start_char}:{page_char_offset + end_char}]"
                )
            
            logger.debug(
                f"📄 [PAGE {page_number}] Completed: {len(page_chunks)} chunks"
            )
            
            return page_chunks
        
        except Exception as e:
            logger.error(f"Error chunking page {page_number}: {str(e)}", exc_info=True)
            return []
    
    def _chunk_page_by_characters(
        self,
        page_text: str,
        page_number: int,
        page_char_offset: int,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fallback: chunk page by character windows."""
        page_chunks = []
        stride = max(1, self.chunk_size - self.chunk_overlap)
        start_char = 0
        seq = 0
        
        while start_char < len(page_text):
            clean_start = self._clean_chunk_start(page_text, start_char) if seq > 0 else start_char
            end_char = min(start_char + self.chunk_size, len(page_text))
            chunk_text = page_text[clean_start:end_char]
            if (
                seq > 0
                and clean_start < start_char
                and self._estimate_token_count(chunk_text) > self._max_clean_chunk_tokens()
            ):
                clean_start = start_char
                chunk_text = page_text[clean_start:end_char]
            page_aware_metadata = metadata.get('page_aware_metadata') or {}
            toc_pages = {
                int(page)
                for page in (page_aware_metadata.get('toc_pages') or [])
                if str(page).isdigit() or isinstance(page, int)
            }
            is_toc_page = bool(page_aware_metadata.get('layout_role') == 'toc') or page_number in toc_pages
            
            if chunk_text.strip():
                page_chunks.append({
                    'text': chunk_text,
                    'start_char': page_char_offset + clean_start,
                    'end_char': page_char_offset + end_char,
                    'token_start': clean_start,
                    'token_end': end_char,
                    'token_count': self._estimate_token_count(chunk_text),
                    'page_number': page_number,
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
                        'is_toc': is_toc_page,
                        'layout_role': 'toc' if is_toc_page else metadata.get('layout_role'),
                    },
                })
                seq += 1
            
            if end_char >= len(page_text):
                break
            start_char += stride
        
        return page_chunks
    
    # ============================================================================
    # CHUNKING + EMBEDDING WORKFLOW
    # ============================================================================
    
    def chunk_and_embed(
        self,
        text: str,
        document_id: str,
        embedding_client,
        qdrant_client,
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Complete workflow: chunk text + generate embeddings + store in DB
        """
        try:
            # Step 1: Chunk text
            chunks = self.chunk_text(text, metadata)
            logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Step 2: Generate embeddings + Store in DB & Qdrant
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            DocumentEmbedding = apps.get_model('documents', 'DocumentEmbedding')
            Document = apps.get_model('documents', 'Document')
            
            # Get document info for payload
            doc_obj = Document.objects.get(pk=document_id)
            
            chunks_with_embeddings = []
            prev_chunk_obj = None
            
            for idx, chunk_dict in enumerate(chunks):
                try:
                    chunk_text = chunk_dict['text']
                    
                    # 1. Generate embedding via configured embedding backend
                    embedding = self._generate_embedding(chunk_text, embedding_client)
                    if not embedding:
                        continue

                    # 2. Save Chunk to PostgreSQL
                    chunk_obj = DocumentChunk.objects.create(
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=idx,
                        token_count=chunk_dict.get('token_count', self._estimate_token_count(chunk_text)),
                        page_number=chunk_dict.get('metadata', {}).get('page_number', 1),
                        node_type='detail',
                        metadata={
                            'start_char': chunk_dict.get('start_char', 0),
                            'end_char': chunk_dict.get('end_char', 0),
                            'token_start': chunk_dict.get('token_start', 0),
                            'token_end': chunk_dict.get('token_end', 0),
                            'strategy': self.strategy_name,
                        },
                        prev_chunk=prev_chunk_obj
                    )

                    # Update sequential link
                    if prev_chunk_obj:
                        prev_chunk_obj.next_chunk = chunk_obj
                        prev_chunk_obj.save(update_fields=['next_chunk'])
                    
                    prev_chunk_obj = chunk_obj

                    # 3. Store in Qdrant (Vector DB)
                    qdrant_payload = {
                        'document_id': str(document_id),
                        'chunk_id': str(chunk_obj.id),
                        'chunk_index': idx,
                        'text': chunk_text[:500],
                        'text_preview': chunk_text[:200],
                        'node_type': 'detail',
                        'page_number': chunk_dict.get('metadata', {}).get('page_number', 1),
                        'token_count': chunk_dict.get('token_count', 0),
                        'access_scope': doc_obj.access_scope,
                        'department_id': str(doc_obj.department_id) if doc_obj.department_id else None,
                        'folder_id': str(doc_obj.folder_id) if doc_obj.folder_id else None,
                    }
                    
                    vector_id = qdrant_client.add_embedding(
                        embedding=embedding,
                        chunk_id=str(chunk_obj.id),
                        payload=qdrant_payload
                    )
                    
                    # Update chunk with vector_id
                    chunk_obj.vector_id = vector_id
                    chunk_obj.save(update_fields=['vector_id'])
                    
                    # 4. Save Embedding metadata to PostgreSQL
                    DocumentEmbedding.objects.create(
                        chunk=chunk_obj,
                        qdrant_vector_id=vector_id,
                        embedding_dimension=len(embedding),
                        embedding_model=embedding_client.model
                    )
                    
                    # Add to result list
                    chunk_dict['embedding'] = embedding
                    chunk_dict['vector_id'] = vector_id
                    chunk_dict['id'] = str(chunk_obj.id)
                    chunks_with_embeddings.append(chunk_dict)
                    
                except Exception as e:
                    logger.warning(
                        f"Error processing chunk {idx}: {str(e)}"
                    )
                    continue
            
            logger.info(
                f"Generated embeddings for {len(chunks_with_embeddings)}/{len(chunks)} chunks"
            )

            if len(chunks_with_embeddings) != len(chunks):
                raise DocumentProcessingError(
                    f"Only embedded {len(chunks_with_embeddings)}/{len(chunks)} chunks"
                )
            
            return chunks_with_embeddings
        
        except Exception as e:
            logger.error(f"Error in chunk_and_embed: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to chunk and embed: {str(e)}")
    
    # ============================================================================
    # INTERNAL - TOKEN WINDOW CHUNKING
    # ============================================================================

    def _apply_chunk_profile(self, file_type: str, doc_text: str = None) -> None:
        """Select a file-type-aware chunk profile, with optional document-type
        detection for Vietnamese internal documents.

        Document-type profiles optimize chunk size and overlap for:
        - regulations (quy định, nghị định): larger chunks, higher overlap
        - contracts (hợp đồng): medium chunks, high overlap for clause linking
        - handbooks (sổ tay, hướng dẫn): standard chunks
        - reports (báo cáo): larger chunks
        - technical (kỹ thuật): smaller chunks for precise retrieval
        """
        normalized = (file_type or '').lower().strip()
        ext = self._normalize_file_extension(normalized)

        # Detect document type from text content if available
        doc_type = None
        if doc_text and self._is_vietnamese_text(doc_text):
            doc_type = self._detect_document_type(doc_text)

        # Select base profile by file extension
        if ext == 'pdf':
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_PDF', 320)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_PDF', 64)
            profile = 'pdf'
        elif ext in ('xlsx', 'xls', 'csv'):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_SPREADSHEET', 520)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_SPREADSHEET', 80)
            profile = 'spreadsheet'
        elif ext in ('docx', 'doc', 'md', 'markdown'):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_DOC', 420)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_DOC', 84)
            profile = 'doc'
        elif ext in ('txt', 'text'):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_TEXT', 360)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_TEXT', 72)
            profile = 'text'
        else:
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE', self.chunk_size)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP', self.chunk_overlap)
            profile = 'default'

        # Apply document-type override for Vietnamese internal documents
        if doc_type:
            type_profiles = {
                'regulation': {
                    'size': getattr(settings, 'CHUNK_TOKEN_SIZE_REGULATION', 480),
                    'overlap': getattr(settings, 'CHUNK_TOKEN_OVERLAP_REGULATION', 96),
                },
                'contract': {
                    'size': getattr(settings, 'CHUNK_TOKEN_SIZE_CONTRACT', 400),
                    'overlap': getattr(settings, 'CHUNK_TOKEN_OVERLAP_CONTRACT', 100),
                },
                'handbook': {
                    'size': getattr(settings, 'CHUNK_TOKEN_SIZE_HANDBOOK', 360),
                    'overlap': getattr(settings, 'CHUNK_TOKEN_OVERLAP_HANDBOOK', 72),
                },
                'report': {
                    'size': getattr(settings, 'CHUNK_TOKEN_SIZE_REPORT', 500),
                    'overlap': getattr(settings, 'CHUNK_TOKEN_OVERLAP_REPORT', 80),
                },
                'technical': {
                    'size': getattr(settings, 'CHUNK_TOKEN_SIZE_TECHNICAL', 280),
                    'overlap': getattr(settings, 'CHUNK_TOKEN_OVERLAP_TECHNICAL', 56),
                },
            }
            override = type_profiles.get(doc_type)
            if override:
                self.chunk_size = override['size']
                self.chunk_overlap = override['overlap']
                profile = f'{profile}_{doc_type}'

        # Safeguard: BGE-M3 has max_length=8192, ensure chunk_size < 6000 for safety
        MAX_SAFE_CHUNK_SIZE = 6000
        if self.chunk_size > MAX_SAFE_CHUNK_SIZE:
            logger.warning(
                f'Chunk size {self.chunk_size} exceeds safe maximum {MAX_SAFE_CHUNK_SIZE} '
                f'for BGE-M3 (max_length=8192). Reducing to {MAX_SAFE_CHUNK_SIZE}'
            )
            self.chunk_size = MAX_SAFE_CHUNK_SIZE

        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size // 4)

        self.strategy_name = f"hybrid_structural_{profile}_{self.chunk_size}_{self.chunk_overlap}"
        logger.info(
            f"Chunk profile selected: file_type={normalized} (ext={ext}), "
            f"doc_type={doc_type or 'generic'}, strategy={self.strategy_name}"
        )

    def _detect_document_type(self, text: str) -> Optional[str]:
        """Detect Vietnamese document type from content keywords.

        Returns one of: 'regulation', 'contract', 'handbook', 'report',
        'technical', or None if no match.

        Checks the first 5000 chars which typically contain title and
        introductory sections where document type indicators appear.
        """
        sample = text[:5000]
        for doc_type, pattern in _DOC_TYPE_PATTERNS:
            if pattern.search(sample):
                return doc_type
        return None

    def _normalize_file_extension(self, file_type: str) -> str:
        """Normalize a MIME type or extension into a short extension label."""
        normalized = (file_type or '').lower().strip()
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/plain': 'txt',
            'text/markdown': 'md',
            'text/csv': 'csv',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-excel': 'xls',
        }

        if normalized in mime_to_ext:
            return mime_to_ext[normalized]
        if normalized in mime_to_ext.values():
            return normalized
        return normalized.split('.')[-1] if '.' in normalized else normalized

    def _is_spreadsheet_file_type(self, file_type: str) -> bool:
        return self._normalize_file_extension(file_type) in {'xlsx', 'xls', 'csv'}

    def _chunk_spreadsheet_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk spreadsheet markdown by complete table rows, preserving headers."""
        lines = text.splitlines()
        if not lines:
            return []

        line_offsets = []
        cursor = 0
        for line in lines:
            line_offsets.append(cursor)
            cursor += len(line) + 1

        sheet_pattern = re.compile(r'^--- Sheet:\s*(.*?)\s*\(Page\s*(\d+)\)\s*---$')
        sheet_starts = [idx for idx, line in enumerate(lines) if sheet_pattern.match(line.strip())]
        if not sheet_starts:
            sheet_starts = [0]

        result_chunks = []
        sequence = 0
        overlap_rows = min(2, max(0, self.chunk_overlap // 80))

        for sheet_order, start_line in enumerate(sheet_starts):
            end_line = sheet_starts[sheet_order + 1] if sheet_order + 1 < len(sheet_starts) else len(lines)
            sheet_lines = lines[start_line:end_line]
            sheet_match = sheet_pattern.match(lines[start_line].strip()) if start_line < len(lines) else None
            sheet_name = sheet_match.group(1).strip() if sheet_match else metadata.get('source_name', 'Sheet')
            page_number = int(sheet_match.group(2)) if sheet_match else int(metadata.get('page_number') or 1)

            table_header_index = None
            for local_idx, line in enumerate(sheet_lines):
                if line.startswith('|') and 'Excel row' in line:
                    table_header_index = local_idx
                    break

            if table_header_index is None:
                sheet_text = "\n".join(sheet_lines).strip()
                if not sheet_text:
                    continue
                start_char = line_offsets[start_line]
                end_char = line_offsets[end_line - 1] + len(lines[end_line - 1]) if end_line > start_line else start_char + len(sheet_text)
                result_chunks.append({
                    'text': sheet_text,
                    'start_char': start_char,
                    'end_char': end_char,
                    'token_start': 0,
                    'token_end': len(sheet_text.split()),
                    'token_count': self._estimate_token_count(sheet_text),
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
                        'sheet_name': sheet_name,
                        'content_format': 'spreadsheet_markdown',
                    },
                    'sequence': sequence,
                    'page_number': page_number,
                    'line_start': start_line + 1,
                    'line_end': end_line,
                })
                sequence += 1
                continue

            header_local_end = min(table_header_index + 2, len(sheet_lines))
            sheet_context = [
                line for line in sheet_lines[:table_header_index]
                if line.strip().startswith('--- Sheet:')
            ]
            repeated_header = sheet_context + [
                line for line in sheet_lines[table_header_index:header_local_end]
                if line.strip()
            ]
            data_local_indices = [
                idx for idx in range(header_local_end, len(sheet_lines))
                if self._spreadsheet_row_number(sheet_lines[idx]) is not None
            ]

            if not data_local_indices:
                continue

            chunk_start_pos = 0
            while chunk_start_pos < len(data_local_indices):
                chunk_data_indices = []
                token_total = self._estimate_token_count("\n".join(repeated_header))
                pos = chunk_start_pos

                while pos < len(data_local_indices):
                    local_idx = data_local_indices[pos]
                    row_tokens = self._estimate_token_count(sheet_lines[local_idx])
                    if chunk_data_indices and token_total + row_tokens > self.chunk_size:
                        break
                    chunk_data_indices.append(local_idx)
                    token_total += row_tokens
                    pos += 1

                if not chunk_data_indices:
                    chunk_data_indices.append(data_local_indices[pos])
                    pos += 1

                chunk_lines = repeated_header + [sheet_lines[idx] for idx in chunk_data_indices]
                chunk_text = "\n".join(chunk_lines).strip()
                first_global_line = start_line + chunk_data_indices[0]
                last_global_line = start_line + chunk_data_indices[-1]
                start_char = line_offsets[first_global_line]
                end_char = line_offsets[last_global_line] + len(lines[last_global_line])
                row_numbers = [
                    self._spreadsheet_row_number(sheet_lines[idx])
                    for idx in chunk_data_indices
                ]
                row_numbers = [row for row in row_numbers if row is not None]

                result_chunks.append({
                    'text': chunk_text,
                    'start_char': start_char,
                    'end_char': end_char,
                    'token_start': 0,
                    'token_end': len(chunk_text.split()),
                    'token_count': self._estimate_token_count(chunk_text),
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
                        'sheet_name': sheet_name,
                        'row_start': min(row_numbers) if row_numbers else None,
                        'row_end': max(row_numbers) if row_numbers else None,
                        'line_start': first_global_line + 1,
                        'line_end': last_global_line + 1,
                        'content_format': 'spreadsheet_markdown',
                    },
                    'sequence': sequence,
                    'page_number': page_number,
                    'line_start': first_global_line + 1,
                    'line_end': last_global_line + 1,
                })
                sequence += 1

                if pos >= len(data_local_indices):
                    break
                chunk_start_pos = max(pos - overlap_rows, chunk_start_pos + 1)

        logger.info(
            f"Chunked spreadsheet into {len(result_chunks)} row-preserving chunks "
            f"(strategy={self.strategy_name})"
        )
        return result_chunks

    def _spreadsheet_row_number(self, line: str) -> Optional[int]:
        match = re.match(r'^\|\s*(\d+)\s*\|', line or '')
        return int(match.group(1)) if match else None
    
    def _build_word_spans(self, text: str, metadata: Dict[str, Any] = None) -> List[tuple[int, int]]:
        """Return exact character spans for token-like units.

        Enhanced with Vietnamese-aware tokenization: when the document language
        is detected as Vietnamese, applies word segmentation (via underthesea or
        syllable-based fallback) to avoid breaking compound words mid-chunk.

        For non-Vietnamese text, the original regex-based tokenization is used.
        """
        merged_metadata = metadata or {}
        force_vi = merged_metadata.get('language') == 'vi'

        regex_spans = self._regex_word_spans(text)

        # Try Vietnamese word segmentation if applicable
        if force_vi or self._is_vietnamese_text(text):
            try:
                from services.document.vietnamese_nlp import segment_words
                tokens = segment_words(text)
                if tokens:
                    spans = []
                    cursor = 0
                    misses = 0
                    for token in tokens:
                        search_token = token.replace('_', ' ')
                        pos = text.find(search_token, cursor)
                        if pos >= 0:
                            actual_end = pos + len(search_token)
                            spans.append((pos, actual_end))
                            cursor = actual_end
                        else:
                            misses += 1
                            if misses > max(3, int(len(tokens) * 0.03)):
                                return regex_spans

                    if spans and self._word_spans_are_safe(text, spans):
                        return spans
            except Exception as e:
                logger.debug(f"Vietnamese word segmentation fallback: {e}")

        return regex_spans

    @staticmethod
    def _regex_word_spans(text: str) -> List[tuple[int, int]]:
        """Safe non-whitespace token spans anchored to the original text."""
        return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]

    @staticmethod
    def _word_spans_are_safe(text: str, spans: List[tuple[int, int]]) -> bool:
        if not spans:
            return False

        last_end = -1
        for start, end in spans:
            if start < 0 or end <= start or end > len(text) or start < last_end:
                return False
            if text[start:end].strip() != text[start:end]:
                return False
            last_end = end
        return True

    def _max_clean_chunk_tokens(self) -> int:
        configured = int(getattr(settings, 'RAG_MAX_CLEAN_CHUNK_TOKENS', 0) or 0)
        if configured > 0:
            return configured
        return max(self.chunk_size + self.chunk_overlap, int(self.chunk_size * 1.35))

    @staticmethod
    def _clean_chunk_start(text: str, start_char: int, search_back_chars: int = 360) -> int:
        """Move overlap starts back to a nearby paragraph/sentence boundary.

        This prevents persisted chunk content from starting in the middle of a
        word or thought while preserving the intentional overlap.
        """
        if start_char <= 0:
            return 0

        start_char = min(max(0, start_char), len(text))
        window_start = max(0, start_char - search_back_chars)
        prefix = text[window_start:start_char]

        paragraph_matches = list(re.finditer(r'\n\s*\n+', prefix))
        if paragraph_matches:
            return window_start + paragraph_matches[-1].end()

        sentence_matches = list(re.finditer(r'[.!?…;:]\s+', prefix))
        if sentence_matches:
            return window_start + sentence_matches[-1].end()

        while start_char > 0 and not text[start_char - 1].isspace():
            start_char -= 1
        return start_char

    @staticmethod
    def _is_vietnamese_text(text: str, sample_chars: int = 1000) -> bool:
        """Quick heuristic: does this text contain significant Vietnamese diacritics?"""
        sample = text[:sample_chars]
        alpha_chars = [c for c in sample if c.isalpha()]
        if not alpha_chars:
            return False
        vi_specific = sum(
            1 for c in alpha_chars
            if (c in 'àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
                or c in 'ÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ')
        )
        return (vi_specific / max(1, len(alpha_chars))) >= 0.08

    def _char_to_word_index(self, char_pos: int, word_ends: List[int]) -> int:
        """Convert a character offset to the number of words that end before or at that position."""
        return bisect_right(word_ends, char_pos)

    def _build_structural_breakpoints(self, text: str, word_spans: List[tuple[int, int]]) -> List[int]:
        """Collect stable breakpoint indices from paragraph, sentence, and
        Vietnamese document structure boundaries (Chương, Điều, Mục, etc.)."""
        if not word_spans:
            return [0]

        word_ends = [end for _, end in word_spans]
        breakpoints = {0, len(word_spans)}

        cursor = 0
        paragraphs = re.split(r'\n\s*\n+', text)

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            paragraph_start = text.find(paragraph, cursor)
            if paragraph_start == -1:
                paragraph_start = text.find(paragraph)
            if paragraph_start == -1:
                continue

            paragraph_end = paragraph_start + len(paragraph)
            cursor = paragraph_end

            breakpoint_index = self._char_to_word_index(paragraph_end, word_ends)
            if 0 < breakpoint_index < len(word_spans):
                breakpoints.add(breakpoint_index)

            # Vietnamese document structure: Chương, Điều, Mục, Phần, Khoản
            first_line = paragraph.split('\n')[0].strip() if paragraph else ''
            if first_line:
                for pattern in _VI_HEADING_PATTERNS:
                    if pattern.match(first_line):
                        breakpoints.add(breakpoint_index)
                        break

            # Standard sentence boundaries
            if len(paragraph.split()) > self.chunk_size:
                for sentence_match in re.finditer(r'[.!?…]+(?:\s+|$)', paragraph):
                    sentence_end = paragraph_start + sentence_match.end()
                    sentence_breakpoint = self._char_to_word_index(sentence_end, word_ends)
                    if 0 < sentence_breakpoint < len(word_spans):
                        breakpoints.add(sentence_breakpoint)

        return sorted(breakpoints)

    def _build_token_windows(self, token_count: int, breakpoints: List[int]) -> List[tuple[int, int]]:
        """Create deterministic sliding windows over token-like units with overlap, preferring structural boundaries."""
        windows = []
        stride = max(1, self.chunk_size - self.chunk_overlap)
        min_boundary = max(1, int(self.chunk_size * 0.65))
        breakpoint_set = set(breakpoints or [])
        start = 0

        while start < token_count:
            end = min(start + self.chunk_size, token_count)

            # Prefer ending on a paragraph/sentence boundary near the target end.
            candidate_breaks = [bp for bp in breakpoint_set if start + min_boundary <= bp <= end]
            if candidate_breaks:
                end = candidate_breaks[-1]

            if end <= start:
                end = min(start + self.chunk_size, token_count)

            windows.append((start, end))

            if end >= token_count:
                break

            next_start = end - self.chunk_overlap
            start_candidates = [
                bp for bp in breakpoint_set
                if next_start <= bp < end and bp > start
            ]
            if start_candidates:
                next_start = start_candidates[0]
            # Guard against non-progress due to unusual configuration
            if next_start <= start:
                next_start = start + stride
            start = next_start

        return windows

    def _chunk_by_character_windows(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback chunking for edge cases where word-span tokenization yields no spans."""
        result_chunks = []
        stride = max(1, self.chunk_size - self.chunk_overlap)
        start_char = 0
        seq = 0

        while start_char < len(text):
            clean_start = self._clean_chunk_start(text, start_char) if seq > 0 else start_char
            end_char = min(start_char + self.chunk_size, len(text))
            chunk_text = text[clean_start:end_char]
            if (
                seq > 0
                and clean_start < start_char
                and self._estimate_token_count(chunk_text) > self._max_clean_chunk_tokens()
            ):
                clean_start = start_char
                chunk_text = text[clean_start:end_char]
            if chunk_text.strip():
                result_chunks.append({
                    'text': chunk_text,
                    'start_char': clean_start,
                    'end_char': end_char,
                    'token_start': clean_start,
                    'token_end': end_char,
                    'token_count': self._estimate_token_count(chunk_text),
                    'metadata': metadata,
                    'sequence': seq,
                })
                seq += 1

            if end_char >= len(text):
                break
            start_char += stride

        logger.info(
            f"Chunked text into {len(result_chunks)} chunks "
            f"(fallback_char_windows, strategy={self.strategy_name})"
        )
        return result_chunks
    
    # ============================================================================
    # EMBEDDING GENERATION
    # ============================================================================
    
    def _generate_embedding(
        self,
        text: str,
        embedding_client
    ) -> List[float]:
        """
        Generate embedding for text via configured embedding backend.

        Args:
            text: Text to embed
            embedding_client: EmbeddingClient or LlamaClient-like client

        Returns:
            Embedding vector (list of floats)
        """
        try:
            embedding = embedding_client.create_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise DocumentProcessingError(f"Failed to generate embedding: {str(e)}")

    def batch_generate_embeddings(
        self,
        texts: List[str],
        embedding_client
    ) -> List[List[float]]:
        """
        P1#5: Batch generate embeddings cho nhieu texts cung luc.
        
        FlagEmbedding BGE-M3 ho tro batch encode qua embedder.encode([texts...])
        nhanh hon 5-10x so voi goi tung cai mot.
        
        Args:
            texts: List of texts to embed
            embedding_client: EmbeddingClient instance
            
        Returns:
            List of embedding vectors (cung thu tu voi texts)
        """
        if not texts:
            return []
        
        try:
            if hasattr(embedding_client, 'create_embeddings'):
                return embedding_client.create_embeddings(texts)

            # Kiem tra xem embedding_client co ho tro batch khong
            if hasattr(embedding_client, 'embedder') and hasattr(embedding_client.embedder, 'encode'):
                # FlagEmbedding backend - batch encode
                # Truncate texts to prevent token limit errors (BGE-M3 max_length=8192)
                MAX_CHARS = 6000
                truncated_texts = [t[:MAX_CHARS] if len(t) > MAX_CHARS else t for t in texts]
                if any(len(t) > MAX_CHARS for t in texts):
                    logger.warning(f'One or more texts truncated to {MAX_CHARS} chars for BGE-M3 (max_length=8192)')
                
                result = embedding_client.embedder.encode(
                    truncated_texts,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False,
                )
                if isinstance(result, dict) and 'dense_vecs' in result:
                    import numpy as np
                    dense = np.asarray(result['dense_vecs'])
                    return [dense[i].tolist() for i in range(len(texts))]
            
            # Fallback: goi tung cai mot (giu lai de backward compatibility)
            logger.debug(f"Batch embedding not supported, falling back to sequential ({len(texts)} texts)")
            return [embedding_client.create_embedding(t) for t in texts]
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}, falling back to sequential")
            return [embedding_client.create_embedding(t) for t in texts]
    
    # ============================================================================
    # RERANKING (Future)
    # ============================================================================
    
    def rerank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        topk: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks by relevance to query
        
        Uses flashrank for efficient reranking
        
        Args:
            chunks: List of chunk dicts
            query: Query text
            topk: Keep only top K chunks
        
        Returns:
            Reranked chunks (top K only)
        
        Note:
            Reranking is optional, mainly for semantic search results
        """
        try:
            topk = topk or getattr(settings, 'FLASHRANK_TOPK', 10)
            
            # TODO: Implement flashrank reranking
            # For now, just return top K by order
            
            return chunks[:topk]
        
        except Exception as e:
            logger.warning(f"Reranking failed, returning original: {str(e)}")
            return chunks
