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
                    'token_count': end_token - start_token,
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
    
    # ============================================================================
    # CHUNKING + EMBEDDING WORKFLOW
    # ============================================================================
    
    def chunk_and_embed(
        self,
        text: str,
        document_id: str,
        llama_client,
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
                    
                    # 1. Generate embedding via LLM
                    embedding = self._generate_embedding(chunk_text, llama_client)
                    if not embedding:
                        continue

                    # 2. Save Chunk to PostgreSQL
                    chunk_obj = DocumentChunk.objects.create(
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=idx,
                        token_count=chunk_dict.get('token_count', len(chunk_text.split())),
                        page_number=1,
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
                        embedding_model=llama_client.model
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
        normalized = (file_type or '').lower()

        if normalized in ('application/pdf',):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_PDF', 200)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_PDF', 40)
            profile = 'pdf'
        elif normalized in (
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/markdown',
        ):
            self.chunk_size = getattr(settings, 'CHUNK_TOKEN_SIZE_DOC', 240)
            self.chunk_overlap = getattr(settings, 'CHUNK_TOKEN_OVERLAP_DOC', 48)
            profile = 'doc'
        elif normalized in ('text/plain',):
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
            f"Chunk profile selected: file_type={normalized or 'unknown'}, strategy={self.strategy_name}"
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
                    'token_count': max(1, len(chunk_text.split())),
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
        llama_client
    ) -> List[float]:
        """
        Generate embedding for text via LLM
        
        Uses LLM to convert text to vector representation
        
        Args:
            text: Text to embed
            llama_client: LlamaClient instance
        
        Returns:
            Embedding vector (list of floats)
        """
        try:
            # Use LlamaClient to generate embedding via /embeddings endpoint
            embedding = llama_client.create_embedding(text)
            return embedding
        
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise DocumentProcessingError(f"Failed to generate embedding: {str(e)}")
    
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
