# tests/schemas/test_feedback_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


class TestFeedbackSchemas:
    """피드백 스키마 검증 테스트"""

    def test_feedback_request_valid(self):
        """유효한 피드백 요청 스키마 테스트"""
        valid_data = {
            "memberId": 1,
            "question": "자기소개를 해보세요.",
            "answer": "안녕하세요. 저는 개발자입니다.",
        }

        request = FeedbackRequest(**valid_data)

        assert request.memberId == 1
        assert request.question == "자기소개를 해보세요."
        assert request.answer == "안녕하세요. 저는 개발자입니다."

    def test_feedback_request_missing_fields(self):
        """필수 필드 누락 시 검증 오류 테스트"""
        invalid_data = {
            "memberId": 1
            # question, answer 누락
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackRequest(**invalid_data)

        errors = exc_info.value.errors()
        field_names = [error["loc"][0] for error in errors]
        assert "question" in field_names
        assert "answer" in field_names

    def test_feedback_request_invalid_types(self):
        """잘못된 타입 시 검증 오류 테스트"""
        invalid_data = {
            "memberId": "not_a_number",  # 문자열이지만 int 필요
            "question": 123,  # 숫자이지만 str 필요
            "answer": None,  # None이지만 str 필요
        }

        with pytest.raises(ValidationError):
            FeedbackRequest(**invalid_data)

    def test_feedback_response_valid(self):
        """유효한 피드백 응답 스키마 테스트"""
        valid_data = {"memberId": 1, "feedback": "좋은 답변입니다."}

        response = FeedbackResponse(**valid_data)

        assert response.memberId == 1
        assert response.feedback == "좋은 답변입니다."
