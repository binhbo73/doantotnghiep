"""
Excel Chunker v2 - Row + Column Aware
=====================================

Creates one chunk per non-empty physical spreadsheet row and renders each row
with explicit Excel column letters. This keeps row/cell questions like "row 1"
or "A10" deterministic instead of depending on semantic vector search.
"""

import logging
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


class ExcelChunkerV2:
    """Row + column aware Excel chunker."""

    def __init__(self):
        self.strategy_name = "excel_row_column_aware"

    def chunk_excel_file(
        self,
        file_path: str,
        document_id: str,
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parse an Excel file and create one chunk per meaningful physical row.

        Args:
            file_path: Path to Excel file.
            document_id: Document ID.
            metadata: Additional metadata.

        Returns:
            List of row-aware chunks.
        """
        try:
            workbook = load_workbook(file_path, data_only=True)
            chunks: List[Dict[str, Any]] = []

            for sheet_idx, sheet_name in enumerate(workbook.sheetnames):
                worksheet = workbook[sheet_name]
                chunks.extend(
                    self._chunk_worksheet(
                        worksheet=worksheet,
                        sheet_name=sheet_name,
                        sheet_idx=sheet_idx,
                        document_id=document_id,
                        metadata=metadata,
                    )
                )

            logger.info(
                "Excel Chunker v2: %s chunks from %s sheet(s)",
                len(chunks),
                len(workbook.sheetnames),
            )
            return chunks

        except Exception as e:
            logger.error("Excel chunking error: %s", str(e), exc_info=True)
            raise

    def _chunk_worksheet(
        self,
        worksheet,
        sheet_name: str,
        sheet_idx: int,
        document_id: str,
        metadata: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk a worksheet row by row.

        A row is included when at least one cell is non-empty. Row 1 is not
        treated specially because users usually mean the literal Excel row.
        """
        chunks: List[Dict[str, Any]] = []

        all_rows = []
        max_col = worksheet.max_column
        merged_ranges = list(worksheet.merged_cells.ranges)
        for row_idx in range(1, worksheet.max_row + 1):
            row_data = []
            inherited_columns = []
            has_raw_value = False

            for col_idx in range(1, max_col + 1):
                cell_value = worksheet.cell(row=row_idx, column=col_idx).value
                if cell_value is not None and str(cell_value).strip():
                    has_raw_value = True

                if cell_value is None:
                    inherited_value = self._merged_row_value(
                        worksheet=worksheet,
                        merged_ranges=merged_ranges,
                        row_idx=row_idx,
                        col_idx=col_idx,
                    )
                    if inherited_value is not None:
                        cell_value = inherited_value
                        inherited_columns.append(get_column_letter(col_idx))

                row_data.append(cell_value if cell_value is not None else "")

            if row_data and any(str(cell).strip() for cell in row_data):
                all_rows.append(
                    {
                        "index": row_idx,
                        "data": row_data,
                        "has_raw_value": has_raw_value,
                        "inherited_columns": inherited_columns,
                    }
                )

        if not all_rows:
            return chunks

        col_letters = [get_column_letter(i + 1) for i in range(max_col)]
        column_names = {
            col_idx: {"letter": col_letter, "name": col_letter}
            for col_idx, col_letter in enumerate(col_letters)
        }

        logger.info(
            "Sheet '%s': %s columns, %s non-empty rows",
            sheet_name,
            max_col,
            len(all_rows),
        )

        for data_row_idx, row_obj in enumerate(all_rows, start=0):
            row_idx = row_obj["index"]
            row_data = row_obj["data"]
            chunk_text = self._render_row_with_context(
                row_data=row_data,
                row_number=row_idx,
                sheet_name=sheet_name,
                column_names=column_names,
                max_col=max_col,
            )

            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update(
                {
                    "sheet_name": sheet_name,
                    "sheet_idx": sheet_idx,
                    "row_number": row_idx,
                    "row_start": row_idx,
                    "row_end": row_idx,
                    "row_idx": data_row_idx,
                    "column_count": max_col,
                    "column_names": [
                        col_names.get("name", f"Col_{i}")
                        for i, col_names in column_names.items()
                    ],
                    "column_letters": col_letters,
                    "content_format": "spreadsheet_markdown",
                    "chunking_strategy": self.strategy_name,
                    "is_header_inclusive": False,
                    "has_merged_cells": len(worksheet.merged_cells.ranges) > 0,
                    "is_merged_expanded_row": not row_obj.get("has_raw_value", True),
                    "merged_inherited_columns": row_obj.get("inherited_columns", []),
                }
            )

            chunks.append(
                {
                    "text": chunk_text,
                    "page_number": sheet_idx + 1,
                    "metadata": chunk_metadata,
                    "chunk_index": data_row_idx,
                    "node_type": "detail",
                }
            )

        return chunks

    def _merged_row_value(
        self,
        worksheet,
        merged_ranges: List[Any],
        row_idx: int,
        col_idx: int,
    ) -> Any:
        """Return the displayed merged value for row continuations.

        OpenPyXL stores a merged range value only in its top-left cell. For
        row-specific retrieval, continuation rows should still be searchable,
        but horizontal merged cells on the anchor row should not be duplicated
        across every covered column.
        """
        for merged_range in merged_ranges:
            if not (
                merged_range.min_row <= row_idx <= merged_range.max_row
                and merged_range.min_col <= col_idx <= merged_range.max_col
            ):
                continue
            if row_idx <= merged_range.min_row:
                return None
            if col_idx != merged_range.min_col:
                return None
            return worksheet.cell(
                row=merged_range.min_row,
                column=merged_range.min_col,
            ).value
        return None

    def _render_row_with_context(
        self,
        row_data: List[Any],
        row_number: int,
        sheet_name: str,
        column_names: Dict[int, Dict[str, str]],
        max_col: int,
    ) -> str:
        """
        Render a physical Excel row as Markdown.

        The first table uses the exact format expected by SpreadsheetRetriever:

        | Excel row | A | B | C |
        | --- | --- | --- | --- |
        | 9 | value A | value B | value C |
        """
        lines = [f"# Sheet: {sheet_name}, Row {row_number}", ""]

        padded_row = list(row_data)
        while len(padded_row) < max_col:
            padded_row.append("")

        col_letters = [
            column_names.get(col_idx, {}).get("letter", get_column_letter(col_idx + 1))
            for col_idx in range(max_col)
        ]
        row_values = [self._markdown_cell_value(value) for value in padded_row[:max_col]]

        lines.append("| " + " | ".join(["Excel row"] + col_letters) + " |")
        lines.append("| " + " | ".join(["---"] * (max_col + 1)) + " |")
        lines.append("| " + " | ".join([str(row_number)] + row_values) + " |")
        lines.append("")
        lines.append("| Column | Value |")
        lines.append("|---|---|")
        for col_letter, value in zip(col_letters, row_values):
            lines.append(f"| {col_letter} | {value} |")

        lines.append("")
        col_start = get_column_letter(1)
        col_end = get_column_letter(max_col)
        lines.append(f"**Position:** {col_start}{row_number}:{col_end}{row_number}")
        lines.append(f"**Context:** Row {row_number} of table on {sheet_name}")

        return "\n".join(lines)

    def _markdown_cell_value(self, value: Any) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            return "(empty)"
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " / ")
        return text.replace("|", "\\|")

    def _estimate_token_count(self, text: str) -> int:
        """Rough token estimation (1 token ~= 4 chars)."""
        return len(text) // 4


class ExcelTableExtractor:
    """
    Extract structured table data from Excel for RAG results.
    Useful when you want to return actual table structure, not markdown.
    """

    @staticmethod
    def extract_as_structured_table(
        file_path: str,
        sheet_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract Excel as structured table data.

        Returns:
        {
            'sheets': [
                {
                    'name': 'Sheet2',
                    'headers': ['TT', 'Activity', 'Score'],
                    'rows': [
                        {'TT': '3', 'Activity': '...', 'Score': '30'},
                        ...
                    ]
                }
            ]
        }
        """
        workbook = load_workbook(file_path, data_only=True)
        sheets_data = []

        for sheet in workbook.sheetnames:
            if sheet_name and sheet != sheet:
                continue

            worksheet = workbook[sheet]
            rows = []
            headers = None

            for row_idx, row in enumerate(worksheet.iter_rows(values_only=True)):
                row_data = [cell if cell is not None else "" for cell in row]

                while row_data and not row_data[-1]:
                    row_data.pop()

                if row_idx == 0 and row_data:
                    headers = [str(h).strip() for h in row_data]
                elif row_data and any(row_data):
                    row_dict = {}
                    for i, header in enumerate(headers) if headers else []:
                        row_dict[header] = (
                            str(row_data[i]).strip() if i < len(row_data) else ""
                        )
                    rows.append(row_dict)

            sheets_data.append(
                {
                    "name": sheet,
                    "headers": headers or [],
                    "rows": rows,
                }
            )

        return {
            "file": file_path,
            "sheets": sheets_data,
        }
