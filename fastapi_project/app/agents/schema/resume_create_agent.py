from pydantic import BaseModel, Field
from typing import TypedDict, Dict, List
from app.schemas.resume_agent import InputsModel


class ResumeAgentState(BaseModel):
    inputs: InputsModel
    user_inputs: Dict[str, str] = Field(default_factory=dict)
    answers: List[Dict] = Field(default_factory=list)
    pending_questions: List[str] = Field(default_factory=list)
    resume: str = ""
    docx_path: str = ""
    asked_count: int = 0
    info_ready: bool = False

    # UI 분기용 step 필드 추가
    step: str = Field(default="questioning")


class ResumeAgentInitRequest(BaseModel):
    email: str
    preferred_job: str
    certification_count: int
    project_count: int
    major_type: str  # ex) "MAJOR" / "NON_MAJOR"
    company_name: str
    position: str
    work_period: int  # 개월 수
    additional_experiences: str
