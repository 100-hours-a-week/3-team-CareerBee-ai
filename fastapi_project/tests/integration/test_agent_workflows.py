# tests/integration/test_agent_workflows.py - 개선된 버전
import pytest
from unittest.mock import patch, AsyncMock, Mock
import json
from datetime import datetime
import asyncio


class TestAgentWorkflows:
    """실제 API 구조에 맞는 에이전트 워크플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_resume_agent_workflow(
        self, async_client, sample_agent_init_request, mock_redis
    ):
        """완전한 이력서 에이전트 워크플로우 테스트 (memberId 기반)"""

        memberId = sample_agent_init_request["memberId"]

        # 1. 에이전트 초기화
        with patch(
            "app.agents.nodes.generate_question.GenerateQuestionNode"
        ) as mock_question_node:
            # 첫 번째 질문 모킹
            mock_node_instance = Mock()
            mock_question_node.return_value = mock_node_instance

            async def mock_execute(state):
                state.pending_questions = [
                    "가장 자신있는 기술 스택이나 프로그래밍 언어는 무엇인가요?"
                ]
                return state

            mock_node_instance.execute = AsyncMock(side_effect=mock_execute)

            init_response = await async_client.post(
                "/resume/agent/init", json=sample_agent_init_request
            )

            assert init_response.status_code == 200
            init_data = init_response.json()

            assert "memberId" in init_data
            assert "question" in init_data
            assert init_data["memberId"] == memberId

            first_question = init_data["question"]
            assert len(first_question) > 0

        # 2. 첫 번째 답변 제공
        first_answer_request = {
            "memberId": memberId,
            "inputs": {"answer": "Python과 FastAPI를 주로 사용합니다."},
        }

        with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent:
            mock_final_state = self._create_mock_state(
                memberId,
                sample_agent_init_request["inputs"],
                asked_count=1,
                next_question="지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트는?",
            )

            # astream 모킹 - async generator
            async def mock_astream(state):
                yield {"generate_question": mock_final_state}

            mock_resume_agent.astream = mock_astream

            update_response = await async_client.post(
                "/resume/agent/update", json=first_answer_request
            )

            assert update_response.status_code == 200
            update_data = update_response.json()

            assert update_data["memberId"] == memberId
            assert update_data["isComplete"] == False
            assert "question" in update_data
            assert update_data["question"] == mock_final_state["pending_questions"][0]

        # 3. 두 번째 답변 제공
        second_answer_request = {
            "memberId": memberId,
            "inputs": {
                "answer": "REST API 서버를 개발한 프로젝트가 가장 인상깊었습니다."
            },
        }

        with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent:
            mock_final_state = self._create_mock_state(
                memberId,
                sample_agent_init_request["inputs"],
                asked_count=2,
                next_question="앞으로 어떤 개발자가 되고 싶으신가요?",
            )

            async def mock_astream(state):
                yield {"generate_question": mock_final_state}

            mock_resume_agent.astream = mock_astream

            update_response = await async_client.post(
                "/resume/agent/update", json=second_answer_request
            )

            assert update_response.status_code == 200
            update_data = update_response.json()

            assert update_data["isComplete"] == False
            assert "question" in update_data

        # 4. 마지막 답변 제공 및 이력서 생성 완료
        final_answer_request = {
            "memberId": memberId,
            "inputs": {
                "answer": "풀스택 개발자가 되어 사용자에게 가치있는 서비스를 만들고 싶습니다."
            },
        }

        with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent, patch(
            "app.utils.create_docx.create_resume_docx"
        ) as mock_create_docx, patch(
            "app.utils.upload_file_to_s3.upload_file"
        ) as mock_upload:

            # 이력서 생성 완료 상태
            mock_final_state = self._create_mock_state(
                memberId,
                sample_agent_init_request["inputs"],
                asked_count=3,
                completed=True,
                docx_path="resume/member_1_20240107_143022.docx",
            )

            # DOCX 생성 및 S3 업로드 모킹
            mock_create_docx.return_value = "resume_member_1.docx"
            mock_upload.return_value = (
                "https://s3.amazonaws.com/bucket/resume/member_1_20240107_143022.docx"
            )

            async def mock_astream(state):
                yield {"create_resume": mock_final_state}

            mock_resume_agent.astream = mock_astream

            final_response = await async_client.post(
                "/resume/agent/update", json=final_answer_request
            )

            assert final_response.status_code == 200
            final_data = final_response.json()

            assert final_data["memberId"] == memberId
            assert final_data["isComplete"] == True
            assert "resumeObjectKey" in final_data
            assert (
                final_data["resumeObjectKey"] == "resume/member_1_20240107_143022.docx"
            )
            assert final_data["question"] is None

    def _create_mock_state(
        self,
        memberId,
        inputs,
        asked_count=0,
        next_question=None,
        completed=False,
        docx_path="",
    ):
        """Mock 상태 생성 헬퍼 메서드"""
        return {
            "memberId": memberId,
            "inputs": inputs,
            "user_inputs": {},
            "answers": [],
            "pending_questions": (
                [next_question] if next_question and not completed else []
            ),
            "asked_count": asked_count,
            "max_questions": 3,
            "info_ready": completed,
            "resume": "# 이력서 내용\n\n생성된 이력서입니다." if completed else "",
            "docx_path": docx_path,
            "step": "completed" if completed else "questioning",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error_message": None,
            "error_details": None,
        }

    @pytest.mark.asyncio
    async def test_agent_init_existing_session(
        self, async_client, sample_agent_init_request, mock_redis
    ):
        """기존 세션이 있는 경우 초기화 테스트"""
        memberId = sample_agent_init_request["memberId"]

        with patch(
            "app.utils.redis_client.get_redis_client", return_value=mock_redis
        ), patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:

            from app.schemas.resume_models import ResumeAgentState
            from app.schemas.base import BaseInputsModel

            # 기존 상태 객체 생성
            existing_state = ResumeAgentState(
                memberId=memberId,
                inputs=BaseInputsModel(**sample_agent_init_request["inputs"]),
                pending_questions=["기존 진행중인 질문입니다."],
                asked_count=1,
                info_ready=False,
                step="questioning",
            )

            mock_load_state.return_value = existing_state

            init_response = await async_client.post(
                "/resume/agent/init", json=sample_agent_init_request
            )

            assert init_response.status_code == 200
            init_data = init_response.json()

            assert init_data["memberId"] == memberId
            assert init_data["question"] == "기존 진행중인 질문입니다."

    @pytest.mark.asyncio
    async def test_agent_status_check(self, async_client, mock_redis):
        """에이전트 상태 조회 테스트"""
        memberId = 123

        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:
            from app.schemas.resume_models import ResumeAgentState
            from app.schemas.base import BaseInputsModel

            # 상태 객체 생성
            test_state = ResumeAgentState(
                memberId=memberId,
                inputs=BaseInputsModel(
                    email="test@example.com", preferred_job="개발자", major_type="MAJOR"
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

            status_response = await async_client.get(f"/resume/agent/status/{memberId}")

            assert status_response.status_code == 200
            status_data = status_response.json()

            assert status_data["memberId"] == memberId
            assert status_data["step"] == "questioning"
            assert status_data["asked_count"] == 2
            assert status_data["max_questions"] == 3
            assert status_data["info_ready"] == False
            assert status_data["pending_questions"] == 1
            assert status_data["answers_count"] == 1

    @pytest.mark.asyncio
    async def test_agent_session_deletion(self, async_client, mock_redis):
        """에이전트 세션 삭제 테스트"""
        memberId = 456

        with patch(
            "app.utils.redis_client.get_redis_client().delete_state"
        ) as mock_delete_state:
            mock_delete_state.return_value = True

            delete_response = await async_client.delete(
                f"/resume/agent/session/{memberId}"
            )

            assert delete_response.status_code == 200
            delete_data = delete_response.json()

            assert delete_data["memberId"] == memberId
            assert delete_data["deleted"] == True
            assert "삭제되었습니다" in delete_data["message"]

    @pytest.mark.asyncio
    async def test_agent_health_check(self, async_client):
        """에이전트 헬스체크 테스트"""
        with patch(
            "app.utils.redis_client.get_redis_client().health_check"
        ) as mock_health_check:
            mock_health_check.return_value = {"status": "healthy", "connection": "ok"}

            health_response = await async_client.get("/resume/agent/health")

            assert health_response.status_code == 200
            health_data = health_response.json()

            assert health_data["agent_status"] == "healthy"
            assert "redis" in health_data
            assert "llm" in health_data
            assert "fallback_questions" in health_data

    @pytest.mark.asyncio
    async def test_concurrent_agent_sessions(self, async_client, mock_redis):
        """동시 에이전트 세션 처리 테스트"""
        member1_request = {
            "memberId": 1,
            "inputs": {
                "email": "user1@example.com",
                "preferred_job": "백엔드 개발자",
                "certification_count": 0,
                "project_count": 0,
                "major_type": "MAJOR",
                "company_name": "",
                "position": "",
                "work_period": 0,
                "additional_experiences": "",
            },
        }

        member2_request = {
            "memberId": 2,
            "inputs": {
                "email": "user2@example.com",
                "preferred_job": "프론트엔드 개발자",
                "certification_count": 0,
                "project_count": 0,
                "major_type": "NON_MAJOR",
                "company_name": "",
                "position": "",
                "work_period": 0,
                "additional_experiences": "",
            },
        }

        with patch(
            "app.agents.nodes.generate_question.GenerateQuestionNode"
        ) as mock_question_node:
            mock_node_instance = Mock()
            mock_question_node.return_value = mock_node_instance

            async def mock_execute(state):
                if state.memberId == 1:
                    state.pending_questions = ["백엔드 관련 질문입니다."]
                else:
                    state.pending_questions = ["프론트엔드 관련 질문입니다."]
                return state

            mock_node_instance.execute = AsyncMock(side_effect=mock_execute)

            # 동시 초기화 요청
            tasks = [
                async_client.post("/resume/agent/init", json=member1_request),
                async_client.post("/resume/agent/init", json=member2_request),
            ]

            responses = await asyncio.gather(*tasks)
            response1, response2 = responses

            assert response1.status_code == 200
            assert response2.status_code == 200

            data1 = response1.json()
            data2 = response2.json()

            # 각각 다른 memberId
            assert data1["memberId"] == 1
            assert data2["memberId"] == 2

            # 각각 다른 질문
            assert data1["question"] == "백엔드 관련 질문입니다."
            assert data2["question"] == "프론트엔드 관련 질문입니다."

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, async_client, sample_agent_init_request):
        """에이전트 오류 처리 테스트"""

        # Redis 연결 실패 시뮬레이션
        with patch(
            "app.utils.redis_client.get_redis_client().save_state"
        ) as mock_save_state:
            mock_save_state.side_effect = Exception("Redis connection failed")

            response = await async_client.post(
                "/resume/agent/init", json=sample_agent_init_request
            )

            # 실제 에러 응답 코드에 맞게 수정 필요
            assert response.status_code in [500, 503]  # 서버 에러 또는 서비스 불가
            error_data = response.json()

            assert "error" in error_data or "detail" in error_data

    @pytest.mark.asyncio
    async def test_agent_update_without_init(self, async_client):
        """초기화 없이 업데이트 시도 테스트"""
        update_request = {
            "memberId": 999,  # 존재하지 않는 memberId
            "inputs": {"answer": "답변입니다."},
        }

        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:
            mock_load_state.return_value = None  # 상태 없음

            response = await async_client.post(
                "/resume/agent/update", json=update_request
            )

            assert response.status_code == 404
            error_data = response.json()

            assert "detail" in error_data
            assert (
                "세션" in error_data["detail"]
                or "찾을 수 없습니다" in error_data["detail"]
            )

    @pytest.mark.asyncio
    async def test_agent_lock_mechanism(
        self, async_client, sample_agent_update_request
    ):
        """에이전트 락 메커니즘 테스트"""

        with patch(
            "app.utils.redis_client.get_redis_client().acquire_lock"
        ) as mock_acquire_lock:
            mock_acquire_lock.return_value = False  # 락 획득 실패

            response = await async_client.post(
                "/resume/agent/update", json=sample_agent_update_request
            )

            assert response.status_code == 409
            error_data = response.json()

            assert "detail" in error_data
            assert "진행 중" in error_data["detail"] or "이미" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(
        self, async_client, sample_agent_update_request
    ):
        """에이전트 타임아웃 처리 테스트"""

        with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent:
            # 타임아웃 시뮬레이션
            async def mock_astream_timeout(state):
                await asyncio.sleep(10)  # 긴 대기 시간
                yield {"timeout": state}

            mock_resume_agent.astream = mock_astream_timeout

            # 실제 구현에서 타임아웃 설정이 있다면 해당 시간보다 짧게 설정
            with patch("asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                response = await async_client.post(
                    "/resume/agent/update", json=sample_agent_update_request
                )

                # 타임아웃 시 예상되는 응답 코드
                assert response.status_code in [408, 500, 503]

    @pytest.mark.asyncio
    async def test_agent_partial_completion_recovery(
        self, async_client, sample_agent_init_request
    ):
        """부분 완료 상태에서 복구 테스트"""
        memberId = sample_agent_init_request["memberId"]

        with patch(
            "app.utils.redis_client.get_redis_client().load_state"
        ) as mock_load_state:
            from app.schemas.resume_models import ResumeAgentState
            from app.schemas.base import BaseInputsModel

            # 부분 완료 상태 (질문은 다 했지만 이력서 생성 중 실패)
            partial_state = ResumeAgentState(
                memberId=memberId,
                inputs=BaseInputsModel(**sample_agent_init_request["inputs"]),
                asked_count=3,
                max_questions=3,
                info_ready=False,  # 아직 완료되지 않음
                step="processing",
                answers=[
                    {"question": "Q1", "answer": "A1", "question_type": "general"},
                    {"question": "Q2", "answer": "A2", "question_type": "general"},
                    {"question": "Q3", "answer": "A3", "question_type": "general"},
                ],
                pending_questions=[],
            )

            mock_load_state.return_value = partial_state

            # 마지막 답변으로 완료 시도
            final_request = {
                "memberId": memberId,
                "inputs": {"answer": "이전 답변 완료"},
            }

            with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent:
                # 이번에는 성공적으로 완료
                completed_state = self._create_mock_state(
                    memberId,
                    sample_agent_init_request["inputs"],
                    asked_count=3,
                    completed=True,
                    docx_path="resume/member_1_recovered.docx",
                )

                async def mock_astream(state):
                    yield {"create_resume": completed_state}

                mock_resume_agent.astream = mock_astream

                response = await async_client.post(
                    "/resume/agent/update", json=final_request
                )

                assert response.status_code == 200
                data = response.json()
                assert data["isComplete"] == True
                assert data["resumeObjectKey"] == "resume/member_1_recovered.docx"

    @pytest.mark.asyncio
    async def test_invalid_member_id_types(self, async_client):
        """잘못된 memberId 타입 테스트"""
        invalid_requests = [
            {
                "memberId": "string_id",
                "inputs": {
                    "email": "test@test.com",
                    "preferred_job": "dev",
                    "major_type": "MAJOR",
                },
            },
            {
                "memberId": -1,
                "inputs": {
                    "email": "test@test.com",
                    "preferred_job": "dev",
                    "major_type": "MAJOR",
                },
            },
            {
                "memberId": 0,
                "inputs": {
                    "email": "test@test.com",
                    "preferred_job": "dev",
                    "major_type": "MAJOR",
                },
            },
        ]

        for invalid_request in invalid_requests:
            response = await async_client.post(
                "/resume/agent/init", json=invalid_request
            )
            assert response.status_code == 422  # Validation Error


# 추가로 만들 수 있는 테스트 파일들:


# tests/integration/test_feedback_workflows.py
class TestFeedbackWorkflows:
    """피드백 워크플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_feedback_workflow(self, async_client):
        """완전한 피드백 생성 워크플로우 테스트"""
        feedback_request = {
            "memberId": 1,
            "question": "자기소개를 해보세요.",
            "answer": "안녕하세요. 저는 3년차 백엔드 개발자입니다.",
        }

        with patch(
            "app.services.feedback_service.create_feedback"
        ) as mock_create_feedback:
            mock_create_feedback.return_value = (
                "구체적인 경험과 기술 스택을 추가하면 더 좋겠습니다."
            )

            response = await async_client.post(
                "/feedback/create/", json=feedback_request
            )

            assert response.status_code == 200
            data = response.json()
            assert data["memberId"] == 1
            assert "피드백" in data["feedback"] or len(data["feedback"]) > 0

    @pytest.mark.asyncio
    async def test_feedback_error_handling(self, async_client):
        """피드백 생성 오류 처리 테스트"""
        feedback_request = {
            "memberId": 1,
            "question": "자기소개를 해보세요.",
            "answer": "안녕하세요.",
        }

        with patch(
            "app.services.feedback_service.create_feedback"
        ) as mock_create_feedback:
            mock_create_feedback.side_effect = Exception("LLM 서비스 오류")

            response = await async_client.post(
                "/feedback/create/", json=feedback_request
            )

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data or "error" in error_data
