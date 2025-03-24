from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ReportCreate(BaseModel):
    """Model for creating a new report."""
    file_ids: List[str] = Field(..., description="List of file IDs to process")
    title: Optional[str] = Field(None, description="Optional report title")
    template_id: Optional[str] = Field(None, description="Optional template ID to use")
    options: Optional[Dict[str, Any]] = Field(None, description="Optional report generation options")

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
    completed_at: Optional[datetime] = Field(None, description="When the report was completed")
    download_url: Optional[str] = Field(None, description="URL to download the report")

class ReportStatus(BaseModel):
    """Model for report status updates."""
    report_id: str = Field(..., description="Report ID")
    status: str = Field(..., description="Current status")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    time_remaining: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    quality_score: Optional[float] = Field(None, description="Current quality score") 