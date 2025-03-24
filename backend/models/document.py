from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Document metadata model containing file properties and analysis results."""
    
    id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the document")
    status: str = Field(..., description="Processing status of the document")
    quality_score: float = Field(0.0, description="Quality score of the generated report")
    edit_count: int = Field(0, description="Number of edits made to the document")
    iterations: int = Field(0, description="Number of AI iterations performed")
    time_saved: int = Field(0, description="Estimated time saved in minutes")
    pages: int = Field(1, description="Number of pages in the document")
    download_count: int = Field(0, description="Number of times the document has been downloaded")
    last_downloaded_at: Optional[datetime] = Field(None, description="Timestamp of last download")
    created_at: datetime = Field(..., description="Timestamp when the document was created")
    updated_at: datetime = Field(..., description="Timestamp when the document was last updated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "1234567890",
                "filename": "Sample Document.pdf",
                "size": 1024000,
                "content_type": "application/pdf",
                "status": "Processed",
                "quality_score": 0.85,
                "edit_count": 2,
                "iterations": 5,
                "time_saved": 15,
                "pages": 10,
                "download_count": 5,
                "last_downloaded_at": "2024-03-24T10:30:00Z",
                "created_at": "2024-03-24T10:00:00Z",
                "updated_at": "2024-03-24T10:30:00Z"
            }
        }

class DocumentMetadataUpdate(BaseModel):
    """
    Model for updating document metadata. All fields are optional.
    """
    filename: Optional[str] = None
    status: Optional[str] = None
    quality_score: Optional[float] = None
    edit_count: Optional[int] = None
    iterations: Optional[int] = None
    time_saved: Optional[int] = None
    pages: Optional[int] = None
    download_count: Optional[int] = None
    last_downloaded_at: Optional[datetime] = None 