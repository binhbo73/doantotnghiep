"""
Document Ingestion Pipeline - Base Classes
============================================

Abstract base and utilities for pipeline stage pattern.

Usage:
    pipeline = DocumentIngestPipeline()
    pipeline.execute(file_path="document.pdf", user_id="user123")
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class StageStatus(str, Enum):
    """Stage execution status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class PipelineContext:
    """Context passed through pipeline stages.
    
    Attributes:
        file_path: Path to uploaded file
        document_id: ID of created Document
        user_id: User who uploaded
        metadata: Additional metadata
        errors: List of errors encountered
        stages_executed: List of executed stage names
    """
    
    file_path: str
    document_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, str]] = field(default_factory=list)
    stages_executed: List[str] = field(default_factory=list)
    
    # Intermediate results
    text_content: Optional[str] = None
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: List[Dict[str, Any]] = field(default_factory=list)
    summaries: Dict[str, str] = field(default_factory=dict)  # chunk_id -> summary
    
    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    stage_timings: Dict[str, float] = field(default_factory=dict)  # stage -> ms
    
    def add_error(self, stage: str, error: str, details: Optional[str] = None):
        """Add error to context."""
        self.errors.append({
            "stage": stage,
            "error": error,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        logger.error(f"Stage {stage} error: {error} | {details}")
    
    def add_timing(self, stage: str, duration_ms: float):
        """Record stage execution time."""
        self.stage_timings[stage] = duration_ms
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def total_time_ms(self) -> float:
        """Get total pipeline time."""
        return sum(self.stage_timings.values())


class PipelineStage(ABC):
    """Abstract base class for pipeline stages.
    
    Each stage:
    - Executes a single responsibility
    - Can be rolled back if needed
    - Can optionally skip based on context
    - Updates context in place
    """
    
    def __init__(self, name: Optional[str] = None):
        """Initialize stage.
        
        Args:
            name: Stage name (defaults to class name)
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"pipeline.{self.name}")

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage.
        
        Args:
            context: Pipeline context
        
        Returns:
            Updated context (or same object after modification)
        
        Raises:
            StageExecutionError: If stage fails
        """
        pass

    def rollback(self, context: PipelineContext) -> None:
        """Rollback changes made by this stage.
        
        Args:
            context: Pipeline context
        
        Note:
            Default implementation does nothing.
            Override in subclass if cleanup needed.
        """
        self.logger.info(f"{self.name}: No rollback needed")

    def can_skip(self, context: PipelineContext) -> bool:
        """Check if this stage can be skipped.
        
        Args:
            context: Pipeline context
        
        Returns:
            True if stage can be skipped
        
        Note:
            Override in subclass for conditional stages.
        """
        return False

    def validate_input(self, context: PipelineContext) -> bool:
        """Validate input before executing.
        
        Args:
            context: Pipeline context
        
        Returns:
            True if valid, False otherwise
        
        Note:
            Override in subclass for custom validation.
        """
        return True

    def validate_output(self, context: PipelineContext) -> bool:
        """Validate output after executing.
        
        Args:
            context: Pipeline context
        
        Returns:
            True if valid, False otherwise
        
        Note:
            Override in subclass for custom validation.
        """
        return True


class StageExecutionError(Exception):
    """Exception raised when stage execution fails."""
    pass


class PipelineOrchestrator:
    """Orchestrates document ingestion pipeline.
    
    Executes stages in sequence with rollback on failure.
    """
    
    def __init__(self, stages: List[PipelineStage]):
        """Initialize orchestrator.
        
        Args:
            stages: List of stages to execute in order
        """
        self.stages = stages
        self.logger = logging.getLogger("pipeline.orchestrator")

    def execute(self, context: PipelineContext) -> bool:
        """Execute pipeline.
        
        Args:
            context: Initial pipeline context
        
        Returns:
            True if successful, False if failed
        """
        executed_stages = []
        
        try:
            for stage in self.stages:
                # Check if stage can be skipped
                if stage.can_skip(context):
                    self.logger.info(f"Skipping stage: {stage.name}")
                    continue
                
                # Validate input
                if not stage.validate_input(context):
                    raise StageExecutionError(
                        f"{stage.name}: Input validation failed"
                    )
                
                # Execute stage
                self.logger.info(f"Executing stage: {stage.name}")
                import time
                start = time.time()
                
                context = stage.execute(context)
                
                duration_ms = (time.time() - start) * 1000
                context.add_timing(stage.name, duration_ms)
                context.stages_executed.append(stage.name)
                executed_stages.append(stage)
                
                self.logger.info(
                    f"Stage {stage.name} completed in {duration_ms:.2f}ms"
                )
                
                # Validate output
                if not stage.validate_output(context):
                    raise StageExecutionError(
                        f"{stage.name}: Output validation failed"
                    )
            
            self.logger.info(
                f"Pipeline completed successfully. "
                f"Total time: {context.total_time_ms():.2f}ms"
            )
            return True
        
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            context.add_error("orchestrator", str(e))
            
            # Rollback in reverse order
            self.logger.info(f"Rolling back {len(executed_stages)} stages")
            for stage in reversed(executed_stages):
                try:
                    self.logger.info(f"Rolling back stage: {stage.name}")
                    stage.rollback(context)
                except Exception as rollback_error:
                    self.logger.error(
                        f"Rollback failed for {stage.name}: {rollback_error}",
                        exc_info=True
                    )
                    context.add_error(
                        f"{stage.name}.rollback",
                        str(rollback_error)
                    )
            
            return False

    def get_stage(self, name: str) -> Optional[PipelineStage]:
        """Get stage by name.
        
        Args:
            name: Stage name
        
        Returns:
            Stage instance or None
        """
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None
