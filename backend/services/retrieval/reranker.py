from typing import List, Dict, Any, Optional
import logging
import math
import time
import re
import unicodedata

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks candidate chunks with semantic + lexical scoring.

    Scoring strategy:
    1. Semantic similarity (embedding cosine)   - 55% weight
    2. Lexical overlap (Jaccard)                - 15% weight
    3. Base retrieval score                     - 30% weight
    4. Intent-aware bonuses/penalties

    Embedding-based dedup at cosine > 0.92 threshold.
    """

    SEMANTIC_WEIGHT = 0.55
    LEXICAL_WEIGHT = 0.15
    BASE_WEIGHT = 0.30
    EMBEDDING_DEDUP_THRESHOLD = 0.92

    def __init__(
        self,
        llama_client: Optional[Any] = None,
        embedding_client: Optional[Any] = None,
        use_llm: bool = False,
    ):
        self.llama = llama_client if use_llm else None
        self.embedding_client = embedding_client
        self._query_embedding_cache: Dict[str, List[float]] = {}

    # ── Public API ────────────────────────────────────────────

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank candidates using semantic + lexical scoring.

        Priority: semantic > lexical > base retrieval score.
        """
        t_rerank_start = time.monotonic()
        if not candidates:
            return []
        if top_k <= 0:
            return []

        # Compute query embedding once. If embedding is unavailable, fall back
        # to lexical scoring without failing retrieval.
        query_embedding = None
        if self.embedding_client:
            try:
                query_embedding = self._get_query_embedding(query)
            except Exception as e:
                logger.debug(f"Query embedding failed, lexical-only: {e}")

        # LLM reranker path (only if explicitly enabled and available)
        if self.llama and hasattr(self.llama, 'score_candidates'):
            try:
                return self._llm_rerank(query, candidates, top_k)
            except Exception as e:
                logger.warning(f"LLM rerank failed: {e}")

        scoring_mode = "semantic+lexical" if query_embedding else "lexical-only"
        logger.debug(f"Reranking mode={scoring_mode}")

        if query_embedding:
            candidates = self._embedding_dedup(candidates)

        query_lower = query.lower()
        query_norm = self._normalize_text(query)
        q_tokens = {t.lower() for t in re.findall(r'\w+', query_norm) if len(t) >= 2}

        # Intent detection
        asks_reason = any(m in query_lower for m in (
            "tại sao", "tai sao", "vì sao", "vi sao", "lý do", "ly do"
        ))
        asks_quantity = any(m in query_lower for m in (
            "bao nhiêu", "bao nhieu", "số lượng", "so luong", "mấy", "may"
        ))
        asks_toc = any(m in query_norm for m in (
            "muc luc", "table of contents", "contents", "index"
        ))
        asks_glossary = any(m in query_norm for m in (
            "tu dien", "glossary", "thuat ngu", "dien giai", "khai niem"
        ))
        reason_markers = (
            "lý do", "ly do", "vì ", "vi ", "do ", "nguyên nhân",
            "nguyen nhan", "buộc", "buoc", "chi phí", "chi phi",
            "tài nguyên", "tai nguyen",
        )
        quantity_markers = (
            "bao nhiêu", "bao nhieu", "số lượng", "so luong",
            "lượt hỏi", "luot hoi", "token", "không công bố",
            "khong cong bo", "không có số liệu", "khong co so lieu",
        )
        glossary_markers = (
            "tu dien", "glossary", "thuat ngu", "dien giai", "khai niem", "bang 1"
        )

        for c in candidates:
            snippet = (c.get('snippet') or '')
            snippet_lower = snippet.lower()
            snippet_norm = self._normalize_text(snippet)
            s_tokens = {t.lower() for t in re.findall(r'\w+', snippet_norm) if len(t) >= 2}

            base_score = float(c.get('score', 0.0) or 0.0)
            asset_bonus = 0.5 if c.get('source') == 'asset' else 0.0

            semantic_score = 0.0
            if query_embedding:
                chunk_emb = c.get('_embedding')
                if chunk_emb:
                    semantic_score = self._cosine_similarity(query_embedding, chunk_emb)

            # Lexical score (Jaccard)
            union = q_tokens | s_tokens
            lexical_score = (len(q_tokens & s_tokens) / len(union)) if union else 0.0

            # Intent bonuses
            intent_bonus = 0.0
            if asks_reason:
                if any(m in snippet_lower for m in reason_markers):
                    intent_bonus += 0.35
                if not asks_quantity and any(m in snippet_lower for m in quantity_markers):
                    intent_bonus -= 0.25

            # Glossary/terminology table bonus
            glossary_bonus = 0.0
            if asks_glossary:
                if any(m in snippet_norm for m in glossary_markers):
                    glossary_bonus += 0.45
                # Penalty for other table references (Bang 2, Bang 3, etc.)
                if re.search(r'\bbang\s+[2-9]\b', snippet_norm):
                    glossary_bonus -= 0.35

            toc_penalty = 0.0 if asks_toc else self._toc_penalty(c, snippet, snippet_norm)

            if semantic_score > 0:
                combined = (
                    self.SEMANTIC_WEIGHT * semantic_score +
                    self.LEXICAL_WEIGHT * lexical_score +
                    self.BASE_WEIGHT * base_score
                )
            else:
                combined = 0.4 * base_score + 0.5 * lexical_score + 0.1 * asset_bonus

            c['score'] = combined + asset_bonus + intent_bonus + glossary_bonus - toc_penalty
            c['_semantic_score'] = round(semantic_score, 4)
            c['_lexical_score'] = round(lexical_score, 4)

        ranked = sorted(candidates, key=lambda x: float(x.get('score', 0) or 0), reverse=True)[:top_k]

        # MMR diversity
        if len(ranked) > 3:
            ranked = self._mmr_diversify(query, ranked, top_k, lambda_param=0.7)

        ranked = self._dedupe_ranked_candidates(ranked, top_k)

        t_rerank_total = (time.monotonic() - t_rerank_start) * 1000
        avg_sem = (
            sum(c.get('_semantic_score', 0) for c in ranked[:3]) / max(1, min(3, len(ranked)))
            if ranked else 0
        )
        logger.debug(
            f"[RERANK_PROFILE] {len(candidates)}→{len(ranked)} "
            f"mode={scoring_mode} avg_semantic(top3)={avg_sem:.3f} "
            f"in {t_rerank_total:.1f}ms"
        )
        return ranked

    # ── LLM reranking ─────────────────────────────────────────

    def _llm_rerank(self, query, candidates, top_k):
        scores = self.llama.score_candidates(query=query, candidates=candidates)
        if not isinstance(scores, (list, tuple)) or len(scores) != len(candidates):
            raise ValueError("Score validation failed")

        ranked = []
        for c, s in zip(candidates, scores):
            try:
                score_val = max(0.0, min(1.0, float(s)))
            except (TypeError, ValueError):
                continue
            c_copy = c.copy()
            c_copy['score'] = score_val
            ranked.append(c_copy)

        if ranked:
            return sorted(ranked, key=lambda x: float(x.get('score', 0) or 0), reverse=True)[:top_k]
        raise ValueError("No valid LLM scores")

    def rerank_pairwise(self, query, candidates, top_k=5):
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]

        max_compare = min(15, len(candidates))
        compare_candidates = candidates[:max_compare]

        if self.llama and hasattr(self.llama, 'compare_candidates'):
            try:
                wins = {i: 0 for i in range(len(compare_candidates))}
                for i in range(len(compare_candidates)):
                    for j in range(i + 1, len(compare_candidates)):
                        try:
                            result = self.llama.compare_candidates(
                                query=query,
                                candidate_a=compare_candidates[i],
                                candidate_b=compare_candidates[j],
                            )
                            if result > 0:
                                wins[i] += 1
                            elif result < 0:
                                wins[j] += 1
                        except Exception:
                            continue

                for idx, c in enumerate(compare_candidates):
                    c['score'] = wins[idx] / max(1, len(compare_candidates) - 1)

                compare_candidates.sort(key=lambda x: float(x.get('score', 0) or 0), reverse=True)
                return compare_candidates[:top_k]
            except Exception as e:
                logger.warning(f"Pairwise rerank failed: {e}")

        return self.rerank(query, candidates, top_k)

    # ── Embedding helpers ────────────────────────────────────

    def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        cache_key = query.strip()
        if cache_key in self._query_embedding_cache:
            return self._query_embedding_cache[cache_key]
        if not self.embedding_client:
            return None
        try:
            emb = self.embedding_client.create_embedding(query)
            if emb:
                self._query_embedding_cache[cache_key] = emb
            return emb
        except Exception:
            return None

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    # ── MMR diversity ────────────────────────────────────────

    def _mmr_diversify(self, query, candidates, top_k, lambda_param=0.7):
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]

        def tokenize(snippet):
            return set((snippet or '').lower().split())

        tokenized = [tokenize(c.get('snippet', '')) for c in candidates]
        selected = [0]
        remaining = list(range(1, len(candidates)))

        while len(selected) < min(top_k, len(candidates)):
            if not remaining:
                break
            best_idx, best_score = None, -float('inf')
            for idx in remaining:
                relevance = candidates[idx].get('score', 0.5)
                max_sim = 0.0
                for s_idx in selected:
                    a, b = tokenized[idx], tokenized[s_idx]
                    if a and b:
                        sim = len(a & b) / max(1, len(a | b))
                        max_sim = max(max_sim, sim)
                mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim
                if mmr_score > best_score:
                    best_score, best_idx = mmr_score, idx
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
            else:
                break

        return [candidates[i] for i in selected]

    # ── Embedding-based dedup ─────────────────────────────────

    def _embedding_dedup(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove near-duplicates using embedding cosine similarity."""
        if len(candidates) <= 1:
            return candidates

        # Ensure embeddings exist
        for c in candidates:
            if not c.get('_embedding') and self.embedding_client:
                snippet = c.get('snippet') or ''
                if snippet:
                    try:
                        c['_embedding'] = self.embedding_client.create_embedding(snippet)
                    except Exception:
                        pass

        kept: List[int] = []
        for i, c in enumerate(candidates):
            emb_i = c.get('_embedding')
            is_dup = False
            for j in kept:
                emb_j = candidates[j].get('_embedding')
                if emb_i and emb_j:
                    sim = self._cosine_similarity(emb_i, emb_j)
                    if sim >= self.EMBEDDING_DEDUP_THRESHOLD:
                        score_i = float(c.get('score', 0) or 0)
                        score_j = float(candidates[j].get('score', 0) or 0)
                        if score_i > score_j:
                            kept.remove(j)
                            kept.append(i)
                        is_dup = True
                        logger.debug(
                            f"[EMBEDDING_DEDUP] cos={sim:.3f} "
                            f"{c.get('chunk_id','?')[:8]} vs {candidates[j].get('chunk_id','?')[:8]}"
                        )
                        break
            if not is_dup:
                kept.append(i)

        deduped = [candidates[i] for i in kept]
        if len(deduped) < len(candidates):
            logger.debug(
                f"[EMBEDDING_DEDUP] {len(candidates)}→{len(deduped)} "
                f"(threshold={self.EMBEDDING_DEDUP_THRESHOLD})"
            )
        return deduped

    # ── Text normalization ───────────────────────────────────

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize('NFD', (text or '').lower())
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # ── TOC penalty ──────────────────────────────────────────

    def _toc_penalty(self, candidate: Dict[str, Any], snippet: str, snippet_norm: str) -> float:
        metadata = candidate.get('metadata') or {}
        if metadata.get('is_toc') or metadata.get('layout_role') == 'toc':
            return 0.9
        if any(m in snippet_norm for m in ('muc luc', 'table of contents', 'contents', 'index')):
            return 0.85

        lines = [l.strip() for l in (snippet or '').splitlines() if l.strip()]
        if len(lines) < 3:
            return 0.0

        short = dotted = numbered = 0
        for line in lines[:20]:
            if len(line.split()) <= 8:
                short += 1
            if re.search(r'\.\.\.\s*\d+$', line) or re.search(r'\s\d+$', line):
                dotted += 1
            if re.search(r'(^\d+[.)-]\s+)|(^[A-ZÀ-Ỹ][\wÀ-ỹ\-/ ]{2,}$)', line):
                numbered += 1

        ratio = (short + dotted + numbered) / max(1, min(len(lines), 20))
        if ratio >= 1.0 and (short >= 2 or dotted >= 2):
            return 0.7
        if ratio >= 0.75 and dotted >= 1:
            return 0.45
        return 0.0

    # ── Token-based dedup (fallback) ─────────────────────────

    def _dedupe_ranked_candidates(self, candidates, top_k):
        if not candidates:
            return []
        grouped: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            sig = self._content_signature(c)
            if not sig:
                sig = f"__fb__:{c.get('chunk_id') or id(c)}"
            existing = grouped.get(sig)
            if existing is None or self._should_replace_candidate(existing, c):
                grouped[sig] = c
        deduped = sorted(grouped.values(), key=lambda x: float(x.get('score', 0) or 0), reverse=True)
        return deduped[:top_k]

    def _content_signature(self, candidate):
        snippet = candidate.get('snippet') or candidate.get('citation_excerpt') or candidate.get('content') or ''
        norm = self._normalize_text(snippet)
        norm = re.sub(r'\s+', ' ', norm).strip()
        if len(norm) < 25:
            return ''
        tokens = [t for t in re.findall(r'\w+', norm) if len(t) > 2][:40]
        return ' '.join(tokens)

    def _should_replace_candidate(self, existing, candidate):
        es = float(existing.get('score', 0) or 0)
        cs = float(candidate.get('score', 0) or 0)
        if cs > es + 0.03:
            return True

        eb = not self._looks_like_front_matter(existing)
        cb = not self._looks_like_front_matter(candidate)
        if cb and not eb:
            return True

        ep = int(existing.get('page') or 0)
        cp = int(candidate.get('page') or 0)
        if cp > 3 and ep <= 3:
            return True

        el = len((existing.get('snippet') or existing.get('citation_excerpt') or ''))
        cl = len((candidate.get('snippet') or candidate.get('citation_excerpt') or ''))
        return cl > el and cs >= es - 0.02

    def _looks_like_front_matter(self, candidate):
        metadata = candidate.get('metadata') or {}
        if metadata.get('is_toc') or metadata.get('layout_role') == 'toc':
            return True
        snippet = self._normalize_text(candidate.get('snippet') or candidate.get('citation_excerpt') or '')
        return any(m in snippet for m in ('muc luc', 'table of contents', 'contents', 'index'))
