from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import UUID4, BaseModel, Field


class ProcessStage(str, Enum):
    """Process stages for report generation workflow."""

    IDLE = "idle"
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    WRITER = "writer"
    REVIEWER = "reviewer"
    REFINEMENT = "refinement"
    FORMATTING = "formatting"
    FINALIZATION = "finalization"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRequest(BaseModel):
    """Request model for creating a new task."""

    stage: ProcessStage = Field(..., description="The initial stage of the task")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata for the task"
    )


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task."""

    stage: Optional[ProcessStage] = Field(
        default=None, description="New stage of the task"
    )
    status: Optional[TaskStatus] = Field(
        default=None, description="New status of the task"
    )
    progress: Optional[float] = Field(
        default=None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    message: Optional[str] = Field(default=None, description="Status message")
    report_id: Optional[str] = Field(
        default=None, description="ID of the generated report"
    )
    estimated_time_remaining: Optional[int] = Field(
        default=None, description="Estimated time remaining in seconds"
    )
    quality: Optional[float] = Field(
        default=None, ge=0, le=100, description="Quality score (0-100)"
    )
    iterations: Optional[int] = Field(
        default=None, ge=0, description="Number of iterations performed"
    )
    can_proceed: Optional[bool] = Field(
        default=None, description="Whether the user can proceed to the next step"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )


class DocumentProcessingResult(BaseModel):
    """Result of document processing task."""

    processed_files: int
    extracted_pages: int
    file_ids: List[str]


class ReportGenerationResult(BaseModel):
    """Result of report generation task."""

    report_id: str
    file_count: int
    word_count: int
    page_count: int


class ReportRefinementResult(BaseModel):
    """Result of report refinement task."""

    report_id: str
    version_id: str
    changes_applied: bool
    refinement_count: int


class ReportExportResult(BaseModel):
    """Result of report export task."""

    report_id: str
    version_id: Optional[str] = None
    format: str
    file_url: str
    file_size: int


class Task(BaseModel):
    """Model representing a long-running task."""

    id: UUID4
    type: str
    status: str  # One of TaskStatus enum values
    stage: ProcessStage
    progress: int = Field(ge=0, le=100)
    message: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    estimated_time_remaining: Optional[int] = None  # seconds

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "type": "report_generation",
                "status": "in_progress",
                "stage": "analysis",
                "progress": 45,
                "message": "Analyzing document content",
                "params": {"file_ids": ["doc1", "doc2"]},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:05:00Z",
                "estimated_time_remaining": 180,
            }
        }


class TaskStatusResponse(BaseModel):
    """Task status response model"""

    task_id: str
    status: str
    progress: Optional[float] = None
    stage: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[int] = None

    class Config:
        orm_mode = True


class TaskList(BaseModel):
    """List of tasks with pagination metadata."""

    tasks: List[Task]
    total: int


class TaskCreate(BaseModel):
    """Model for creating a new task."""

    type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    """Model for updating a task."""

    status: Optional[str] = None  # Should be one of TaskStatus enum values
    stage: Optional[ProcessStage] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[int] = None
