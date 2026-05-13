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
from typing import List, Dict, Any
from django.conf import settings
from django.apps import apps
from core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


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
        """
        if not text:
            return 0
        
        # P1#4: Dung BGE-M3/XLM-RoBERTa tokenizer that neu co
        tokenizer = self._get_tokenizer()
        if tokenizer is not None:
            try:
                encoding = tokenizer.encode(text, add_special_tokens=False)
                return max(1, len(encoding))
            except Exception as e:
                logger.debug('Tokenizer encode failed: %s, using heuristic', e)
        
        # Fallback heuristic
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
            self._apply_chunk_profile(file_type)

            word_spans = self._build_word_spans(text)

            # Fallback to char windows when text has no word spans (edge cases)
            if not word_spans:
                return self._chunk_by_character_windows(text, merged_metadata)

            breakpoints = self._build_structural_breakpoints(text, word_spans)
            window_indices = self._build_token_windows(len(word_spans), breakpoints)
            result_chunks = []
            for seq, (start_token, end_token) in enumerate(window_indices):
                start_char = word_spans[start_token][0]
                end_char = word_spans[end_token - 1][1]
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
                logger.warning("No page-aware text provided, falling back to regular chunking")
                return self.chunk_text(page_aware_text.text if hasattr(page_aware_text, 'text') else '', metadata)
            
            text = page_aware_text.text
            boundaries = page_aware_text.boundaries
            total_pages = page_aware_text.total_pages
            
            if not text or len(text.strip()) == 0:
                raise DocumentProcessingError("Empty text cannot be chunked")
            
            merged_metadata = metadata or {}
            file_type = (merged_metadata.get('file_type') or '').lower()
            self._apply_chunk_profile(file_type)
            
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
            
            word_spans = self._build_word_spans(page_text)
            
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
                start_char = word_spans[start_token][0]
                end_char = word_spans[end_token - 1][1]
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
            end_char = min(start_char + self.chunk_size, len(page_text))
            chunk_text = page_text[start_char:end_char]
            
            if chunk_text.strip():
                page_chunks.append({
                    'text': chunk_text,
                    'start_char': page_char_offset + start_char,
                    'end_char': page_char_offset + end_char,
                    'token_start': start_char,
                    'token_end': end_char,
                    'token_count': self._estimate_token_count(chunk_text),
                    'page_number': page_number,
                    'metadata': {
                        **metadata,
                        'page_number': page_number,
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

    def _apply_chunk_profile(self, file_type: str) -> None:
        """Select a file-type-aware chunk profile, keeping a safe default for unknown inputs."""
        normalized = (file_type or '').lower().strip()
        
        # Handle both MIME types and file extensions
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/plain': 'txt',
            'text/markdown': 'md',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-excel': 'xls',
        }
        
        # Convert MIME to extension if needed, or use as-is if already extension
        if normalized in mime_to_ext:
            ext = mime_to_ext[normalized]
        elif normalized in mime_to_ext.values():
            ext = normalized
        else:
            # Try to extract extension
            ext = normalized.split('.')[-1] if '.' in normalized else normalized

        if ext == 'pdf':
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_PDF', 200)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_PDF', 40)
            profile = 'pdf'
        elif ext in ('docx', 'doc', 'md', 'xlsx', 'xls'):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_DOC', 240)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_DOC', 48)
            profile = 'doc'
        elif ext in ('txt', 'text'):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_TEXT', 260)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_TEXT', 52)
            profile = 'text'
        else:
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE', self.chunk_size)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP', self.chunk_overlap)
            profile = 'default'

        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size // 4)

        self.strategy_name = f"hybrid_structural_{profile}_{self.chunk_size}_{self.chunk_overlap}"
        logger.info(
            f"Chunk profile selected: file_type={normalized} (ext={ext}), strategy={self.strategy_name}"
        )
    
    def _build_word_spans(self, text: str) -> List[tuple[int, int]]:
        """Return exact character spans for token-like units (non-whitespace sequences)."""
        return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]

    def _char_to_word_index(self, char_pos: int, word_ends: List[int]) -> int:
        """Convert a character offset to the number of words that end before or at that position."""
        return bisect_right(word_ends, char_pos)

    def _build_structural_breakpoints(self, text: str, word_spans: List[tuple[int, int]]) -> List[int]:
        """Collect stable breakpoint indices from paragraph and sentence boundaries."""
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

            if len(paragraph.split()) > self.chunk_size:
                for sentence_match in re.finditer(r'[.!?]+(?:\s+|$)', paragraph):
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
            end_char = min(start_char + self.chunk_size, len(text))
            chunk_text = text[start_char:end_char]
            if chunk_text.strip():
                result_chunks.append({
                    'text': chunk_text,
                    'start_char': start_char,
                    'end_char': end_char,
                    'token_start': start_char,
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
            # Kiem tra xem embedding_client co ho tro batch khong
            if hasattr(embedding_client, 'embedder') and hasattr(embedding_client.embedder, 'encode'):
                # FlagEmbedding backend - batch encode
                result = embedding_client.embedder.encode(
                    texts,
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
