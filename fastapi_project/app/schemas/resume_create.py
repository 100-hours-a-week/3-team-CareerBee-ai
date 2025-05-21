from pydantic import BaseModel, Field
from typing import Optional

class ProjectInfo(BaseModel):
    title: str
    duration: str
    role: str
    impact: str

class ResumeCreateRequest(BaseModel):
    email: str = Field(..., description="이메일")
    preferred_job: str = Field(..., description="선호 직무")
    certification_count: int = Field(..., description="자격증 개수")
    project_count: int = Field(..., description="프로젝트 개수")
    major_type: str = Field(..., description="전공 여부 (MAJOR / NON_MAJOR)")
    company_name: Optional[str] = Field(None, description="회사 이름")
    work_period: Optional[int] = Field(None, description="경력 개월 수")
    position: Optional[str] = Field(None, description="직무")
    additional_experiences: Optional[str] = Field("", description="기타")
