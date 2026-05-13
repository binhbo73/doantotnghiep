"""
Retrieval Quality Benchmarking
================================

Metrics for evaluating retrieval quality:
- MRR (Mean Reciprocal Rank): How high is first relevant result?
- NDCG@K (Normalized Discounted Cumulative Gain): Quality of top-K ranking?
- MAP@K (Mean Average Precision): Precision across all relevant results?
- Latency: Query time, embedding time, reranking time

Usage:
    from backend.services.retrieval.benchmark_utils import RetrieverBenchmark
    
    benchmark = RetrieverBenchmark(retriever, reranker)
    metrics = benchmark.evaluate_query(
        query=\"tìm thông tin về X\",
        relevant_chunk_ids=[\"chunk_1\", \"chunk_2\"]
    )
    print(metrics)  # {mrr, ndcg, latency, ...}
"""

import time
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single retrieval benchmark."""
    
    query: str
    top_k: int
    
    # Ranking metrics
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    map_score: float = 0.0  # Mean Average Precision
    precision_at_k: float = 0.0  # Precision@K
    recall_at_k: float = 0.0  # Recall@K
    
    # Latency metrics (milliseconds)
    total_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    sparse_latency_ms: float = 0.0
    dense_latency_ms: float = 0.0
    reranking_latency_ms: float = 0.0
    
    # Result info
    retrieved_count: int = 0
    relevant_count: int = 0
    relevant_retrieved: int = 0
    
    # Debug info
    retriever_sources: Dict[str, int] = field(default_factory=dict)  # {source: count}
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        """Human-readable benchmark result."""
        return (
            f"Query: {self.query[:50]}...\n"
            f"  Metrics: MRR={self.mrr:.3f}, NDCG={self.ndcg:.3f}, MAP={self.map_score:.3f}\n"
            f"  Precision@{self.top_k}={self.precision_at_k:.3f}, Recall@{self.top_k}={self.recall_at_k:.3f}\n"
            f"  Latency: {self.total_latency_ms:.1f}ms "
            f"(embedding={self.embedding_latency_ms:.1f}ms, "
            f"sparse={self.sparse_latency_ms:.1f}ms, "
            f"dense={self.dense_latency_ms:.1f}ms, "
            f"rerank={self.reranking_latency_ms:.1f}ms)\n"
            f"  Retrieved {self.relevant_retrieved}/{self.relevant_count} relevant in top-{self.top_k}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'query': self.query,
            'top_k': self.top_k,
            'mrr': round(self.mrr, 4),
            'ndcg': round(self.ndcg, 4),
            'map': round(self.map_score, 4),
            'precision_at_k': round(self.precision_at_k, 4),
            'recall_at_k': round(self.recall_at_k, 4),
            'latency_ms': round(self.total_latency_ms, 2),
            'embedding_ms': round(self.embedding_latency_ms, 2),
            'sparse_ms': round(self.sparse_latency_ms, 2),
            'dense_ms': round(self.dense_latency_ms, 2),
            'rerank_ms': round(self.reranking_latency_ms, 2),
            'retrieved_count': self.retrieved_count,
            'relevant_retrieved': self.relevant_retrieved,
            'sources': self.retriever_sources,
            'timestamp': self.timestamp.isoformat()
        }


class RetrieverBenchmark:
    """Benchmark retrieval quality and performance."""
    
    def __init__(self, retriever, reranker=None):
        """Initialize benchmark.
        
        Args:
            retriever: HybridRetriever instance
            reranker: Optional Reranker instance for reranking benchmarks
        """
        self.retriever = retriever
        self.reranker = reranker

    def evaluate_query(
        self,
        query: str,
        relevant_chunk_ids: Set[str],
        top_k: int = 10,
        use_reranking: bool = False
    ) -> BenchmarkResult:
        """Evaluate retrieval quality for a single query.
        
        Args:
            query: Search query
            relevant_chunk_ids: Set of chunk IDs known to be relevant
            top_k: Number of results to evaluate
            use_reranking: Apply reranking if available
        
        Returns:
            BenchmarkResult with all metrics
        """
        result = BenchmarkResult(query=query, top_k=top_k)
        
        # Retrieve results with timing
        start_time = time.time()
        try:
            results = self.retriever.retrieve(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Retrieval failed for query '{query}': {e}")
            return result
        
        result.total_latency_ms = (time.time() - start_time) * 1000
        
        # Track sources
        for r in results:
            source = r.get('source', 'unknown')
            result.retriever_sources[source] = result.retriever_sources.get(source, 0) + 1
        
        # Rerank if requested
        if use_reranking and self.reranker:
            rerank_start = time.time()
            results = self.reranker.rerank(query, results, top_k=top_k)
            result.reranking_latency_ms = (time.time() - rerank_start) * 1000
        
        # Extract retrieved chunk IDs
        retrieved_ids = {r['chunk_id'] for r in results}
        relevant_retrieved = retrieved_ids & relevant_chunk_ids
        
        result.retrieved_count = len(retrieved_ids)
        result.relevant_count = len(relevant_chunk_ids)
        result.relevant_retrieved = len(relevant_retrieved)
        
        # Calculate metrics
        result.mrr = self._calculate_mrr(results, relevant_chunk_ids)
        result.ndcg = self._calculate_ndcg(results, relevant_chunk_ids, top_k)
        result.map_score = self._calculate_map(results, relevant_chunk_ids)
        result.precision_at_k = self._calculate_precision_at_k(results, relevant_chunk_ids, top_k)
        result.recall_at_k = self._calculate_recall_at_k(results, relevant_chunk_ids, top_k)
        
        return result

    @staticmethod
    def _calculate_mrr(results: List[Dict], relevant_ids: Set[str]) -> float:
        """Mean Reciprocal Rank: 1 / (position of first relevant result).
        
        Range: [0, 1]
        - 1.0: First result is relevant
        - 0.5: Second result is relevant
        - 0.0: No relevant results
        """
        for i, result in enumerate(results, 1):
            if result['chunk_id'] in relevant_ids:
                return 1.0 / i
        return 0.0

    @staticmethod
    def _calculate_ndcg(
        results: List[Dict],
        relevant_ids: Set[str],
        k: int = 10
    ) -> float:
        """Normalized Discounted Cumulative Gain.
        
        Factors in:
        - Position of relevant results (lower is better)
        - Number of relevant results in top-K
        
        Range: [0, 1]
        - 1.0: All top-K results are relevant
        - 0.5: Some relevant results but not all at top
        - 0.0: No relevant results
        
        Formula:
            DCG@K = Σ(rel_i / log2(i+1)) for i=1..K
            IDCG@K = optimal DCG (all relevant results at top)
            NDCG@K = DCG@K / IDCG@K
        """
        # Calculate DCG
        dcg = 0.0
        for i, result in enumerate(results[:k], 1):
            rel = 1.0 if result['chunk_id'] in relevant_ids else 0.0
            dcg += rel / (1.0 + (i - 1))  # log2(i+1) approximation

        # Calculate IDCG (ideal: all top-K results are relevant)
        idcg = 0.0
        for i in range(1, min(k, len(relevant_ids)) + 1):
            idcg += 1.0 / (1.0 + (i - 1))

        if idcg == 0:
            return 0.0
        return dcg / idcg

    @staticmethod
    def _calculate_map(
        results: List[Dict],
        relevant_ids: Set[str]
    ) -> float:
        """Mean Average Precision.
        
        Averages precision at each position where a relevant result appears.
        
        Range: [0, 1]
        - Emphasizes finding relevant results early
        - Accounts for multiple relevant results
        
        Formula:
            AP = Σ(P(k) * rel(k)) / |relevant_docs|
            MAP = mean of AP across all queries
        """
        if not relevant_ids:
            return 0.0

        score = 0.0
        num_relevant = 0

        for i, result in enumerate(results, 1):
            if result['chunk_id'] in relevant_ids:
                num_relevant += 1
                precision_at_i = num_relevant / i
                score += precision_at_i

        return score / len(relevant_ids) if relevant_ids else 0.0

    @staticmethod
    def _calculate_precision_at_k(
        results: List[Dict],
        relevant_ids: Set[str],
        k: int = 10
    ) -> float:
        """Precision@K: fraction of top-K results that are relevant.
        
        Range: [0, 1]
        - 1.0: All top-K are relevant
        - 0.5: Half of top-K are relevant
        - 0.0: None are relevant
        """
        if not results:
            return 0.0
        
        relevant_in_top_k = sum(
            1 for r in results[:k] if r['chunk_id'] in relevant_ids
        )
        return relevant_in_top_k / min(k, len(results))

    @staticmethod
    def _calculate_recall_at_k(
        results: List[Dict],
        relevant_ids: Set[str],
        k: int = 10
    ) -> float:
        """Recall@K: fraction of all relevant results in top-K.
        
        Range: [0, 1]
        - 1.0: All relevant results in top-K
        - 0.5: Half of relevant results in top-K
        - 0.0: None of relevant results in top-K
        """
        if not relevant_ids:
            return 1.0  # No relevant docs = trivially satisfied
        
        relevant_in_top_k = sum(
            1 for r in results[:k] if r['chunk_id'] in relevant_ids
        )
        return relevant_in_top_k / len(relevant_ids)


class BenchmarkSuite:
    """Run multiple benchmark queries."""
    
    def __init__(self, retriever, reranker=None):
        self.benchmark = RetrieverBenchmark(retriever, reranker)
        self.results: List[BenchmarkResult] = []

    def run_suite(
        self,
        queries: List[Dict[str, Any]],
        top_k: int = 10,
        use_reranking: bool = False
    ) -> Dict[str, Any]:
        """Run benchmark on multiple queries.
        
        Args:
            queries: List of {query, relevant_chunk_ids}
            top_k: Number of results per query
            use_reranking: Use reranking
        
        Returns:
            Suite summary with aggregate metrics
        """
        logger.info(f"Running benchmark suite: {len(queries)} queries")
        
        self.results = []
        for q in queries:
            result = self.benchmark.evaluate_query(
                query=q['query'],
                relevant_chunk_ids=set(q.get('relevant_chunk_ids', [])),
                top_k=top_k,
                use_reranking=use_reranking
            )
            self.results.append(result)
            logger.info(str(result))

        return self._aggregate_metrics()

    def _aggregate_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics across all queries."""
        if not self.results:
            return {}

        # Calculate averages
        avg_mrr = sum(r.mrr for r in self.results) / len(self.results)
        avg_ndcg = sum(r.ndcg for r in self.results) / len(self.results)
        avg_map = sum(r.map_score for r in self.results) / len(self.results)
        avg_precision = sum(r.precision_at_k for r in self.results) / len(self.results)
        avg_recall = sum(r.recall_at_k for r in self.results) / len(self.results)
        avg_latency = sum(r.total_latency_ms for r in self.results) / len(self.results)

        return {
            'query_count': len(self.results),
            'average_mrr': round(avg_mrr, 4),
            'average_ndcg': round(avg_ndcg, 4),
            'average_map': round(avg_map, 4),
            'average_precision': round(avg_precision, 4),
            'average_recall': round(avg_recall, 4),
            'average_latency_ms': round(avg_latency, 2),
            'results': [r.to_dict() for r in self.results]
        }
