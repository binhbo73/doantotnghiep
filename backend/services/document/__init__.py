"""
Document Processing Package
============================
Parse + chunk + embed documents

Services:
- DocumentParser: Extract text from PDF/DOCX
- DocumentChunker: Split text into semantic chunks + generate embeddings
"""

from .parser import DocumentParser
from .chunker import DocumentChunker

__all__ = [
    'DocumentParser',
    'DocumentChunker',
]
