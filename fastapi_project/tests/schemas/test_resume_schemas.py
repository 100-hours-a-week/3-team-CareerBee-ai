# tests/schemas/test_resume_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.resume_models import ResumeCreateRequest


class TestResumeSchemas:
    """이력서 스키마 검증 테스트"""

    def test_personal_info_valid(self):
        """개인정보 스키마 유효성 테스트"""
        valid_data = {
            "name": "홍길동",
            "email": "hong@example.com",
            "phone": "010-1234-5678",
            "address": "서울시 강남구",
        }

        personal_info = PersonalInfo(**valid_data)

        assert personal_info.name == "홍길동"
        assert personal_info.email == "hong@example.com"
        assert personal_info.phone == "010-1234-5678"

    def test_personal_info_invalid_email(self):
        """잘못된 이메일 형식 테스트"""
        invalid_data = {
            "name": "홍길동",
            "email": "invalid-email",  # 잘못된 이메일 형식
            "phone": "010-1234-5678",
        }

        with pytest.raises(ValidationError) as exc_info:
            PersonalInfo(**invalid_data)

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "email" for error in errors)

    def test_experience_valid(self):
        """경력 스키마 유효성 테스트"""
        valid_data = {
            "company": "테스트 회사",
            "position": "소프트웨어 개발자",
            "duration": "2020.03 - 2023.02",
            "description": "웹 애플리케이션 개발",
        }

        experience = Experience(**valid_data)

        assert experience.company == "테스트 회사"
        assert experience.position == "소프트웨어 개발자"

    def test_education_valid(self):
        """학력 스키마 유효성 테스트"""
        valid_data = {
            "school": "테스트 대학교",
            "major": "컴퓨터공학과",
            "degree": "학사",
            "graduation": "2020.02",
        }

        education = Education(**valid_data)

        assert education.school == "테스트 대학교"
        assert education.major == "컴퓨터공학과"

    def test_resume_create_request_valid(self, sample_resume_data):
        """이력서 생성 요청 스키마 유효성 테스트"""
        request = ResumeCreateRequest(**sample_resume_data)

        assert request.memberId == sample_resume_data["memberId"]
        assert request.personal_info.name == sample_resume_data["personal_info"]["name"]
        assert len(request.experiences) == len(sample_resume_data["experiences"])
        assert len(request.education) == len(sample_resume_data["education"])

    def test_resume_create_request_missing_personal_info(self):
        """개인정보 누락 시 검증 오류 테스트"""
        invalid_data = {
            "memberId": 1,
            "experiences": [],
            "education": [],
            # personal_info 누락
        }

        with pytest.raises(ValidationError) as exc_info:
            ResumeCreateRequest(**invalid_data)

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "personal_info" for error in errors)
