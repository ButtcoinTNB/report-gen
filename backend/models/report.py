from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Model for creating a new report."""

    file_ids: List[str] = Field(..., description="List of file IDs to process")
    title: Optional[str] = Field(None, description="Optional report title")
    template_id: Optional[str] = Field(None, description="Optional template ID to use")
    options: Optional[Dict[str, Any]] = Field(
        None, description="Optional report generation options"
    )


class Report(BaseModel):
    """Model for a completed report."""

    id: str = Field(..., description="Unique report ID")
    title: str = Field(..., description="Report title")
    status: str = Field(..., description="Report status")
    file_ids: List[str] = Field(..., description="List of file IDs processed")
    quality_score: float = Field(..., description="Quality score of the report")
    iterations: int = Field(..., description="Number of iterations performed")
    time_saved: int = Field(..., description="Estimated time saved in minutes")
    created_at: datetime = Field(..., description="When the report was created")
    updated_at: datetime = Field(..., description="When the report was last updated")
    completed_at: Optional[datetime] = Field(
        None, description="When the report was completed"
    )
    download_url: Optional[str] = Field(None, description="URL to download the report")
    current_version: Optional[int] = Field(None, description="Current version number")


class ReportStatus(BaseModel):
    """Model for report status updates."""

    report_id: str = Field(..., description="Report ID")
    status: str = Field(..., description="Current status")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    time_remaining: Optional[int] = Field(
        None, description="Estimated time remaining in seconds"
    )
    quality_score: Optional[float] = Field(None, description="Current quality score")


class ReportUpdate(BaseModel):
    """Model for updating a report"""

    title: Optional[str] = None
    content: Optional[str] = None
    is_finalized: Optional[bool] = None
    current_version: Optional[int] = None


class ReportVersion(BaseModel):
    """Model for tracking report versions"""

    id: UUID
    report_id: UUID
    version_number: int
    content: str
    created_by: Optional[UUID] = None
    changes_description: Optional[str] = None


class ReportVersionCreate(BaseModel):
    """Model for creating a new report version"""

    report_id: UUID
    version_number: int
    content: str
    changes_description: Optional[str] = None
    created_by: Optional[UUID] = None


class ReportVersionResponse(BaseModel):
    """Response model for report version endpoints"""

    versions: List[ReportVersion]
    current_version: int
