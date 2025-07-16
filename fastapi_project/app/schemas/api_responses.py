# app/schemas/api_responses.py
"""
API 응답 전용 모델들 (Spring과의 통신용)
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# ================================
# 1. 이력서 에이전트 응답 모델들
# ================================


class ResumeAgentInitResponse(BaseModel):
    memberId: int = Field(..., description="회원 ID")
    question: str = Field(..., description="첫 번째 질문")

    class Config:
        schema_extra = {"example": {"memberId": 3, "question": "첫번째 질문입니다"}}


class ResumeAgentUpdateResponse(BaseModel):
    """이력서 에이전트 업데이트 응답 (FastAPI -> Spring)"""

    memberId: int = Field(..., description="회원 ID")
    isComplete: bool = Field(..., alias="isComplete", description="완료 여부")

    # 추가 질문 있는 경우
    question: Optional[str] = Field(default=None, description="다음 질문 (미완료시)")

    # 완료된 경우
    resumeObjectKey: Optional[str] = Field(
        default=None, description="S3 객체 키 (완료시)"
    )

    class Config:
        schema_extra = {
            "examples": {
                "continue": {
                    "summary": "추가 질문이 있는 경우",
                    "value": {
                        "memberId": 3,
                        "isComplete": False,
                        "question": "두번째 질문입니다",
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


# ================================
# 2. 기본 이력서 생성 응답 모델
# ================================


class ResumeCreateData(BaseModel):
    file_url: str = Field(..., description="이력서 다운로드 URL")
    file_name: str = Field(..., description="파일명")


class ResumeCreateResponse(BaseModel):
    message: str = Field(..., description="resume_draft_success")  # e.g.
    data: ResumeCreateData = Field(..., description="응답 데이터")


# ================================
# 3. 공통 에러 응답 모델
# ================================


class ErrorResponse(BaseModel):
    """공통 에러 응답"""

    error: bool = Field(default=True, description="에러 여부")
    message: str = Field(..., description="에러 메시지")
    status_code: int = Field(..., description="HTTP 상태 코드")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="에러 발생 시간"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ValidationErrorResponse(ErrorResponse):
    """유효성 검증 에러 응답"""

    validation_errors: Optional[list] = Field(
        default=None, description="유효성 검증 오류 목록"
    )


# ================================
# 4. 헬스체크 응답 모델
# ================================


class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""

    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(default_factory=datetime.now, description="체크 시간")
    services: Dict[str, Any] = Field(default_factory=dict, description="각 서비스 상태")
    version: Optional[str] = Field(default=None, description="API 버전")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ================================
# 5. 상태 조회 응답 모델 (디버깅용)
# ================================


class AgentStatusResponse(BaseModel):
    """에이전트 상태 조회 응답"""

    memberId: int = Field(..., description="회원 ID")
    step: str = Field(..., description="현재 단계")
    asked_count: int = Field(..., description="질문한 횟수")
    max_questions: int = Field(..., description="최대 질문 수")
    info_ready: bool = Field(..., description="완료 여부")
    pending_questions: int = Field(..., description="대기 질문 수")
    answers_count: int = Field(..., description="답변 수")
    created_at: str = Field(..., description="생성 시간")
    updated_at: str = Field(..., description="수정 시간")


# ================================
# 6. 응답 생성 헬퍼 함수들
# ================================


def create_agent_init_response(memberId: int, question: str) -> ResumeAgentInitResponse:
    """에이전트 초기화 응답 생성"""
    return ResumeAgentInitResponse(memberId=memberId, question=question)


def create_agent_update_response(
    memberId: int,
    isComplete: bool,
    question: Optional[str] = None,
    resumeObjectKey: Optional[str] = None,
) -> ResumeAgentUpdateResponse:
    """에이전트 업데이트 응답 생성"""
    return ResumeAgentUpdateResponse(
        memberId=memberId,
        isComplete=isComplete,
        question=question,
        resumeObjectKey=resumeObjectKey,
    )


def create_error_response(
    message: str,
    status_code: int = 500,
    detail: Optional[str] = None,
    data: Optional[Any] = None,
) -> dict:
    """에러 응답 생성

    Args:
        message (str): 사용자에게 표시할 메시지
        status_code (int): HTTP 상태 코드
        detail (str): 내부 디버깅용 상세 설명
        data (Any): 추가 정보 전달용 (선택)

    Returns:
        dict: 일관된 에러 응답 JSON
    """
    return {
        "httpStatusCode": status_code,
        "message": message,
        "detail": detail,
        "data": data,
    }


def create_resume_create_response(
    resume_url: str, filename: str
) -> ResumeCreateResponse:
    """이력서 생성 응답 생성"""
    return ResumeCreateResponse(
        message="resume_draft_success",
        data=ResumeCreateData(
            file_url=resume_url,
            file_name=filename,
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


# ================================
# 7. 기본 이력서 에러 응답 모델
# ================================


class ErrorData(BaseModel):
    error: str = Field(..., description="에러 유형 코드")
    details: str = Field(..., description="에러 상세 설명")


class ErrorResponseV2(BaseModel):
    message: str = Field(..., description="에러 메시지 코드")
    data: ErrorData = Field(..., description="에러 상세 데이터")


# 에러 응답 생성 헬퍼 함수 추가


def create_error_response_v2(
    message: str,
    error_code: str,
    details: str,
) -> ErrorResponseV2:
    """명세 기반 에러 응답 생성"""
    return ErrorResponseV2(
        message=message,
        data=ErrorData(
            error=error_code,
            details=details,
        ),
    )
