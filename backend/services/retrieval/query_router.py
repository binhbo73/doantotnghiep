from typing import Any, Dict, List
import logging
import re
import time
from django.apps import apps
from django.conf import settings

from .hybrid_retriever import HybridRetriever
from .query_rewriter import QueryRewriter
from .reranker import Reranker
from .raptor_tree import RaptorTreeBuilder
from .query_intent import QueryIntentClassifier, QueryIntent, RetrievalConfig
from .spreadsheet_retriever import SpreadsheetRetriever

logger = logging.getLogger(__name__)


class QueryRouter:
    """Intent-driven retrieval strategy router.

    Now uses QueryIntentClassifier to select optimal strategy per query type:
    - factual/definitional → fast hybrid, low top_k, precision-focused
    - list/table/analytical/comparative → deep search, neighbor expansion (table stays chunk-native)
    - procedural → sequential chunks, neighbor expansion
    - image → asset-first search

    Simple rules:
    - If query length > 40 words -> consider 'raptor' if document long
    - If query contains keywords ("mã","số","code","id") -> prefer 'sparse' (lexical)
    - Else -> hybrid dense + sparse
    """

    def __init__(self, qdrant_client, embedding_client, llama_client=None):
        self.hybrid = HybridRetriever(qdrant_client=qdrant_client, embedding_client=embedding_client)
        self.reranker = Reranker(
            llama_client=None,
            embedding_client=embedding_client,
        )
        self.raptor = RaptorTreeBuilder()
        self.rewriter = QueryRewriter(llama_client)
        self.intent_classifier = QueryIntentClassifier(embedding_client=embedding_client)
        self.spreadsheet = SpreadsheetRetriever()

    def route(
        self,
        query: str,
        user_context: Dict = None,
        top_k: int = 5,
        conversation_history: List[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """Intent-driven retrieval: classify query intent → select strategy → retrieve → rerank.

        user_context hỗ trợ 2 keys:
          - 'document_id'  : str  — single doc (cũ, backward compatible)
          - 'document_ids' : List[str] — multi-doc filter (ưu tiên hơn)
        """
        t_route_start = time.monotonic()

        # ── Classify query intent ────────────────────────────
        intent = self.intent_classifier.classify(query)
        intent_config = self.intent_classifier.get_retrieval_config(intent)

        # Lấy danh sách document IDs để filter (ưu tiên 'document_ids' list)
        document_ids: List[str] = []
        if user_context:
            if user_context.get('document_ids'):
                document_ids = [str(d) for d in user_context['document_ids'] if d]
            elif user_context.get('document_id'):
                document_ids = [str(user_context['document_id'])]

        spreadsheet_intents = {
            QueryIntent.SPREADSHEET_CELL,
            QueryIntent.SPREADSHEET_ROW,
            QueryIntent.SPREADSHEET_COLUMN,
            QueryIntent.SPREADSHEET_LOOKUP,
        }
        if intent in spreadsheet_intents:
            spreadsheet_candidates = self.spreadsheet.retrieve(
                query=query,
                document_ids=document_ids,
                top_k=max(1, top_k),
            )
            if spreadsheet_candidates:
                logger.info(
                    f"[ROUTER_PROFILE] strategy=spreadsheet intent={intent.value} query='{query[:40]}...' "
                    f"docs={len(document_ids)} results={len(spreadsheet_candidates)}"
                )
                return spreadsheet_candidates

        # Use intent-driven top_k (unless overridden by caller with non-default)
        effective_top_k = top_k if top_k != 5 else intent_config.top_k
        effective_sparse_k = intent_config.sparse_k

        # quick heuristics
        q_words = query.split()
        word_count = len(q_words)
        query_lower = query.lower()

        rag_mode = (user_context or {}).get('rag_mode') or (user_context or {}).get('retrieval_mode') or 'fast'
        deep_mode = str(rag_mode).lower() == 'deep' or bool((user_context or {}).get('deep_mode'))
        allow_deep_llm = deep_mode and getattr(settings, 'RAG_DEEP_MODE_ENABLE_LLM_STEPS', True)

        # Fix: Query expansion disabled for speed - LLM expansion costs 70s on CPU
        # The QueryRewriter is available but only used for simple expansions
        # List/analytical intents benefit from query expansion
        expand_query = intent in (QueryIntent.LIST, QueryIntent.ANALYTICAL, QueryIntent.COMPARATIVE)
        query_variants = (
            self.rewriter.expand(
                query,
                conversation_history=conversation_history,
                force_llm=allow_deep_llm,
            )
            if expand_query else [query]
        )
        retrieval_variants = [variant for variant in query_variants if variant]
        expanded_query = query_variants[0] if query_variants else query
        if len(query_variants) > 1:
            expanded_query = self.rewriter._choose_best_variant(query, query_variants)
        if expanded_query and expanded_query not in retrieval_variants:
            retrieval_variants.insert(0, expanded_query)
        if not retrieval_variants:
            retrieval_variants = [query]

        def _merge_candidate_lists(candidate_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
            merged: Dict[str, Dict[str, Any]] = {}

            def _content_signature(candidate: Dict[str, Any]) -> str:
                text = candidate.get('snippet') or candidate.get('citation_excerpt') or candidate.get('content') or ''
                normalized = self.rewriter._normalize_text(text)
                normalized = re.sub(r'\s+', ' ', normalized).strip()
                if len(normalized) < 25:
                    return ''
                tokens = [token for token in re.findall(r'\w+', normalized) if len(token) > 2]
                if len(tokens) > 40:
                    tokens = tokens[:40]
                return ' '.join(tokens)

            def _candidate_key(candidate: Dict[str, Any]) -> str:
                document_id = str(candidate.get('document_id') or '')
                signature = _content_signature(candidate)
                if signature:
                    return f"{document_id}:{signature}"
                return f"{document_id}:{candidate.get('chunk_id') or id(candidate)}"

            for candidate_list in candidate_lists:
                for candidate in candidate_list:
                    key = _candidate_key(candidate)
                    if not key:
                        continue
                    score = float(candidate.get('score', 0.0) or 0.0)
                    existing = merged.get(key)
                    if not existing or score > float(existing.get('score', 0.0) or 0.0):
                        merged[key] = candidate.copy()
                        merged[key]['score'] = score
                    else:
                        existing['score'] = max(float(existing.get('score', 0.0) or 0.0), score)
                        if not existing.get('snippet') and candidate.get('snippet'):
                            existing['snippet'] = candidate.get('snippet')
                        if not existing.get('source') and candidate.get('source'):
                            existing['source'] = candidate.get('source')
            return sorted(
                merged.values(),
                key=lambda item: float(item.get('score', 0.0) or 0.0),
                reverse=True,
            )[:effective_top_k * 3]

        retrieval_query = expanded_query or query

        # ── HyDE: hypothetical answer embedding for analytical/comparative ──
        hyde_text = ''
        if intent in (QueryIntent.ANALYTICAL, QueryIntent.COMPARATIVE):
            hyde_text = self.rewriter.generate_hypothetical_answer(query, force_llm=allow_deep_llm)
            if hyde_text:
                logger.debug(f"[HYDE] Using hypothetical answer embedding for dense search")

        # ── Page hints: detect "trang X" or "cuối file" ──────────────────
        page_hints = self.rewriter.extract_page_hints(query)
        if page_hints['has_page_ref']:
            logger.debug(f"[PAGE_HINT] Found page refs: {page_hints}")
            # Boost top_k to reach deep pages
            effective_top_k = max(effective_top_k, 15)
            effective_sparse_k = max(effective_sparse_k, 30)
        elif page_hints['position'] == 'end':
            # "cuối file" without page number → still need more candidates
            effective_top_k = max(effective_top_k, 12)

        # ── Multi-hop: decompose complex queries ──────────────────────────
        sub_queries = []
        if intent in (QueryIntent.ANALYTICAL, QueryIntent.COMPARATIVE, QueryIntent.LIST, QueryIntent.TABLE):
            sub_queries = self.rewriter.decompose_complex_query(query, force_llm=allow_deep_llm)
            if sub_queries:
                logger.debug(f"[MULTI_HOP] Decomposed into {len(sub_queries)} sub-queries")

        # Step 1: Short or structured questions are usually fact/action lookups.
        # Use hybrid directly and keep RAPTOR for broader, longer questions.
        # Intent-aware: skip RAPTOR for factual/definitional even if long
        skip_raptor_intents = {QueryIntent.FACTUAL, QueryIntent.DEFINITIONAL, QueryIntent.IMAGE, QueryIntent.TABLE}
        has_structured_token = bool(
            re.search(r'\b\d{1,4}([/-]\d{1,2}){1,2}\b', query_lower)
            or re.search(r'\b\d+([.,]\d+)?\b', query_lower)
            or re.search(r'\S+@\S+\.\S+', query_lower)
            or re.search(r'https?://|www\.', query_lower)
        )
        if word_count <= 12 or has_structured_token or intent in skip_raptor_intents:
            t_strategy_start = time.monotonic()
            candidate_lists = [
                self.hybrid.retrieve(
                    variant,
                    top_k=effective_top_k,
                    sparse_k=effective_sparse_k,
                    document_ids=document_ids,
                    dense_weight=intent_config.dense_weight,
                )
                for variant in retrieval_variants[:2]
            ]
            # HyDE: add retrieval with hypothetical answer embedding
            if hyde_text:
                try:
                    hyde_results = self.hybrid.retrieve(
                        hyde_text,
                        top_k=effective_top_k,
                        sparse_k=0,
                        document_ids=document_ids,
                        dense_weight=1.0,
                    )
                    candidate_lists.append(hyde_results)
                    logger.debug(f"[HYDE] Added {len(hyde_results)} candidates from hypothetical answer")
                except Exception as e:
                    logger.debug(f"[HYDE] Retrieval failed: {e}")
            # Multi-hop: retrieve per sub-query
            if sub_queries:
                for sq in sub_queries[:2]:
                    try:
                        sq_results = self.hybrid.retrieve(
                            sq,
                            top_k=max(3, effective_top_k // 2),
                            sparse_k=effective_sparse_k,
                            document_ids=document_ids,
                            dense_weight=intent_config.dense_weight,
                        )
                        candidate_lists.append(sq_results)
                    except Exception as e:
                        logger.debug(f"[MULTI_HOP] Sub-query retrieval failed: {e}")
                logger.debug(f"[MULTI_HOP] Added results from {len(sub_queries)} sub-queries")
            candidates = _merge_candidate_lists(candidate_lists)
            logger.info(
                f"[ROUTER_PROFILE] strategy=hybrid intent={intent.value} query='{query[:40]}...' "
                f"resolved='{retrieval_query[:40]}...' docs={len(document_ids)} "
                f"hyde={'Y' if hyde_text else 'N'} multi_hop={len(sub_queries)} "
                f"time={(time.monotonic() - t_strategy_start) * 1000:.1f}ms"
            )

        # Step 2: RAPTOR Logic — dùng khi query dài hoặc document có hierarchical structure
        else:
            # Chỉ thử RAPTOR khi tìm kiếm trong đúng 1 document (nhiều docs → hybrid tốt hơn)
            doc_id = document_ids[0] if len(document_ids) == 1 else None
            use_raptor = False

            if doc_id:
                try:
                    Document = apps.get_model('documents', 'Document')
                    DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                    doc = Document.objects.get(pk=doc_id)
                    metadata = doc.metadata or {}
                    raptor_ready = bool(metadata.get('raptor_ready')) or metadata.get('raptor_status') == 'ready'
                    has_vectorized_summaries = DocumentChunk.objects.filter(
                        document_id=doc_id,
                        node_type='summary',
                        vector_id__isnull=False,
                        is_deleted=False,
                    ).exists()
                    # Use RAPTOR only after the background tree is marked ready.
                    if raptor_ready and has_vectorized_summaries:
                        use_raptor = True
                except Exception:
                    pass

            # Also use RAPTOR for long queries (>25 words) even without explicit doc_id hint
            if not use_raptor and not doc_id and word_count > 25:
                use_raptor = True

            if use_raptor and doc_id:
                logger.info(f"🚀 Routing query to RAPTOR strategy for document {doc_id}")
                t_strategy_start = time.monotonic()
                candidates = self._retrieve_via_raptor(retrieval_query, doc_id, top_k=effective_top_k)
                logger.info(
                    f"[ROUTER_PROFILE] strategy=raptor query='{query[:40]}...' doc_id={doc_id} "
                    f"time={(time.monotonic() - t_strategy_start) * 1000:.1f}ms"
                )
            else:
                # Default to Hybrid search (multi-doc hoặc không có RAPTOR)
                t_strategy_start = time.monotonic()
                candidate_lists = [
                    self.hybrid.retrieve(
                        variant,
                        top_k=effective_top_k,
                        sparse_k=effective_sparse_k,
                        document_ids=document_ids,
                        dense_weight=intent_config.dense_weight,
                    )
                    for variant in retrieval_variants[:2]
                ]
                # HyDE + Multi-hop same as above
                if hyde_text:
                    try:
                        hyde_results = self.hybrid.retrieve(
                            hyde_text,
                            top_k=effective_top_k,
                            sparse_k=0,
                            document_ids=document_ids,
                            dense_weight=1.0,
                        )
                        candidate_lists.append(hyde_results)
                    except Exception as e:
                        logger.debug(f"[HYDE] Retrieval failed: {e}")
                if sub_queries:
                    for sq in sub_queries[:2]:
                        try:
                            sq_results = self.hybrid.retrieve(
                                sq,
                                top_k=max(3, effective_top_k // 2),
                                sparse_k=effective_sparse_k,
                                document_ids=document_ids,
                                dense_weight=intent_config.dense_weight,
                            )
                            candidate_lists.append(sq_results)
                        except Exception as e:
                            logger.debug(f"[MULTI_HOP] Sub-query retrieval failed: {e}")
                candidates = _merge_candidate_lists(candidate_lists)
                logger.info(
                    f"[ROUTER_PROFILE] strategy=hybrid query='{query[:40]}...' "
                    f"resolved='{retrieval_query[:40]}...' docs={len(document_ids)} "
                    f"hyde={'Y' if hyde_text else 'N'} multi_hop={len(sub_queries)} "
                    f"time={(time.monotonic() - t_strategy_start) * 1000:.1f}ms"
                )

        # Step 2.5: Hydrate DB chunks before page boosting/reranking.
        # Dense and sparse retrieval return short previews; reranking should see
        # enough evidence text to score the real chunk, not just the preview.
        candidates = self._hydrate_candidate_snippets(candidates)

        # Step 2.5.5: Intent-aware candidate filtering (e.g., exclude TOC for TABLE queries)
        candidates_before_filter = len(candidates)
        # TEMPORARILY DISABLED for debugging - will re-enable after testing
        # candidates = self._filter_candidates_by_intent(candidates, intent, query)
        if len(candidates) < candidates_before_filter:
            logger.debug(f"[FILTER] Intent-aware filtering: {candidates_before_filter} → {len(candidates)} candidates")

        # Step 2.6: Page-aware candidate boosting
        if page_hints['has_page_ref'] or page_hints['position']:
            candidates = self._apply_page_hints(candidates, page_hints)
            logger.debug(f"[PAGE_HINT] Applied page hints, {len(candidates)} candidates after boost")

        # Step 3: Final Rerank for maximum relevance
        t_rerank_start = time.monotonic()
        ranked = self.reranker.rerank(query=query, candidates=candidates, top_k=effective_top_k)
        logger.info(
            f"[ROUTER_PROFILE] rerank intent={intent.value} query='{query[:40]}...' "
            f"candidates={len(candidates)}→{len(ranked)} "
            f"time={(time.monotonic() - t_rerank_start) * 1000:.1f}ms total={(time.monotonic() - t_route_start) * 1000:.1f}ms"
        )
        return ranked

    def _hydrate_candidate_snippets(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replace short retrieval previews with stored chunk content for reranking."""
        if not candidates:
            return []

        chunk_ids = [
            str(candidate.get('chunk_id'))
            for candidate in candidates
            if candidate.get('chunk_id') and candidate.get('source') != 'asset'
        ]
        if not chunk_ids:
            return candidates

        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            rows = DocumentChunk.objects.filter(
                id__in=chunk_ids,
                is_deleted=False,
            ).values(
                'id',
                'document_id',
                'content',
                'page_number',
                'chunk_index',
                'metadata',
                'node_type',
            )
            row_map = {str(row['id']): row for row in rows}
            max_chars = int(getattr(settings, 'RAG_RERANK_SNIPPET_CHARS', 1800))

            for candidate in candidates:
                chunk_id = str(candidate.get('chunk_id') or '')
                row = row_map.get(chunk_id)
                if not row:
                    continue

                content = (row.get('content') or '').strip()
                if content:
                    candidate['_retrieval_preview'] = candidate.get('snippet') or ''
                    candidate['snippet'] = content[:max_chars]
                candidate['document_id'] = str(row.get('document_id') or candidate.get('document_id') or '')
                candidate['page'] = row.get('page_number') or candidate.get('page')
                candidate['chunk_index'] = row.get('chunk_index')
                candidate['metadata'] = row.get('metadata') or candidate.get('metadata') or {}
                candidate['node_type'] = row.get('node_type') or candidate.get('node_type')
        except Exception as e:
            logger.debug(f"[ROUTER] Could not hydrate candidate snippets: {e}")

        return candidates

    def _apply_page_hints(self, candidates: List[Dict], page_hints: Dict[str, Any]) -> List[Dict]:
        """Boost candidates matching page references using proportional thresholds.

        Instead of hardcoded "page >= 20 = end", computes max page from actual
        candidates and boosts proportionally. Works for any document size.

        - Exact page match: +0.25 score boost
        - Nearby page (+/- 1): +0.10 boost
        - "cuối file" mode: boost pages in last 25% proportionally, penalize first 15%
        - "đầu file" mode: boost pages in first 25%, penalize last 25%
        """
        target_pages = set(page_hints.get('page_numbers', []) or [])
        position = page_hints.get('position')

        # Compute actual page range from candidates
        pages = []
        for c in candidates:
            page = c.get('page')
            if page is not None:
                try:
                    pages.append(int(page))
                except (ValueError, TypeError):
                    pass

        max_page = max(pages) if pages else 1
        min_page = min(pages) if pages else 1

        # Proportional thresholds
        early_cutoff = min_page + max(2, int((max_page - min_page) * 0.15))
        late_start = max_page - max(2, int((max_page - min_page) * 0.25))

        for c in candidates:
            page = c.get('page')
            if page is None:
                continue

            try:
                page_num = int(page)
            except (ValueError, TypeError):
                continue

            # Exact page match
            if page_num in target_pages:
                c['score'] = float(c.get('score', 0) or 0) + 0.25
                c['_page_boost'] = 'exact'
                continue

            # Nearby page (+/- 1)
            for tp in target_pages:
                if abs(page_num - tp) <= 1:
                    c['score'] = float(c.get('score', 0) or 0) + 0.10
                    c['_page_boost'] = 'nearby'
                    break

        # Position-based proportional boosting
        if position == 'end':
            for c in candidates:
                page = c.get('page')
                if page is None or c.get('_page_boost'):
                    continue
                try:
                    page_num = int(page)
                except (ValueError, TypeError):
                    continue
                if page_num <= early_cutoff:
                    c['score'] = float(c.get('score', 0) or 0) - 0.30
                    c['_page_boost'] = 'early_penalty'
                elif page_num >= late_start:
                    c['score'] = float(c.get('score', 0) or 0) + 0.15
                    c['_page_boost'] = 'end_boost'

        elif position == 'start':
            for c in candidates:
                page = c.get('page')
                if page is None or c.get('_page_boost'):
                    continue
                try:
                    page_num = int(page)
                except (ValueError, TypeError):
                    continue
                if page_num <= early_cutoff:
                    c['score'] = float(c.get('score', 0) or 0) + 0.15
                    c['_page_boost'] = 'start_boost'
                elif page_num >= late_start:
                    c['score'] = float(c.get('score', 0) or 0) - 0.20
                    c['_page_boost'] = 'late_penalty'

        logger.debug(
            f"[PAGE_HINT] target={target_pages} pos={position} "
            f"range=[{min_page}-{max_page}] early<={early_cutoff} late>={late_start} "
            f"boosted={sum(1 for c in candidates if c.get('_page_boost'))}"
        )
        return candidates

    def _filter_candidates_by_intent(
        self, 
        candidates: List[Dict[str, Any]], 
        intent: QueryIntent, 
        query: str
    ) -> List[Dict[str, Any]]:
        """Filter candidates based on query intent.
        
        For TABLE intent:
        - Exclude chunks marked as TOC (is_toc=True)
        - Exclude chunks containing TOC keywords (mục lục, page, contents, etc.)
        - This ensures we retrieve actual table data, not table-of-contents
        
        For other intents: no filtering
        """
        if intent != QueryIntent.TABLE or not candidates:
            return candidates
        
        toc_keywords = (
            'muc luc', 'mục lục', 'table of contents', 'contents', 
            'index', 'chapter', 'section', 'contents page', 'trang'
        )
        
        filtered = []
        excluded_toc = 0
        excluded_keywords = 0
        
        for candidate in candidates:
            # Check is_toc flag in metadata
            metadata = candidate.get('metadata') or {}
            if metadata.get('is_toc'):
                excluded_toc += 1
                continue
            
            # Check for TOC keywords in snippet/content
            snippet = (candidate.get('snippet') or '').lower()
            has_toc_keyword = any(kw in snippet for kw in toc_keywords)
            
            if has_toc_keyword:
                excluded_keywords += 1
                continue
            
            filtered.append(candidate)
        
        if excluded_toc > 0 or excluded_keywords > 0:
            logger.debug(
                f"[TABLE_FILTER] Excluded TOC chunks: {excluded_toc} (marked), "
                f"{excluded_keywords} (keyword-based). Remaining: {len(filtered)}/{len(candidates)}"
            )
        
        # If we filtered out too many, return at least top candidates to avoid empty result
        if not filtered and excluded_toc + excluded_keywords > 0:
            logger.warning(
                f"[TABLE_FILTER] All candidates were TOC. Returning original top candidates."
            )
            return candidates[:max(3, len(candidates) // 2)]
        
        return filtered

    def _retrieve_via_raptor(self, query: str, document_id: str, top_k: int = 5) -> List[Dict]:
        """Retrieve using RAPTOR tree: search summary nodes FIRST, then descend to children.
        
        Strategy:
        1. Query summary nodes (node_type='summary') for document
        2. Rank summaries by relevance to query
        3. For top K/2 summaries, retrieve their child chunks
        4. Return merged results with boosted scores from parent summaries
        """
        t_raptor_start = time.monotonic()
        try:
            from django.apps import apps
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            
            # Step 1: Get all summary nodes for this document
            summary_chunks = DocumentChunk.objects.filter(
                document_id=document_id,
                node_type='summary',
                is_deleted=False
            ).order_by('page_number')
            
            if not summary_chunks.exists():
                logger.debug(f"No summary nodes for document {document_id}, falling back to hybrid")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id])
            
            # Step 2: Generate query embedding
            try:
                query_embedding = self.hybrid.embedding_client.create_embedding(query)
            except Exception as e:
                logger.warning(f"Failed to embed query for RAPTOR: {e}")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id])
            
            # Step 3: Search Qdrant for summary nodes
            summary_results = self.hybrid.qdrant.search_similar(
                embedding=query_embedding,
                limit=max(6, top_k * 2),
                filter_payload={
                    'document_id': document_id,
                    'node_type': 'summary',
                },
            )
            
            # Filter to only summary nodes in this document
            top_summaries = []
            for vector_id, score, payload in summary_results:
                chunk_id = payload.get('chunk_id')
                if not chunk_id:
                    continue
                try:
                    summary_node = DocumentChunk.objects.get(
                        id=chunk_id,
                        document_id=document_id,
                        node_type='summary',
                        is_deleted=False
                    )
                    top_summaries.append({
                        'node': summary_node,
                        'score': float(score) if score else 0.5,
                        'vector_id': vector_id
                    })
                except DocumentChunk.DoesNotExist:
                    continue
            
            if not top_summaries:
                logger.debug(f"No summary nodes found via Qdrant for document {document_id}")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id])
            
            logger.debug(f"RAPTOR: Found {len(top_summaries)} summary nodes for document {document_id}")
            
            # Step 4: For each summary, retrieve its children or descendants
            final_candidates = []

            def collect_detail_descendants(root_node, limit: int) -> List[Any]:
                """Walk RAPTOR summary nodes until detail chunks are reached."""
                detail_nodes = []
                frontier = [root_node]
                seen = set()

                while frontier and len(detail_nodes) < limit:
                    node = frontier.pop(0)
                    if str(node.id) in seen:
                        continue
                    seen.add(str(node.id))

                    children = list(
                        DocumentChunk.objects.filter(
                            parent_node_id=node.id,
                            is_deleted=False,
                        ).order_by('page_number', 'chunk_index')[: max(limit * 3, limit)]
                    )
                    for child in children:
                        if getattr(child, 'node_type', '') == 'detail':
                            detail_nodes.append(child)
                            if len(detail_nodes) >= limit:
                                break
                        else:
                            frontier.append(child)

                return detail_nodes
            
            for summary_info in top_summaries:
                summary_node = summary_info['node']
                summary_score = summary_info['score']
                node_type = getattr(summary_node, 'node_type', 'summary')

                detail_children = collect_detail_descendants(summary_node, top_k)
                if detail_children:
                    for child in detail_children:
                        child_score = summary_score * 0.85
                        final_candidates.append({
                            'chunk_id': str(child.id),
                            'document_id': str(document_id),
                            'score': child_score,
                            'source': f'raptor_{node_type}_detail',
                            'snippet': (child.content or '')[:300],
                            'page': child.page_number,
                            'parent_summary_id': str(summary_node.id)
                        })
                else:
                    final_candidates.append({
                        'chunk_id': str(summary_node.id),
                        'document_id': str(document_id),
                        'score': summary_score * 0.9,
                        'source': f'raptor_{node_type}',
                        'snippet': (summary_node.content or '')[:300],
                        'page': summary_node.page_number
                    })
            
            # Sort by score and return top K
            final_candidates = sorted(final_candidates, key=lambda x: float(x.get('score', 0) or 0), reverse=True)
            result = final_candidates[:top_k]
            
            # Merge RAPTOR results with hybrid results for better coverage
            hybrid_candidates = self.hybrid.retrieve(
                query,
                top_k=top_k,
                document_ids=[document_id],
                query_embedding=query_embedding,
            )
            
            # Deduplicate by chunk_id
            seen_ids = {c['chunk_id'] for c in result}
            for hc in hybrid_candidates:
                if hc['chunk_id'] not in seen_ids:
                    result.append(hc)
                    seen_ids.add(hc['chunk_id'])
            
            result = sorted(result, key=lambda x: float(x.get('score', 0) or 0), reverse=True)[:top_k * 2]
            
            logger.info(
                f"RAPTOR retrieval: {len(result)} results "
                f"({len([c for c in result if 'raptor' in c.get('source', '')])} RAPTOR, "
                f"{len([c for c in result if 'raptor' not in c.get('source', '')])} hybrid)"
            )
            logger.info(
                f"[RAPTOR_PROFILE] query='{query[:40]}...' doc_id={document_id} "
                f"top_k={top_k} time={(time.monotonic() - t_raptor_start) * 1000:.1f}ms"
            )
            return result
        
        except Exception as e:
            logger.error(f"RAPTOR retrieval failed: {e}", exc_info=True)
            logger.info("Falling back to standard hybrid retrieval")
            return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id])
