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

    class Config:
        json_schema_extra = {
            "example": {
                "memberId": 3,
                "inputs": {
                    "email": "test@example.com",
                    "preferred_job": "AI 엔지니어",
                    "certification_count": 2,
                    "project_count": 3,
                    "major_type": "MAJOR",
                    "company_name": "카카오",
                    "position": "백엔드 개발자",
                    "work_period": 24,
                    "additional_experiences": "Python, FastAPI 경험",
                },
            }
        }


class ResumeAgentUpdateRequest(BaseModel):
    """이력서 에이전트 업데이트 요청 (Spring → FastAPI)"""

    memberId: int = Field(..., description="회원 ID")
    inputs: "UpdateInputs" = Field(..., description="업데이트 입력 데이터")

    @property
    def answer(self) -> str:
        """API 명세에 따른 답변 추출"""
        return self.inputs.answer

    class Config:
        json_schema_extra = {
            "example": {
                "memberId": 3,
                "inputs": {"answer": "커리어비가 가장 열심히한 프로젝트입니다."},
            }
        }


class UpdateInputs(BaseModel):
    """업데이트 요청의 inputs 부분"""

    answer: str = Field(..., description="사용자 답변")

    class Config:
        json_schema_extra = {
            "example": {"answer": "커리어비가 가장 열심히한 프로젝트입니다."}
        }


# ================================
# 3. API 응답 모델들 (누락된 모델들 추가)
# ================================


class ResumeAgentInitResponse(BaseModel):
    """이력서 에이전트 초기화 응답 (FastAPI → Spring)"""

    memberId: int = Field(..., description="회원 ID")
    question: str = Field(..., description="첫 번째 질문")

    class Config:
        json_schema_extra = {
            "example": {
                "memberId": 3,
                "question": "가장 자신있는 기술 스택이나 프로그래밍 언어는 무엇인가요?",
            }
        }


class ResumeAgentUpdateResponse(BaseModel):
    """이력서 에이전트 업데이트 응답 (FastAPI → Spring)"""

    memberId: int = Field(..., description="회원 ID")
    isComplete: bool = Field(..., description="완료 여부")
    question: Optional[str] = Field(default=None, description="다음 질문 (미완료시)")
    resumeObjectKey: Optional[str] = Field(
        default=None, description="S3 객체 키 (완료시)"
    )

    class Config:
        json_schema_extra = {
            "examples": {
                "continue": {
                    "summary": "추가 질문이 있는 경우",
                    "value": {
                        "memberId": 3,
                        "isComplete": False,
                        "question": "두번째 질문입니다.",
                        "resumeObjectKey": None,
                    },
                },
                "complete": {
                    "summary": "이력서 생성 완료",
                    "value": {
                        "memberId": 3,
                        "isComplete": True,
                        "question": None,
                        "resumeObjectKey": "resume/member_3_20240107_143022.docx",
                    },
                },
            }
        }


class AgentStatusResponse(BaseModel):
    """에이전트 상태 조회 응답 (디버깅용)"""

    memberId: int = Field(..., description="회원 ID")
    step: str = Field(..., description="현재 단계")
    asked_count: int = Field(..., description="질문한 횟수")
    max_questions: int = Field(..., description="최대 질문 수")
    info_ready: bool = Field(..., description="완료 여부")
    pending_questions: int = Field(..., description="대기 질문 수")
    answers_count: int = Field(..., description="답변 수")
    created_at: str = Field(..., description="생성 시간")
    updated_at: str = Field(..., description="수정 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "memberId": 3,
                "step": "questioning",
                "asked_count": 1,
                "max_questions": 3,
                "info_ready": False,
                "pending_questions": 1,
                "answers_count": 1,
                "created_at": "2024-01-07T14:30:22",
                "updated_at": "2024-01-07T14:35:15",
            }
        }


# ================================
# 4. 기존 이력서 생성 요청 모델
# ================================


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

    class Config:
        json_schema_extra = {
            "example": {
                "email": "test@example.com",
                "preferred_job": "백엔드 개발자",
                "certification_count": 2,
                "project_count": 3,
                "major_type": "MAJOR",
                "company_name": "스타트업",
                "work_period": 12,
                "position": "주니어 개발자",
                "additional_experiences": "Python, FastAPI 경험",
            }
        }


class ResumeCreateResponse(BaseModel):
    """기본 이력서 생성 응답"""

    httpStatusCode: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(..., description="응답 메시지")
    data: "ResumeCreateData" = Field(..., description="응답 데이터")


class ResumeCreateData(BaseModel):
    """기본 이력서 생성 응답 데이터"""

    resumeUrl: str = Field(..., description="이력서 다운로드 URL")
    filename: str = Field(..., description="파일명")
    createdAt: datetime = Field(..., description="생성 시간")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# 5. 공통 에러 응답 모델
# ================================


class ErrorResponse(BaseModel):
    """공통 에러 응답"""

    error: bool = Field(default=True, description="에러 여부")
    message: str = Field(..., description="에러 메시지")
    status_code: int = Field(..., description="HTTP 상태 코드")
    details: Optional[Dict] = Field(default=None, description="상세 정보")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="에러 발생 시간"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# 6. 레거시 호환성 모델
# ================================

# 기존 코드와의 호환성을 위해 유지 (나중에 제거 예정)
InputsModel = BaseInputsModel  # 별칭


# ================================
# 7. 유틸리티 함수들
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


# ================================
# 8. 응답 생성 헬퍼 함수들
# ================================


def create_agent_init_response(memberId: int, question: str) -> dict:
    """에이전트 초기화 응답 생성"""
    return {"memberId": memberId, "question": question}


def create_agent_update_response(
    memberId: int,
    is_complete: bool,
    question: Optional[str] = None,
    resume_object_key: Optional[str] = None,
) -> dict:
    """에이전트 업데이트 응답 생성"""
    return {
        "memberId": memberId,
        "isComplete": is_complete,
        "question": question,
        "resumeObjectKey": resume_object_key,
    }


def create_error_response(
    message: str, status_code: int, details: Optional[Dict] = None
) -> ErrorResponse:
    """에러 응답 생성"""
    return ErrorResponse(message=message, status_code=status_code, details=details)


def create_resume_create_response(
    resume_url: str, filename: str, message: str = "이력서 초안 생성에 성공하였습니다."
) -> ResumeCreateResponse:
    """이력서 생성 응답 생성"""
    return ResumeCreateResponse(
        message=message,
        data=ResumeCreateData(
            resumeUrl=resume_url, filename=filename, createdAt=datetime.now()
        ),
    )


def create_agent_status_response(
    memberId: int,
    step: str,
    asked_count: int,
    max_questions: int,
    info_ready: bool,
    pending_questions_count: int,
    answers_count: int,
    created_at: str,
    updated_at: str,
) -> AgentStatusResponse:
    """에이전트 상태 조회 응답 생성"""
    return AgentStatusResponse(
        memberId=memberId,
        step=step,
        asked_count=asked_count,
        max_questions=max_questions,
        info_ready=info_ready,
        pending_questions=pending_questions_count,
        answers_count=answers_count,
        created_at=created_at,
        updated_at=updated_at,
    )


# Forward reference 해결
ResumeCreateResponse.model_rebuild()
