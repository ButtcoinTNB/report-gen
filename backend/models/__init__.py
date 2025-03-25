"""
Models package for the Insurance Report Generator.
"""

from .document import DocumentMetadata, DocumentMetadataUpdate
from .report import (
    Report,
    ReportUpdate,
    ReportVersion,
    ReportVersionCreate,
    ReportVersionResponse,
)
from .share import ShareLink, ShareLinkResponse
from .template import Template, TemplateCreate, TemplateUpdate
from .user import User

__all__ = [
    "DocumentMetadata",
    "DocumentMetadataUpdate",
    "Report",
    "ReportUpdate",
    "ReportVersion",
    "ReportVersionCreate",
    "ReportVersionResponse",
    "ShareLink",
    "ShareLinkResponse",
    "Template",
    "TemplateCreate",
    "TemplateUpdate",
    "User",
]
