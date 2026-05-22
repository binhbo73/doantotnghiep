"""
Local structured document representation for RAG ingestion.

This module intentionally does not depend on MinerU at runtime. It borrows the
useful output shape: page-oriented blocks with type, bbox, reading order, and
heading/table/image/equation metadata. Parsers can progressively map richer
layout output into the same schema, while current local parsers can still
produce a useful block structure from page-aware text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import re


AUXILIARY_BLOCK_TYPES = {
    "header",
    "footer",
    "page_number",
    "page_header",
    "page_footer",
    "page_footnote",
    "page_aside_text",
}

CONTENT_BLOCK_TYPES = {
    "title",
    "paragraph",
    "table",
    "image",
    "chart",
    "equation",
    "list",
    "code",
    "algorithm",
    "ocr_text",
}


@dataclass
class ParsedBlock:
    type: str
    text: str = ""
    page_idx: int = 0
    reading_order: int = 0
    bbox: Optional[List[int]] = None
    text_level: int = 0
    heading_path: List[str] = field(default_factory=list)
    html: Optional[str] = None
    latex: Optional[str] = None
    caption: Optional[str] = None
    image_path: Optional[str] = None
    table_id: Optional[str] = None
    image_id: Optional[str] = None
    source: str = "local_heuristic"
    is_discarded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def content_text(self) -> str:
        parts = []
        if self.caption:
            parts.append(self.caption)
        if self.html and self.type == "table":
            parts.append(self.html)
        elif self.latex:
            parts.append(self.latex)
        if self.text:
            parts.append(self.text)
        return "\n".join(part for part in parts if part).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "page_idx": self.page_idx,
            "page_number": self.page_idx + 1,
            "reading_order": self.reading_order,
            "bbox": self.bbox,
            "text_level": self.text_level,
            "heading_path": self.heading_path,
            "html": self.html,
            "latex": self.latex,
            "caption": self.caption,
            "image_path": self.image_path,
            "table_id": self.table_id,
            "image_id": self.image_id,
            "source": self.source,
            "is_discarded": self.is_discarded,
            "metadata": self.metadata,
        }


@dataclass
class ParsedPage:
    page_idx: int
    blocks: List[ParsedBlock] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None

    @property
    def page_number(self) -> int:
        return self.page_idx + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_idx": self.page_idx,
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass
class ParsedDocument:
    text: str
    pages: List[ParsedPage]
    source_name: str = ""
    parse_backend: str = "local_page_aware"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def blocks(self, include_discarded: bool = False) -> List[ParsedBlock]:
        result: List[ParsedBlock] = []
        for page in self.pages:
            for block in page.blocks:
                if include_discarded or not block.is_discarded:
                    result.append(block)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "parse_backend": self.parse_backend,
            "metadata": self.metadata,
            "pages": [page.to_dict() for page in self.pages],
        }

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        discarded = 0
        for block in self.blocks(include_discarded=True):
            counts[block.type] = counts.get(block.type, 0) + 1
            if block.is_discarded:
                discarded += 1
        return {
            "parse_backend": self.parse_backend,
            "page_count": len(self.pages),
            "block_count": sum(counts.values()),
            "discarded_block_count": discarded,
            "block_type_counts": counts,
        }


class LocalStructuredParser:
    """Build a MinerU-like structured representation from PageAwareText."""

    TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
    PAGE_BREAK_RE = re.compile(r"^\s*---\s*\[PAGE BREAK\]\s*---\s*$", re.IGNORECASE)
    MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+){0,5})\.\s+(.{3,160})$")
    TABLE_CAPTION_RE = re.compile(r"^\s*(?:Bảng|Bang|Table)\s+\d+\s*[:.\-]?\s+.+$", re.IGNORECASE)
    EQUATION_RE = re.compile(r"^\s*(\$\$.*\$\$|\\\[.*\\\]|\\begin\{equation\}.*|[A-Za-z0-9_{}^\\]+\s*=.+)\s*$")
    IMAGE_RE = re.compile(r"^\s*(?:!\[[^\]]*\]\([^)]+\)|\[Image(?::[^\]]*)?\])\s*$", re.IGNORECASE)
    PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?\d{1,5}\s*$", re.IGNORECASE)

    def build(
        self,
        page_aware_text,
        source_name: str = "",
        parse_backend: str = "local_page_aware",
        file_type: str = "",
    ) -> ParsedDocument:
        text = getattr(page_aware_text, "text", "") or ""
        pages = self._split_pages(page_aware_text)
        repeated_headers, repeated_footers = self._detect_repeated_marginal_lines(pages)

        parsed_pages: List[ParsedPage] = []
        global_order = 0
        heading_stack: List[str] = []

        for page_idx, page_text in enumerate(pages):
            parsed_page = ParsedPage(page_idx=page_idx)
            page_blocks = self._page_text_to_blocks(
                page_text=page_text,
                page_idx=page_idx,
                start_order=global_order,
                heading_stack=heading_stack,
                repeated_headers=repeated_headers,
                repeated_footers=repeated_footers,
            )
            if page_blocks:
                global_order = max(block.reading_order for block in page_blocks) + 1
            parsed_page.blocks.extend(page_blocks)
            parsed_pages.append(parsed_page)

        metadata = dict(getattr(page_aware_text, "metadata", {}) or {})
        metadata.update({
            "file_type": file_type,
            "structured_source": parse_backend,
        })
        return ParsedDocument(
            text=text,
            pages=parsed_pages,
            source_name=source_name,
            parse_backend=parse_backend,
            metadata=metadata,
        )

    def _split_pages(self, page_aware_text) -> List[str]:
        text = getattr(page_aware_text, "text", "") or ""
        boundaries = list(getattr(page_aware_text, "boundaries", []) or [])
        if not boundaries:
            return [text] if text else []

        pages = []
        for boundary in boundaries:
            start = max(0, int(getattr(boundary, "char_start", 0) or 0))
            end = int(getattr(boundary, "char_end", 0) or 0) or len(text)
            page_text = text[start:end]
            page_text = re.sub(r"^\s*---\s*(?:Page|Sheet|CSV Page)[^\n]*---\s*", "", page_text, flags=re.IGNORECASE)
            pages.append(self._strip_page_break_markers(page_text).strip())
        return pages

    def _strip_page_break_markers(self, text: str) -> str:
        """Remove synthetic page-break markers before block classification."""
        if not text:
            return ""
        lines = [
            line
            for line in text.splitlines()
            if not self.PAGE_BREAK_RE.match(line.strip())
        ]
        return "\n".join(lines)

    def _detect_repeated_marginal_lines(self, pages: List[str]) -> tuple[set[str], set[str]]:
        if len(pages) < 3:
            return set(), set()

        header_counts: Dict[str, int] = {}
        footer_counts: Dict[str, int] = {}

        for page in pages:
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            if not lines:
                continue
            for line in lines[:3]:
                key = self._line_key(line)
                if key:
                    header_counts[key] = header_counts.get(key, 0) + 1
            for line in lines[-3:]:
                key = self._line_key(line)
                if key:
                    footer_counts[key] = footer_counts.get(key, 0) + 1

        threshold = max(2, int(len(pages) * 0.5))
        return (
            {key for key, count in header_counts.items() if count >= threshold},
            {key for key, count in footer_counts.items() if count >= threshold},
        )

    def _line_key(self, line: str) -> str:
        normalized = re.sub(r"\d+", "#", (line or "").strip().lower())
        normalized = re.sub(r"\s+", " ", normalized)
        if len(normalized) < 3 or len(normalized) > 140:
            return ""
        return normalized

    def _page_text_to_blocks(
        self,
        page_text: str,
        page_idx: int,
        start_order: int,
        heading_stack: List[str],
        repeated_headers: set[str],
        repeated_footers: set[str],
    ) -> List[ParsedBlock]:
        lines = page_text.splitlines()
        blocks: List[ParsedBlock] = []
        order = start_order
        paragraph: List[str] = []
        paragraph_start_line = 0
        idx = 0

        def flush_paragraph(end_line: int):
            nonlocal paragraph, paragraph_start_line, order
            text = "\n".join(paragraph).strip()
            paragraph = []
            if not text:
                return
            block_type, level = self._classify_text_block(text)
            if block_type == "title":
                self._update_heading_stack(heading_stack, text, level)
            block = ParsedBlock(
                type=block_type,
                text=text,
                page_idx=page_idx,
                reading_order=order,
                text_level=level,
                heading_path=list(heading_stack),
                source="local_heuristic",
                metadata={
                    "line_start": paragraph_start_line + 1,
                    "line_end": end_line,
                },
            )
            blocks.append(block)
            order += 1

        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            line_key = self._line_key(stripped)

            if self.PAGE_BREAK_RE.match(stripped):
                flush_paragraph(idx)
                idx += 1
                continue

            if not stripped:
                flush_paragraph(idx)
                idx += 1
                continue

            if idx <= 2 and line_key in repeated_headers:
                flush_paragraph(idx)
                blocks.append(self._aux_block("header", stripped, page_idx, order, idx))
                order += 1
                idx += 1
                continue

            if idx >= max(0, len(lines) - 3) and line_key in repeated_footers:
                flush_paragraph(idx)
                block_type = "page_number" if self.PAGE_NUMBER_RE.match(stripped) else "footer"
                blocks.append(self._aux_block(block_type, stripped, page_idx, order, idx))
                order += 1
                idx += 1
                continue

            if self.PAGE_NUMBER_RE.match(stripped) and (idx <= 2 or idx >= len(lines) - 3):
                flush_paragraph(idx)
                blocks.append(self._aux_block("page_number", stripped, page_idx, order, idx))
                order += 1
                idx += 1
                continue

            if self.TABLE_LINE_RE.match(stripped):
                flush_paragraph(idx)
                table_lines = []
                start_line = idx
                while idx < len(lines) and self.TABLE_LINE_RE.match(lines[idx].strip()):
                    table_lines.append(lines[idx].strip())
                    idx += 1
                table_text = "\n".join(table_lines).strip()
                table_id = self._stable_block_id("table", page_idx, order, table_text)
                blocks.append(ParsedBlock(
                    type="table",
                    text=table_text,
                    html=None,
                    table_id=table_id,
                    page_idx=page_idx,
                    reading_order=order,
                    heading_path=list(heading_stack),
                    source="local_heuristic",
                    metadata={
                        "line_start": start_line + 1,
                        "line_end": idx,
                        "table_format": "markdown",
                    },
                ))
                order += 1
                continue

            if self._is_table_caption_line(stripped):
                flush_paragraph(idx)
                table_lines = [stripped]
                start_line = idx
                idx += 1
                while idx < len(lines):
                    next_line = lines[idx]
                    next_stripped = next_line.strip()
                    if self.PAGE_BREAK_RE.match(next_stripped):
                        break
                    if next_stripped and self._is_table_caption_line(next_stripped):
                        break
                    if next_stripped and self._is_standalone_heading_line(next_stripped):
                        break
                    if self.IMAGE_RE.match(next_stripped) or self._looks_like_equation(next_stripped):
                        break
                    table_lines.append(next_line.rstrip())
                    idx += 1

                table_text = "\n".join(table_lines).strip()
                table_id = self._stable_block_id("table", page_idx, order, table_text)
                blocks.append(ParsedBlock(
                    type="table",
                    text=table_text,
                    html=None,
                    table_id=table_id,
                    page_idx=page_idx,
                    reading_order=order,
                    heading_path=list(heading_stack),
                    source="local_heuristic",
                    metadata={
                        "line_start": start_line + 1,
                        "line_end": idx,
                        "table_format": "plain_text",
                    },
                ))
                order += 1
                continue

            if self.IMAGE_RE.match(stripped):
                flush_paragraph(idx)
                image_id = self._stable_block_id("image", page_idx, order, stripped)
                blocks.append(ParsedBlock(
                    type="image",
                    text=stripped,
                    caption=stripped,
                    image_id=image_id,
                    page_idx=page_idx,
                    reading_order=order,
                    heading_path=list(heading_stack),
                    source="local_heuristic",
                    metadata={"line_start": idx + 1, "line_end": idx + 1},
                ))
                order += 1
                idx += 1
                continue

            if self._looks_like_equation(stripped):
                flush_paragraph(idx)
                latex = stripped if "$" in stripped or "\\" in stripped else None
                blocks.append(ParsedBlock(
                    type="equation",
                    text=stripped,
                    latex=latex,
                    page_idx=page_idx,
                    reading_order=order,
                    heading_path=list(heading_stack),
                    source="local_heuristic",
                    metadata={"line_start": idx + 1, "line_end": idx + 1},
                ))
                order += 1
                idx += 1
                continue

            if self._is_standalone_heading_line(stripped):
                flush_paragraph(idx)
                paragraph_start_line = idx
                paragraph = [line]
                flush_paragraph(idx + 1)
                idx += 1
                continue

            if not paragraph:
                paragraph_start_line = idx
            paragraph.append(line)
            idx += 1

        flush_paragraph(len(lines))
        return blocks

    def _aux_block(self, block_type: str, text: str, page_idx: int, order: int, line_idx: int) -> ParsedBlock:
        return ParsedBlock(
            type=block_type,
            text=text,
            page_idx=page_idx,
            reading_order=order,
            source="local_heuristic",
            is_discarded=True,
            metadata={
                "line_start": line_idx + 1,
                "line_end": line_idx + 1,
                "is_header_footer": block_type in {"header", "footer", "page_number"},
            },
        )

    def _classify_text_block(self, text: str) -> tuple[str, int]:
        one_line = " ".join(line.strip() for line in text.splitlines() if line.strip())
        md = self.MARKDOWN_HEADING_RE.match(one_line)
        if md:
            return "title", min(6, len(md.group(1)))

        numbered = self.NUMBERED_HEADING_RE.match(one_line)
        if numbered and len(one_line.split()) <= 18:
            level = min(6, numbered.group(1).count(".") + 1)
            return "title", level

        words = one_line.split()
        if 2 <= len(words) <= 12 and len(one_line) <= 100:
            letters = [ch for ch in one_line if ch.isalpha()]
            upper_ratio = (
                sum(1 for ch in letters if ch.isupper()) / max(1, len(letters))
                if letters else 0.0
            )
            if upper_ratio >= 0.65 or one_line.endswith(":"):
                return "title", 2

        if self._looks_like_list(text):
            return "list", 0

        return "paragraph", 0

    def _is_standalone_heading_line(self, line: str) -> bool:
        if self.MARKDOWN_HEADING_RE.match(line):
            return True
        numbered = self.NUMBERED_HEADING_RE.match(line)
        if numbered and len(line.split()) <= 18:
            return True
        words = line.split()
        if 2 <= len(words) <= 12 and len(line) <= 100:
            letters = [ch for ch in line if ch.isalpha()]
            upper_ratio = (
                sum(1 for ch in letters if ch.isupper()) / max(1, len(letters))
                if letters else 0.0
            )
            return upper_ratio >= 0.65 or line.endswith(":")
        return False

    def _is_table_caption_line(self, line: str) -> bool:
        return bool(self.TABLE_CAPTION_RE.match(line or ""))

    def _looks_like_list(self, text: str) -> bool:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return False
        hits = sum(1 for line in lines if re.match(r"^(\d+[.)]|[-*+])\s+", line))
        return hits >= max(2, int(len(lines) * 0.6))

    def _looks_like_equation(self, line: str) -> bool:
        if len(line) > 300:
            return False
        if self.EQUATION_RE.match(line):
            math_tokens = sum(token in line for token in ("=", "\\frac", "\\sum", "\\int", "^", "_", "$$"))
            return math_tokens >= 1
        return False

    def _update_heading_stack(self, heading_stack: List[str], heading: str, level: int) -> None:
        clean = re.sub(r"^#{1,6}\s+", "", heading).strip()
        level = max(1, min(level or 1, 6))
        while len(heading_stack) >= level:
            heading_stack.pop()
        heading_stack.append(clean)

    def _stable_block_id(self, block_type: str, page_idx: int, order: int, text: str) -> str:
        digest = hashlib.md5(f"{block_type}:{page_idx}:{order}:{text[:500]}".encode("utf-8")).hexdigest()[:16]
        return f"{block_type}_{page_idx + 1}_{digest}"


def structured_document_from_content_list(
    content_list: Iterable[Any],
    source_name: str = "",
    parse_backend: str = "content_list",
) -> ParsedDocument:
    """Map a MinerU-like content_list/content_list_v2 structure into ParsedDocument."""
    pages: Dict[int, ParsedPage] = {}
    heading_stack: List[str] = []
    order = 0

    def ensure_page(page_idx: int) -> ParsedPage:
        if page_idx not in pages:
            pages[page_idx] = ParsedPage(page_idx=page_idx)
        return pages[page_idx]

    flattened: List[Dict[str, Any]] = []
    if isinstance(content_list, list) and content_list and isinstance(content_list[0], list):
        for page_idx, page_items in enumerate(content_list):
            for item in page_items:
                if isinstance(item, dict):
                    copied = dict(item)
                    copied.setdefault("page_idx", page_idx)
                    flattened.append(copied)
    else:
        flattened = [item for item in content_list if isinstance(item, dict)]

    text_parts: List[str] = []
    for item in flattened:
        block = _content_item_to_block(item, order, heading_stack, parse_backend)
        ensure_page(block.page_idx).blocks.append(block)
        if not block.is_discarded:
            text = block.content_text()
            if text:
                text_parts.append(text)
        order += 1

    return ParsedDocument(
        text="\n\n".join(text_parts),
        pages=[pages[idx] for idx in sorted(pages)],
        source_name=source_name,
        parse_backend=parse_backend,
    )


def _content_item_to_block(
    item: Dict[str, Any],
    reading_order: int,
    heading_stack: List[str],
    parse_backend: str,
) -> ParsedBlock:
    raw_type = str(item.get("type") or "paragraph")
    block_type = _normalize_content_type(raw_type)
    page_idx = int(item.get("page_idx") or item.get("page") or 0)
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    text_level = int(item.get("text_level") or content.get("level") or 0)
    text = _extract_text_from_content_item(item, content, block_type)
    caption = _extract_caption_from_content_item(item, content)
    html = item.get("table_body") or content.get("table_body") or content.get("html")
    latex = (
        item.get("latex")
        or content.get("math_content")
        or (item.get("text") if block_type == "equation" else None)
    )

    if block_type == "title":
        clean = text.strip()
        if clean:
            level = max(1, min(text_level or 1, 6))
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(clean)
            text_level = level

    is_discarded = block_type in AUXILIARY_BLOCK_TYPES or bool(item.get("is_discarded"))
    return ParsedBlock(
        type=block_type,
        text=text,
        page_idx=page_idx,
        reading_order=reading_order,
        bbox=item.get("bbox"),
        text_level=text_level,
        heading_path=list(heading_stack),
        html=html,
        latex=latex if block_type == "equation" else None,
        caption=caption,
        image_path=item.get("img_path") or content.get("img_path"),
        table_id=item.get("table_id"),
        image_id=item.get("image_id"),
        source=parse_backend,
        is_discarded=is_discarded,
        metadata={
            key: value
            for key, value in item.items()
            if key not in {"content", "text", "bbox", "type"}
        },
    )


def _normalize_content_type(raw_type: str) -> str:
    mapping = {
        "text": "paragraph",
        "title": "title",
        "paragraph": "paragraph",
        "equation_interline": "equation",
        "inline_equation": "equation",
        "interline_equation": "equation",
        "page_header": "header",
        "page_footer": "footer",
    }
    return mapping.get(raw_type, raw_type)


def _extract_text_from_content_item(item: Dict[str, Any], content: Dict[str, Any], block_type: str) -> str:
    for key in ("text", "paragraph", "code_body", "algorithm_content"):
        if item.get(key):
            return _flatten_text(item[key])

    if block_type == "title":
        return _flatten_text(content.get("title_content") or item.get("title"))
    if block_type == "paragraph":
        return _flatten_text(content.get("paragraph_content") or content.get("text") or item.get("content"))
    if block_type == "table":
        return _flatten_text(item.get("table_body") or content.get("table_body") or content.get("content"))
    if block_type == "equation":
        return _flatten_text(content.get("math_content") or item.get("text"))
    if block_type in {"list", "index"}:
        return "\n".join(_flatten_text(v) for v in (item.get("list_items") or content.get("list_items") or []))
    if block_type in AUXILIARY_BLOCK_TYPES:
        aux_key = f"{block_type}_content"
        return _flatten_text(content.get(aux_key) or item.get("text") or item.get("content"))
    return _flatten_text(content or item.get("content"))


def _extract_caption_from_content_item(item: Dict[str, Any], content: Dict[str, Any]) -> Optional[str]:
    for key in ("image_caption", "table_caption", "chart_caption", "code_caption", "algorithm_caption"):
        value = item.get(key) or content.get(key)
        if value:
            return _flatten_text(value)
    return None


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            flattened = _flatten_text(item)
            if flattened:
                parts.append(flattened)
        return " ".join(parts).strip()
    if isinstance(value, dict):
        if "content" in value and isinstance(value.get("content"), str):
            return value["content"].strip()
        parts = []
        for key in ("text", "content", "children"):
            if key in value:
                parts.append(_flatten_text(value[key]))
        return " ".join(part for part in parts if part).strip()
    return str(value).strip()
