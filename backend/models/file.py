from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    """Model representing a file record in the database."""
    id: UUID = Field(..., description="Internal database ID")
    file_id: UUID = Field(..., description="Public file ID")
    report_id: Optional[UUID] = Field(None, description="Associated report ID")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to file in storage")
    file_type: str = Field(..., description="File extension/type")
    mime_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    content: Optional[str] = Field(None, description="Extracted text content")
    status: str = Field("uploaded", description="File processing status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class FileUpdate(BaseModel):
    """Model for updating a file record."""
    report_id: Optional[UUID] = None
    status: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 