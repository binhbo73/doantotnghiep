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
        forced_intent = (user_context or {}).get('forced_intent')
        if forced_intent:
            try:
                intent = QueryIntent(str(forced_intent))
                logger.debug("[QUERY_INTENT] forced intent=%s query='%s'", intent.value, query[:80])
            except ValueError:
                intent = self.intent_classifier.classify(query)
        else:
            intent = self.intent_classifier.classify(query)
        intent_config = self.intent_classifier.get_retrieval_config(intent)

        # Lấy danh sách document IDs để filter (ưu tiên 'document_ids' list)
        document_ids: List[str] = []
        explicit_document_ids: List[str] = []
        folder_ids: List[str] = []
        if user_context:
            if user_context.get('document_ids'):
                document_ids = [str(d) for d in user_context['document_ids'] if d]
            if user_context.get('explicit_document_ids'):
                explicit_document_ids = [str(d) for d in user_context['explicit_document_ids'] if d]
            if user_context.get('folder_ids'):
                folder_ids = [str(d) for d in user_context['folder_ids'] if d]
            elif user_context.get('document_id'):
                document_ids = [str(user_context['document_id'])]

        include_historical = bool((user_context or {}).get('include_historical'))
        qdrant_filter: Dict[str, Any] = {'node_type': 'detail'}
        if include_historical:
            qdrant_filter['__include_historical'] = True
        else:
            qdrant_filter['is_current'] = True
        # HybridRetriever already receives the fully resolved document scope.
        # Do not replace it with only the explicitly selected current version:
        # amendment retrieval also needs inherited ancestor document IDs.
        if folder_ids:
            qdrant_filter['folder_id'] = folder_ids

        page_numbers = (user_context or {}).get('page_numbers') or []
        if not page_numbers and (user_context or {}).get('current_page') is not None:
            page_numbers = [user_context.get('current_page')]
        if len(page_numbers) == 1:
            try:
                qdrant_filter['page_number'] = [int(page_numbers[0])]
            except (TypeError, ValueError):
                pass

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

        spreadsheet_probe_candidates: List[Dict[str, Any]] = []
        spreadsheet_probe_score = 0.0
        if self._should_probe_spreadsheets(query, intent, document_ids):
            try:
                spreadsheet_probe_candidates = self.spreadsheet.retrieve(
                    query=query,
                    document_ids=document_ids,
                    top_k=max(3, effective_top_k),
                )
                spreadsheet_probe_score = max(
                    (float(candidate.get('score', 0.0) or 0.0) for candidate in spreadsheet_probe_candidates),
                    default=0.0,
                )
                if spreadsheet_probe_candidates:
                    logger.info(
                        f"[ROUTER_PROFILE] strategy=spreadsheet_probe intent={intent.value} "
                        f"query='{query[:40]}...' docs={len(document_ids)} "
                        f"results={len(spreadsheet_probe_candidates)} top_score={spreadsheet_probe_score:.1f}"
                    )
            except Exception as exc:
                logger.debug(f"[SPREADSHEET_PROBE] failed: {exc}")
                spreadsheet_probe_candidates = []
                spreadsheet_probe_score = 0.0

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
        normalized_query = self.rewriter._normalize_text(query)
        current_page = None
        if user_context and re.search(r'\b(?:trang\s*(?:nay|hien tai)|page\s*(?:nay|hien tai)|current page|this page)\b', normalized_query):
            current_page = (
                user_context.get('current_page')
                or user_context.get('currentPage')
                or user_context.get('page_number')
                or user_context.get('page')
            )
        if current_page and not page_hints.get('page_numbers'):
            try:
                current_page_num = int(current_page)
                if current_page_num > 0:
                    page_hints['page_numbers'] = [current_page_num]
                    page_hints['page_range'] = [current_page_num, current_page_num]
                    page_hints['has_page_ref'] = True
            except (TypeError, ValueError):
                logger.debug(f"[PAGE_HINT] Invalid current_page in user_context: {current_page!r}")
        if page_hints['has_page_ref']:
            logger.debug(f"[PAGE_HINT] Found page refs: {page_hints}")
            if len(page_hints.get('page_numbers') or []) == 1:
                try:
                    qdrant_filter['page_number'] = [int(page_hints['page_numbers'][0])]
                except (TypeError, ValueError):
                    pass
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
        broad_raptor_intent = bool(intent_config.use_raptor and intent not in skip_raptor_intents)
        has_structured_token = bool(
            re.search(r'\b\d{1,4}([/-]\d{1,2}){1,2}\b', query_lower)
            or re.search(r'\b\d+([.,]\d+)?\b', query_lower)
            or re.search(r'\S+@\S+\.\S+', query_lower)
            or re.search(r'https?://|www\.', query_lower)
        )
        spreadsheet_direct_threshold = float(
            getattr(settings, 'RAG_SPREADSHEET_DIRECT_MATCH_SCORE', 68.0)
        )
        if spreadsheet_probe_candidates and spreadsheet_probe_score >= spreadsheet_direct_threshold:
            candidates = spreadsheet_probe_candidates
            logger.info(
                f"[ROUTER_PROFILE] strategy=spreadsheet_content intent={intent.value} "
                f"query='{query[:40]}...' docs={len(document_ids)} "
                f"results={len(candidates)} top_score={spreadsheet_probe_score:.1f}"
            )
        elif (word_count <= 12 or has_structured_token or intent in skip_raptor_intents) and not broad_raptor_intent:
            t_strategy_start = time.monotonic()
            candidate_lists = [
                self.hybrid.retrieve(
                    variant,
                    top_k=effective_top_k,
                    sparse_k=effective_sparse_k,
                    document_ids=document_ids,
                    qdrant_filter=qdrant_filter,
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
                        qdrant_filter=qdrant_filter,
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
                            qdrant_filter=qdrant_filter,
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
                candidates = self._retrieve_via_raptor(
                    retrieval_query,
                    doc_id,
                    top_k=effective_top_k,
                    page_hints=page_hints,
                )
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
                        qdrant_filter=qdrant_filter,
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
                            qdrant_filter=qdrant_filter,
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
                                qdrant_filter=qdrant_filter,
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

        # Step 2.5.5: exclude TOC/front-matter unless the user explicitly asks for it.
        candidates_before_filter = len(candidates)
        candidates = self._filter_candidates_by_intent(candidates, intent, query)
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

    def _should_probe_spreadsheets(
        self,
        query: str,
        intent: QueryIntent,
        document_ids: List[str],
    ) -> bool:
        """Run content-first spreadsheet discovery for table-like broad searches.

        This is intentionally not a filename shortcut. It lets spreadsheet row,
        sheet-title, and whole-table chunks compete only when the user asks a
        table/list-style question with spreadsheet-ish business terms.
        """
        if not document_ids:
            return False

        if not bool(getattr(settings, 'RAG_SPREADSHEET_CONTENT_DISCOVERY_ENABLED', True)):
            return False

        if intent not in {QueryIntent.TABLE, QueryIntent.LIST, QueryIntent.FACTUAL}:
            return False

        normalized = self.rewriter._normalize_text(query or '')
        if not normalized:
            return False

        markers = (
            'bang', 'table', 'bang tinh', 'excel', 'csv', 'sheet',
            'dong', 'hang', 'cot', 'row', 'column',
            'luong', 'thuong', 'phu cap', 'khau tru', 'kpi',
            'san pham', 'nhan vien', 'cong nhan',
            'so lieu', 'du lieu', 'thong ke', 'bao cao',
        )
        return any(marker in normalized for marker in markers)

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
            spreadsheet_max_chars = int(
                getattr(settings, 'RAG_SPREADSHEET_RERANK_SNIPPET_CHARS', 5000)
            )

            for candidate in candidates:
                chunk_id = str(candidate.get('chunk_id') or '')
                row = row_map.get(chunk_id)
                if not row:
                    continue

                content = (row.get('content') or '').strip()
                if content:
                    metadata = row.get('metadata') or candidate.get('metadata') or {}
                    is_spreadsheet = (
                        candidate.get('source') == 'spreadsheet'
                        or metadata.get('content_format') == 'spreadsheet_markdown'
                        or metadata.get('source') == 'excel_chunker_v2'
                    )
                    candidate['_retrieval_preview'] = candidate.get('snippet') or ''
                    candidate['snippet'] = content[:spreadsheet_max_chars if is_spreadsheet else max_chars]
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
        """Filter front-matter unless the user explicitly asks for TOC/list pages.
        
        Applies to all intents:
        - Exclude chunks marked as TOC (is_toc=True)
        - Exclude chunks containing TOC keywords (mục lục, page, contents, etc.)
        - This ensures we retrieve actual document content, not table-of-contents
        
        Explicit TOC queries bypass this filter.
        """
        if not candidates:
            return candidates

        query_norm = self.rewriter._normalize_text(query or '')
        asks_toc = any(
            marker in query_norm
            for marker in ('muc luc', 'table of contents', 'contents page', 'bang muc luc')
        )
        if asks_toc:
            return candidates

        filtered = []
        excluded = 0
        for candidate in candidates:
            if candidate.get('source') != 'asset' and self._is_front_matter_candidate(candidate):
                excluded += 1
                continue
            filtered.append(candidate)

        if excluded:
            logger.debug(f"[FRONT_MATTER_FILTER] Excluded {excluded}/{len(candidates)} TOC/front-matter candidates")
        return filtered

    def _is_front_matter_candidate(self, candidate: Dict[str, Any]) -> bool:
        metadata = candidate.get('metadata') or {}
        if metadata.get('is_toc') or metadata.get('layout_role') == 'toc':
            return True

        text = candidate.get('snippet') or candidate.get('citation_excerpt') or candidate.get('content') or ''
        text_norm = self.rewriter._normalize_text(text)
        if any(
            marker in text_norm
            for marker in ('muc luc', 'danh sach bang', 'danh sach hinh anh', 'table of contents', 'contents page')
        ):
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(re.search(r'\.\.\.\s*\d+$', line) for line in lines[:20]):
            return True
        if len(lines) < 2:
            return False

        toc_like = 0
        for line in lines[:20]:
            if re.search(r'\.\.\.\s*\d+$', line) or re.search(r'^(?:\d+(?:\.\d+)*|bảng\s+\d+|hình\s+\d+)\b.+\s\d+$', line, flags=re.IGNORECASE):
                toc_like += 1
        return toc_like >= 2 and (toc_like / max(1, min(len(lines), 20))) >= 0.35

    def _page_summary_candidates(
        self,
        DocumentChunk,
        document_id: str,
        page_hints: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return page summary nodes for explicit page/page-range summary requests."""
        page_numbers = page_hints.get('page_numbers') or []
        if not page_numbers:
            return []

        qs = DocumentChunk.objects.filter(
            document_id=document_id,
            node_type='summary',
            metadata__summary_kind='page_summary',
            page_number__in=page_numbers,
            is_deleted=False,
        ).order_by('page_number')

        result = []
        for node in qs:
            result.append({
                'node': node,
                'score': 1.0,
                'vector_id': node.vector_id,
            })
        return result

    def _retrieve_via_raptor(
        self,
        query: str,
        document_id: str,
        top_k: int = 5,
        page_hints: Dict[str, Any] = None,
    ) -> List[Dict]:
        """Retrieve using RAPTOR tree: search summary nodes, then rank descendants.
        
        Strategy:
        1. Query summary nodes (node_type='summary') for document
        2. Rank summaries by relevance to query
        3. Gather detail descendants from top summaries
        4. Re-rank descendants by detail embedding similarity, blended with parent score
        5. Return merged RAPTOR + hybrid results for coverage
        """
        t_raptor_start = time.monotonic()
        try:
            from django.apps import apps
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            page_hints = page_hints or {}
            
            # Step 1: Get all summary nodes for this document
            summary_chunks = DocumentChunk.objects.filter(
                document_id=document_id,
                node_type='summary',
                is_deleted=False
            ).order_by('page_number')
            
            if not summary_chunks.exists():
                logger.debug(f"No summary nodes for document {document_id}, falling back to hybrid")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id], qdrant_filter={'node_type': 'detail'})
            
            # Step 2: Generate query embedding
            try:
                query_embedding = self.hybrid.embedding_client.create_embedding(query)
            except Exception as e:
                logger.warning(f"Failed to embed query for RAPTOR: {e}")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id], qdrant_filter={'node_type': 'detail'})

            page_summary_candidates = self._page_summary_candidates(
                DocumentChunk=DocumentChunk,
                document_id=document_id,
                page_hints=page_hints,
            )
            
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
            top_summaries = page_summary_candidates[:]
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
                    if any(str(item['node'].id) == str(summary_node.id) for item in top_summaries):
                        continue
                    top_summaries.append({
                        'node': summary_node,
                        'score': float(score) if score else 0.5,
                        'vector_id': vector_id
                    })
                except DocumentChunk.DoesNotExist:
                    continue
            
            if not top_summaries:
                logger.debug(f"No summary nodes found via Qdrant for document {document_id}")
                return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id], qdrant_filter={'node_type': 'detail'})
            
            logger.debug(f"RAPTOR: Found {len(top_summaries)} summary nodes for document {document_id}")
            
            # Step 4: Gather descendants from top summaries, then rank details
            # against the query. The older logic returned the first children in
            # page order, which can miss the best chunk inside a large cluster.
            detail_candidates = {}
            summary_candidates = []
            descendant_limit = max(
                top_k * 8,
                int(getattr(settings, 'RAG_RAPTOR_DESCENDANT_LIMIT', 80)),
            )

            def cosine_similarity(a, b):
                if hasattr(a, 'tolist'):
                    a = a.tolist()
                if hasattr(b, 'tolist'):
                    b = b.tolist()
                if not a or not b:
                    return 0.0
                n = min(len(a), len(b))
                dot = 0.0
                norm_a = 0.0
                norm_b = 0.0
                for i in range(n):
                    av = float(a[i])
                    bv = float(b[i])
                    dot += av * bv
                    norm_a += av * av
                    norm_b += bv * bv
                if norm_a <= 0.0 or norm_b <= 0.0:
                    return 0.0
                return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))

            def collect_detail_descendants(root_node, limit: int) -> List[Any]:
                """Walk RAPTOR summary nodes until detail chunks are reached.

                Multi-cluster RAPTOR stores secondary memberships in each
                summary node's metadata['child_node_ids']. The database still
                has a single parent_node FK for fast canonical traversal, so
                retrieval must read both sources.
                """
                detail_nodes = []
                frontier = [root_node]
                seen = set()
                seen_children = set()

                while frontier and len(detail_nodes) < limit:
                    node = frontier.pop(0)
                    if str(node.id) in seen:
                        continue
                    seen.add(str(node.id))

                    children_by_id = {}
                    fk_children = list(
                        DocumentChunk.objects.filter(
                            parent_node_id=node.id,
                            is_deleted=False,
                        ).order_by('page_number', 'chunk_index')[: max(limit * 3, limit)]
                    )
                    for child in fk_children:
                        children_by_id[str(child.id)] = child

                    metadata = getattr(node, 'metadata', None) or {}
                    metadata_child_ids = [
                        str(child_id)
                        for child_id in (metadata.get('child_node_ids') or [])
                        if child_id
                    ]
                    missing_child_ids = [
                        child_id
                        for child_id in metadata_child_ids
                        if child_id not in children_by_id and child_id not in seen_children
                    ]
                    if missing_child_ids:
                        metadata_children = DocumentChunk.objects.filter(
                            id__in=missing_child_ids,
                            is_deleted=False,
                        ).order_by('page_number', 'chunk_index')
                        for child in metadata_children:
                            children_by_id[str(child.id)] = child

                    children = sorted(children_by_id.values(), key=lambda item: (
                        getattr(item, 'page_number', 10**9) or 10**9,
                        getattr(item, 'chunk_index', 0) or 0,
                    ))

                    for child in children:
                        child_id = str(child.id)
                        if child_id in seen_children:
                            continue
                        seen_children.add(child_id)
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

                summary_candidates.append({
                    'chunk_id': str(summary_node.id),
                    'document_id': str(document_id),
                    'score': summary_score * 0.9,
                    'source': f'raptor_{node_type}',
                    'snippet': (summary_node.content or '')[:300],
                    'page': summary_node.page_number,
                    'node_type': node_type,
                })

                detail_children = collect_detail_descendants(summary_node, descendant_limit)
                if detail_children:
                    for child in detail_children:
                        chunk_id = str(child.id)
                        embedding = self.raptor._load_node_embedding(child)
                        detail_score = cosine_similarity(query_embedding, embedding) if embedding else 0.0
                        # Blend local detail relevance with the matched summary
                        # score, so the tree still guides retrieval without
                        # blindly returning page-order descendants.
                        child_score = (0.7 * detail_score) + (0.3 * summary_score)
                        existing = detail_candidates.get(chunk_id)
                        if existing and float(existing.get('score', 0.0) or 0.0) >= child_score:
                            continue
                        detail_candidates[chunk_id] = {
                            'chunk_id': chunk_id,
                            'document_id': str(document_id),
                            'score': child_score,
                            'source': f'raptor_{node_type}_detail',
                            'snippet': (child.content or '')[:300],
                            'page': child.page_number,
                            'parent_summary_id': str(summary_node.id),
                            'parent_summary_score': summary_score,
                            'detail_score': detail_score,
                            '_embedding': embedding,
                        }
            
            detail_ranked = sorted(
                detail_candidates.values(),
                key=lambda x: float(x.get('score', 0) or 0),
                reverse=True,
            )
            summary_ranked = sorted(
                summary_candidates,
                key=lambda x: float(x.get('score', 0) or 0),
                reverse=True,
            )
            result = detail_ranked[:top_k]
            for summary_candidate in summary_ranked[: max(1, top_k // 3)]:
                if summary_candidate['chunk_id'] not in {c['chunk_id'] for c in result}:
                    result.append(summary_candidate)
            
            # Merge RAPTOR results with hybrid results for better coverage
            hybrid_candidates = self.hybrid.retrieve(
                query,
                top_k=top_k,
                document_ids=[document_id],
                qdrant_filter={'node_type': 'detail'},
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
            return self.hybrid.retrieve(query, top_k=top_k, document_ids=[document_id], qdrant_filter={'node_type': 'detail'})
