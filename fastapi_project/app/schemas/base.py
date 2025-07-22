# app/schemas/base.py

"""
공통 기본 모델들
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime


class BaseInputsModel(BaseModel):
    """이력서 생성을 위한 기본 입력 데이터 (모든 곳에서 공통 사용)"""

    email: str = Field(..., description="이메일 주소")
    preferred_job: str = Field(..., description="희망 직무")
    certification_count: int = Field(default=0, ge=0, description="자격증 개수")
    project_count: int = Field(default=0, ge=0, description="프로젝트 개수")
    major_type: Literal["MAJOR", "NON_MAJOR"] = Field(..., description="전공 유형")
    company_name: Optional[str] = Field(default="", description="회사명")
    position: Optional[str] = Field(default="", description="직책")
    work_period: Optional[int] = Field(default=0, ge=0, description="근무 기간 (개월)")
    additional_experiences: Optional[str] = Field(
        default="", description="추가 경험사항"
    )  # 오타 수정: dafault -> default

    @validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("올바른 이메일 형식이 아닙니다")
        return v.strip().lower()

    @validator("preferred_job", "company_name", "position")
    def validate_strings(cls, v):
        return v.strip() if v else ""

    @validator("work_period")
    def validate_work_period(cls, v):
        if v < 0:
            raise ValueError("근무 기간은 0 이상이어야 합니다")
        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BaseTimestampModel(BaseModel):
    """타임스탬프 기본 모델"""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_timestamp(self):
        """업데이트 시간 갱신"""
        self.updated_at = datetime.now()

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class QuestionAnswerPair(BaseModel):
    """질문-답변 쌍"""

    question: str = Field(..., description="질문 내용")
    answer: str = Field(..., description="답변 내용")
    question_type: str = Field(
        default="general", description="질문 유형"
    )  # 오타 수정: defaulr -> default
    asked_at: datetime = Field(default_factory=datetime.now, description="질문 시간")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Redis 관련 공통 Mixin
class RedisMixin:
    """Redis 저장/로드를 위한 공통 메서드들"""

    def to_redis_dict(self) -> dict:
        """Redis 저장용 dict 변환 (기본 구현)"""
        data = self.dict()
        # datetime 객체들을 ISO 문자열로 변환
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_redis_dict(cls, data: dict):
        """Redis에서 로드할 때 dict에서 변환 (기본 구현)"""
        # ISO 문자열을 datetime으로 변환
        for key, value in data.items():
            if isinstance(value, str) and key.endswith("_at"):
                try:
                    data[key] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
        return cls(**data)
