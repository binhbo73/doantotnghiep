from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks candidate chunks. Uses simple lexical scoring with optional LLM-based re-ranking.

    If `llama_client` is provided and has `score(prompt, candidates)` method, uses it.
    Otherwise falls back to a lightweight lexical relevance score.
    """

    def __init__(self, llama_client: Optional[Any] = None):
        self.llama = llama_client

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

        return sorted(candidates, key=lambda x: x['score'], reverse=True)[:top_k]
