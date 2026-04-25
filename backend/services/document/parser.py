"""
Document Parser
===============
Extract text from documents (PDF, DOCX, TXT, Markdown)

Features:
- PDF parsing via docling
- DOCX parsing via docling
- Text file parsing
- Markdown parsing
- Metadata extraction
- Error handling

Configuration (from settings.py):
    DOCLING_MAX_FILE_SIZE_MB = 100
    DOCLING_TIMEOUT = 60

Usage:
    parser = DocumentParser()
    
    # Parse from file
    text, metadata = parser.parse_file('/path/to/document.pdf')
    
    # Parse PDF
    pdf_text = parser.parse_pdf(file_path)
    
    # Parse DOCX
    docx_text = parser.parse_docx(file_path)
"""

import logging
import os
import mimetypes
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from django.conf import settings
from core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Document parser - extracts text from various formats
    
    Supported formats:
    - PDF (.pdf)
    - DOCX (.docx, .doc)
    - TXT (.txt)
    - Markdown (.md)
    """
    
    SUPPORTED_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/msword',  # .doc
        'text/plain',
        'text/markdown',
    }
    
    def __init__(
        self,
        max_file_size_mb: int = None,
        timeout: int = None,
    ):
        """
        Initialize parser
        
        Args:
            max_file_size_mb: Max file size in MB (default from settings)
            timeout: Processing timeout in seconds (default 60)
        """
        self.max_file_size_mb = max_file_size_mb or getattr(
            settings, 'DOCLING_MAX_FILE_SIZE_MB', 100
        )
        self.timeout = timeout or getattr(settings, 'DOCLING_TIMEOUT', 60)
        
        logger.info(f"DocumentParser initialized: max_size={self.max_file_size_mb}MB")
    
    # ============================================================================
    # MAIN PARSING METHOD
    # ============================================================================
    
    def parse_file(self, file_path: str, file_type: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Parse document file and extract text + metadata
        
        Args:
            file_path: Path to document file
            file_type: Optional MIME type. If not provided, will guess from extension.
        
        Returns:
            (text, metadata) tuple
            metadata: {
                'title': str,
                'pages': int,
                'word_count': int,
                'file_type': str,
                'language': str,
            }
        
        Raises:
            DocumentProcessingError: If parsing fails
        
        Example:
            text, meta = parser.parse_file('/uploads/research.pdf')
            print(f"Extracted {meta['word_count']} words from {meta['pages']} pages")
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise DocumentProcessingError(f"File not found: {file_path}")
            
            # Validate file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                raise DocumentProcessingError(
                    f"File too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB"
                )
            
            # Get file type if not provided
            if not file_type:
                file_type = mimetypes.guess_type(file_path)[0] or 'unknown'
            
            # Parse based on type
            if file_type == 'application/pdf':
                text = self.parse_pdf(file_path)
            elif file_type in ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'):
                text = self.parse_docx(file_path)
            elif file_type in ('text/plain', 'text/markdown'):
                text = self.parse_text(file_path)
            else:
                raise DocumentProcessingError(f"Unsupported file type: {file_type}")
            
            # Extract metadata
            metadata = self._extract_metadata(text, file_path, file_type)
            
            logger.info(
                f"Parsed {file_path}: {len(text)} chars, "
                f"{metadata['word_count']} words, {metadata['pages']} pages"
            )
            
            return text, metadata
        
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to parse file: {str(e)}")
    
    # ============================================================================
    # FORMAT-SPECIFIC PARSERS
    # ============================================================================
    
    def parse_pdf(self, file_path: str) -> str:
        """
        Parse PDF file and extract text
        
        Uses docling library for robust PDF parsing
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Extracted text
        
        Raises:
            DocumentProcessingError: If parsing fails
        """
        try:
            from docling.document_converter import DocumentConverter
            
            logger.debug(f"Parsing PDF: {file_path}")
            
            # Convert PDF to document
            converter = DocumentConverter()
            result = converter.convert(file_path)
            
            # Extract text
            text = result.document.export_to_markdown()
            
            logger.debug(f"PDF parsing completed: {len(text)} chars")
            return text
        
        except ImportError:
            raise DocumentProcessingError("docling library not installed. Install: pip install docling")
        except Exception as e:
            logger.error(f"PDF parsing error: {str(e)}", exc_info=True)
            raise DocumentProcessingError(f"Failed to parse PDF: {str(e)}")
    
    def parse_docx(self, file_path: str) -> str:
        """
        Parse DOCX file and extract text
        
        Uses docling for consistent parsing
        
        Args:
            file_path: Path to DOCX file
        
        Returns:
            Extracted text
        """
        try:
            from docling.document_converter import DocumentConverter
            
            logger.debug(f"Parsing DOCX: {file_path}")
            
            converter = DocumentConverter()
            result = converter.convert(file_path)
            
            text = result.document.export_to_markdown()
            
            logger.debug(f"DOCX parsing completed: {len(text)} chars")
            return text
        
        except ImportError:
            raise DocumentProcessingError("docling library not installed")
        except Exception as e:
            logger.error(f"DOCX parsing error: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse DOCX: {str(e)}")
    
    def parse_text(self, file_path: str) -> str:
        """
        Parse plain text / markdown file
        
        Args:
            file_path: Path to text file
        
        Returns:
            File content
        """
        try:
            logger.debug(f"Parsing text file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            logger.debug(f"Text parsing completed: {len(text)} chars")
            return text
        
        except Exception as e:
            logger.error(f"Text parsing error: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse text file: {str(e)}")
    
    # ============================================================================
    # METADATA EXTRACTION
    # ============================================================================
    
    def _extract_metadata(
        self,
        text: str,
        file_path: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from parsed text
        
        Args:
            text: Extracted text
            file_path: Original file path
            file_type: MIME type
        
        Returns:
            Metadata dict
        """
        try:
            # Count words + lines
            lines = text.split('\n')
            words = text.split()
            
            # Estimate pages (avg 300 words per page)
            pages = max(1, len(words) // 300)
            
            # Get filename as potential title
            filename = Path(file_path).stem
            
            metadata = {
                'title': filename,
                'pages': pages,
                'word_count': len(words),
                'char_count': len(text),
                'line_count': len(lines),
                'file_type': file_type,
                'language': 'unknown',  # Could add language detection
            }
            
            logger.debug(f"Metadata extracted: {metadata}")
            return metadata
        
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
            return {
                'title': 'Unknown',
                'pages': 0,
                'word_count': 0,
                'char_count': len(text),
                'line_count': 0,
                'file_type': file_type,
                'language': 'unknown',
            }
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    @staticmethod
    def is_supported_type(file_type: str) -> bool:
        """Check if file type is supported"""
        return file_type in DocumentParser.SUPPORTED_TYPES
    
    @staticmethod
    def get_supported_types() -> set:
        """Get set of supported MIME types"""
        return DocumentParser.SUPPORTED_TYPES.copy()
