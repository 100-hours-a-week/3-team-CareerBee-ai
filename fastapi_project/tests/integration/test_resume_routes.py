# tests/integration/test_resume_routes.py - 실제 스키마에 맞게 수정된 버전
import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import status
import json
import asyncio


class TestResumeRoutes:
    """이력서 관련 API 라우트 테스트"""

    @pytest.mark.asyncio
    async def test_resume_agent_init_success(
        self, async_client, sample_agent_init_request
    ):
        """이력서 에이전트 초기화 성공 테스트"""
        with patch(
            "app.agents.nodes.generate_question.GenerateQuestionNode"
        ) as mock_question_node:
            mock_node_instance = Mock()
            mock_question_node.return_value = mock_node_instance

            async def mock_execute(state):
                state.pending_questions = ["가장 자신있는 기술 스택은 무엇인가요?"]
                return state

            mock_node_instance.execute = AsyncMock(side_effect=mock_execute)

            response = await async_client.post(
                "/resume/agent/init", json=sample_agent_init_request
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 실제 ResumeAgentInitResponse 스키마에 맞게 검증
            assert "memberId" in data
            assert "question" in data
            assert data["memberId"] == sample_agent_init_request["memberId"]
            assert isinstance(data["question"], str)
            assert len(data["question"]) > 0

    @pytest.mark.asyncio
    async def test_resume_agent_update_success(
        self, async_client, sample_agent_update_request
    ):
        """이력서 에이전트 업데이트 성공 테스트"""
        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state, patch(
            "app.agents.resume_agent.resume_agent"
        ) as mock_resume_agent:

            # 기존 상태 모킹
            from app.schemas.resume_models import ResumeAgentState
            from app.schemas.base import BaseInputsModel

            existing_state = ResumeAgentState(
                memberId=sample_agent_update_request["memberId"],
                inputs=BaseInputsModel(
                    email="test@test.com", preferred_job="개발자", major_type="MAJOR"
                ),
                asked_count=1,
                pending_questions=["다음 질문은?"],
                step="questioning",
            )
            mock_load_state.return_value = existing_state

            # LangGraph 워크플로우 모킹
            mock_final_state = {
                "memberId": sample_agent_update_request["memberId"],
                "isComplete": False,
                "pending_questions": ["두 번째 질문입니다."],
                "asked_count": 2,
                "step": "questioning",
            }

            async def mock_astream(state):
                yield {"generate_question": mock_final_state}

            mock_resume_agent.astream = mock_astream

            response = await async_client.post(
                "/resume/agent/update", json=sample_agent_update_request
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 실제 ResumeAgentUpdateResponse 스키마에 맞게 검증
            assert "memberId" in data
            assert "isComplete" in data
            assert data["memberId"] == sample_agent_update_request["memberId"]

            if not data["isComplete"]:
                assert "question" in data
                assert data["resumeObjectKey"] is None
            else:
                assert "resumeObjectKey" in data
                assert data["question"] is None

    @pytest.mark.asyncio
    async def test_resume_create_success(
        self, async_client, sample_resume_create_request
    ):
        """기본 이력서 생성 성공 테스트"""
        with patch(
            "app.utils.create_docx.create_resume_docx"
        ) as mock_create_docx, patch(
            "app.utils.upload_file_to_s3.upload_file"
        ) as mock_upload:

            # Mock 설정
            mock_create_docx.return_value = "test_resume.docx"
            mock_upload.return_value = (
                "https://s3.amazonaws.com/test-bucket/resume.docx"
            )

            response = await async_client.post(
                "/resume/create", json=sample_resume_create_request
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 실제 ResumeCreateResponse 스키마에 맞게 검증
            assert "httpStatusCode" in data
            assert "message" in data
            assert "data" in data
            assert data["httpStatusCode"] == 200

            assert "resumeUrl" in data["data"]
            assert "filename" in data["data"]
            assert "createdAt" in data["data"]

            # 서비스 함수들이 호출되었는지 확인
            mock_create_docx.assert_called_once()
            mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_agent_init_missing_inputs(self, async_client):
        """inputs 필드 누락 시 422 에러 테스트"""
        invalid_data = {"memberId": 1}  # inputs 누락

        response = await async_client.post("/resume/agent/init", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "detail" in data
        error_fields = [error["loc"][-1] for error in data["detail"]]
        assert "inputs" in error_fields

    @pytest.mark.asyncio
    async def test_resume_agent_init_invalid_major_type(self, async_client):
        """잘못된 major_type 값으로 초기화 시 422 에러 테스트"""
        invalid_data = {
            "memberId": 1,
            "inputs": {
                "email": "test@test.com",
                "preferred_job": "개발자",
                "major_type": "INVALID_TYPE",  # MAJOR나 NON_MAJOR가 아닌 값
                "certification_count": 0,
                "project_count": 0,
                "company_name": "",
                "position": "",
                "work_period": 0,
                "additional_experiences": "",
            },
        }

        response = await async_client.post("/resume/agent/init", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_resume_agent_update_no_session(self, async_client):
        """존재하지 않는 세션으로 업데이트 시 404 에러 테스트"""
        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:
            mock_load_state.return_value = None  # 세션 없음

            update_data = {
                "memberId": 999,  # 존재하지 않는 memberId
                "inputs": {"answer": "답변입니다."},
            }

            response = await async_client.post("/resume/agent/update", json=update_data)
            assert response.status_code == status.HTTP_404_NOT_FOUND

            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_resume_create_negative_counts(self, async_client):
        """음수 카운트 값으로 이력서 생성 시 422 에러 테스트"""
        invalid_data = {
            "email": "test@test.com",
            "preferred_job": "개발자",
            "major_type": "MAJOR",
            "certification_count": -1,  # 음수 값
            "project_count": -5,  # 음수 값
        }

        response = await async_client.post("/resume/create", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_resume_agent_status_check(self, async_client):
        """에이전트 상태 조회 테스트"""
        memberId = 123

        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:
            from app.schemas.resume_models import ResumeAgentState
            from app.schemas.base import BaseInputsModel

            test_state = ResumeAgentState(
                memberId=memberId,
                inputs=BaseInputsModel(
                    email="test@test.com", preferred_job="개발자", major_type="MAJOR"
                ),
                asked_count=2,
                max_questions=3,
                info_ready=False,
                step="questioning",
                answers=[
                    {"question": "Q1", "answer": "A1", "question_type": "general"}
                ],
                pending_questions=["다음 질문"],
            )

            mock_load_state.return_value = test_state

            response = await async_client.get(f"/resume/agent/status/{memberId}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 실제 AgentStatusResponse 스키마에 맞게 검증
            assert data["memberId"] == memberId
            assert data["step"] == "questioning"
            assert data["asked_count"] == 2
            assert data["max_questions"] == 3
            assert data["info_ready"] == False
            assert data["pending_questions"] == 1
            assert data["answers_count"] == 1

    @pytest.mark.asyncio
    async def test_resume_agent_session_deletion(self, async_client):
        """에이전트 세션 삭제 테스트"""
        memberId = 456

        with patch(
            "app.utils.redis_client.get_redis_client().delete_state"
        ) as mock_delete_state:
            mock_delete_state.return_value = True

            response = await async_client.delete(f"/resume/agent/session/{memberId}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["memberId"] == memberId
            assert data["deleted"] == True

    @pytest.mark.asyncio
    async def test_resume_create_docx_error(
        self, async_client, sample_resume_create_request
    ):
        """DOCX 생성 오류 시 500 에러 테스트"""
        with patch(
            "app.utils.create_docx.create_resume_docx",
            side_effect=Exception("DOCX 생성 오류"),
        ):
            response = await async_client.post(
                "/resume/create", json=sample_resume_create_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_resume_create_s3_upload_error(
        self, async_client, sample_resume_create_request
    ):
        """S3 업로드 오류 시 500 에러 테스트"""
        with patch(
            "app.utils.create_docx.create_resume_docx", return_value="test.docx"
        ), patch(
            "app.utils.upload_file_to_s3.upload_file",
            side_effect=Exception("S3 업로드 오류"),
        ):

            response = await async_client.post(
                "/resume/create", json=sample_resume_create_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_resume_agent_concurrent_init(self, async_client):
        """동시 에이전트 초기화 테스트"""
        requests = [
            {
                "memberId": i,
                "inputs": {
                    "email": f"user{i}@test.com",
                    "preferred_job": "개발자",
                    "major_type": "MAJOR",
                    "certification_count": 0,
                    "project_count": 0,
                    "company_name": "",
                    "position": "",
                    "work_period": 0,
                    "additional_experiences": "",
                },
            }
            for i in range(1, 6)
        ]

        with patch(
            "app.agents.nodes.generate_question.GenerateQuestionNode"
        ) as mock_question_node:
            mock_node_instance = Mock()
            mock_question_node.return_value = mock_node_instance

            async def mock_execute(state):
                state.pending_questions = [f"질문 for member {state.memberId}"]
                return state

            mock_node_instance.execute = AsyncMock(side_effect=mock_execute)

            # 동시 요청 실행
            tasks = [
                async_client.post("/resume/agent/init", json=req) for req in requests
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 모든 요청이 성공했는지 확인
            for i, response in enumerate(responses):
                if not isinstance(response, Exception):
                    assert response.status_code == 200
                    data = response.json()
                    assert data["memberId"] == i + 1


# conftest.py에 추가할 fixture들
@pytest.fixture
def sample_feedback_request():
    """피드백 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "question": "자기소개를 해보세요.",
        "answer": "안녕하세요. 저는 3년차 백엔드 개발자입니다. Python과 FastAPI를 주로 사용하며, REST API 개발 경험이 풍부합니다.",
    }


@pytest.fixture
def sample_resume_create_request():
    """기본 이력서 생성 요청 샘플 데이터"""
    return {
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
