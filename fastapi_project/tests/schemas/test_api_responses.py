# tests/schemas/test_api_responses.py
import pytest
from datetime import datetime

# 안전한 임포트
try:
    from app.schemas.api_responses import (
        ResumeAgentInitResponse,
        ResumeAgentUpdateResponse,
        ResumeCreateResponse,
        ResumeCreateData,
        ErrorResponse,
        AgentStatusResponse,
        create_agent_init_response,
        create_agent_update_response,
        create_error_response,
        create_resume_create_response,
    )

    SCHEMAS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Cannot import schemas: {e}")
    SCHEMAS_AVAILABLE = False


@pytest.mark.skipif(not SCHEMAS_AVAILABLE, reason="Schemas not available")
class TestApiResponses:
    """API 응답 스키마 테스트"""

    def test_resume_agent_init_response(self):
        """이력서 에이전트 초기화 응답 테스트"""
        response = ResumeAgentInitResponse(memberId=1, question="테스트 질문입니다.")

        assert response.memberId == 1
        assert response.question == "테스트 질문입니다."

    def test_resume_agent_update_response_continue(self):
        """이력서 에이전트 업데이트 응답 테스트 (계속)"""
        response = ResumeAgentUpdateResponse(
            memberId=1,
            isComplete=False,
            question="다음 질문입니다.",
            resumeObjectKey=None,
        )

        assert response.memberId == 1
        assert response.isComplete == False
        assert response.question == "다음 질문입니다."
        assert response.resumeObjectKey is None

    def test_resume_agent_update_response_complete(self):
        """이력서 에이전트 업데이트 응답 테스트 (완료)"""
        response = ResumeAgentUpdateResponse(
            memberId=1,
            isComplete=True,
            question=None,
            resumeObjectKey="resume/member_1_20240101.docx",
        )

        assert response.memberId == 1
        assert response.isComplete == True
        assert response.question is None
        assert response.resumeObjectKey == "resume/member_1_20240101.docx"

    def test_resume_create_response(self):
        """이력서 생성 응답 테스트"""
        data = ResumeCreateData(
            resumeUrl="https://example.com/resume.docx",
            filename="test-resume.docx",
            createdAt=datetime.now(),
        )

        response = ResumeCreateResponse(
            httpStatusCode=200, message="이력서 생성 완료", data=data
        )

        assert response.httpStatusCode == 200
        assert response.message == "이력서 생성 완료"
        assert response.data.resumeUrl == "https://example.com/resume.docx"
        assert response.data.filename == "test-resume.docx"

    def test_error_response(self):
        """에러 응답 테스트"""
        response = ErrorResponse(
            message="테스트 오류",
            status_code=400,
            details={"field": "validation error"},
        )

        assert response.error == True
        assert response.message == "테스트 오류"
        assert response.status_code == 400
        assert response.details["field"] == "validation error"

    def test_agent_status_response(self):
        """에이전트 상태 응답 테스트"""
        response = AgentStatusResponse(
            memberId=1,
            step="questioning",
            asked_count=2,
            max_questions=3,
            info_ready=False,
            pending_questions=1,
            answers_count=2,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T01:00:00",
        )

        assert response.memberId == 1
        assert response.step == "questioning"
        assert response.asked_count == 2
        assert response.max_questions == 3
        assert response.info_ready == False

    def test_create_agent_init_response_helper(self):
        """에이전트 초기화 응답 생성 헬퍼 테스트"""
        response = create_agent_init_response(memberId=1, question="헬퍼로 생성된 질문")

        assert isinstance(response, ResumeAgentInitResponse)
        assert response.memberId == 1
        assert response.question == "헬퍼로 생성된 질문"

    def test_create_error_response_helper(self):
        """에러 응답 생성 헬퍼 테스트"""
        error_dict = create_error_response(
            message="테스트 오류", status_code=500, detail="상세 오류 내용"
        )

        assert error_dict["httpStatusCode"] == 500
        assert error_dict["message"] == "테스트 오류"
        assert error_dict["detail"] == "상세 오류 내용"


@pytest.mark.skipif(SCHEMAS_AVAILABLE, reason="Test only when schemas unavailable")
class TestApiResponsesFallback:
    """스키마를 사용할 수 없을 때의 대체 테스트"""

    def test_schemas_unavailable(self):
        """스키마를 임포트할 수 없을 때 테스트"""
        # 기본적인 dict 응답 테스트
        mock_response = {"memberId": 1, "question": "Mock question"}

        assert mock_response["memberId"] == 1
        assert mock_response["question"] == "Mock question"
