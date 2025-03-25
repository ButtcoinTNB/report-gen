from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, UUID4, Field


class Template(BaseModel):
    """Model representing a report template."""

    template_id: UUID4 = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Template name")
    version: str = Field(default="1.0", description="Template version")
    content: str = Field(default="", description="Template content")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="Template metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), description="Last update timestamp")
    created_by: Optional[UUID4] = Field(None, description="User ID who created the template")
    is_active: bool = Field(default=True, description="Whether the template is active")

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    """Model for creating a new template."""

    name: str = Field(..., description="Template name")
    version: str = Field(default="1.0", description="Template version")
    content: str = Field(default="", description="Template content")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="Template metadata")


class TemplateUpdate(BaseModel):
    """Model for updating an existing template."""

    name: Optional[str] = Field(None, description="Template name")
    version: Optional[str] = Field(None, description="Template version")
    content: Optional[str] = Field(None, description="Template content")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Template metadata")
    is_active: Optional[bool] = Field(None, description="Whether the template is active") 