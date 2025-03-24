from typing import Any, Dict, List, Optional

from pydantic import UUID4, BaseModel


# Pydantic Models for API and Supabase
class SupabaseModel(BaseModel):
    """Base model for Supabase tables"""

    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_deleted: bool = False

    class Config:
        orm_mode = True


class User(SupabaseModel):
    """User model for the 'users' table in Supabase"""

    user_id: UUID4
    email: str
    username: str
    hashed_password: Optional[str] = None
    is_active: bool = True


class File(SupabaseModel):
    """File model for the 'files' table in Supabase"""

    file_id: UUID4
    report_id: UUID4
    filename: str
    file_path: str
    file_type: str
    content: Optional[str] = None
    file_size: int
    mime_type: Optional[str] = None
    user_id: Optional[UUID4] = None


class FormatMetadata(BaseModel):
    """Format metadata for templates"""

    header: Optional[str] = None
    footer: Optional[str] = None
    fonts: Dict[str, str] = {}
    margins: Dict[str, int] = {}
    logo_path: Optional[str] = None


class Template(SupabaseModel):
    """Template model for the 'templates' table in Supabase"""

    template_id: UUID4
    name: str
    content: str
    version: str
    file_path: Optional[str] = None
    meta_data: Optional[FormatMetadata] = None
    user_id: Optional[UUID4] = None


class Report(SupabaseModel):
    """Report model for the 'reports' table in Supabase"""

    report_id: UUID4
    title: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    is_finalized: bool = False
    files_cleaned: bool = False
    template_id: Optional[UUID4] = None
    user_id: Optional[UUID4] = None
    current_version: int = 1


class ReportUpdate(BaseModel):
    """Model for updating a report"""

    title: Optional[str] = None
    content: Optional[str] = None
    is_finalized: Optional[bool] = None
    current_version: Optional[int] = None


class ReportCreate(BaseModel):
    """Model for creating a new report"""

    title: Optional[str] = None
    content: Optional[str] = None
    template_id: Optional[UUID4] = None
    user_id: Optional[UUID4] = None


class ReportVersion(SupabaseModel):
    """Model for tracking report versions"""

    id: UUID4
    report_id: UUID4
    version_number: int
    content: str
    created_by: Optional[UUID4] = None
    changes_description: Optional[str] = None


class ReportVersionCreate(BaseModel):
    """Model for creating a new report version"""

    report_id: UUID4
    version_number: int
    content: str
    changes_description: Optional[str] = None
    created_by: Optional[UUID4] = None


class ReportVersionResponse(BaseModel):
    """Response model for report version endpoints"""

    versions: List[ReportVersion]
    current_version: int


class FileCreate(BaseModel):
    """Model for creating a new file"""

    filename: str
    file_type: str
    content: Optional[str] = None
    file_size: int
    mime_type: Optional[str] = None
    report_id: Optional[UUID4] = None
    user_id: Optional[UUID4] = None


class TemplateCreate(BaseModel):
    """Model for creating a new template"""

    name: str
    content: str
    version: str
    file_path: Optional[str] = None
    meta_data: Optional[FormatMetadata] = None
    user_id: Optional[UUID4] = None


class ReferenceReport(SupabaseModel):
    """Reference report model for the 'reference_reports' table in Supabase"""

    reference_id: UUID4
    title: str
    content: str
    category: str
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    public_url: Optional[str] = None
    user_id: Optional[UUID4] = None


class ReferenceReportCreate(BaseModel):
    """Model for creating a new reference report"""

    title: str
    content: str
    category: str
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[UUID4] = None


# Helper functions for converting between Supabase rows and Pydantic models
def supabase_to_pydantic(table_name: str, row: Dict[str, Any]) -> SupabaseModel:
    """Convert a Supabase row to a Pydantic model"""
    if table_name == "users":
        return User(**row)
    elif table_name == "files":
        return File(**row)
    elif table_name == "templates":
        return Template(**row)
    elif table_name == "reports":
        return Report(**row)
    elif table_name == "reference_reports":
        return ReferenceReport(**row)
    elif table_name == "report_versions":
        return ReportVersion(**row)
    else:
        raise ValueError(f"Unknown table name: {table_name}")


def pydantic_to_supabase(model: SupabaseModel) -> Dict[str, Any]:
    """Convert a Pydantic model to a Supabase row"""
    return model.dict(exclude_unset=True)
