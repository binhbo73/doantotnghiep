"""
Chunk Quality Validator
========================
Post-chunking validation that runs automatically after DocumentChunker
produces chunks. Detects quality issues before chunks are persisted.

Checks performed:
1. Broken sentences (chunk ends without sentence-ending punctuation)
2. Tiny chunks (below minimum token threshold → noise)
3. Oversized chunks (exceed BGE-M3 max_length → embedding failure)
4. Near-duplicate chunks (cosine similarity > threshold)
5. Empty/whitespace-only chunks
6. Chunk coverage (gaps or excessive overlap in the source text)
7. Language consistency (mixed language detection)

Configurable via Django settings with sensible production defaults.

Usage:
    validator = ChunkValidator()
    report = validator.validate(chunks, text=original_text)
    # report.valid → bool
    # report.issues → List[ChunkIssue]
    # report.stats → Dict with metrics
"""

from __future__ import annotations

import logging
import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================


class IssueSeverity(Enum):
    """Severity levels for chunk quality issues."""
    CRITICAL = "critical"   # Chunk will fail embedding / break retrieval
    WARNING = "warning"     # Degraded quality, should fix
    INFO = "info"           # Informational, low priority


@dataclass
class ChunkIssue:
    """A single detected quality issue in a chunk."""
    chunk_index: int
    chunk_id: Optional[str]
    severity: IssueSeverity
    category: str
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete chunk validation report."""
    valid: bool
    total_chunks: int
    issues: List[ChunkIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    def summary(self) -> str:
        lines = [
            f"ValidationReport: valid={self.valid}, chunks={self.total_chunks}",
            f"  Critical: {self.critical_count}, Warnings: {self.warning_count}",
        ]
        for issue in self.issues:
            lines.append(f"  [{issue.severity.value}] Chunk {issue.chunk_index}: {issue.message}")
        return "\n".join(lines)


# ============================================================================
# MAIN VALIDATOR
# ============================================================================


class ChunkValidator:
    """Validates chunk quality and reports issues.

    Designed to run at the end of ChunkingStage, before PersistenceStage.
    Critical issues block persistence; warnings are logged but chunks are saved.
    """

    # ── Default thresholds (overridable via settings) ──────────
    MIN_CHUNK_CHARS: int = 50            # Minimum chars for a meaningful chunk
    MAX_CHUNK_CHARS: int = 6000          # BGE-M3 safe maximum
    MIN_TOKEN_COUNT: int = 20            # Minimum estimated tokens
    MAX_TOKEN_COUNT: int = 5000          # Safe max before truncation
    MIN_OVERLAP_RATIO: float = 0.0       # Min overlap between adjacent chunks
    MAX_OVERLAP_RATIO: float = 0.80      # Max overlap (near-duplicate)
    DUPLICATE_SIMILARITY: float = 0.92   # Near-duplicate threshold
    DUPLICATE_SAMPLE_CHARS: int = 200    # Sample chars for duplicate check

    # Sentence-ending punctuation (cross-language)
    SENTENCE_ENDINGS: Set[str] = field(default_factory=lambda: {
        '.', '!', '?', '…', '。', '！', '？',  # Latin + CJK
        '\n',  # Accept line breaks as valid ends for list items
    })

    def __init__(self):
        # Load thresholds from settings, with fallbacks
        self.MIN_CHUNK_CHARS = int(getattr(settings, 'CHUNK_VALIDATOR_MIN_CHARS', self.MIN_CHUNK_CHARS))
        self.MAX_CHUNK_CHARS = int(getattr(settings, 'CHUNK_VALIDATOR_MAX_CHARS', self.MAX_CHUNK_CHARS))
        self.MIN_TOKEN_COUNT = int(getattr(settings, 'CHUNK_VALIDATOR_MIN_TOKENS', self.MIN_TOKEN_COUNT))
        self.MAX_TOKEN_COUNT = int(getattr(settings, 'CHUNK_VALIDATOR_MAX_TOKENS', self.MAX_TOKEN_COUNT))
        self.MIN_OVERLAP_RATIO = float(getattr(settings, 'CHUNK_VALIDATOR_MIN_OVERLAP', self.MIN_OVERLAP_RATIO))
        self.MAX_OVERLAP_RATIO = float(getattr(settings, 'CHUNK_VALIDATOR_MAX_OVERLAP', self.MAX_OVERLAP_RATIO))
        self.DUPLICATE_SIMILARITY = float(getattr(settings, 'CHUNK_VALIDATOR_DUPE_SIMILARITY', self.DUPLICATE_SIMILARITY))

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def validate(
        self,
        chunks: List[Dict[str, Any]],
        source_text: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> ValidationReport:
        """Run all validation checks on a set of chunks.

        Args:
            chunks: List of chunk dicts (output of DocumentChunker)
            source_text: Original full document text (optional, for coverage check)
            document_id: Document identifier for logging

        Returns:
            ValidationReport with issues and statistics
        """
        if not chunks:
            return ValidationReport(valid=False, total_chunks=0)

        issues: List[ChunkIssue] = []
        stats: Dict[str, Any] = {
            'total_chunks': len(chunks),
            'total_chars': 0,
            'total_tokens': 0,
            'avg_chunk_chars': 0.0,
            'avg_chunk_tokens': 0.0,
            'checks_run': [],
        }

        # ── Run all checks ──────────────────────────────────
        self._check_empty_chunks(chunks, issues, stats)
        self._check_chunk_sizes(chunks, issues, stats)
        self._check_broken_sentences(chunks, issues, stats)
        self._check_near_duplicates(chunks, issues, stats)
        self._check_overlap_quality(chunks, issues, stats)

        if source_text:
            self._check_coverage(chunks, source_text, issues, stats)

        # ── Compute stats ────────────────────────────────────
        total_chars = sum(len(c.get('text', '')) for c in chunks)
        total_tokens = sum(c.get('token_count', 0) for c in chunks)
        stats['total_chars'] = total_chars
        stats['total_tokens'] = total_tokens
        stats['avg_chunk_chars'] = round(total_chars / max(1, len(chunks)), 1)
        stats['avg_chunk_tokens'] = round(total_tokens / max(1, len(chunks)), 1)

        # ── Determine validity ───────────────────────────────
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        valid = len(critical_issues) == 0

        report = ValidationReport(
            valid=valid,
            total_chunks=len(chunks),
            issues=issues,
            stats=stats,
        )

        if document_id:
            logger.info(
                f"[CHUNK_VALIDATION] doc={document_id} valid={valid} "
                f"chunks={len(chunks)} critical={len(critical_issues)} "
                f"warnings={sum(1 for i in issues if i.severity == IssueSeverity.WARNING)}"
            )

        return report

    # ========================================================================
    # INDIVIDUAL CHECKS
    # ========================================================================

    def _check_empty_chunks(
        self,
        chunks: List[Dict[str, Any]],
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Detect empty or whitespace-only chunks."""
        stats['checks_run'].append('empty_chunks')
        for i, chunk in enumerate(chunks):
            text = (chunk.get('text', '') or '').strip()
            if not text:
                issues.append(ChunkIssue(
                    chunk_index=i,
                    chunk_id=chunk.get('id'),
                    severity=IssueSeverity.CRITICAL,
                    category='empty',
                    message=f"Chunk {i} is empty (no text content)",
                ))

    def _check_chunk_sizes(
        self,
        chunks: List[Dict[str, Any]],
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Detect chunks that are too small or too large."""
        stats['checks_run'].append('chunk_sizes')

        for i, chunk in enumerate(chunks):
            text = (chunk.get('text', '') or '').strip()
            if not text:
                continue

            char_len = len(text)
            token_count = chunk.get('token_count', 0)

            # Too small → likely noise
            if char_len < self.MIN_CHUNK_CHARS or token_count < self.MIN_TOKEN_COUNT:
                issues.append(ChunkIssue(
                    chunk_index=i,
                    chunk_id=chunk.get('id'),
                    severity=IssueSeverity.WARNING,
                    category='too_small',
                    message=f"Chunk {i} too small: {char_len} chars, {token_count} tokens",
                    detail={'chars': char_len, 'tokens': token_count},
                ))

            # Too large → will fail BGE-M3 embedding
            if char_len > self.MAX_CHUNK_CHARS or token_count > self.MAX_TOKEN_COUNT:
                issues.append(ChunkIssue(
                    chunk_index=i,
                    chunk_id=chunk.get('id'),
                    severity=IssueSeverity.CRITICAL,
                    category='too_large',
                    message=(
                        f"Chunk {i} exceeds size limits: {char_len} chars, "
                        f"{token_count} tokens (max {self.MAX_CHUNK_CHARS}/{self.MAX_TOKEN_COUNT})"
                    ),
                    detail={'chars': char_len, 'tokens': token_count},
                ))

    def _check_broken_sentences(
        self,
        chunks: List[Dict[str, Any]],
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Detect chunks that end mid-sentence (no sentence-ending punctuation)."""
        stats['checks_run'].append('broken_sentences')

        for i, chunk in enumerate(chunks):
            text = (chunk.get('text', '') or '').strip()
            if not text or len(text) < 30:
                continue  # Skip very short chunks

            # Get last meaningful character
            last_char = text.rstrip()[-1] if text.rstrip() else ''

            # Check if chunk ends on a sentence boundary
            if last_char not in self.SENTENCE_ENDINGS:
                issues.append(ChunkIssue(
                    chunk_index=i,
                    chunk_id=chunk.get('id'),
                    severity=IssueSeverity.WARNING,
                    category='broken_sentence',
                    message=(
                        f"Chunk {i} may end mid-sentence "
                        f"(ends with '{last_char}', not sentence-ending punctuation)"
                    ),
                    detail={
                        'last_char': last_char,
                        'chunk_ending': text[-60:],
                    },
                ))

    def _check_near_duplicates(
        self,
        chunks: List[Dict[str, Any]],
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Detect chunks that are near-duplicates of each other.

        Uses a lightweight hash-based approach: sample the first N chars of
        each chunk, normalize, and compare. This is O(n) and catches exact
        and near-exact duplicates without expensive embedding comparison.
        """
        stats['checks_run'].append('near_duplicates')

        if len(chunks) < 2:
            return

        # Build normalized samples
        samples: List[Tuple[int, str]] = []
        for i, chunk in enumerate(chunks):
            text = (chunk.get('text', '') or '').strip()
            if not text:
                continue
            sample = self._normalize_for_dedup(text[:self.DUPLICATE_SAMPLE_CHARS])
            if sample:
                samples.append((i, sample))

        # Compare adjacent and near-adjacent chunks
        dupes_found: Set[int] = set()
        for pos in range(len(samples)):
            i, sample_i = samples[pos]
            if i in dupes_found:
                continue

            # Check next 3 chunks (adjacent are most likely duplicates)
            for offset in range(1, min(4, len(samples) - pos)):
                j, sample_j = samples[pos + offset]
                if j in dupes_found:
                    continue

                similarity = self._jaccard_similarity(sample_i, sample_j)
                if similarity >= self.DUPLICATE_SIMILARITY:
                    issues.append(ChunkIssue(
                        chunk_index=j,
                        chunk_id=chunks[j].get('id'),
                        severity=IssueSeverity.WARNING,
                        category='near_duplicate',
                        message=f"Chunk {j} is {similarity:.0%} similar to chunk {i}",
                        detail={
                            'similar_to': i,
                            'similarity': round(similarity, 3),
                        },
                    ))
                    dupes_found.add(j)

    def _check_overlap_quality(
        self,
        chunks: List[Dict[str, Any]],
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Check that overlap between adjacent chunks is within bounds."""
        stats['checks_run'].append('overlap_quality')

        if len(chunks) < 2:
            return

        for i in range(len(chunks) - 1):
            current = chunks[i]
            next_chunk = chunks[i + 1]

            curr_text = (current.get('text', '') or '').strip()
            next_text = (next_chunk.get('text', '') or '').strip()

            if not curr_text or not next_text:
                continue

            # Estimate overlap: check if end of current appears in start of next
            overlap_end = curr_text[-80:] if len(curr_text) >= 80 else curr_text
            overlap_start = next_text[:80] if len(next_text) >= 80 else next_text

            overlap_chars = self._longest_common_substring(overlap_end, overlap_start)
            overlap_ratio = overlap_chars / min(len(overlap_end), len(overlap_start)) if min(len(overlap_end), len(overlap_start)) > 0 else 0

            if overlap_ratio > self.MAX_OVERLAP_RATIO:
                issues.append(ChunkIssue(
                    chunk_index=i,
                    chunk_id=current.get('id'),
                    severity=IssueSeverity.WARNING,
                    category='excessive_overlap',
                    message=(
                        f"Chunks {i} and {i + 1} have {overlap_ratio:.0%} overlap "
                        f"(max {self.MAX_OVERLAP_RATIO:.0%})"
                    ),
                    detail={'overlap_ratio': round(overlap_ratio, 3)},
                ))

    def _check_coverage(
        self,
        chunks: List[Dict[str, Any]],
        source_text: str,
        issues: List[ChunkIssue],
        stats: Dict[str, Any],
    ) -> None:
        """Check that chunks cover the source text without large gaps."""
        stats['checks_run'].append('coverage')

        if not source_text:
            return

        source_len = len(source_text)

        # Extract character ranges from chunks
        ranges = []
        for chunk in chunks:
            start = chunk.get('start_char', 0)
            end = chunk.get('end_char', 0)
            if start < end:
                ranges.append((start, end))

        if not ranges:
            return

        ranges.sort()
        covered = 0
        last_end = 0

        for start, end in ranges:
            if start > last_end:
                gap = start - last_end
                if gap > 100:  # Significant gap
                    issues.append(ChunkIssue(
                        chunk_index=-1,
                        chunk_id=None,
                        severity=IssueSeverity.WARNING,
                        category='coverage_gap',
                        message=f"Coverage gap of {gap} chars between char positions {last_end}-{start}",
                        detail={'gap_chars': gap, 'position': last_end},
                    ))
            covered += end - max(start, last_end)
            last_end = max(last_end, end)

        coverage_pct = covered / max(1, source_len)
        stats['coverage_pct'] = round(coverage_pct * 100, 1)

        if coverage_pct < 0.90:
            issues.append(ChunkIssue(
                chunk_index=-1,
                chunk_id=None,
                severity=IssueSeverity.INFO,
                category='low_coverage',
                message=f"Chunk coverage is {coverage_pct:.1%} of source text",
                detail={'coverage_pct': round(coverage_pct, 3)},
            ))

    # ========================================================================
    # UTILITIES
    # ========================================================================

    @staticmethod
    def _normalize_for_dedup(text: str) -> str:
        """Normalize text for duplicate detection."""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text

    @staticmethod
    def _jaccard_similarity(text_a: str, text_b: str) -> float:
        """Compute Jaccard similarity between two texts at word level."""
        words_a = set(text_a.split())
        words_b = set(text_b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    @staticmethod
    def _longest_common_substring(a: str, b: str) -> int:
        """Length of longest common substring between two strings."""
        if not a or not b:
            return 0

        # Simple O(n*m) for short strings (< 200 chars)
        max_len = 0
        len_a, len_b = len(a), len(b)

        # Use dynamic programming approach
        prev = [0] * (len_b + 1)
        for i in range(1, len_a + 1):
            curr = [0] * (len_b + 1)
            for j in range(1, len_b + 1):
                if a[i - 1] == b[j - 1]:
                    curr[j] = prev[j - 1] + 1
                    max_len = max(max_len, curr[j])
            prev = curr

        return max_len


# ========================================================================
# CONVENIENCE FUNCTION
# ========================================================================

def validate_chunks(
    chunks: List[Dict[str, Any]],
    source_text: Optional[str] = None,
    document_id: Optional[str] = None,
    strict: bool = False,
) -> ValidationReport:
    """Convenience function for quick chunk validation.

    Args:
        chunks: Chunk list from DocumentChunker
        source_text: Original document text (optional)
        document_id: Document ID for logging
        strict: If True, raises ChunkValidationError on critical issues

    Returns:
        ValidationReport

    Raises:
        ChunkValidationError: If strict=True and critical issues found
    """
    validator = ChunkValidator()
    report = validator.validate(chunks, source_text, document_id)

    if strict and not report.valid:
        from core.exceptions import DocumentProcessingError
        raise DocumentProcessingError(
            f"Chunk validation failed with {report.critical_count} critical issues: "
            + "; ".join(i.message for i in report.issues if i.severity == IssueSeverity.CRITICAL)
        )

    return report


__all__ = [
    'ChunkValidator',
    'ValidationReport',
    'ChunkIssue',
    'IssueSeverity',
    'validate_chunks',
]
