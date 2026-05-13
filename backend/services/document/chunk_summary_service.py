"""
Chunk Summarization Service
============================
Generates AI summaries for document chunks.

Strategies:
1. SYNC: For short documents (< 5 pages)
2. ASYNC: For long documents (via background thread)
3. CACHE: Redis cache with 7-day TTL

Uses Qwen3-4B LLM for summarization (local, no API cost).
"""

import logging
import hashlib
import threading
from typing import Optional
from django.conf import settings
from django_redis import get_redis_connection
from services.ai.llama_client import LlamaClient
from django.apps import apps

logger = logging.getLogger(__name__)


class ChunkSummaryService:
    """
    Generates and manages chunk summaries.
    
    Usage:
        summary_service = ChunkSummaryService()
        
        # Generate summary synchronously
        summary = summary_service.generate_summary_sync(chunk_text)
        
        # Or queue asynchronously
        summary_service.queue_summary(chunk_id, chunk_text)
    """
    
    # Configuration (Fix #3: optimized for Qwen3-4B latency)
    SUMMARY_MAX_TOKENS = 80   # Giam tu 100 -> 80 de LLM phan hoi nhanh hon
    SUMMARY_TEMPERATURE = 0.3  # Low for consistency
    SUMMARY_TIMEOUT = 300      # Tang tu 180 -> 300 de tranh timeout tren CPU
    CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
    SUMMARY_PROMPT_VERSION = "v2"
    CACHE_KEY_PREFIX = "chunk_summary"
    PROCESSING_KEY_PREFIX = "chunk_summary_processing"

    # 🚀 NEW: Class-level semaphore to ensure we don't overwhelm llama-server
    # Only allow 2 summary generations at a time across all threads (safer for 16GB RAM)
    _llm_semaphore = threading.Semaphore(2)

    def __init__(self):
        self.llama = LlamaClient()
        self.redis_client = self._get_redis_client()
        self.celery_enabled = getattr(settings, 'CELERY_ENABLED', False)
        self.celery_task = self._load_celery_task()

    def _get_redis_client(self):
        try:
            return get_redis_connection("default")
        except Exception as e:
            logger.warning(f"Redis client not available for chunk summary cache: {e}")
            return None

    def _load_celery_task(self):
        if not self.celery_enabled:
            return None
        try:
            from services.document.tasks import summarize_chunk_task
            return summarize_chunk_task
        except Exception as e:
            logger.warning(f"Celery summary task not loaded: {e}")
            return None

    def _should_generate_summary_sync(self, document_size_bytes: int, page_count: int) -> bool:
        """
        Decide whether to generate summary synchronously or asynchronously.
        
        SYNC: Small files (< 5 pages or < 500KB)
        ASYNC: Large files (will not block upload)
        """
        return page_count < 5 or document_size_bytes < 500 * 1024
    
    def generate_summary_sync(self, chunk_text: str, timeout: int = None) -> Optional[str]:
        """
        Generate summary synchronously (blocking).
        
        Best for: Short chunks during upload of small files
        
        Args:
            chunk_text: Text to summarize
            timeout: Override default timeout in seconds
        
        Returns:
            Summary string (1-3 sentences, ~150 chars)
        """
        try:
            if not chunk_text or len(chunk_text.strip()) < 50:
                logger.debug(f"Chunk too short ({len(chunk_text)} chars), skipping summary")
                return chunk_text[:100]  # Too short to summarize
            
            # Use semaphore to avoid concurrency issues with LLM server
            with self._llm_semaphore:
                prompt = self._build_summary_prompt(chunk_text)
                
                logger.info(f"📝 Generating summary for {len(chunk_text)} char chunk (locked)...")
                
                summary = self.llama.complete(
                    prompt=prompt,
                    max_tokens=self.SUMMARY_MAX_TOKENS,
                    temperature=self.SUMMARY_TEMPERATURE,
                    timeout=timeout or self.SUMMARY_TIMEOUT
                )
            
            clean_summary = summary.strip() if summary else None
            
            if clean_summary:
                logger.debug(f"✅ Summary generated ({len(clean_summary)} chars): {clean_summary[:60]}...")
            else:
                logger.warning(f"⚠️  Summary generation returned empty result")
            
            return clean_summary
        
        except Exception as e:
            logger.error(f"❌ Error generating summary: {str(e)}")
            return None
    
    def queue_summary_async(self, chunk_id: str, chunk_text: str, document_id: str = None):
        """
        Queue summary generation for background processing.
        
        Best for: Large files during upload (non-blocking)
        
        Args:
            chunk_id: DocumentChunk.id
            chunk_text: Text to summarize
            document_id: Parent Document.id (optional)
        """
        try:
            if self.celery_enabled and self.celery_task:
                try:
                    self.celery_task.delay(chunk_id, chunk_text, document_id)
                    logger.debug(f"Queued Celery summary task for chunk {chunk_id}")
                    return
                except Exception as e:
                    logger.warning(f"Celery task enqueue failed, falling back to thread: {e}")

            thread = threading.Thread(
                target=self._summarize_in_background,
                args=(chunk_id, chunk_text, document_id),
                daemon=True
            )
            thread.start()
            logger.debug(f"Queued background summary for chunk {chunk_id}")
        
        except Exception as e:
            logger.error(f"Error queuing background summary: {str(e)}")
    
    def _summarize_in_background(self, chunk_id: str, chunk_text: str, document_id: str = None):
        """
        Generate summary in background thread and save to DB.
        
        Marks chunk as 'pending_summary' initially, then 'summary_generated'.
        """
        try:
            # Mark as processing
            key = f"{self.PROCESSING_KEY_PREFIX}:{chunk_id}"
            if self.redis_client:
                self.redis_client.set(key, "1", self.CACHE_TTL_SECONDS)
            
            # Generate summary
            summary = self.generate_summary_sync(chunk_text)
            
            if not summary:
                logger.warning(f"Failed to generate summary for chunk {chunk_id}")
                return
            
            # Save to database
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            chunk = DocumentChunk.objects.get(id=chunk_id)
            chunk.summary = summary
            chunk.save(update_fields=['summary', 'updated_at'])
            
            logger.info(
                f"✅ [SUMMARY] Completed: Page {chunk.page_number} | "
                f"Type: {chunk.node_type} | ID: {str(chunk.id)[:8]}... | "
                f"Preview: {summary[:60]}..."
            )
        
        except DocumentChunk.DoesNotExist:
            logger.warning(f"Chunk {chunk_id} not found for summary update")
        except Exception as e:
            logger.error(f"Error in background summary: {str(e)}", exc_info=True)
        finally:
            # Clean processing flag
            if self.redis_client:
                key = f"{self.PROCESSING_KEY_PREFIX}:{chunk_id}"
                self.redis_client.delete(key)
    
    def get_or_generate_summary(
        self,
        chunk_text: str,
        chunk_id: str = None,
        use_cache: bool = True,
        sync: bool = True,
        timeout: int = None
    ) -> Optional[str]:
        """
        Get or generate summary with caching.
        
        Args:
            chunk_text: Text to summarize
            chunk_id: For DB lookup (optional)
            use_cache: Use Redis cache (default True)
            sync: Generate synchronously (default True)
            timeout: Override default timeout in seconds
        
        Returns:
            Summary string or None
        """
        if not chunk_text:
            return None
        
        chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:16]
        prompt_version = getattr(self, 'SUMMARY_PROMPT_VERSION', 'v1')
        cache_key = f"{self.CACHE_KEY_PREFIX}:{prompt_version}:{chunk_hash}"
        
        # Try cache first
        if use_cache and self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        
        # Generate
        summary = self.generate_summary_sync(chunk_text, timeout=timeout) if sync else None
        
        if not summary and not sync:
            # Queue for background
            if chunk_id:
                self.queue_summary_async(chunk_id, chunk_text)
            return None
        
        # Cache result
        if summary and use_cache and self.redis_client:
            self.redis_client.set(cache_key, summary, self.CACHE_TTL_SECONDS)
        
        return summary
    
    def _build_summary_prompt(self, chunk_text: str) -> str:
        """Build prompt for chunk summarization.
        
        Fix #3: Giam prompt size (1200 chars thay vi 2000) de giam LLM latency.
        Qwen3-4B xu ly prompt ngan nhanh hon dang ke, tranh timeout.
        """
        return (
            "Tom tat doan van sau bang 1-3 cau ngan gon tieng Viet (toi da 150 ky tu). "
            "Giu dung y chinh, ten rieng, so lieu. Khong them tieu de hay giai thich.\n\n"
            f"{chunk_text[:1200]}\n\n"
            "Tom tat:"
        )
    
    def estimate_summary_time(self, document_page_count: int, chunk_count: int) -> float:
        """
        Estimate time to generate summaries for all chunks.
        
        Benchmark: ~1-3 seconds per chunk
        """
        time_per_chunk = 1.5  # seconds
        total_time = chunk_count * time_per_chunk
        return total_time
    
    def should_process_summaries_async(self, document_page_count: int, chunk_count: int) -> bool:
        """
        Decide if summary generation should be async to avoid blocking.
        """
        estimated_time = self.estimate_summary_time(document_page_count, chunk_count)
        async_threshold = 30  # seconds
        return estimated_time > async_threshold
