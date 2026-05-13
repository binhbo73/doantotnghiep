"""
Page-Aware Document Parser
===========================
Enhances standard parsing with explicit page boundary tracking.

Features:
- Extracts actual page numbers from PDF/DOCX
- Marks page boundaries in text
- Preserves paragraph structure
- Maps text spans to pages

For PDF: Uses PyPDF or pdf2image to extract page count + page breaks
For DOCX: Analyzes section/paragraph structure for logical pages
For Excel: Treats each sheet as a "page"
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PageBoundary:
    """Represents a page boundary marker."""
    def __init__(self, page_number: int, char_start: int, char_end: int = None):
        self.page_number = page_number
        self.char_start = char_start
        self.char_end = char_end
    
    def __repr__(self):
        return f"Page{self.page_number}[{self.char_start}:{self.char_end}]"


class PageAwareText:
    """Text with explicit page mapping."""
    def __init__(self, text: str, boundaries: List[PageBoundary], total_pages: int):
        self.text = text
        self.boundaries = sorted(boundaries, key=lambda b: b.char_start)
        self.total_pages = total_pages

        # Fill end positions so page lookup works reliably.
        for index, boundary in enumerate(self.boundaries):
            next_start = self.boundaries[index + 1].char_start if index + 1 < len(self.boundaries) else len(self.text)
            boundary.char_end = next_start
    
    def get_page_at_position(self, char_pos: int) -> int:
        """Get page number for a character position."""
        for boundary in self.boundaries:
            if boundary.char_start <= char_pos < (boundary.char_end or len(self.text)):
                return boundary.page_number
        return self.total_pages or 1
    
    def get_page_range(self, start_char: int, end_char: int) -> Tuple[int, int]:
        """Get start and end page numbers for a character range."""
        start_page = self.get_page_at_position(start_char)
        end_page = self.get_page_at_position(end_char - 1) if end_char > 0 else start_page
        return start_page, end_page


class PageAwareParserEnhancer:
    """
    Enhances existing parser output with page-aware information.
    
    Usage:
        enhancer = PageAwareParserEnhancer()
        raw_text, metadata = existing_parser.parse_file(path)
        page_aware = enhancer.enhance_pdf(raw_text, path)
        # Now use page_aware.get_page_at_position() for chunks
    """
    
    # PDF page marker (inserted by parse_pdf)
    PAGE_BREAK_MARKER = "\n\n--- [PAGE BREAK] ---\n\n"
    PAGE_BREAK_PATTERN = r"\n\n--- \[PAGE BREAK\] ---\n\n"
    
    def __init__(self):
        pass
    
    def enhance_pdf(self, file_path: str) -> Optional[PageAwareText]:
        """
        Extract page boundaries from PDF.
        
        Returns:
            PageAwareText with page mapping
        """
        try:
            from pypdf import PdfReader  # v5+ has pypdf package, not PyPDF2
            import tempfile
            import shutil
            import opendataloader_pdf
            
            # Get page count first
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
            
            # Parse with opendataloader-pdf
            with tempfile.TemporaryDirectory() as temp_dir:
                opendataloader_pdf.convert(
                    input_path=[file_path],
                    output_dir=temp_dir,
                    format="markdown-with-images",
                    image_output="embedded",
                    image_format="png"
                )
                
                base_name = Path(file_path).stem
                md_file = Path(temp_dir) / f"{base_name}.md"
                
                if not md_file.exists():
                    logger.warning(f"No markdown output for {file_path}")
                    return None
                
                with open(md_file, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            # Insert page markers after parsing
            # Since opendataloader-pdf doesn't preserve page info in markdown,
            # we'll estimate based on text length per page
            text_with_markers = self._insert_page_markers(text, total_pages)
            boundaries = self._extract_boundaries(text_with_markers)
            
            return PageAwareText(text_with_markers, boundaries, total_pages)
        
        except Exception as e:
            logger.error(f"Error in PDF page-aware parsing: {str(e)}")
            return None
    
    def enhance_docx(self, file_path: str) -> Optional[PageAwareText]:
        """
        Extract page boundaries from DOCX with improved detection.
        """
        try:
            from docx import Document as DocxDoc
            
            docx = DocxDoc(file_path)
            
            text_parts = []
            page_num = 1
            boundaries = [PageBoundary(1, 0)] # Start with page 1
            char_pos = 0
            
            for para in docx.paragraphs:
                # 1. Check for page break in this paragraph
                if self._has_page_break(para):
                    page_num += 1
                    text_parts.append(self.PAGE_BREAK_MARKER)
                    char_pos += len(self.PAGE_BREAK_MARKER)
                    boundaries.append(PageBoundary(page_num, char_pos))
                
                para_text = para.text + "\n"
                text_parts.append(para_text)
                char_pos += len(para_text)
            
            # Handle tables
            for table in docx.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_parts.append(cell.text + " ")
                        char_pos += len(cell.text) + 1
                    text_parts.append("\n")
                    char_pos += 1
            
            full_text = "".join(text_parts)
            
            # 2. FALLBACK: If document is long but no page breaks were found
            # Word pages are roughly 3000 characters. 
            if page_num == 1 and len(full_text) > 3500:
                logger.info(f"DOCX has no explicit breaks but is long ({len(full_text)} chars). Using logical page estimation.")
                return self._estimate_logical_pages(full_text)
            
            return PageAwareText(full_text, boundaries, page_num)
        
        except Exception as e:
            logger.error(f"Error in DOCX page-aware parsing: {str(e)}")
            return None

    def _estimate_logical_pages(self, text: str, chars_per_page: int = 3000) -> PageAwareText:
        """Fallback to estimate pages based on character count for documents without markers."""
        total_pages = max(1, (len(text) + chars_per_page - 1) // chars_per_page)
        boundaries = []
        
        # We'll try to find paragraph breaks near the 3000-char intervals
        current_pos = 0
        for p in range(1, total_pages + 1):
            boundaries.append(PageBoundary(p, current_pos))
            
            target_next = p * chars_per_page
            if target_next >= len(text):
                break
            
            # Find nearest newline to make a clean break
            next_break = text.find('\n', target_next)
            if next_break != -1 and next_break - target_next < 500:
                current_pos = next_break + 1
            else:
                current_pos = target_next

        return PageAwareText(text, boundaries, total_pages)
    
    def enhance_excel(self, file_path: str) -> Optional[PageAwareText]:
        """
        Extract page boundaries from Excel.
        
        Each sheet is treated as a page.
        """
        try:
            import openpyxl
            
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            
            text_parts = []
            page_num = 1
            boundaries = []
            char_pos = 0
            
            for sheet in workbook.sheetnames:
                ws = workbook[sheet]
                
                # Add sheet header
                sheet_header = f"\n--- Sheet: {sheet} (Page {page_num}) ---\n\n"
                text_parts.append(sheet_header)
                boundaries.append(PageBoundary(page_num, char_pos))
                char_pos += len(sheet_header)
                
                # Extract cell values
                for row in ws.iter_rows(values_only=True):
                    row_text = " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                    text_parts.append(row_text)
                    char_pos += len(row_text)
                
                page_num += 1
            
            text = "".join(text_parts)
            
            return PageAwareText(text, boundaries, page_num - 1)
        
        except Exception as e:
            logger.error(f"Error in Excel page-aware parsing: {str(e)}")
            return None
    
    def enhance_text(self, file_path: str) -> Optional[PageAwareText]:
        """
        For plain text: estimate pages based on content length.
        Assume ~2000 chars per page (typical).
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Estimate pages
            chars_per_page = 2000
            total_pages = max(1, (len(text) + chars_per_page - 1) // chars_per_page)
            
            # Create boundaries
            boundaries = []
            for page in range(1, total_pages + 1):
                start_char = (page - 1) * chars_per_page
                boundaries.append(PageBoundary(page, start_char))
            
            return PageAwareText(text, boundaries, total_pages)
        
        except Exception as e:
            logger.error(f"Error in text page-aware parsing: {str(e)}")
            return None

    def enhance_csv(self, file_path: str, rows_per_page: int = 100) -> Optional[PageAwareText]:
        """Treat CSV as paged row groups so the chunker can keep page-like locality."""
        try:
            import csv

            text_parts = []
            boundaries = []
            char_pos = 0
            page_num = 1

            with open(file_path, 'r', encoding='utf-8-sig', newline='') as csv_file:
                reader = csv.reader(csv_file)
                for row_index, row in enumerate(reader):
                    if row_index % rows_per_page == 0:
                        boundaries.append(PageBoundary(page_num, char_pos))
                        text_parts.append(f"\n--- CSV Page {page_num} ---\n")
                        char_pos += len(text_parts[-1])
                        page_num += 1

                    row_text = " | ".join(cell.strip() for cell in row) + "\n"
                    text_parts.append(row_text)
                    char_pos += len(row_text)

            text = "".join(text_parts)
            total_pages = max(1, page_num - 1)
            return PageAwareText(text, boundaries, total_pages)
        except Exception as e:
            logger.error(f"Error in CSV page-aware parsing: {str(e)}")
            return None
    
    def _insert_page_markers(self, text: str, total_pages: int) -> str:
        """
        Heuristically insert page markers into parsed text.
        
        Strategy: Estimate page boundaries based on text length
        """
        if total_pages <= 1:
            return text
        
        chars_per_page = len(text) // total_pages
        markers = []
        
        for page in range(1, total_pages):
            # Find good break point (paragraph, sentence, or exact position)
            target_pos = page * chars_per_page
            break_pos = self._find_good_break_point(text, target_pos)
            markers.append((break_pos, page))
        
        # Insert markers in reverse order to maintain positions
        result = text
        for pos, page in sorted(markers, reverse=True):
            result = result[:pos] + self.PAGE_BREAK_MARKER + result[pos:]
        
        return result
    
    def _find_good_break_point(self, text: str, target_pos: int, window: int = 200) -> int:
        """Find a good place to break (paragraph or sentence)."""
        start = max(0, target_pos - window)
        end = min(len(text), target_pos + window)
        
        segment = text[start:end]
        
        # Look for paragraph break first (double newline)
        para_break = segment.rfind('\n\n')
        if para_break != -1:
            return start + para_break
        
        # Look for sentence end (period followed by space)
        sentence_ends = [m.end() for m in re.finditer(r'\.\s', segment)]
        if sentence_ends:
            closest = min(sentence_ends, key=lambda x: abs(x - (target_pos - start)))
            return start + closest
        
        # Fallback to target position
        return target_pos
    
    def _extract_boundaries(self, text: str) -> List[PageBoundary]:
        """Extract page boundaries from text with markers."""
        boundaries = []
        page_num = 1
        
        for match in re.finditer(self.PAGE_BREAK_PATTERN, text):
            boundaries.append(PageBoundary(page_num, match.start()))
            page_num += 1
        
        # Always start with page 1
        if not boundaries or boundaries[0].page_number != 1:
            boundaries.insert(0, PageBoundary(1, 0))
        
        return sorted(boundaries, key=lambda b: b.char_start)
    
    def _has_page_break(self, paragraph) -> bool:
        """
        Check if paragraph has a page break (manual or rendered).
        
        Detection logic:
        1. Explicit pageBreakBefore in paragraph properties
        2. <w:br w:type="page"/> in any run
        3. <w:lastRenderedPageBreak/> in any run (inserted by Word when paginating)
        """
        try:
            # 1. Check paragraph properties for "Page Break Before"
            if paragraph._element.pPr is not None:
                pPr = paragraph._element.pPr
                # Looking for <w:pageBreakBefore/>
                if pPr.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pageBreakBefore') is not None:
                    return True

            # 2. Check each run for break elements
            for run in paragraph.runs:
                # Check for <w:br w:type="page"/> (Manual page break)
                if 'lastRenderedPageBreak' in run._element.xml or 'w:br' in run._element.xml:
                    if run._element.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}lastRenderedPageBreak') is not None:
                        return True
                    
                    brs = run._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')
                    for br in brs:
                        if br.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type') == 'page':
                            return True
            return False
        except Exception:
            return False
