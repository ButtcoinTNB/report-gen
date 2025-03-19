from pydantic import BaseModel, UUID4
from typing import List, Optional

class AdditionalInfoRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: str
    template_id: Optional[UUID4] = None

class GenerateReportRequest(BaseModel):
    document_ids: List[UUID4]
    additional_info: Optional[str] = ""
    template_id: Optional[UUID4] = None 