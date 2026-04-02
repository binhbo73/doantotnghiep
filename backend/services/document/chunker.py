"""
Document Chunker
================
Split documents into chunks + generate embeddings

Features:
- Semantic chunking (preserve meaning)
- Overlap between chunks
- Metadata preservation
- Reranking via flashrank
- Embedding generation via LLM
- Batch processing

Configuration (from settings.py):
    CHUNK_SIZE = 512  # chars per chunk
    CHUNK_OVERLAP = 100  # overlap between chunks
    FLASHRANK_TOPK = 10  # rerank top K results

Usage:
    chunker = DocumentChunker()
    
    # Chunk document
    chunks = chunker.chunk_text(
        text="Long document text...",
        metadata={'document_id': 1, 'source': 'pdf'}
    )
    
    # Generate embeddings for chunks
    chunks_with_embeddings = chunker.chunk_and_embed(
        text="...",
        document_id=1,
        llama_client=client,
        qdrant_client=db_client
    )
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from django.conf import settings
from django.apps import apps
from core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class DocumentChunker:
    """
    Document chunker - splits text into semantic chunks + generates embeddings
    
    Strategy:
    1. Split by paragraphs first
    2. If paragraph > chunk_size, split by sentences
    3. Merge small chunks
    4. Maintain overlap between chunks
    5. Generate embeddings for each chunk
    6. Rerank for quality
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        Initialize chunker
        
        Args:
            chunk_size: Characters per chunk (default 512)
            chunk_overlap: Overlap chars between chunks (default 100)
        """
        self.chunk_size = chunk_size or getattr(settings, 'CHUNK_SIZE', 512)
        self.chunk_overlap = chunk_overlap or getattr(settings, 'CHUNK_OVERLAP', 100)
        
        logger.info(
            f"DocumentChunker initialized: "
            f"chunk_size={self.chunk_size}, overlap={self.chunk_overlap}"
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
            
            # Split into paragraphs first
            paragraphs = self._split_paragraphs(text)
            
            # Further split large paragraphs into sentences
            sentences = []
            for para in paragraphs:
                if len(para) > self.chunk_size * 2:
                    # Large paragraph, split by sentences
                    para_sentences = self._split_sentences(para)
                    sentences.extend(para_sentences)
                else:
                    sentences.append(para)
            
            # Merge sentences into chunks
            chunks = self._merge_into_chunks(sentences)
            
            # Add metadata and position tracking
            result_chunks = []
            char_pos = 0
            
            for seq, chunk_text in enumerate(chunks):
                start_char = text.find(chunk_text, char_pos)
                if start_char == -1:
                    start_char = char_pos
                
                end_char = start_char + len(chunk_text)
                char_pos = end_char - self.chunk_overlap  # Prepare for next overlap
                
                result_chunks.append({
                    'text': chunk_text,
                    'start_char': start_char,
                    'end_char': end_char,
                    'metadata': metadata or {},
                    'sequence': seq,
                })
            
            logger.info(
                f"Chunked text into {len(result_chunks)} chunks "
                f"(avg {len(text) // len(result_chunks) if result_chunks else 0} chars)"
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
        document_id: int,
        llama_client,  # LlamaClient instance
        qdrant_client,  # QdrantClient instance
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Complete workflow: chunk text + generate embeddings + store in DB
        
        Args:
            text: Document text
            document_id: Document ID
            llama_client: LlamaClient for embedding generation
            qdrant_client: QdrantClient for vector storage
            metadata: Additional metadata
        
        Returns:
            List of chunk dicts with embeddings
        
        Raises:
            DocumentProcessingError: If processing fails
        
        Example:
            chunks_with_embeddings = chunker.chunk_and_embed(
                text=doc_text,
                document_id=123,
                llama_client=llama_client,
                qdrant_client=qdrant_client
            )
        """
        try:
            # Step 1: Chunk text
            chunks = self.chunk_text(text, metadata)
            logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Step 2: Generate embeddings + Store in DB & Qdrant
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            DocumentEmbedding = apps.get_model('documents', 'DocumentEmbedding')
            
            chunks_with_embeddings = []
            
            for chunk_dict in chunks:
                try:
                    chunk_text = chunk_dict['text']
                    
                    # 1. Generate embedding via LLM
                    embedding = self._generate_embedding(chunk_text, llama_client)
                    
                    # 2. Save Chunk to PostgreSQL
                    chunk_obj = DocumentChunk.objects.create(
                        document_id=document_id,
                        content=chunk_text,
                        sequence=chunk_dict['sequence'],
                        start_char=chunk_dict['start_char'],
                        end_char=chunk_dict['end_char']
                    )
                    
                    # 3. Store in Qdrant (Vector DB)
                    vector_id = qdrant_client.add_embedding(
                        embedding=embedding,
                        chunk_id=chunk_obj.id,
                        payload={
                            'document_id': document_id,
                            'chunk_id': chunk_obj.id,
                            'sequence': chunk_dict['sequence'],
                        }
                    )
                    
                    # 4. Save Embedding metadata to PostgreSQL
                    DocumentEmbedding.objects.create(
                        chunk=chunk_obj,
                        qdrant_vector_id=vector_id,
                        vector_size=len(embedding),
                        model_name=llama_client.model
                    )
                    
                    # Add to result list
                    chunk_dict['embedding'] = embedding
                    chunk_dict['vector_id'] = vector_id
                    chunk_dict['id'] = chunk_obj.id
                    chunks_with_embeddings.append(chunk_dict)
                    
                except Exception as e:
                    logger.warning(
                        f"Error processing chunk {chunk_dict['sequence']}: {str(e)}"
                    )
                    continue
            
            logger.info(
                f"Generated embeddings for {len(chunks_with_embeddings)}/{len(chunks)} chunks"
            )
            
            return chunks_with_embeddings
        
        except Exception as e:
            logger.error(f"Error in chunk_and_embed: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to chunk and embed: {str(e)}")
    
    # ============================================================================
    # INTERNAL - TEXT SPLITTING
    # ============================================================================
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines
        paragraphs = re.split(r'\n\n+', text)
        
        # Clean and filter empty
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        
        # Reconstruct with punctuation + clean
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                result.append(sentence + '.')
        
        return result
    
    def _merge_into_chunks(self, items: List[str]) -> List[str]:
        """
        Merge items into chunks of chunk_size,
        maintaining overlap_size overlap
        """
        if not items:
            return []
        
        chunks = []
        current_chunk = ""
        
        for item in items:
            # If adding this item would exceed chunk_size
            if len(current_chunk) + len(item) > self.chunk_size:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Start new chunk with overlap from previous
                if len(current_chunk) > self.chunk_overlap:
                    # Keep last N chars of current for overlap
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + item
                else:
                    current_chunk = item
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += " " + item
                else:
                    current_chunk = item
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
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
