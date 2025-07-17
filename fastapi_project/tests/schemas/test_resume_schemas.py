# tests/schemas/test_resume_schemas.py
import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.resume_models import (
    ResumeCreateRequest,
    ResumeAgentState,
    ResumeAgentInitRequest,
    ResumeAgentUpdateRequest,
    ResumeAgentInitResponse,
    ResumeAgentUpdateResponse,
    create_initial_state,
    update_state_with_answer,
)
from app.schemas.base import BaseInputsModel


class TestResumeSchemas:
    """이력서 스키마 검증 테스트"""

    @pytest.fixture
    def sample_base_inputs(self):
        """기본 입력 데이터 샘플"""
        return {
            "email": "test@example.com",
            "preferred_job": "백엔드 개발자",
            "certification_count": 2,
            "project_count": 3,
            "major_type": "MAJOR",
            "company_name": "테스트 회사",
            "position": "주니어 개발자",
            "work_period": 12,
            "additional_experiences": "Python, FastAPI 경험",
        }

    @pytest.fixture
    def sample_resume_create_data(self, sample_base_inputs):
        """이력서 생성 요청 샘플 데이터"""
        return sample_base_inputs.copy()

    def test_resume_create_request_valid(self, sample_resume_create_data):
        """유효한 이력서 생성 요청 스키마 테스트"""
        request = ResumeCreateRequest(**sample_resume_create_data)

        assert request.email == "test@example.com"
        assert request.preferred_job == "백엔드 개발자"
        assert request.certification_count == 2
        assert request.project_count == 3
        assert request.major_type == "MAJOR"
        assert request.company_name == "테스트 회사"
        assert request.work_period == 12

    def test_resume_create_request_missing_required_fields(self):
        """필수 필드 누락 시 검증 오류 테스트"""
        invalid_data = {
            "email": "test@example.com",
            # preferred_job, major_type 누락
        }

        with pytest.raises(ValidationError) as exc_info:
            ResumeCreateRequest(**invalid_data)

        errors = exc_info.value.errors()
        field_names = [error["loc"][0] for error in errors]
        assert "preferred_job" in field_names
        assert "major_type" in field_names

    def test_resume_create_request_invalid_major_type(self):
        """잘못된 major_type 값 테스트"""
        invalid_data = {
            "email": "test@example.com",
            "preferred_job": "개발자",
            "major_type": "INVALID_TYPE",  # 유효하지 않은 값
        }

        with pytest.raises(ValidationError) as exc_info:
            ResumeCreateRequest(**invalid_data)

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "major_type" for error in errors)

    def test_resume_create_request_negative_counts(self):
        """음수 카운트 값 테스트"""
        invalid_data = {
            "email": "test@example.com",
            "preferred_job": "개발자",
            "major_type": "MAJOR",
            "certification_count": -1,  # 음수 값
            "project_count": -5,  # 음수 값
        }

        with pytest.raises(ValidationError) as exc_info:
            ResumeCreateRequest(**invalid_data)

        errors = exc_info.value.errors()
        error_fields = [error["loc"][0] for error in errors]
        assert "certification_count" in error_fields
        assert "project_count" in error_fields

    def test_resume_create_request_to_base_inputs_conversion(
        self, sample_resume_create_data
    ):
        """ResumeCreateRequest를 BaseInputsModel로 변환 테스트"""
        request = ResumeCreateRequest(**sample_resume_create_data)
        base_inputs = request.to_base_inputs()

        assert isinstance(base_inputs, BaseInputsModel)
        assert base_inputs.email == request.email
        assert base_inputs.preferred_job == request.preferred_job
        assert base_inputs.certification_count == request.certification_count


class TestResumeAgentModels:
    """이력서 에이전트 모델 테스트"""

    @pytest.fixture
    def sample_base_inputs(self):
        """기본 입력 데이터"""
        return BaseInputsModel(
            email="test@example.com",
            preferred_job="백엔드 개발자",
            certification_count=2,
            project_count=3,
            major_type="MAJOR",
            company_name="테스트 회사",
            position="주니어 개발자",
            work_period=12,
            additional_experiences="Python, FastAPI 경험",
        )

    def test_resume_agent_init_request_valid(self, sample_base_inputs):
        """유효한 에이전트 초기화 요청 테스트"""
        request = ResumeAgentInitRequest(memberId=1, inputs=sample_base_inputs)

        assert request.memberId == 1
        assert request.inputs.email == "test@example.com"
        assert request.inputs.preferred_job == "백엔드 개발자"

    def test_resume_agent_update_request_valid(self):
        """유효한 에이전트 업데이트 요청 테스트"""
        from app.schemas.resume_models import UpdateInputs

        update_inputs = UpdateInputs(answer="저는 Python 개발자입니다.")
        request = ResumeAgentUpdateRequest(memberId=1, inputs=update_inputs)

        assert request.memberId == 1
        assert request.answer == "저는 Python 개발자입니다."

    def test_resume_agent_state_creation(self, sample_base_inputs):
        """에이전트 상태 생성 테스트"""
        state = create_initial_state(memberId=1, inputs=sample_base_inputs)

        assert state.memberId == 1
        assert state.inputs.email == "test@example.com"
        assert state.asked_count == 0
        assert state.step == "questioning"
        assert state.info_ready is False
        assert len(state.answers) == 0

    def test_resume_agent_state_add_answer(self, sample_base_inputs):
        """에이전트 상태에 답변 추가 테스트"""
        state = create_initial_state(memberId=1, inputs=sample_base_inputs)

        state.add_answer("자기소개를 해보세요.", "저는 개발자입니다.")

        assert state.asked_count == 1
        assert len(state.answers) == 1
        assert state.answers[0]["question"] == "자기소개를 해보세요."
        assert state.answers[0]["answer"] == "저는 개발자입니다."
        assert state.user_inputs["자기소개를 해보세요."] == "저는 개발자입니다."

    def test_resume_agent_state_mark_completed(self, sample_base_inputs):
        """에이전트 상태 완료 처리 테스트"""
        state = create_initial_state(memberId=1, inputs=sample_base_inputs)

        state.mark_completed(
            resume_content="# 이력서 내용", docx_path="resume/member_1_20240107.docx"
        )

        assert state.info_ready is True
        assert state.step == "completed"
        assert state.resume == "# 이력서 내용"
        assert state.docx_path == "resume/member_1_20240107.docx"
        assert len(state.pending_questions) == 0

    def test_resume_agent_state_mark_error(self, sample_base_inputs):
        """에이전트 상태 에러 처리 테스트"""
        state = create_initial_state(memberId=1, inputs=sample_base_inputs)

        state.mark_error(
            error_message="이력서 생성 실패", error_details={"code": "GENERATION_ERROR"}
        )

        assert state.step == "error"
        assert state.error_message == "이력서 생성 실패"
        assert state.error_details["code"] == "GENERATION_ERROR"

    def test_resume_agent_state_is_complete(self, sample_base_inputs):
        """에이전트 상태 완료 여부 확인 테스트"""
        state = create_initial_state(memberId=1, inputs=sample_base_inputs)

        # 초기 상태에서는 완료되지 않음
        assert state.is_complete() is False

        # 최대 질문 수에 도달하면 완료
        state.asked_count = 3
        assert state.is_complete() is True

        # 또는 info_ready가 True면 완료
        state.asked_count = 1
        state.info_ready = True
        assert state.is_complete() is True

    def test_resume_agent_state_redis_serialization(self, sample_base_inputs):
        """Redis 직렬화/역직렬화 테스트"""
        original_state = create_initial_state(memberId=1, inputs=sample_base_inputs)
        original_state.add_answer("질문", "답변")

        # Redis dict로 변환
        redis_dict = original_state.to_redis_dict()

        # Redis dict에서 복원
        restored_state = ResumeAgentState.from_redis_dict(redis_dict)

        assert restored_state.memberId == original_state.memberId
        assert restored_state.inputs.email == original_state.inputs.email
        assert restored_state.asked_count == original_state.asked_count
        assert len(restored_state.answers) == len(original_state.answers)
        assert (
            restored_state.answers[0]["question"]
            == original_state.answers[0]["question"]
        )


class TestResumeAgentResponses:
    """이력서 에이전트 응답 모델 테스트"""

    def test_resume_agent_init_response_valid(self):
        """유효한 초기화 응답 테스트"""
        response = ResumeAgentInitResponse(
            memberId=1, question="가장 자신있는 기술 스택은 무엇인가요?"
        )

        assert response.memberId == 1
        assert response.question == "가장 자신있는 기술 스택은 무엇인가요?"

    def test_resume_agent_update_response_continue(self):
        """계속 진행 응답 테스트"""
        response = ResumeAgentUpdateResponse(
            memberId=1,
            isComplete=False,
            question="두 번째 질문입니다.",
            resumeObjectKey=None,
        )

        assert response.memberId == 1
        assert response.isComplete is False
        assert response.question == "두 번째 질문입니다."
        assert response.resumeObjectKey is None

    def test_resume_agent_update_response_complete(self):
        """완료 응답 테스트"""
        response = ResumeAgentUpdateResponse(
            memberId=1,
            isComplete=True,
            question=None,
            resumeObjectKey="resume/member_1_20240107.docx",
        )

        assert response.memberId == 1
        assert response.isComplete is True
        assert response.question is None
        assert response.resumeObjectKey == "resume/member_1_20240107.docx"


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

    def test_feedback_request_empty_strings(self):
        """빈 문자열 허용 여부 테스트"""
        valid_data = {
            "memberId": 1,
            "question": "",  # 빈 문자열
            "answer": "",  # 빈 문자열
        }

        # 빈 문자열도 유효한 문자열이므로 통과해야 함
        request = FeedbackRequest(**valid_data)
        assert request.question == ""
        assert request.answer == ""

    def test_feedback_response_valid(self):
        """유효한 피드백 응답 스키마 테스트"""
        valid_data = {
            "memberId": 1,
            "feedback": "좋은 답변입니다. 더 구체적인 예시를 들어보세요.",
        }

        response = FeedbackResponse(**valid_data)

        assert response.memberId == 1
        assert response.feedback == "좋은 답변입니다. 더 구체적인 예시를 들어보세요."

    def test_feedback_response_missing_fields(self):
        """피드백 응답 필수 필드 누락 테스트"""
        invalid_data = {
            "memberId": 1
            # feedback 누락
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackResponse(**invalid_data)

        errors = exc_info.value.errors()
        field_names = [error["loc"][0] for error in errors]
        assert "feedback" in field_names

    def test_feedback_response_invalid_member_id(self):
        """잘못된 멤버 ID 타입 테스트"""
        invalid_data = {
            "memberId": "invalid_id",  # 문자열이지만 int 필요
            "feedback": "피드백 내용",
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackResponse(**invalid_data)

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "memberId" for error in errors)
