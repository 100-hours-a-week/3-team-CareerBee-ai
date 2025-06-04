# app/schemas/resume_agent.py

from pydantic import BaseModel, Field
from typing import Dict, List


class ResumeAgentRequest(BaseModel):
    inputs: Dict = Field(default_factory=dict)
    user_inputs: Dict = Field(default_factory=dict)
    answers: List[Dict] = Field(default_factory=list)
    pending_questions: List[str] = Field(default_factory=list)
    resume: str = ""
    docx_path: str = ""
    info_ready: bool = False
    asked_count: int = 0


class InputsModel(BaseModel):
    email: str
    preferred_job: str
    certification_count: int
    project_count: int
    major_type: str
    company_name: str
    position: str
    work_period: int
    additional_experiences: str


class ResumeAgentInitRequest(BaseModel):
    inputs: InputsModel
