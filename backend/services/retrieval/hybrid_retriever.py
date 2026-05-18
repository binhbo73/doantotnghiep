from typing import List, Dict, Any, Optional
import logging
import math
import hashlib
import re
import time
from django.db.models import Q
from django.apps import apps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever: BM25 (sparse) + Qdrant (dense) + Asset search."""

    def __init__(self, qdrant_client, embedding_client, sparse_boost: float = 1.0):
        self.qdrant = qdrant_client
        self.embedding_client = embedding_client
        self.sparse_boost = sparse_boost
        self.cache_ttl = getattr(settings, 'CACHE_TTL', 600)

        try:
            from .bm25_searcher import BM25Searcher
            self.bm25 = BM25Searcher()
            logger.info("BM25 sparse search initialized")
        except Exception as e:
            logger.warning(f"BM25 init failed: {e}")
            self.bm25 = None

    def retrieve(
        self, query: str, top_k: int = 10, sparse_k: int = 10,
        document_ids: List[str] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Return merged candidates: chunks + assets."""
        t_start = time.monotonic()

        doc_hash = hashlib.md5(
            ','.join(sorted(document_ids or [])).encode()
        ).hexdigest()[:12]
        cache_key = f"hybrid_retrieval:v4:{query}:{top_k}:{sparse_k}:{doc_hash}"
        try:
            cached = cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

        candidates: Dict[str, Dict[str, Any]] = {}
        asset_candidates: List[Dict[str, Any]] = []
        sparse_scores: Dict[str, float] = {}
        dense_scores: Dict[str, float] = {}
        timing = {}

        import unicodedata
        query_norm = ''.join(
            c for c in unicodedata.normalize('NFD', (query or '').lower())
            if unicodedata.category(c) != 'Mn'
        )
        query_tokens = set(re.findall(r'\w+', query_norm))
        image_intent_tokens = {'anh', 'asset', 'image', 'photo', 'screenshot'}
        image_action_tokens = {'xem', 'show', 'hien', 'thi', 'liet', 'ke', 'tim'}
        should_search_assets = (
            bool(query_tokens & image_intent_tokens)
            or 'hinh anh' in query_norm
            or 'minh chung' in query_norm
            or 'dinh kem' in query_norm
            or ('hinh' in query_tokens and 'mo' not in query_tokens and bool(query_tokens & image_action_tokens))
        )

        import concurrent.futures
        import threading

        lock = threading.Lock()
        max_sparse = [0.0]
        max_dense = [0.0]

        # ── Sparse search ──────────────────────────────────────
        def run_sparse():
            local_max = 0.0
            t0 = time.monotonic()
            try:
                if self.bm25:
                    sparse_results = self.bm25.search(query, top_k=sparse_k, document_ids=document_ids)
                    for result in sparse_results:
                        cid = result['chunk_id']
                        doc_id = result['document_id']
                        if document_ids and str(doc_id) not in document_ids:
                            continue
                        score = float(result['score']) * self.sparse_boost
                        with lock:
                            candidates[cid] = {
                                'chunk_id': cid, 'document_id': doc_id,
                                'score': 0.0, 'source': 'bm25',
                                'snippet': result['content'][:300],
                            }
                            sparse_scores[cid] = score
                        local_max = max(local_max, score)
                else:
                    from repositories.document_repository import DocumentRepository
                    doc_repo = DocumentRepository()
                    for doc in doc_repo.search(query)[:5]:
                        if document_ids and str(doc.id) not in document_ids:
                            continue
                        chunks_qs = apps.get_model('documents', 'DocumentChunk').objects.filter(
                            document_id=doc.id, is_deleted=False
                        ).filter(content__icontains=query).order_by('chunk_index')[:3]
                        for c in chunks_qs:
                            cid = str(c.id)
                            score = 1.0 * self.sparse_boost
                            with lock:
                                candidates[cid] = {
                                    'chunk_id': cid, 'document_id': str(c.document_id),
                                    'score': 0.0, 'source': 'icontains',
                                    'snippet': (c.content or '')[:300],
                                }
                                sparse_scores[cid] = score
                            local_max = max(local_max, score)
            except Exception as e:
                logger.warning(f"Sparse error: {e}")
            timing['sparse_ms'] = (time.monotonic() - t0) * 1000
            max_sparse[0] = local_max

        # ── Dense search ───────────────────────────────────────
        def run_dense():
            local_max = 0.0
            t0 = time.monotonic()
            try:
                emb = query_embedding  # pre-computed in main thread

                qdrant_filter = {'node_type': 'detail'}
                if document_ids:
                    qdrant_filter['document_id'] = document_ids

                t_q = time.monotonic()
                dense_results = self.qdrant.search_similar(
                    embedding=emb, limit=top_k, filter_payload=qdrant_filter,
                )
                # Backward compatibility: older ingestion code did not store
                # node_type in Qdrant payloads, so node_type='detail' can filter
                # out valid document vectors. Retry with only document scope.
                if not dense_results and document_ids:
                    legacy_filter = {'document_id': document_ids}
                    dense_results = self.qdrant.search_similar(
                        embedding=emb, limit=top_k, filter_payload=legacy_filter,
                    )
                timing['qdrant_ms'] = (time.monotonic() - t_q) * 1000

                for vector_id, score, payload in dense_results:
                    cid = str(payload.get('chunk_id') or vector_id)
                    doc_id = str(payload.get('document_id') or '')
                    score = float(score or 0.0)
                    with lock:
                        dense_scores[cid] = score
                        if cid in candidates:
                            candidates[cid]['source'] = 'hybrid'
                        else:
                            candidates[cid] = {
                                'chunk_id': cid, 'document_id': doc_id,
                                'score': 0.0, 'source': 'dense',
                                'snippet': (payload.get('text_preview') or '')[:300],
                            }
                    local_max = max(local_max, score)
            except Exception as e:
                logger.warning(f"Dense error: {e}")
            max_dense[0] = local_max

        # ── Asset search (NEW) ─────────────────────────────────
        def run_asset_search():
            t0 = time.monotonic()
            try:
                if not should_search_assets:
                    return

                emb = query_embedding  # pre-computed in main thread

                # Fix: Lower threshold if user explicitly asks for images/assets
                query_lower = query.lower()
                # Normalize for robust keyword matching
                import unicodedata
                query_no_accents = ''.join(c for c in unicodedata.normalize('NFD', query_lower) if unicodedata.category(c) != 'Mn')
                
                image_keywords = ['ảnh', 'hình', 'asset', 'minh chứng', 'đính kèm', 'anh', 'hinh', 'minh chung', 'dinh kem']
                is_image_query = any(kw in query_no_accents for kw in image_keywords)
                
                effective_threshold = 0.15
                # For image queries, we want to see more assets
                asset_limit = top_k * 3

                asset_results = self.qdrant.search_assets(
                    embedding=emb, limit=asset_limit, score_threshold=effective_threshold,
                    document_ids=document_ids,
                )
                
                # HEALING: Keyword fallback for assets if vector search returns too few
                if is_image_query and document_ids and len(asset_results or []) < 2:
                    try:
                        DocumentAsset = apps.get_model('documents', 'DocumentAsset')
                        # Search for assets with common image keywords in caption
                        kw_assets = DocumentAsset.objects.filter(
                            document_id__in=document_ids,
                            is_deleted=False
                        ).filter(
                            Q(caption__icontains='ảnh') | Q(caption__icontains='hình') | 
                            Q(caption__icontains='anh') | Q(caption__icontains='hinh') |
                            Q(caption__icontains='image')
                        )[:asset_limit]
                        
                        existing_ids = {str(a.get('asset_id')) for a in asset_results if a.get('asset_id')}
                        for ka in kw_assets:
                            if str(ka.id) not in existing_ids:
                                asset_results.append({
                                    'asset_id': str(ka.id),
                                    'document_id': str(ka.document_id),
                                    'score': 0.35, # Sufficient to pass but lower than clear vector matches
                                    'caption': ka.caption,
                                    'image_path': ka.image_path,
                                    'page_number': ka.page_number,
                                    'sheet_name': ka.sheet_name,
                                    'anchor_cell': ka.anchor_cell,
                                })
                    except Exception as e:
                        logger.warning(f"Asset keyword fallback failed: {e}")
                with lock:
                    asset_candidates.extend(asset_results or [])
            except Exception as e:
                logger.warning(f"Asset search error: {e}")
            timing['asset_ms'] = (time.monotonic() - t0) * 1000

        # ── Pre-compute embedding ONCE ──────────────────────────
        if query_embedding is None:
            t_emb = time.monotonic()
            query_embedding = self.embedding_client.create_embedding(query)
            timing['embedding_ms'] = (time.monotonic() - t_emb) * 1000

        # ── Run all 3 in parallel ──────────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            f1 = executor.submit(run_sparse)
            f2 = executor.submit(run_dense)
            f3 = executor.submit(run_asset_search)
            f1.result()
            f2.result()
            f3.result()

        # ── Normalize + combine chunk scores ───────────────────
        def _softmax(scores_dict, temperature=0.5):
            if not scores_dict:
                return {}
            values = list(scores_dict.values())
            max_val = max(values)
            exps = [math.exp((v - max_val) / temperature) for v in values]
            total = sum(exps)
            if total == 0:
                return {k: 0.0 for k in scores_dict}
            return {k: exps[i] / total for i, k in enumerate(scores_dict.keys())}

        sparse_scores = _softmax(sparse_scores)
        dense_scores = _softmax(dense_scores)

        for cid, candidate in candidates.items():
            s = sparse_scores.get(cid, 0.0)
            d = dense_scores.get(cid, 0.0)
            candidate['score'] = 0.5 * s + 0.5 * d

        sorted_candidates = sorted(candidates.values(), key=lambda x: x['score'], reverse=True)

        # ── Merge asset results vào candidates ─────────────────
        if asset_candidates and should_search_assets:
            # Batch check for existence to avoid N+1 queries
            asset_ids_from_q = [str(a.get('asset_id')) for a in asset_candidates if a.get('asset_id')]
            DocumentAsset = apps.get_model('documents', 'DocumentAsset')
            
            # Map existing assets for quick lookup
            existing_assets = {
                str(a.id): a for a in DocumentAsset.objects.filter(id__in=asset_ids_from_q, is_deleted=False)
            }

            for asset in asset_candidates:
                asset_id = str(asset.get('asset_id', ''))
                if not asset_id:
                    continue
                
                target_asset = existing_assets.get(asset_id)
                
                # HEALING: If asset not found by ID, try to find a replacement at the same location
                if not target_asset and asset.get('sheet_name') and asset.get('anchor_cell'):
                    target_asset = DocumentAsset.objects.filter(
                        document_id=asset.get('document_id'),
                        sheet_name=asset.get('sheet_name'),
                        anchor_cell=asset.get('anchor_cell'),
                        is_deleted=False
                    ).order_by('-created_at').first()
                    
                    if target_asset:
                        logger.info(f"[HYBRID_RETR] Healed stale asset {asset_id} -> {target_asset.id} via coordinates")
                        asset_id = str(target_asset.id)

                if not target_asset:
                    logger.warning(f"[HYBRID_RETR] Skipping non-existent asset {asset_id}")
                    continue

                # Boost asset score if it's an explicit image query
                raw_score = float(asset.get('score', 0.5))
                # Identify if query specifically asks for images
                import unicodedata
                q_norm = ''.join(c for c in unicodedata.normalize('NFD', query.lower()) if unicodedata.category(c) != 'Mn')
                is_img_q = any(kw in q_norm for kw in ['anh', 'hinh', 'asset', 'minh chung'])
                
                boosted_score = raw_score
                if is_img_q:
                    # Give a massive boost to ensure assets are ALWAYS in the top context
                    boosted_score = min(0.98, raw_score + 0.6)

                sorted_candidates.append({
                    'chunk_id': '',
                    'document_id': str(target_asset.document_id),
                    'score': boosted_score,
                    'source': 'asset',
                    'snippet': (target_asset.caption or asset.get('caption', ''))[:300],
                    'asset_id': asset_id,
                    'asset_caption': target_asset.caption or asset.get('caption', ''),
                    'asset_image_path': target_asset.image_path,
                    'asset_page_number': target_asset.page_number,
                    'asset_sheet_name': target_asset.sheet_name,
                    'asset_anchor_cell': target_asset.anchor_cell,
                    'asset_paragraph_index': target_asset.paragraph_index,
                    'asset_position_in_document': target_asset.position_in_document or {},
                    'asset_context_text': target_asset.context_text or '',
                })

        # Re-sort
        sorted_candidates = sorted(sorted_candidates, key=lambda x: x['score'], reverse=True)

        t_total = (time.monotonic() - t_start) * 1000
        n_assets = sum(1 for c in sorted_candidates if c['source'] == 'asset')
        logger.info(
            f"[RETRIEVAL] query='{query[:40]}...' results={len(sorted_candidates)} "
            f"assets={n_assets} | sparse={timing.get('sparse_ms',0):.0f}ms "
            f"dense={timing.get('qdrant_ms',0):.0f}ms asset={timing.get('asset_ms',0):.0f}ms "
            f"total={t_total:.0f}ms"
        )

        # Separate assets and non-assets
        asset_results = [c for c in sorted_candidates if c.get('source') == 'asset']
        non_asset_results = [c for c in sorted_candidates if c.get('source') != 'asset']
        
        # Take top (top_k - len(assets)) non-assets + all assets
        non_asset_limit = max(0, top_k - len(asset_results))
        result = non_asset_results[:non_asset_limit] + asset_results
        result = sorted(result, key=lambda x: x['score'], reverse=True)
        
        try:
            cache.set(cache_key, result, self.cache_ttl)
        except Exception:
            pass
        return result
