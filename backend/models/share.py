from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ShareLink(BaseModel):
    """Database model for share links."""
    token: str = Field(..., description="Unique token for the share link")
    document_id: str = Field(..., description="ID of the shared document")
    expires_at: datetime = Field(..., description="When the share link expires")
    max_downloads: int = Field(..., description="Maximum number of downloads allowed")
    remaining_downloads: int = Field(..., description="Number of downloads remaining")
    created_at: datetime = Field(..., description="When the share link was created")
    last_downloaded_at: Optional[datetime] = Field(None, description="When the document was last downloaded")

class ShareLinkCreate(BaseModel):
    """Request model for creating a share link."""
    document_id: str = Field(..., description="ID of the document to share")
    expires_in: int = Field(
        default=86400,  # 24 hours
        ge=300,  # minimum 5 minutes
        le=2592000,  # maximum 30 days
        description="How long the share link should be valid for (in seconds)"
    )
    max_downloads: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of times the document can be downloaded"
    )

class ShareLinkResponse(BaseModel):
    """Response model for share link operations."""
    url: str = Field(..., description="Full URL for sharing the document")
    token: str = Field(..., description="Token used in the share URL")
    expires_at: datetime = Field(..., description="When the share link will expire")
    remaining_downloads: int = Field(..., description="Number of downloads remaining")
    document_id: str = Field(..., description="ID of the shared document") 