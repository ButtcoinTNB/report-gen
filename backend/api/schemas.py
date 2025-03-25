"""
API schemas for request and response validation.

This module contains Pydantic models for validating API requests and responses.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

# Import core types
from core.types import DataResponse, ErrorResponse

# Generic type variable for data
T = TypeVar('T')

# Re-export core types for backward compatibility
APIResponse = DataResponse

class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)


class DocumentMetadata(BaseModel):
    """Document metadata schema"""
    id: str
    filename: str
    size: int
    content_type: str
    upload_date: datetime
    user_id: Optional[str] = None
    status: str = "pending"


class ReportRequest(BaseModel):
    """Report generation request schema"""
    document_id: str
    title: Optional[str] = None
    template_id: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class ReportMetadata(BaseModel):
    """Report metadata schema"""
    id: str
    title: str
    document_id: str
    created_at: datetime
    updated_at: datetime
    status: str
    progress: Optional[float] = None
    user_id: Optional[str] = None
    template_id: Optional[str] = None
    

class ReportContent(BaseModel):
    """Report content schema"""
    id: str
    metadata: ReportMetadata
    content: Dict[str, Any]
    document_url: Optional[str] = None


class UserProfile(BaseModel):
    """User profile schema"""
    id: str
    email: str
    name: Optional[str] = None
    created_at: datetime
    settings: Dict[str, Any] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    """Document upload response schema"""
    document_id: str
    upload_url: str
    expires_at: datetime


class TaskStatus(BaseModel):
    """Task status schema"""
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_more: bool


class AdditionalInfoRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: str
    template_id: Optional[UUID4] = None


class GenerateReportRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: Optional[str] = ""
    template_id: Optional[UUID4] = None


class ReportFileResponse(BaseModel):
    """Response model for report file information"""

    file_path: str
    file_exists: bool
    content_type: str


class UploadQueryResult(BaseModel):
    """
    Response model for upload query endpoint

    This model represents the result of querying uploads
    """

    upload_id: str = Field(..., description="Upload identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Upload status")
    progress: float = Field(..., description="Upload progress 0-100")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        """Configuration for the UploadQueryResult model"""

        schema_extra = {
            "example": {
                "upload_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "example.pdf",
                "status": "in_progress",
                "progress": 42.5,
                "created_at": "2023-04-01T12:34:56Z",
            }
        }


class DocxReportResponse(BaseModel):
    """Response model for DOCX report download endpoint"""

    report_id: str
    docx_path: str


class DocxFileResponse(BaseModel):
    """Response model for serving DOCX file endpoint"""

    file_path: str
    content_type: str = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


class ServeReportFileResponse(BaseModel):
    """Response model for serving generic report file endpoint"""

    file_path: str


class DownloadReportResponse(BaseModel):
    """Response model for generic report download endpoint"""

    file_path: str


class RefineReportResponse(BaseModel):
    """Response model for report refinement endpoint"""

    report_id: str
    content: str


class SimpleTestResponse(BaseModel):
    """Response model for simple test endpoint"""

    message: str


class GenerateDocxResponse(BaseModel):
    """Response model for DOCX report generation endpoint"""

    docx_path: str
    download_url: str


class GenerateFromIdResponse(BaseModel):
    """Response model for generating report from ID endpoint"""

    report_id: str
    content: str
    status: str


class GenerateReportResponse(BaseModel):
    """Response model for report creation endpoint"""

    report_id: str


class GenerateContentResponse(BaseModel):
    """Response model for report content generation endpoint"""

    report_id: str
    content: str
    status: str


class PreviewFileResponse(BaseModel):
    file_path: str
    file_exists: bool
    content_type: str


class PreviewFileGenerationResponse(BaseModel):
    preview_id: str


class UpdateReportResponse(BaseModel):
    report_id: str
    title: str
    content: str
    is_finalized: bool
    updated_at: str


class AIRefineResponse(BaseModel):
    report_id: str
    content: str
    updated_at: str
