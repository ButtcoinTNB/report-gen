from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, UUID4, Field, EmailStr


class User(BaseModel):
    """Model representing a user."""

    id: UUID4 = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., description="User's full name")
    is_active: bool = Field(default=True, description="Whether the user is active")
    is_admin: bool = Field(default=False, description="Whether the user is an admin")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), description="Last update timestamp")

    class Config:
        from_attributes = True 