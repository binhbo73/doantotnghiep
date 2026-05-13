from typing import Dict, Optional
from apps.documents.models import Document, DocumentChunk

class Contextualizer:
    """Builds a short contextual prefix for a chunk before embedding/retrieval.

    The goal is to keep this tiny and factual: file title, page, heading, neighbor snippets.
    """

    def __init__(self, max_tokens: int = 128):
        self.max_tokens = max_tokens

    def build_context(self, chunk: DocumentChunk, document: Optional[Document] = None) -> str:
        parts = []
        if document:
            if getattr(document, 'original_name', None):
                parts.append(f"File: {document.original_name}")
            if getattr(document, 'page_count', None):
                parts.append(f"Pages: {document.page_count}")

        # page and chunk location
        if getattr(chunk, 'page_number', None):
            parts.append(f"Page: {chunk.page_number}")
        if getattr(chunk, 'paragraph_index', None):
            parts.append(f"Paragraph: {chunk.paragraph_index}")

        # Try to include a short surrounding snippet (first 120 chars)
        text = (chunk.content or '').strip()
        if text:
            snippet = text.replace('\n', ' ')[:120]
            parts.append(f"Snippet: {snippet}")

        ctx = ' | '.join(parts)
        # Truncate to approx max_tokens characters
        if len(ctx) > self.max_tokens:
            return ctx[: self.max_tokens - 3] + '...'
        return ctx
