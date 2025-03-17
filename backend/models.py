from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from typing import Dict, Optional
from pydantic import BaseModel
import datetime

Base = declarative_base()


# Database Models
class TemplateDB(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    file_path = Column(String)  # Path in Supabase Storage
    meta_data = Column(JSON)  # Format metadata (headers, footers, fonts, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReportDB(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True)  # Add UUID field
    template_id = Column(Integer, ForeignKey("templates.id"))
    title = Column(String, index=True)
    content = Column(Text)
    formatted_file_path = Column(
        String, nullable=True
    )  # Path in Supabase Storage
    meta_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_finalized = Column(Boolean, default=False)


# Pydantic Models for API
class FormatMetadata(BaseModel):
    header: Optional[str] = None
    footer: Optional[str] = None
    fonts: Dict[str, str] = {}
    margins: Dict[str, int] = {}
    logo_path: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    meta_data: Optional[FormatMetadata] = None


class Template(TemplateCreate):
    id: int
    file_path: str
    created_at: datetime.datetime

    class Config:
        orm_mode = True


class ReportCreate(BaseModel):
    template_id: int
    title: str
    content: str


class Report(ReportCreate):
    id: int
    formatted_file_path: Optional[str] = None
    meta_data: Optional[Dict] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    is_finalized: bool = False

    class Config:
        orm_mode = True


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_finalized: Optional[bool] = None
