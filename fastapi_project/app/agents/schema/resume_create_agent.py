from pydantic import BaseModel, Field
from typing import TypedDict, Dict, List


class ResumeAgentState(BaseModel):
    inputs: Dict
    user_inputs: Dict
    pending_questions: List[str] = []
    answers: List[Dict] = []
    resume: str = ""
    docx_path: str = ""
    asked_count: int = 0
    info_ready: bool = False


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
