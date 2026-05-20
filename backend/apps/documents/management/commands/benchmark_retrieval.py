import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from services.ai.embedding_client import EmbeddingClient
from services.ai.qdrant_client import QdrantClient
from services.retrieval.benchmark_utils import BenchmarkResult, RetrieverBenchmark
from services.retrieval.query_router import QueryRouter


class Command(BaseCommand):
    help = "Run retrieval benchmark from a JSON question set."

    def add_arguments(self, parser):
        parser.add_argument(
            "--questions",
            required=True,
            help="Path to JSON file with benchmark cases.",
        )
        parser.add_argument("--top-k", type=int, default=10)
        parser.add_argument(
            "--output",
            default="",
            help="Optional path to write JSON summary.",
        )

    def handle(self, *args, **options):
        question_path = Path(options["questions"])
        if not question_path.exists():
            raise CommandError(f"Question file not found: {question_path}")

        with question_path.open("r", encoding="utf-8") as fh:
            cases = json.load(fh)
        if not isinstance(cases, list):
            raise CommandError("Question file must contain a JSON array.")

        top_k = int(options["top_k"])
        router = QueryRouter(
            qdrant_client=QdrantClient(),
            embedding_client=EmbeddingClient(),
            llama_client=None,
        )

        results = []
        for case in cases:
            query = case.get("query", "").strip()
            if not query:
                continue

            user_context = {}
            document_ids = case.get("document_ids") or []
            if document_ids:
                cleaned_document_ids = [
                    str(item)
                    for item in document_ids
                    if item and not str(item).startswith("replace-with")
                ]
                if cleaned_document_ids:
                    user_context["document_ids"] = cleaned_document_ids

            started = time.time()
            candidates = router.route(query=query, user_context=user_context, top_k=top_k)
            latency_ms = (time.time() - started) * 1000

            relevant_ids = {str(item) for item in case.get("relevant_chunk_ids", [])}
            expected_citations = {
                str(item)
                for item in (case.get("expected_citation_ids") or case.get("relevant_chunk_ids", []))
            }
            result = BenchmarkResult(query=query, top_k=top_k)
            result.total_latency_ms = latency_ms
            result.retrieved_count = len(candidates)
            result.relevant_count = len(relevant_ids)
            result.relevant_retrieved = len(
                {str(c.get("chunk_id")) for c in candidates[:top_k]} & relevant_ids
            )
            result.mrr = RetrieverBenchmark._calculate_mrr(candidates, relevant_ids)
            result.ndcg = RetrieverBenchmark._calculate_ndcg(candidates, relevant_ids, top_k)
            result.map_score = RetrieverBenchmark._calculate_map(candidates, relevant_ids)
            result.precision_at_k = RetrieverBenchmark._calculate_precision_at_k(candidates, relevant_ids, top_k)
            result.recall_at_k = RetrieverBenchmark._calculate_recall_at_k(candidates, relevant_ids, top_k)
            result.citation_accuracy = RetrieverBenchmark._calculate_citation_accuracy(
                candidates,
                expected_citations,
                top_k,
            )
            result.hallucination_rate = RetrieverBenchmark._estimate_hallucination_rate(
                answer_text=case.get("answer_text", ""),
                evidence_texts=[
                    c.get("snippet") or c.get("citation_excerpt") or c.get("content") or ""
                    for c in candidates[:top_k]
                ],
            )

            sources = {}
            for candidate in candidates:
                source = candidate.get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1
            result.retriever_sources = sources

            results.append(result)
            self.stdout.write(str(result))

        summary = self._aggregate(results)
        payload = {
            "summary": summary,
            "results": [result.to_dict() for result in results],
        }
        formatted = json.dumps(payload, ensure_ascii=False, indent=2)

        output = options.get("output")
        if output:
            Path(output).write_text(formatted, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Benchmark written to {output}"))
        else:
            self.stdout.write(formatted)

    def _aggregate(self, results):
        if not results:
            return {}
        total = len(results)
        return {
            "query_count": total,
            "average_mrr": round(sum(r.mrr for r in results) / total, 4),
            "average_ndcg": round(sum(r.ndcg for r in results) / total, 4),
            "average_map": round(sum(r.map_score for r in results) / total, 4),
            "average_precision": round(sum(r.precision_at_k for r in results) / total, 4),
            "average_recall": round(sum(r.recall_at_k for r in results) / total, 4),
            "average_citation_accuracy": round(sum(r.citation_accuracy for r in results) / total, 4),
            "average_hallucination_rate": round(sum(r.hallucination_rate for r in results) / total, 4),
            "average_latency_ms": round(sum(r.total_latency_ms for r in results) / total, 2),
        }
