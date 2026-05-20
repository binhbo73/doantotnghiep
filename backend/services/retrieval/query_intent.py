"""
Query intent classification for retrieval.

The classifier normalizes Vietnamese text to lowercase ASCII-like tokens first
and then matches only accentless patterns. This keeps intent routing stable for
both Vietnamese with diacritics and user input without diacritics.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    LIST = "list"
    TABLE = "table"
    ANALYTICAL = "analytical"
    COMPARATIVE = "comparative"
    PROCEDURAL = "procedural"
    DEFINITIONAL = "definitional"
    IMAGE = "image"


@dataclass
class RetrievalConfig:
    """Retrieval parameters selected from query intent."""

    top_k: int = 5
    sparse_k: int = 20
    neighbor_before: int = 0
    neighbor_after: int = 0
    max_context_chunks: int = 8
    snippet_chars: int = 900
    mmr_lambda: float = 0.7
    dense_weight: float = 0.6
    use_raptor: bool = False
    prioritize_assets: bool = False
    require_grounding: bool = True


INTENT_CONFIG: Dict[QueryIntent, RetrievalConfig] = {
    QueryIntent.FACTUAL: RetrievalConfig(
        top_k=3,
        sparse_k=18,
        neighbor_before=0,
        neighbor_after=1,
        max_context_chunks=5,
        snippet_chars=700,
        mmr_lambda=0.85,
        dense_weight=0.45,
        use_raptor=False,
    ),
    QueryIntent.LIST: RetrievalConfig(
        top_k=10,
        sparse_k=30,
        neighbor_before=1,
        neighbor_after=4,
        max_context_chunks=18,
        snippet_chars=2200,
        mmr_lambda=0.6,
        dense_weight=0.5,
        use_raptor=True,
    ),
    QueryIntent.TABLE: RetrievalConfig(
        top_k=12,
        sparse_k=32,
        neighbor_before=0,
        neighbor_after=2,
        max_context_chunks=16,
        snippet_chars=3200,
        mmr_lambda=0.58,
        dense_weight=0.5,
        use_raptor=False,
    ),
    QueryIntent.ANALYTICAL: RetrievalConfig(
        top_k=7,
        sparse_k=24,
        neighbor_before=1,
        neighbor_after=3,
        max_context_chunks=12,
        snippet_chars=1700,
        mmr_lambda=0.65,
        dense_weight=0.65,
        use_raptor=True,
    ),
    QueryIntent.COMPARATIVE: RetrievalConfig(
        top_k=8,
        sparse_k=28,
        neighbor_before=1,
        neighbor_after=2,
        max_context_chunks=14,
        snippet_chars=1500,
        mmr_lambda=0.55,
        dense_weight=0.6,
        use_raptor=True,
    ),
    QueryIntent.PROCEDURAL: RetrievalConfig(
        top_k=6,
        sparse_k=22,
        neighbor_before=1,
        neighbor_after=3,
        max_context_chunks=10,
        snippet_chars=1300,
        mmr_lambda=0.7,
        dense_weight=0.55,
        use_raptor=False,
    ),
    QueryIntent.DEFINITIONAL: RetrievalConfig(
        top_k=3,
        sparse_k=15,
        neighbor_before=0,
        neighbor_after=1,
        max_context_chunks=4,
        snippet_chars=700,
        mmr_lambda=0.9,
        dense_weight=0.6,
        use_raptor=False,
    ),
    QueryIntent.IMAGE: RetrievalConfig(
        top_k=5,
        sparse_k=12,
        neighbor_before=0,
        neighbor_after=0,
        max_context_chunks=6,
        snippet_chars=500,
        mmr_lambda=0.8,
        dense_weight=0.4,
        use_raptor=False,
        prioritize_assets=True,
    ),
}


class QueryIntentClassifier:
    """Classify a query into retrieval intents using normalized Vietnamese text."""

    INTENT_PRIORITY: Dict[QueryIntent, int] = {
        QueryIntent.IMAGE: 70,
        QueryIntent.COMPARATIVE: 60,
        QueryIntent.TABLE: 55,
        QueryIntent.PROCEDURAL: 50,
        QueryIntent.LIST: 45,
        QueryIntent.ANALYTICAL: 40,
        QueryIntent.DEFINITIONAL: 35,
    }

    PATTERNS: Dict[QueryIntent, List[Tuple[str, int]]] = {
        QueryIntent.IMAGE: [
            (r"\b(xem|hien thi|cho xem|tim|liet ke)\s+(anh|hinh|hinh anh|minh chung|screenshot|asset)\b", 3),
            (r"\b(anh|hinh anh|minh chung|hinh ve|bieu do|so do|screenshot|asset)\b", 2),
            (r"\b(caption|ocr|visual|image|photo|capture)\b", 2),
        ],
        QueryIntent.COMPARATIVE: [
            (r"\b(so sanh|khac biet|phan biet|doi chieu)\b", 3),
            (r"\b(giong va khac|uu diem|nhuoc diem)\b", 2),
            (r"\b(giua\s+.+\s+va\s+.+|.+\s+voi\s+.+|hon|kem|vs)\b", 1),
        ],
        QueryIntent.PROCEDURAL: [
            (r"\b(cach|lam the nao|huong dan|thuc hien nhu the nao)\b", 2),
            (r"\b(quy trinh|cac buoc|tung buoc|thu tuc|workflow)\b", 3),
            (r"\b(bat dau|thuc hien|trien khai|cai dat|thiet lap|cau hinh)\b", 1),
        ],
        QueryIntent.LIST: [
            (r"\b(liet ke|ke ra|neu ra|trinh bay|tong hop|danh sach)\b", 5),
            (r"\b(tat ca|toan bo|day du|chi tiet)\b", 2),
            (r"\b(bao gom|gom nhung gi|co nhung gi|nhung muc nao|cac loai|cac muc)\b", 3),
            (r"^\s*\d+\s*[/.)-]\s*", 2),
        ],
        QueryIntent.TABLE: [
            (r"\b(bang|table|hang cot|cot|dong|row|column|grid|spreadsheet)\b", 3),
            (r"\b(xem|trich|lay|in)\s+bang\b", 3),
            (r"\b(bang\s+thong tin|bang\s+du lieu|bang\s+so lieu|bang\s+thu thuat ngu)\b", 4),
            (r"\b(tu dien|glossary|terminology|khai niem|dien giai)\b", 4),
            (r"\b(tu dien\s+thuat ngu|thuat ngu.*dien giai|bang.*tu dien)\b", 5),
            (r"\b(giu nguyen|nguyen ven|dang bang|duoi dang bang)\b", 2),
            (r"\b(bang\s+\d+)\b", 2),
        ],
        QueryIntent.ANALYTICAL: [
            (r"\b(tai sao|vi sao|ly do|nguyen nhan)\b", 3),
            (r"\b(phan tich|danh gia|giai thich|nhan xet|binh luan)\b", 3),
            (r"\b(nguyen ly|co che|anh huong|he qua|tac dong)\b", 2),
        ],
        QueryIntent.DEFINITIONAL: [
            (r"\b(la gi|dinh nghia|khai niem)\b", 3),
            (r"\b(duoc hieu|hieu nhu the nao|nghia la gi)\b", 2),
        ],
    }

    FACTUAL_MARKERS = (
        "ma",
        "so",
        "code",
        "id",
        "email",
        "url",
        "link",
        "bao nhieu",
        "may",
        "khi nao",
        "o dau",
        "ai",
        "ngay nao",
    )

    def __init__(self, embedding_client=None):
        self._embedding_client = embedding_client

    def classify(self, query: str) -> QueryIntent:
        if not query or not query.strip():
            return QueryIntent.FACTUAL

        normalized = self._normalize(query)
        scored: List[Tuple[QueryIntent, int, int]] = []

        for intent, patterns in self.PATTERNS.items():
            score = self._match_score(normalized, patterns)
            if score > 0:
                scored.append((intent, score, self.INTENT_PRIORITY[intent]))

        if scored:
            scored.sort(key=lambda item: (item[1], item[2]), reverse=True)
            best_intent, best_score, _priority = scored[0]
            if best_score >= 2:
                logger.debug(
                    "[QUERY_INTENT] query='%s' normalized='%s' intent=%s score=%s",
                    query[:80],
                    normalized[:80],
                    best_intent.value,
                    best_score,
                )
                return best_intent

        if any(marker in normalized for marker in self.FACTUAL_MARKERS):
            return QueryIntent.FACTUAL
        return QueryIntent.FACTUAL

    def get_retrieval_config(self, intent: QueryIntent) -> RetrievalConfig:
        return INTENT_CONFIG.get(intent, INTENT_CONFIG[QueryIntent.FACTUAL])

    def _normalize(self, text: str) -> str:
        text = (text or "").lower().replace("đ", "d").replace("Đ", "d")
        normalized = unicodedata.normalize("NFD", text)
        without_marks = "".join(
            ch for ch in normalized if unicodedata.category(ch) != "Mn"
        )
        without_marks = re.sub(r"[^\w\s./)-]", " ", without_marks)
        return re.sub(r"\s+", " ", without_marks).strip()

    def _match_score(self, normalized_query: str, patterns: List[Tuple[str, int]]) -> int:
        score = 0
        for pattern, weight in patterns:
            if re.search(pattern, normalized_query, re.IGNORECASE | re.UNICODE):
                score += weight
        return score
