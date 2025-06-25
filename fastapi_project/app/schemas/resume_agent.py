# app/schemas/resume_agent.py

from pydantic import BaseModel, Field
from typing import Dict, List, Union


class InputsModel(BaseModel):  # 사용자 초기 입력의 내부 필드 모델 (pydantic model)
    email: str
    preferred_job: str
    certification_count: int
    project_count: int
    major_type: str
    company_name: str
    position: str
    work_period: int
    additional_experiences: str


class ResumeAgentInitRequest(
    BaseModel
):  # 최초 init 호출시 FastAPI에서 입력받는 request 모델
    inputs: Union[InputsModel, dict]


class ResumeAgentRequest(
    BaseModel
):  # 전체 LangGraph state를 관리하는 메인 모델 (pydantic model)
    inputs: InputsModel
    user_inputs: Dict = Field(default_factory=dict)
    answers: List[Dict] = Field(default_factory=list)
    pending_questions: List[str] = Field(default_factory=list)
    resume: str = ""
    docx_path: str = ""
    info_ready: bool = False
    asked_count: int = 0
