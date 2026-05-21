from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.apps import apps
from django.db.models import Q

from .query_intent import QueryIntent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpreadsheetQuerySpec:
    intent: QueryIntent
    cell_ref: Optional[str] = None
    row_number: Optional[int] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    column_letter: Optional[str] = None
    lookup_term: Optional[str] = None


class SpreadsheetRetriever:
    """Intent-specific spreadsheet retriever for Excel/XLSX content."""

    _CELL_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(?:o|ô|cell)\s*([A-Z]{1,3}\d{1,5})\b", re.IGNORECASE),
        re.compile(r"\b([A-Z]{1,3}\d{1,5})\s+(?:la gi|chua gi|gia tri)\b", re.IGNORECASE),
    )
    _ROW_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(?:dong|hang|row)(?:\s+excel)?\s*(\d+)\b", re.IGNORECASE),
        re.compile(r"\b(\d+)\s+(?:dong|hang|row)(?:\s+excel)?\b", re.IGNORECASE),
    )
    _ROW_RANGE_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(
            r"\b(?:cac\s+)?(?:dong|hang|row)(?:\s+excel)?\s*(\d+)\s*(?:den|toi|-)\s*(\d+)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(\d+)\s*(?:den|toi|-)\s*(\d+)\s+(?:dong|hang|row)(?:\s+excel)?\b",
            re.IGNORECASE,
        ),
    )
    _COLUMN_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(?:cot|column)\s*([A-Z]{1,3})\b", re.IGNORECASE),
        re.compile(r"\b([A-Z]{1,3})\s+(?:cot|column)\b", re.IGNORECASE),
    )
    _LOOKUP_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(r"(?:bang|table|thong tin)\s+(?:cua|cho)\s+(.+?)(?:\s+la|$)", re.IGNORECASE),
        re.compile(r"(?:tim|tim kiem|search|lookup)\s+(.+?)(?:\s+trong|bao nhieu|$)", re.IGNORECASE),
        re.compile(r"(?:chi tiet|xem|show)\s+(?:cua|cho|tung)?\s*(.+)", re.IGNORECASE),
        re.compile(r"(.+?)\s+(?:co|bao nhieu|gia|luong|bao)$", re.IGNORECASE),
    )
    _ROW_LINE_PATTERN = re.compile(r'^\|\s*(\d+)\s*\|')
    _SHEET_HEADER_PATTERN = re.compile(r'^---\s*Sheet:\s*(.*?)\s*\(Page\s*(\d+)\)\s*---$')
    _V2_SHEET_HEADER_PATTERN = re.compile(r'^#\s*Sheet:\s*(.*?),\s*Row\s*(\d+)\s*$')

    def retrieve(
        self,
        query: str,
        document_ids: Sequence[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return spreadsheet-aware candidates sorted by relevance."""
        spec = self.parse_query(query)
        if not document_ids:
            return []

        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        except Exception as exc:
            logger.warning(f"[SPREADSHEET] DocumentChunk model unavailable: {exc}")
            return []

        chunks = list(
            DocumentChunk.objects.filter(
                document_id__in=document_ids,
                is_deleted=False,
            ).filter(
                Q(metadata__content_format='spreadsheet_markdown')
                | Q(metadata__source='excel_chunker_v2')
                | Q(metadata__chunking_strategy='excel_row_column_aware')
                | Q(content__contains='| Excel row |')
                | Q(content__icontains='--- Sheet:')
                | Q(content__icontains='# Sheet:')
            ).values(
                'id',
                'document_id',
                'content',
                'page_number',
                'chunk_index',
                'metadata',
            )
        )
        if not chunks:
            return []

        scored: List[Dict[str, Any]] = []
        for chunk in chunks:
            chunk_score, excerpt, match_type = self._score_chunk(query, spec, chunk)
            if chunk_score <= 0:
                continue

            chunk_metadata = dict(chunk.get('metadata') or {})
            sheet_name = self._sheet_name(chunk.get('content') or '', chunk_metadata)
            row_numbers = self._extract_row_numbers(chunk.get('content') or '', chunk_metadata)
            candidate = {
                'chunk_id': str(chunk['id']),
                'document_id': str(chunk['document_id']),
                'score': float(chunk_score),
                'source': 'spreadsheet',
                'snippet': excerpt,
                'citation_excerpt': excerpt,
                'page': chunk.get('page_number'),
                'chunk_index': chunk.get('chunk_index'),
                'metadata': {
                    **chunk_metadata,
                    'content_format': 'spreadsheet_markdown',
                    'sheet_name': sheet_name,
                    'spreadsheet_intent': spec.intent.value,
                    'spreadsheet_match_type': match_type,
                    'spreadsheet_row_numbers': row_numbers,
                },
            }
            if spec.cell_ref:
                candidate['metadata']['cell_reference'] = spec.cell_ref
            if spec.row_number is not None:
                candidate['metadata']['row_number'] = spec.row_number
            if spec.row_start is not None and spec.row_end is not None:
                candidate['metadata']['row_start'] = spec.row_start
                candidate['metadata']['row_end'] = spec.row_end
            if spec.column_letter:
                candidate['metadata']['column_letter'] = spec.column_letter
            if spec.lookup_term:
                candidate['metadata']['lookup_term'] = spec.lookup_term
            scored.append(candidate)

        if spec.row_start is not None and spec.row_end is not None:
            scored.sort(
                key=lambda item: (
                    int((item.get('metadata') or {}).get('row_number') or 0),
                    -float(item.get('score', 0.0) or 0.0),
                )
            )
            return scored[:max(top_k, abs(spec.row_end - spec.row_start) + 1)]

        scored.sort(key=lambda item: float(item.get('score', 0.0) or 0.0), reverse=True)
        return scored[:top_k]

    def parse_query(self, query: str) -> SpreadsheetQuerySpec:
        normalized = self._normalize(query)

        cell_ref = self._first_group(self._CELL_PATTERNS, normalized)
        if cell_ref:
            return SpreadsheetQuerySpec(intent=QueryIntent.SPREADSHEET_CELL, cell_ref=cell_ref.upper())

        row_range = self._first_int_pair(self._ROW_RANGE_PATTERNS, normalized)
        if row_range is not None:
            row_start, row_end = sorted(row_range)
            return SpreadsheetQuerySpec(
                intent=QueryIntent.SPREADSHEET_ROW,
                row_start=row_start,
                row_end=row_end,
            )

        row_number = self._first_int(self._ROW_PATTERNS, normalized)
        if row_number is not None:
            return SpreadsheetQuerySpec(intent=QueryIntent.SPREADSHEET_ROW, row_number=row_number)

        column_letter = self._first_group(self._COLUMN_PATTERNS, normalized)
        if column_letter:
            return SpreadsheetQuerySpec(intent=QueryIntent.SPREADSHEET_COLUMN, column_letter=column_letter.upper())

        lookup_term = self._first_group(self._LOOKUP_PATTERNS, normalized)
        if lookup_term:
            return SpreadsheetQuerySpec(intent=QueryIntent.SPREADSHEET_LOOKUP, lookup_term=lookup_term.strip())

        return SpreadsheetQuerySpec(intent=QueryIntent.SPREADSHEET_LOOKUP, lookup_term=normalized or query)

    def _score_chunk(
        self,
        query: str,
        spec: SpreadsheetQuerySpec,
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        content = (chunk.get('content') or '').strip()
        if not content:
            return 0.0, '', 'empty'

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        row_lines = [line for line in lines if self._ROW_LINE_PATTERN.match(line)]
        normalized_query = self._normalize(spec.lookup_term or query)

        if spec.intent == QueryIntent.SPREADSHEET_CELL:
            cell_ref = spec.cell_ref or ''
            return self._score_cell_query(cell_ref, row_lines, lines, chunk)

        if spec.intent == QueryIntent.SPREADSHEET_ROW:
            if spec.row_start is not None and spec.row_end is not None:
                return self._score_row_range_query(spec.row_start, spec.row_end, row_lines, lines, chunk)
            return self._score_row_query(spec.row_number, row_lines, lines, chunk)

        if spec.intent == QueryIntent.SPREADSHEET_COLUMN:
            return self._score_column_query(spec.column_letter, row_lines, lines, chunk)

        return self._score_lookup_query(normalized_query, row_lines, lines, chunk)

    def _score_cell_query(
        self,
        cell_ref: str,
        row_lines: List[str],
        lines: List[str],
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        if not cell_ref:
            return 0.0, '', 'cell_missing'

        row_number, column_letter = self._split_cell_ref(cell_ref)
        if row_number is None or not column_letter:
            return 0.0, '', 'cell_invalid'

        row_line = self._find_row_line(row_lines, row_number)
        if row_line:
            value = self._extract_cell_from_row_line(row_line, column_letter, lines)
            if value:
                excerpt = self._build_excerpt(lines, row_line, f"{cell_ref} = {value}")
                return 100.0, excerpt, 'cell_exact'
            if self._column_index_from_header(column_letter, lines) == -1:
                return 0.0, '', 'cell_not_found'
            excerpt = self._build_excerpt(lines, row_line, f"{cell_ref}")
            return 85.0, excerpt, 'cell_row_match'

        for line in row_lines:
            if cell_ref.lower() in self._normalize(line):
                return 70.0, self._build_excerpt(lines, line, cell_ref), 'cell_text_match'

        return 0.0, '', 'cell_not_found'

    def _score_row_query(
        self,
        row_number: Optional[int],
        row_lines: List[str],
        lines: List[str],
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        if row_number is None:
            return 0.0, '', 'row_missing'

        row_line = self._find_row_line(row_lines, row_number)
        if row_line:
            return 100.0, self._build_excerpt(lines, row_line, f"row {row_number}"), 'row_exact'

        metadata = chunk.get('metadata') or {}
        metadata_rows = self._metadata_row_numbers(metadata)
        if row_number in metadata_rows:
            focus_line = next((line for line in lines if f"Row {row_number}" in line), lines[0] if lines else '')
            return 96.0, self._build_excerpt(lines, focus_line, f"row {row_number}"), 'row_metadata_exact'

        return 0.0, '', 'row_not_found'

    def _score_row_range_query(
        self,
        row_start: Optional[int],
        row_end: Optional[int],
        row_lines: List[str],
        lines: List[str],
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        if row_start is None or row_end is None:
            return 0.0, '', 'row_range_missing'

        low, high = sorted((row_start, row_end))
        metadata = chunk.get('metadata') or {}
        row_candidates = self._metadata_row_numbers(metadata)
        for row_line in row_lines:
            match = self._ROW_LINE_PATTERN.match(row_line)
            if match:
                row_candidates.append(int(match.group(1)))

        row_candidates = sorted(set(row_candidates))
        for row_number in row_candidates:
            if low <= row_number <= high:
                row_line = self._find_row_line(row_lines, row_number)
                focus_line = row_line or next((line for line in lines if f"Row {row_number}" in line), lines[0] if lines else '')
                return 100.0, self._build_excerpt(lines, focus_line, f"row {row_number}"), 'row_range_exact'

        return 0.0, '', 'row_range_not_found'

    def _score_column_query(
        self,
        column_letter: Optional[str],
        row_lines: List[str],
        lines: List[str],
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        if not column_letter:
            return 0.0, '', 'column_missing'

        column_letter = column_letter.upper()
        matches: List[str] = []
        for line in row_lines:
            value = self._extract_cell_from_row_line(line, column_letter, lines)
            if value:
                matches.append(value)

        if matches:
            preview = ', '.join(matches[:8])
            sheet_name = self._sheet_name(chunk.get('content') or '', chunk.get('metadata') or {})
            excerpt = f"Sheet: {sheet_name}\nColumn {column_letter}: {preview}"
            return 90.0, excerpt, 'column_exact'

        return 0.0, '', 'column_not_found'

    def _score_lookup_query(
        self,
        normalized_query: str,
        row_lines: List[str],
        lines: List[str],
        chunk: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        if not normalized_query:
            return 0.0, '', 'lookup_missing'

        best_score = 0.0
        best_line = ''
        best_type = 'lookup_not_found'

        for line in row_lines:
            normalized_line = self._normalize(line)
            if normalized_query == normalized_line:
                return 100.0, self._build_excerpt(lines, line, normalized_query), 'lookup_exact'
            if normalized_query and normalized_query in normalized_line:
                score = 92.0
                if score > best_score:
                    best_score = score
                    best_line = line
                    best_type = 'lookup_substring'
                continue

            query_tokens = {token for token in re.split(r'\W+', normalized_query) if len(token) >= 2}
            line_tokens = {token for token in re.split(r'\W+', normalized_line) if len(token) >= 2}
            overlap = len(query_tokens & line_tokens)
            if overlap:
                score = min(80.0, 45.0 + overlap * 8.0)
                if score > best_score:
                    best_score = score
                    best_line = line
                    best_type = 'lookup_token'

        if best_line:
            return best_score, self._build_excerpt(lines, best_line, normalized_query), best_type

        return 0.0, '', 'lookup_not_found'

    def _build_excerpt(self, lines: Sequence[str], focus_line: str, label: str, window: int = 2) -> str:
        try:
            focus_index = next(i for i, line in enumerate(lines) if line.strip() == focus_line.strip())
        except StopIteration:
            excerpt_lines = [label, focus_line]
            return '\n'.join(line for line in excerpt_lines if line).strip()

        start = max(0, focus_index - window)
        end = min(len(lines), focus_index + window + 1)
        excerpt_lines = list(lines[start:end])
        if label:
            excerpt_lines.insert(0, f"Match: {label}")
        return '\n'.join(line for line in excerpt_lines if line).strip()

    def _find_row_line(self, row_lines: Sequence[str], row_number: int) -> Optional[str]:
        for line in row_lines:
            match = self._ROW_LINE_PATTERN.match(line)
            if match and int(match.group(1)) == row_number:
                return line
        return None

    def _extract_cell_from_row_line(
        self,
        row_line: str,
        column_letter: str,
        lines: Optional[Sequence[str]] = None,
    ) -> str:
        cells = self._split_markdown_row(row_line)
        if len(cells) <= 1:
            return ''

        header_index = self._column_index_from_header(column_letter, lines or [])
        if header_index == -1:
            return ''
        col_index = header_index if header_index is not None else self._column_letter_to_index(column_letter)
        if col_index is None:
            return ''

        value_index = col_index
        if value_index >= len(cells):
            return ''
        return cells[value_index].strip()

    def _column_index_from_header(
        self,
        column_letter: str,
        lines: Sequence[str],
    ) -> Optional[int]:
        """Return row-cell index using the markdown header.

        Spreadsheet rows are serialized as:
        | Excel row | C | D | E |
        | 10        | ...       |

        In that case column C is at cell index 1, not 3. Falling back to the
        absolute A=1 index is only safe for legacy chunks without a header.
        """
        wanted = (column_letter or '').strip().upper()
        if not wanted:
            return None

        for line in lines[:12]:
            cells = self._split_markdown_row(line)
            if len(cells) <= 1:
                continue
            first = self._normalize(cells[0])
            if first != 'excel row':
                continue
            for index, value in enumerate(cells[1:], start=1):
                if value.strip().upper() == wanted:
                    return index
            return -1
        return None

    def _extract_row_numbers(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[int]:
        numbers: List[int] = []
        for line in content.splitlines():
            match = self._ROW_LINE_PATTERN.match(line.strip())
            if match:
                numbers.append(int(match.group(1)))
        for number in self._metadata_row_numbers(metadata or {}):
            if number not in numbers:
                numbers.append(number)
        return numbers

    def _metadata_row_numbers(self, metadata: Dict[str, Any]) -> List[int]:
        numbers: List[int] = []
        for key in ('row_number', 'row_start', 'row_end'):
            value = metadata.get(key)
            if value is None:
                continue
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number not in numbers:
                numbers.append(number)
        return numbers

    def _sheet_name(self, content: str, metadata: Dict[str, Any]) -> str:
        if metadata.get('sheet_name'):
            return str(metadata['sheet_name'])
        for line in content.splitlines()[:5]:
            match = self._SHEET_HEADER_PATTERN.match(line.strip())
            if match:
                return match.group(1).strip()
            match = self._V2_SHEET_HEADER_PATTERN.match(line.strip())
            if match:
                return match.group(1).strip()
        return 'spreadsheet'

    def _split_cell_ref(self, cell_ref: str) -> Tuple[Optional[int], Optional[str]]:
        match = re.match(r'^([A-Z]{1,3})(\d{1,5})$', cell_ref.upper())
        if not match:
            return None, None
        return int(match.group(2)), match.group(1)

    def _column_letter_to_index(self, column_letter: str) -> Optional[int]:
        column_letter = (column_letter or '').strip().upper()
        if not column_letter or not re.fullmatch(r'[A-Z]{1,3}', column_letter):
            return None

        index = 0
        for char in column_letter:
            index = index * 26 + (ord(char) - 64)
        return index

    def _split_markdown_row(self, row_line: str) -> List[str]:
        row_line = (row_line or '').strip().strip('|')
        if not row_line:
            return []
        return [cell.strip() for cell in row_line.split('|')]

    def _normalize(self, text: str) -> str:
        value = (text or '').strip().lower().replace('đ', 'd')
        value = unicodedata.normalize('NFD', value)
        value = ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')
        value = re.sub(r'[^\w\s./()-]', ' ', value)
        return re.sub(r'\s+', ' ', value).strip()

    def _first_group(self, patterns: Sequence[re.Pattern[str]], text: str) -> Optional[str]:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    def _first_int(self, patterns: Sequence[re.Pattern[str]], text: str) -> Optional[int]:
        group = self._first_group(patterns, text)
        if not group:
            return None
        try:
            return int(group)
        except ValueError:
            return None

    def _first_int_pair(self, patterns: Sequence[re.Pattern[str]], text: str) -> Optional[Tuple[int, int]]:
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            try:
                return int(match.group(1)), int(match.group(2))
            except (IndexError, ValueError):
                continue
        return None
