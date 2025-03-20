from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, TypeVar, Generic, Any, Dict, Union
from pydantic.generics import GenericModel

# Define a generic type variable for the response data
T = TypeVar('T')

class APIResponse(GenericModel, Generic[T]):
    """Standard API response wrapper"""
    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None
    code: Optional[str] = None

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
    """Response model for query upload endpoint"""
    upload_id: str

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