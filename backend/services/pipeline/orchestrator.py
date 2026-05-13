"""
Document Ingestion Pipeline - Orchestrator
=============================================

Main entry point for document ingestion using pipeline pattern.
"""

import logging
import os
import uuid
from typing import Optional
from django.apps import apps
from django.conf import settings

from .base import PipelineContext, PipelineOrchestrator
from .stages import (
    ValidationStage,
    ParsingStage,
    ChunkingStage,
    SummarizationStage,
    PersistenceStage
)

logger = logging.getLogger(__name__)


class DocumentIngestPipeline:
    """Orchestrates complete document ingestion pipeline."""
    
    def __init__(self):
        """Initialize pipeline with all stages."""
        self.stages = [
            ValidationStage(name="validation"),
            ParsingStage(name="parsing"),
            ChunkingStage(name="chunking"),
            SummarizationStage(name="summarization"),
            PersistenceStage(name="persistence"),
        ]
        self.orchestrator = PipelineOrchestrator(self.stages)
        self.logger = logging.getLogger("pipeline.document_ingest")

    def execute(
        self,
        file_path: str,
        user_id: str,
        document_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> tuple[bool, PipelineContext]:
        """Execute document ingestion pipeline.
        
        Args:
            file_path: Path to uploaded file
            user_id: User ID performing upload
            document_id: Optional existing document ID to update
            metadata: Optional additional metadata
        
        Returns:
            (success: bool, context: PipelineContext)
        
        Example:
            pipeline = DocumentIngestPipeline()
            success, context = pipeline.execute(
                file_path="/tmp/document.pdf",
                user_id="user123"
            )
            
            if success:
                print(f"Uploaded as document {context.document_id}")
            else:
                print(f"Errors: {context.errors}")
        """
        # Create context
        context = PipelineContext(
            file_path=file_path,
            document_id=document_id or str(uuid.uuid4()),
            user_id=user_id,
            metadata=metadata or {}
        )

        self._ensure_document_exists(context)
        
        self.logger.info(
            f"Starting pipeline: file={file_path}, user={user_id}"
        )
        
        # Execute
        success = self.orchestrator.execute(context)
        
        # Log results
        if success:
            self.logger.info(
                f"Pipeline succeeded. "
                f"Document: {context.document_id}, "
                f"Chunks: {len(context.chunks)}, "
                f"Time: {context.total_time_ms():.0f}ms"
            )
        else:
            self.logger.error(
                f"Pipeline failed. "
                f"Errors: {len(context.errors)}, "
                f"Time: {context.total_time_ms():.0f}ms"
            )
            for error in context.errors:
                self.logger.error(f"  {error['stage']}: {error['error']}")
        
        return success, context

    def _ensure_document_exists(self, context: PipelineContext) -> None:
        """Create the backing Document row early so parsing/chunking stages have a real target."""
        Document = apps.get_model('documents', 'Document')

        if not context.document_id:
            return

        if Document.objects.filter(id=context.document_id).exists():
            return

        file_name = os.path.basename(context.file_path)
        file_extension = context.metadata.get('file_extension', '').lstrip('.')
        file_size = os.path.getsize(context.file_path) if os.path.exists(context.file_path) else 0

        doc = Document.objects.create(
            id=context.document_id,
            filename=file_name,
            original_name=file_name,
            storage_path=context.file_path,
            file_type=file_extension or 'unknown',
            file_size=file_size,
            uploader_id=context.user_id or None,
            metadata=context.metadata,
            embedding_model=context.metadata.get('embedding_model', getattr(settings, 'EMBEDDING_MODEL', 'bge-m3')),
            chunking_strategy=context.metadata.get('strategy', 'token_window'),
            status='processing',
        )
        context.document_id = str(doc.id)

    def get_stage_status(self, stage_name: str) -> Optional[dict]:
        """Get status of a specific stage.
        
        Args:
            stage_name: Name of stage
        
        Returns:
            Stage info or None if not found
        """
        stage = self.orchestrator.get_stage(stage_name)
        if stage:
            return {
                "name": stage.name,
                "type": stage.__class__.__name__
            }
        return None

    def list_stages(self) -> list[dict]:
        """List all pipeline stages.
        
        Returns:
            List of stage info dicts
        """
        return [
            {
                "name": stage.name,
                "type": stage.__class__.__name__
            }
            for stage in self.stages
        ]


__all__ = [
    'DocumentIngestPipeline',
    'PipelineContext',
    'PipelineOrchestrator',
    'ValidationStage',
    'ParsingStage',
    'ChunkingStage',
    'SummarizationStage',
    'PersistenceStage',
]
