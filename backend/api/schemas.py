from pydantic import BaseModel
from typing import List, Optional

class AdditionalInfoRequest(BaseModel):
    document_ids: List[str]
    additional_info: str
    template_id: Optional[int] = None

class GenerateReportRequest(BaseModel):
    document_ids: List[str]
    additional_info: Optional[str] = ""
    template_id: Optional[int] = None 