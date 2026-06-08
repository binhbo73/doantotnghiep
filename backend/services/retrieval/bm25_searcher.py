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
import unicodedata
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
        document_ids: List[str] = None,
        include_historical: bool = False,
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

            # Adaptive AND/OR: AND first for precision, OR fallback for recall
            search_query = self._build_adaptive_query(terms)

            # Build query set
            t_db_start = time.monotonic()
            strategy = 'AND' if ' & ' in str(search_query) else 'OR'
            if ' <-> ' in str(search_query):
                strategy = 'PHRASE'
            queryset = self.DocumentChunk.objects.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(
                search_vector=search_query,
                node_type='detail',
                is_deleted=False
            )
            if not include_historical:
                queryset = queryset.filter(is_current=True)

            # Optional: filter by document(s)
            if document_ids:
                if isinstance(document_ids, list):
                    queryset = queryset.filter(document_id__in=document_ids)
                else:
                    queryset = queryset.filter(document_id=document_ids)

            candidate_limit = self._candidate_limit(top_k)

            # Fetch a wider candidate set, then apply Vietnamese-aware lexical
            # reranking. PostgreSQL FTS rank can tie on common terms such as
            # "phòng", "tổng", "giám", so a deterministic second pass is
            # needed to lift exact headings/phrases.
            queryset = queryset.order_by('-rank')[:candidate_limit]

            # Fallback: if strict phrase/AND returns too few, retry with OR.
            # This is important for Vietnamese because the same concept often
            # spans tokenization/chunk boundaries and phrase search can be too
            # brittle for two-word queries.
            results_count = queryset.count()
            fallback_threshold = 1 if strategy == 'PHRASE' else max(2, top_k // 2)
            if results_count < fallback_threshold and strategy in ('AND', 'PHRASE') and len(terms) >= 2:
                or_query = SearchQuery(
                    self._join_terms(terms, ' | '),
                    search_type='raw',
                    config=self.FTS_CONFIG
                )
                fallback_qs = self.DocumentChunk.objects.annotate(
                    rank=SearchRank(F('search_vector'), or_query)
                ).filter(
                    search_vector=or_query,
                    node_type='detail',
                    is_deleted=False
                )
                if not include_historical:
                    fallback_qs = fallback_qs.filter(is_current=True)
                if document_ids:
                    fallback_qs = fallback_qs.filter(document_id__in=document_ids if isinstance(document_ids, list) else [document_ids])
                queryset = fallback_qs.order_by('-rank')[:candidate_limit]
                strategy = 'OR (fallback)'
            
            # Execute query and fetch results
            results = []
            for chunk in queryset:
                bm25_score = float(chunk.rank or 0.0)
                lexical_score = self._lexical_relevance_score(query, chunk.content or '')
                final_score = self._combine_scores(bm25_score, lexical_score)
                results.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'score': final_score,
                    '_bm25_score': bm25_score,
                    '_lexical_score': lexical_score,
                    'content': chunk.content[:2000] if chunk.content else '',
                    'page': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    'metadata': chunk.metadata or {},
                    'source': 'bm25'
                })
            results.sort(
                key=lambda item: (
                    float(item.get('score') or 0.0),
                    float(item.get('_lexical_score') or 0.0),
                    float(item.get('_bm25_score') or 0.0),
                    -int(item.get('chunk_index') or 0),
                ),
                reverse=True,
            )
            results = results[:top_k]
            
            t_db_ms = (time.monotonic() - t_db_start) * 1000
            t_bm25_total = (time.monotonic() - t_bm25_start) * 1000

            logger.info(
                f"[BM25_PROFILE] query='{query[:40]}...' strategy={strategy} "
                f"results={len(results)} | "
                f"timing: parse={t_parse_ms:.1f}ms, db={t_db_ms:.1f}ms, total={t_bm25_total:.1f}ms"
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
            or_terms = self._join_terms(terms, ' | ')
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
                is_current=True,
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

            queryset = queryset.order_by('-rank')[:self._candidate_limit(top_k)]

            results = []
            for chunk in queryset:
                bm25_score = float(chunk.rank or 0.0)
                lexical_score = self._lexical_relevance_score(query, chunk.content or '')
                final_score = self._combine_scores(bm25_score, lexical_score)
                results.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'score': final_score,
                    '_bm25_score': bm25_score,
                    '_lexical_score': lexical_score,
                    'content': chunk.content[:2000] if chunk.content else '',
                    'page': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    'metadata': chunk.metadata or {},
                    'source': 'bm25'
                })
            results.sort(
                key=lambda item: (
                    float(item.get('score') or 0.0),
                    float(item.get('_lexical_score') or 0.0),
                    float(item.get('_bm25_score') or 0.0),
                    -int(item.get('chunk_index') or 0),
                ),
                reverse=True,
            )

            return results[:top_k]

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

    @staticmethod
    def _candidate_limit(top_k: int) -> int:
        return max(top_k, min(max(top_k * 5, 40), 120))

    def _combine_scores(self, bm25_score: float, lexical_score: float) -> float:
        bm25_score = max(0.0, float(bm25_score or 0.0))
        lexical_score = max(0.0, min(2.0, float(lexical_score or 0.0)))
        return round((0.55 * bm25_score) + (0.45 * lexical_score), 6)

    def _normalize_term(self, term: str) -> str:
        normalized = unicodedata.normalize('NFD', (term or '').lower())
        normalized = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        return normalized.replace('đ', 'd').replace('Đ', 'd')

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize('NFD', (text or '').lower())
        normalized = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        normalized = normalized.replace('đ', 'd').replace('Đ', 'd')
        normalized = re.sub(r'[^\w\s]+', ' ', normalized, flags=re.UNICODE)
        return re.sub(r'\s+', ' ', normalized).strip()

    def _lexical_relevance_score(self, query: str, text: str) -> float:
        query_norm = self._normalize_text(query)
        text_norm = self._normalize_text(text)
        if not query_norm or not text_norm:
            return 0.0

        query_tokens = self._meaningful_tokens(query_norm)
        if not query_tokens:
            return 0.0

        text_tokens = re.findall(r'\w+', text_norm, flags=re.UNICODE)
        text_token_set = set(text_tokens)
        overlap = sum(1 for token in query_tokens if token in text_token_set)
        coverage = overlap / max(1, len(query_tokens))

        score = 0.55 * coverage

        query_phrase = ' '.join(query_tokens)
        if query_phrase and query_phrase in text_norm:
            score += 0.85

        ordered_score = self._ordered_token_score(query_tokens, text_tokens)
        score += 0.35 * ordered_score

        ngram_score = self._ngram_overlap_score(query_tokens, text_norm)
        score += 0.35 * ngram_score

        first_text = text_norm[:500]
        if query_phrase and query_phrase in first_text:
            score += 0.25

        heading_bonus = self._heading_match_bonus(query_tokens, text_norm)
        score += heading_bonus

        # Down-rank broad glossary/definition chunks that match only generic
        # terms but miss the distinctive query phrase.
        if coverage < 0.75 and ngram_score == 0:
            score -= 0.20

        return max(0.0, min(2.0, score))

    @staticmethod
    def _meaningful_tokens(normalized_text: str) -> List[str]:
        stop_terms = {
            'cua', 'cac', 'cho', 'theo', 'trong', 'voi', 'va', 'la', 'co',
            'duoc', 've', 'den', 'tu', 'mot', 'nhung', 'nay', 'do', 'thi',
        }
        tokens = re.findall(r'\w+', normalized_text or '', flags=re.UNICODE)
        kept = []
        for token in tokens:
            if len(token) < 2:
                continue
            if token in stop_terms:
                continue
            if token not in kept:
                kept.append(token)
        return kept

    @staticmethod
    def _ordered_token_score(query_tokens: List[str], text_tokens: List[str]) -> float:
        if not query_tokens or not text_tokens:
            return 0.0
        pos = 0
        matched = 0
        for query_token in query_tokens:
            try:
                found = text_tokens.index(query_token, pos)
            except ValueError:
                continue
            matched += 1
            pos = found + 1
        return matched / max(1, len(query_tokens))

    @staticmethod
    def _ngram_overlap_score(query_tokens: List[str], text_norm: str) -> float:
        grams = []
        for size in (2, 3, 4):
            grams.extend(
                ' '.join(query_tokens[index:index + size])
                for index in range(0, max(0, len(query_tokens) - size + 1))
            )
        grams = [gram for gram in grams if gram]
        if not grams:
            return 0.0
        hits = sum(1 for gram in grams if gram in text_norm)
        return hits / len(grams)

    @staticmethod
    def _heading_match_bonus(query_tokens: List[str], text_norm: str) -> float:
        if not query_tokens:
            return 0.0
        first_lines = [
            line.strip()
            for line in text_norm.splitlines()[:6]
            if line.strip()
        ]
        if not first_lines:
            first_lines = [text_norm[:300]]
        heading_text = ' '.join(first_lines)
        heading_hits = sum(1 for token in query_tokens if token in heading_text)
        bonus = 0.0
        if heading_hits >= max(2, int(len(query_tokens) * 0.6)):
            bonus += 0.25
        if len(query_tokens) >= 2:
            leading_bigram = ' '.join(query_tokens[:2])
            if leading_bigram in heading_text:
                bonus += 0.25
        return bonus

    def _term_variants(self, term: str) -> List[str]:
        variants = []
        for item in (term, self._normalize_term(term)):
            item = re.sub(r"[^\w]+", "", item or "", flags=re.UNICODE)
            if item and item not in variants:
                variants.append(item)
        return variants

    def _tsquery_term(self, term: str) -> str:
        variants = self._term_variants(term)
        if not variants:
            return ''
        if len(variants) == 1:
            return variants[0]
        return '(' + ' | '.join(variants) + ')'

    def _join_terms(self, terms: List[str], operator: str) -> str:
        query_terms = [self._tsquery_term(term) for term in terms]
        query_terms = [term for term in query_terms if term]
        return operator.join(query_terms)

    def _build_adaptive_query(self, terms: List[str]) -> SearchQuery:
        """Build adaptive FTS query: phrase for 1-2 terms, AND for 3+, OR fallback handled by caller.

        Strategy:
        - 1 term: plain search
        - 2 terms: phrase search (terms must appear adjacent) for precision
        - 3+ terms: AND logic (all terms must appear) for precision
        - If AND returns too few results, caller falls back to OR
        """
        if not terms:
            return SearchQuery('', search_type='raw', config=self.FTS_CONFIG)

        if len(terms) == 1:
            return SearchQuery(
                self._tsquery_term(terms[0]),
                search_type='raw',
                config=self.FTS_CONFIG
            )

        if len(terms) == 2:
            # Two terms: phrase search for precision
            phrase = self._join_terms(terms, ' <-> ')
            return SearchQuery(
                phrase,
                search_type='raw',
                config=self.FTS_CONFIG
            )

        # 3+ terms: AND logic
        and_terms = self._join_terms(terms, ' & ')
        return SearchQuery(
            and_terms,
            search_type='raw',
            config=self.FTS_CONFIG
        )

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
