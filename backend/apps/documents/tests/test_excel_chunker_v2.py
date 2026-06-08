import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from openpyxl import Workbook

from services.document.excel_chunker_v2 import ExcelChunkerV2


@override_settings(RAG_TABLE_CHUNK_MAX_TOKENS=1600)
class ExcelChunkerV2Tests(SimpleTestCase):
    def setUp(self):
        self.chunker = ExcelChunkerV2()

    def test_xlsx_creates_table_and_physical_row_chunks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "kpi.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "KPI"
            sheet.append(["Code", "Metric", "Weight"])
            sheet.append([1, "Revenue", 40])
            workbook.save(path)

            chunks = self.chunker.chunk_excel_file(str(path), "document-id")

        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[0]["metadata"]["table_preserved"])
        self.assertEqual(chunks[2]["metadata"]["row_number"], 2)
        self.assertIn("| 2 | 1 | Revenue | 40 |", chunks[2]["text"])

    def test_csv_uses_row_aware_chunking(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "kpi.csv"
            path.write_text(
                "Code;Metric;Weight\n1;Revenue;40\n",
                encoding="utf-8",
            )

            chunks = self.chunker.chunk_excel_file(str(path), "document-id")

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[1]["metadata"]["row_number"], 1)
        self.assertEqual(chunks[2]["metadata"]["row_number"], 2)
        self.assertEqual(chunks[2]["metadata"]["sheet_name"], "kpi")
        self.assertIn("Revenue", chunks[2]["text"])

    def test_xls_dispatches_to_xlrd_and_expands_vertical_merge(self):
        class FakeSheet:
            name = "Legacy"
            nrows = 3
            ncols = 2
            merged_cells = [(1, 3, 0, 1)]

            values = [
                ["Group", "Value"],
                ["KPI", "Revenue"],
                ["", "Profit"],
            ]

            def cell_value(self, row, col):
                return self.values[row][col]

            def cell_type(self, row, col):
                return 1

        class FakeWorkbook:
            datemode = 0
            nsheets = 1

            def sheets(self):
                return [FakeSheet()]

        with patch("xlrd.open_workbook", return_value=FakeWorkbook()):
            chunks = self.chunker.chunk_excel_file("legacy.xls", "document-id")

        self.assertEqual(len(chunks), 4)
        continuation = chunks[-1]
        self.assertEqual(continuation["metadata"]["row_number"], 3)
        self.assertEqual(continuation["metadata"]["merged_inherited_columns"], ["A"])
        self.assertIn("| 3 | KPI | Profit |", continuation["text"])
