# app/schemas/resume_models.py
"""
이력서 관련 모든 모델 통합 - Redis 통합 및 새로운 API 요구사항 반영
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Union
from datetime import datetime

from .base import BaseInputsModel, BaseTimestampModel, QuestionAnswerPair, RedisMixin


# ================================
# 1. 에이전트 상태 관리 모델 (Redis용)
# ================================


class ResumeAgentState(BaseTimestampModel, RedisMixin):
    """
    Redis에 저장되는 이력서 에이전트 상태
    새로운 API 요구사항 및 Redis 통합 반영
    """

    # 기본 정보
    memberId: int = Field(..., description="회원 ID")
    inputs: BaseInputsModel = Field(..., description="기본 입력 데이터")

    # 질문-답변 관련
    user_inputs: Dict[str, str] = Field(
        default_factory=dict, description="사용자 입력 매핑"
    )
    answers: List[Dict] = Field(default_factory=list, description="질문-답변 목록")
    pending_questions: List[str] = Field(
        default_factory=list, description="대기 중인 질문"
    )

    # 진행 상태
    asked_count: int = Field(default=0, ge=0, description="질문한 횟수")
    max_questions: int = Field(default=3, description="최대 질문 수")
    info_ready: bool = Field(default=False, description="정보 수집 완료 여부")

    # 결과 정보
    resume: str = Field(default="", description="생성된 이력서 내용 (Markdown)")
    docx_path: str = Field(default="", description="생성된 문서 경로 또는 S3 키")

    # UI/API 제어
    step: Literal["questioning", "processing", "completed", "error"] = Field(
        default="questioning", description="현재 단계"
    )

    # 에러 정보
    error_message: Optional[str] = Field(default=None, description="에러 메시지")
    error_details: Optional[Dict] = Field(default=None, description="에러 상세 정보")

    def add_answer(
        self, question: str, answer: str, question_type: str = "general"
    ) -> None:
        """새 답변 추가"""
        qa_pair = QuestionAnswerPair(
            question=question, answer=answer, question_type=question_type
        )
        self.answers.append(qa_pair.dict())
        self.user_inputs[question] = answer  # 기존 호환성
        self.asked_count += 1
        self.update_timestamp()

    def mark_completed(self, resume_content: str = "", docx_path: str = "") -> None:
        """완료 상태로 설정"""
        self.info_ready = True
        self.step = "completed"
        self.resume = resume_content
        self.docx_path = docx_path
        self.pending_questions = []
        self.update_timestamp()

    def mark_error(
        self, error_message: str, error_details: Optional[Dict] = None
    ) -> None:
        """에러 상태로 설정"""
        self.step = "error"
        self.error_message = error_message
        self.error_details = error_details or {}
        self.update_timestamp()

    def get_next_question(self) -> Optional[str]:
        """다음 질문 반환"""
        return self.pending_questions[0] if self.pending_questions else None

    def is_complete(self) -> bool:
        """완료 여부 확인"""
        return self.info_ready or self.asked_count >= self.max_questions

    def to_redis_dict(self) -> dict:
        """Redis 저장용 dict 변환 (오버라이드)"""
        return {
            "memberId": self.memberId,
            "inputs": self.inputs.dict(),
            "user_inputs": self.user_inputs,
            "answers": self.answers,
            "pending_questions": self.pending_questions,
            "asked_count": self.asked_count,
            "max_questions": self.max_questions,
            "info_ready": self.info_ready,
            "resume": self.resume,
            "docx_path": self.docx_path,
            "step": self.step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "error_details": self.error_details,
        }

    @classmethod
    def from_redis_dict(cls, data: dict) -> "ResumeAgentState":
        """Redis에서 로드할 때 dict에서 변환 (오버라이드)"""
        # 기본값 보장
        safe_data = {
            "memberId": data["memberId"],
            "inputs": BaseInputsModel(**data["inputs"]),
            "user_inputs": data.get("user_inputs", {}),
            "answers": data.get("answers", []),
            "pending_questions": data.get("pending_questions", []),
            "asked_count": data.get("asked_count", 0),
            "max_questions": data.get("max_questions", 3),
            "info_ready": data.get("info_ready", False),
            "resume": data.get("resume", ""),
            "docx_path": data.get("docx_path", ""),  # 기본값 명시적 설정
            "step": data.get("step", "questioning"),
            "error_message": data.get("error_message"),
            "error_details": data.get("error_details"),
        }

        # datetime 처리
        try:
            safe_data["created_at"] = datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            )
            safe_data["updated_at"] = datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat())
            )
        except (ValueError, TypeError):
            safe_data["created_at"] = datetime.now()
            safe_data["updated_at"] = datetime.now()

        return cls(**safe_data)


# ================================
# 2. API 요청 모델들 (새로운 요구사항 반영)
# ================================


class ResumeAgentInitRequest(BaseModel):
    """이력서 에이전트 초기화 요청 (Spring → FastAPI)"""

    memberId: int = Field(..., description="회원 ID")
    inputs: BaseInputsModel = Field(..., description="기본 입력 데이터")


class ResumeAgentUpdateRequest(BaseModel):
    """이력서 에이전트 업데이트 요청 (Spring → FastAPI)"""

    memberId: int = Field(..., description="회원 ID")
    inputs: "UpdateInputs" = Field(..., description="업데이트 입력 데이터")

    @property
    def answer(self) -> str:
        """API 명세에 따른 답변 추출"""
        return self.inputs.answer


class UpdateInputs(BaseModel):
    """업데이트 요청의 inputs 부분"""

    answer: str = Field(..., description="사용자 답변")

    class Config:
        schema_extra = {
            "example": {"answer": "커리어비가 가장 열심히한 프로젝트입니다."}
        }


class ResumeCreateRequest(BaseModel):
    """기본 이력서 생성 요청 (하드코딩 템플릿용)"""

    email: str = Field(..., description="이메일")
    preferred_job: str = Field(..., description="선호 직무")
    certification_count: int = Field(default=0, ge=0, description="자격증 개수")
    project_count: int = Field(default=0, ge=0, description="프로젝트 개수")
    major_type: Literal["MAJOR", "NON_MAJOR"] = Field(..., description="전공 여부")
    company_name: Optional[str] = Field(default="", description="회사 이름")
    work_period: Optional[int] = Field(default=0, ge=0, description="경력 개월 수")
    position: Optional[str] = Field(default="", description="직무")
    additional_experiences: Optional[str] = Field(default="", description="기타")

    def to_base_inputs(self) -> BaseInputsModel:
        """BaseInputsModel로 변환"""
        return BaseInputsModel(
            email=self.email,
            preferred_job=self.preferred_job,
            certification_count=self.certification_count or 0,
            project_count=self.project_count or 0,
            major_type=self.major_type,
            company_name=self.company_name or "",
            position=self.position or "",
            work_period=self.work_period or 0,
            additional_experiences=self.additional_experiences or "",
        )


# ================================
# 3. 레거시 호환성 모델 (점진적 마이그레이션용)
# ================================

# 기존 코드와의 호환성을 위해 유지 (나중에 제거 예정)
InputsModel = BaseInputsModel  # 별칭


# ================================
# 4. 유틸리티 함수들
# ================================


def create_initial_state(memberId: int, inputs: BaseInputsModel) -> ResumeAgentState:
    """초기 상태 생성 헬퍼 함수"""
    return ResumeAgentState(
        memberId=memberId,
        inputs=inputs,
        user_inputs={},
        answers=[],
        pending_questions=[],
        asked_count=0,
        max_questions=3,
        info_ready=False,
        resume="",  # 명시적 기본값
        docx_path="",  # 명시적 기본값
        step="questioning",
        error_message=None,
        error_details=None,
    )


def update_state_with_answer(
    state: ResumeAgentState, question: str, answer: str
) -> ResumeAgentState:
    """상태에 답변 추가 헬퍼 함수"""
    state.add_answer(question, answer)
    return state
