from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, TypeVar, Generic, Any, Dict, Union
from pydantic.generics import GenericModel

# Define a generic type variable for the response data
T = TypeVar('T')

class APIResponse(GenericModel, Generic[T]):
    """
    Standard API response format for all endpoints
    
    Properties:
        status: Success or error
        data: Response data (only for success)
        message: Human-readable message (required for errors)
        code: Error code (only for errors)
        details: Additional error details
    """
    status: str = Field(
        default="success", 
        description="Response status (success or error)"
    )
    data: Optional[T] = Field(
        default=None, 
        description="Response data for successful operations"
    )
    message: Optional[str] = Field(
        default=None, 
        description="Human-readable message, usually for errors"
    )
    code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details, usually for errors"
    )
    
    class Config:
        """Configuration for the APIResponse model"""
        schema_extra = {
            "example": {
                "status": "success",
                "data": {"id": "123", "name": "Example"}
            }
        }

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
                "created_at": "2023-04-01T12:34:56Z"
            }
        }

class DocxReportResponse(BaseModel):
    """Response model for DOCX report download endpoint"""
    report_id: str
    docx_path: str

class DocxFileResponse(BaseModel):
    """Response model for serving DOCX file endpoint"""
    file_path: str
    content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

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