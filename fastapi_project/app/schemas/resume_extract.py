# app/schemas/resume_extract.py
from pydantic import BaseModel, HttpUrl
from typing import Optional

class ResumeExtractRequest(BaseModel):
    file_url: HttpUrl

class ResumeInfo(BaseModel):
    certification_count: int
    project_count: int
    major_type: str                     # "MAJOR" 또는 "NON_MAJOR"
    company_name: Optional[str] = None
    work_period: Optional[int] = 0     # 없으면 0으로 대체
    position: Optional[str] = None
    additional_experiences: Optional[str] = None

class ResumeExtractResponse(BaseModel):
    message: str
    data: Optional[ResumeInfo]