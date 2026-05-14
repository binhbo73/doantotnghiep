"""
BM25 Sparse Search
==================
Implements BM25-based sparse retrieval using PostgreSQL full-text search.

Algorithm:
- Uses PostgreSQL SearchVector + SearchRank for efficient BM25-like scoring
- Avoids external dependencies like Elasticsearch
- Integrates seamlessly with Django ORM

Configuration:
- BM25 parameters: k1=2.0 (default), b=0.75 (default)
- Min term length: 3 characters
- Language: Vietnamese + English
"""

import logging
import re
import time
from typing import List, Dict, Any
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.apps import apps

logger = logging.getLogger(__name__)


class BM25Searcher:
    """BM25 sparse search using PostgreSQL full-text search."""

    # BM25 parameters
    K1 = 2.0  # term frequency saturation parameter
    B = 0.75  # field length normalization parameter
    # ✅ P0#2: Dùng 'simple' config cho PostgreSQL FTS.
    # 'english' stemming + stopword list không phù hợp tiếng Việt — tất cả từ
    # tiếng Việt bị coi là unknown, stemming sai, stopword không lọc đúng.
    # 'simple' không stemming, không stopword → phù hợp cho multilingual.
    # Khi có giải pháp FTS tiếng Việt (vd: pg_bigm + custom dictionary),
    # có thể chuyển sang config chuyên dụng.
    FTS_CONFIG = getattr(settings, 'POSTGRES_FTS_CONFIG', 'simple')

    def __init__(self):
        self.DocumentChunk = apps.get_model('documents', 'DocumentChunk')

    def search(self,        query: str, 
        top_k: int = 20, 
        document_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Search chunks using BM25 scoring.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            document_ids: Optional list of document IDs to filter
        
        Returns:
            List of {chunk_id, document_id, score, content} sorted by BM25 score
        """
        t_bm25_start = time.monotonic()
        try:
            # Parse query into terms
            t_parse_start = time.monotonic()
            terms = self._parse_query(query)
            t_parse_ms = (time.monotonic() - t_parse_start) * 1000
            if not terms:
                logger.debug("No valid search terms extracted")
                return []

            # Search directly on the migrated tsvector field
            # Fix: OR logic for multi-word queries - AND logic fails for Tieng Viet
            # vi khong chunk nao chua TAT CA cac tu cung luc
            or_terms = ' | '.join(terms)
            search_query = SearchQuery(
                or_terms,
                search_type='raw',
                config=self.FTS_CONFIG
            )

            # Build query set
            t_db_start = time.monotonic()
            queryset = self.DocumentChunk.objects.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(
                search_vector=search_query,
                node_type='detail',
                is_deleted=False
            )

            # Optional: filter by document(s)
            if document_ids:
                if isinstance(document_ids, list):
                    queryset = queryset.filter(document_id__in=document_ids)
                else:
                    queryset = queryset.filter(document_id=document_ids)

            # Order by BM25 rank and execute query
            queryset = queryset.order_by('-rank')[:top_k]
            
            # Execute query and fetch results
            results = []
            for chunk in queryset:
                results.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'score': float(chunk.rank or 0.0),  # BM25 score (typically 0-1 after normalization)
                    'content': chunk.content[:300] if chunk.content else '',
                    'source': 'bm25'
                })
            
            t_db_ms = (time.monotonic() - t_db_start) * 1000
            t_bm25_total = (time.monotonic() - t_bm25_start) * 1000

            logger.info(
                f"[BM25_PROFILE] query='{query[:40]}...' results={len(results)} | "
                f"timing: parse={t_parse_ms:.1f}ms, db_query={t_db_ms:.1f}ms, total={t_bm25_total:.1f}ms"
            )
            logger.debug(f"BM25 search: {len(results)} results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"BM25 search error: {str(e)}", exc_info=True)
            return []

    def search_with_filters(
        self,
        query: str,
        document_ids: List[str] = None,
        page_number: int = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Search with additional filters (document, page).
        
        Args:
            query: Search query
            document_id: Filter by document ID
            page_number: Filter by page number
            top_k: Number of results
        
        Returns:
            Filtered BM25 results
        """
        try:
            terms = self._parse_query(query)
            if not terms:
                return []

            # Fix: OR logic for multi-word queries - AND logic fails for Tieng Viet
            # vi khong chunk nao chua TAT CA cac tu cung luc
            or_terms = ' | '.join(terms)
            search_query = SearchQuery(
                or_terms,
                search_type='raw',
                config=self.FTS_CONFIG
            )

            queryset = self.DocumentChunk.objects.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(
                search_vector=search_query,
                node_type='detail',
                is_deleted=False
            )

            # Apply filters
            if document_ids:
                if isinstance(document_ids, list):
                    queryset = queryset.filter(document_id__in=document_ids)
                else:
                    queryset = queryset.filter(document_id=document_ids)
            if page_number:
                queryset = queryset.filter(page_number=page_number)

            queryset = queryset.order_by('-rank')[:top_k]

            results = []
            for chunk in queryset:
                results.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'score': float(chunk.rank or 0.0),
                    'content': chunk.content[:300] if chunk.content else '',
                    'page': chunk.page_number,
                    'source': 'bm25'
                })

            return results

        except Exception as e:
            logger.error(f"Filtered BM25 search error: {str(e)}", exc_info=True)
            return []

    def _parse_query(self, query: str) -> List[str]:
        """Parse query into valid search terms.
        
        - Remove special characters
        - Filter short terms (< 3 chars)
        - Return significant terms for BM25
        
        Args:
            query: Raw query string
        
        Returns:
            List of valid search terms
        """
        if not query:
            return []

        # Remove special PostgreSQL FTS characters: | & ! ( ) : * "
        cleaned = re.sub(r'[|&!():*"\']', ' ', query)

        # Split by whitespace
        terms = cleaned.split()

        # Filter: keep terms >= 3 chars, remove duplicates
        # ✅ P0#3: Giữ lại từ >= 2 ký tự thay vì >= 3.
        # Tiếng Việt có rất nhiều từ 2 ký tự quan trọng.
        ONE_CHAR_WHITELIST = {'ý', 't', 'p', 'k'}
        valid_terms = list(dict.fromkeys(
            t for t in terms if len(t) >= 2 or t.lower() in ONE_CHAR_WHITELIST
        ))

        if not valid_terms:
            # Fallback: if all terms too short, use original query (risky but better than nothing)
            fallback = ' '.join(t for t in terms if len(t) >= 2)
            return [fallback] if fallback else []

        return valid_terms

    def get_term_frequency_stats(self, query: str) -> Dict[str, Any]:
        """Get term frequency statistics for a query.
        
        Useful for:
        - Debugging BM25 scoring
        - Understanding term importance
        - Query optimization
        
        Args:
            query: Search query
        
        Returns:
            Stats dict with term frequencies
        """
        try:
            terms = self._parse_query(query)
            if not terms:
                return {}

            stats = {}
            for term in terms:
                count = self.DocumentChunk.objects.filter(
                    content__icontains=term,
                    is_deleted=False
                ).count()
                stats[term] = count

            return stats

        except Exception as e:
            logger.error(f"Error getting term stats: {str(e)}")
            return {}

    @staticmethod
    def validate_bm25_support() -> bool:
        """Check if PostgreSQL FTS is available.
        
        Returns:
            True if postgresql.search module can be imported and used
        """
        try:
            from django.contrib.postgres.search import SearchVector, SearchQuery
            return True
        except ImportError:
            logger.warning("PostgreSQL full-text search not available. Install psycopg2-binary and enable PostgreSQL extension.")
            return False
