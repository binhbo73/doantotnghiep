from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks candidate chunks. Uses simple lexical scoring with optional LLM-based re-ranking.

    If `llama_client` is provided and has `score(prompt, candidates)` method, uses it.
    Otherwise falls back to a lightweight lexical relevance score.
    """

    def __init__(self, llama_client: Optional[Any] = None, use_llm: bool = False):
        # Fix A: LLM reranker disabled by default - too slow (90s+) on CPU Qwen3-4B
        # and poorly calibrated. Lexical-only is fast (<1ms) and reliable.
        self.llama = llama_client if use_llm else None

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank candidates using LLM if available, fallback to lexical scoring.
        
        Args:
            query: User query
            candidates: List of {chunk_id, snippet, score, ...}
            top_k: Number of top results to return
            
        Returns:
            Reranked candidates with updated scores
        """
        if not candidates:
            return []
        
        if top_k <= 0:
            return []

        # If LLM reranker available and supports scoring, attempt LLM-based ranking
        if self.llama and hasattr(self.llama, 'score_candidates'):
            try:
                scores = self.llama.score_candidates(query=query, candidates=candidates)
                
                # Validate LLM scores
                if not isinstance(scores, (list, tuple)):
                    raise ValueError(f"Expected scores list/tuple, got {type(scores)}")
                if len(scores) != len(candidates):
                    logger.warning(
                        f"Score count mismatch: expected {len(candidates)}, got {len(scores)}. "
                        f"Falling back to lexical scoring."
                    )
                    raise ValueError("Score count mismatch")
                
                # Create new list to avoid modifying input (functional style)
                ranked_candidates = []
                for c, s in zip(candidates, scores):
                    # Validate and normalize score
                    try:
                        score_val = float(s)
                        # Clip to [0, 1] if out of range
                        if score_val < 0 or score_val > 1:
                            logger.debug(f"Score {score_val} outside [0,1], clipping")
                            score_val = max(0.0, min(1.0, score_val))
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid score {s}, skipping candidate")
                        continue
                    
                    # Copy candidate and update score
                    c_copy = c.copy()
                    c_copy['score'] = score_val
                    ranked_candidates.append(c_copy)
                
                if ranked_candidates:
                    logger.debug(f"LLM reranking: {len(ranked_candidates)} of {len(candidates)} candidates scored")
                    result = sorted(ranked_candidates, key=lambda x: x['score'], reverse=True)[:top_k]
                    return result
                else:
                    logger.warning("No valid scores from LLM, falling back to lexical scoring")
                    
            except Exception as e:
                logger.warning(f"LLM rerank failed ({type(e).__name__}): {e}. Falling back to lexical scoring.")

        # Fallback lexical scoring: token overlap
        logger.debug("Using fallback lexical scoring")
        q_tokens = set([t.lower() for t in query.split() if len(t) > 2])
        
        for c in candidates:
            snippet = (c.get('snippet') or '')
            s_tokens = set([t.lower() for t in snippet.split() if len(t) > 2])
            overlap = len(q_tokens & s_tokens)
            # combine existing score with overlap (preserve existing score + add overlap bonus)
            base = float(c.get('score', 0.0) or 0.0)
            c['score'] = base + (overlap * 0.1)

        ranked = sorted(candidates, key=lambda x: x['score'], reverse=True)[:top_k]
        # P2#12: Apply MMR diversity re-ranking
        if len(ranked) > 3:
            ranked = self._mmr_diversify(query, ranked, top_k, lambda_param=0.7)
        return ranked

    def rerank_pairwise(self, query, candidates, top_k=5):
        """P2#8: Pairwise comparison reranking - chinh xac hon pointwise.
        LLM so sanh tung CAP candidates thay vi cham diem tung cai.
        """
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]
        
        max_compare = min(15, len(candidates))
        compare_candidates = candidates[:max_compare]
        
        if self.llama and hasattr(self.llama, 'compare_candidates'):
            try:
                wins = {i: 0 for i in range(len(compare_candidates))}
                comparisons = 0
                
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
                            comparisons += 1
                        except Exception:
                            continue
                
                for idx, c in enumerate(compare_candidates):
                    c['score'] = wins[idx] / max(1, len(compare_candidates) - 1)
                
                compare_candidates.sort(key=lambda x: x['score'], reverse=True)
                return compare_candidates[:top_k]
            except Exception as e:
                logger.warning(f"Pairwise rerank failed: {e}")
        
        return self.rerank(query, candidates, top_k)

    def _mmr_diversify(self, query, candidates, top_k, lambda_param=0.7):
        """P2#12: MMR diversity re-ranking - can bang relevance va diversity.
        
        Dung Jaccard similarity de do overlap giua cac snippet,
        uu tien candidate vua relevant vua khac biet voi nhung cai da chon.
        lambda_param=0.7: 70% relevance, 30% diversity.
        """
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]
        
        def tokenize(snippet):
            return set((snippet or '').lower().split())
        
        tokenized = [tokenize(c.get('snippet', '')) for c in candidates]
        selected = []
        remaining = list(range(len(candidates)))
        selected.append(remaining.pop(0))
        
        while len(selected) < min(top_k, len(candidates)):
            if not remaining:
                break
            best_idx = None
            best_score = -float('inf')
            
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
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
            else:
                break
        
        return [candidates[i] for i in selected]
