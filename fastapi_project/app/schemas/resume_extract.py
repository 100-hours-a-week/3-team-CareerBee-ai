# app/schemas/resume_extract.py
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List

class ResumeExtractRequest(BaseModel):
    file_url: HttpUrl
    
class ResumeInfo(BaseModel):
    certification_count: int
    project_count: int
    major_type: str                     # "MAJOR" 또는 "NON_MAJOR"
    company_name: Optional[str] = None # 없으면 null 허용
    work_period: int                   # 없으면 0으로 받음
    position: Optional[str] = None     # 없으면 null 허용
    additional_experiences: Optional[str] = None
    
class ResumeExtractResponse(BaseModel):
    message: str
    data: Optional[ResumeInfo]