"""
Share link models for the Insurance Report Generator.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ShareLink(BaseModel):
    """Share link model for database records"""

    token: str
    document_id: str
    expires_at: datetime
    max_downloads: int
    remaining_downloads: int
    created_at: datetime
    last_downloaded_at: Optional[datetime] = None


class ShareLinkCreate(BaseModel):
    """Request model for creating a share link."""

    document_id: str = Field(..., description="ID of the document to share")
    expires_in: int = Field(
        default=86400,  # 24 hours
        ge=300,  # minimum 5 minutes
        le=2592000,  # maximum 30 days
        description="How long the share link should be valid for (in seconds)",
    )
    max_downloads: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of times the document can be downloaded",
    )


class ShareLinkResponse(BaseModel):
    """Share link response model for API responses"""

    url: str
    token: str
    expires_at: datetime
    remaining_downloads: int
    document_id: str
