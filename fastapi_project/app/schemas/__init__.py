# app/schemas/__init__.py

"""
통합된 스키마 모듈 - 중앙 집중식 import
"""

# 기본 모델들
from .base import BaseInputsModel, BaseTimestampModel, QuestionAnswerPair, RedisMixin

# 이력서 관련 모델들
from .resume_models import (
    ResumeAgentState,
    ResumeAgentInitRequest,
    ResumeAgentUpdateRequest,
    ResumeCreateRequest,
    InputsModel,
    create_initial_state,
    update_state_with_answer,
)

# API 응답 모델들
from .api_responses import (
    ResumeAgentInitResponse,
    ResumeAgentUpdateResponse,
    ResumeCreateResponse,
    ResumeCreateData,
    ErrorResponse,
    ValidationErrorResponse,
    HealthCheckResponse,
    create_agent_init_response,
    create_agent_update_response,
    create_error_response,
    create_resume_create_response,
)


# 편의를 위한 그룹 export
API_MODELS = [
    ResumeAgentInitRequest,
    ResumeAgentUpdateRequest,
    ResumeCreateRequest,
]

RESPONSE_MODELS = [
    ResumeAgentInitResponse,
    ResumeAgentUpdateResponse,
    ResumeCreateResponse,
    ErrorResponse,
    HealthCheckResponse,
]

CORE_MODELS = [
    ResumeAgentState,
    BaseInputsModel,
    QuestionAnswerPair,
]

__all__ = [
    # 기본 모델
    "BaseInputsModel",
    "BaseTimestampModel",
    "QuestionAnswerPair",
    "RedisMixin",
    # 이력서 모델
    "ResumeAgentState",
    "ResumeAgentInitRequest",
    "ResumeAgentUpdateRequest",
    "ResumeCreateRequest",
    "InputsModel",
    "create_initial_state",
    "update_state_with_answer",
    # 응답 모델
    "ResumeAgentInitResponse",
    "ResumeAgentUpdateResponse",
    "ResumeCreateResponse",
    "ResumeCreateData",
    "ErrorResponse",
    "ValidationErrorResponse",
    "HealthCheckResponse",
    # 헬퍼 함수
    "create_initial_state",
    "update_state_with_answer",
    "create_agent_init_response",
    "create_agent_update_response",
    "create_error_response",
    "create_resume_create_response",
    # 그룹
    "API_MODELS",
    "RESPONSE_MODELS",
    "CORE_MODELS",
]
