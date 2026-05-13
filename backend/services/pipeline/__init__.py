"""
Pipeline Package - Document Ingestion Pipeline Pattern

Provides a modular, testable, and maintainable approach to document processing.

Modules:
    - base: Abstract base classes and orchestrator
    - stages: Individual processing stages
    - orchestrator: Main entry point
"""

from .base import (
    PipelineStage,
    PipelineContext,
    PipelineOrchestrator,
    StageExecutionError,
    StageStatus,
)

from .stages import (
    ValidationStage,
    ParsingStage,
    ChunkingStage,
    SummarizationStage,
    PersistenceStage,
)

from .orchestrator import DocumentIngestPipeline

__all__ = [
    # Base classes
    'PipelineStage',
    'PipelineContext',
    'PipelineOrchestrator',
    'StageExecutionError',
    'StageStatus',
    # Stages
    'ValidationStage',
    'ParsingStage',
    'ChunkingStage',
    'SummarizationStage',
    'PersistenceStage',
    # Main orchestrator
    'DocumentIngestPipeline',
]

__version__ = '1.0.0'
