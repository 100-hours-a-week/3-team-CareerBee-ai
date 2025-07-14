# tests/conftest.py 수정 부분 - 새로운 fixture 추가
import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture
def sample_agent_init_request():
    """이력서 에이전트 초기화 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "inputs": {
            "email": "hong@example.com",
            "preferred_job": "백엔드 개발자",
            "certification_count": 3,
            "project_count": 5,
            "major_type": "MAJOR",
            "company_name": "테크 스타트업",
            "position": "주니어 개발자",
            "work_period": 24,
            "additional_experiences": "오픈소스 프로젝트 기여, 해커톤 수상 경험",
        },
    }


@pytest.fixture
def sample_agent_update_request():
    """이력서 에이전트 업데이트 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "inputs": {
            "answer": "Python과 FastAPI를 주로 사용하며, 3년간의 웹 개발 경험이 있습니다."
        },
    }


@pytest.fixture
def mock_resume_agent_state():
    """Redis에 저장될 ResumeAgentState 모킹 데이터"""
    from app.schemas.resume_models import ResumeAgentState
    from app.schemas.base import BaseInputsModel
    from datetime import datetime

    return {
        "memberId": 1,
        "inputs": {
            "email": "test@example.com",
            "preferred_job": "개발자",
            "certification_count": 2,
            "project_count": 3,
            "major_type": "MAJOR",
            "company_name": "회사",
            "position": "개발자",
            "work_period": 12,
            "additional_experiences": "경험",
        },
        "user_inputs": {"질문1": "답변1"},
        "answers": [
            {"question": "질문1", "answer": "답변1", "question_type": "general"}
        ],
        "pending_questions": ["다음 질문은 무엇인가요?"],
        "asked_count": 1,
        "max_questions": 3,
        "info_ready": False,
        "resume": "",
        "docx_path": "",
        "step": "questioning",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error_message": None,
        "error_details": None,
    }


# tests/integration/test_agent_workflows.py 완전 수정
import pytest
from unittest.mock import patch, AsyncMock, Mock
import json
from datetime import datetime


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

            # mock_node_instance.execute 메서드 모킹
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
            # LangGraph 워크플로우 모킹
            mock_final_state = {
                "memberId": memberId,
                "inputs": sample_agent_init_request["inputs"],
                "user_inputs": {first_question: "Python과 FastAPI를 주로 사용합니다."},
                "answers": [
                    {
                        "question": first_question,
                        "answer": "Python과 FastAPI를 주로 사용합니다.",
                        "question_type": "general",
                    }
                ],
                "pending_questions": [
                    "지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트는?"
                ],
                "asked_count": 1,
                "max_questions": 3,
                "info_ready": False,
                "resume": "",
                "docx_path": "",
                "step": "questioning",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "error_message": None,
                "error_details": None,
            }

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
            assert (
                update_data["question"]
                == "지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트는?"
            )

        # 3. 두 번째 답변 제공
        second_answer_request = {
            "memberId": memberId,
            "inputs": {
                "answer": "REST API 서버를 개발한 프로젝트가 가장 인상깊었습니다."
            },
        }

        with patch("app.agents.resume_agent.resume_agent") as mock_resume_agent:
            # 세 번째 질문을 위한 상태
            mock_final_state["asked_count"] = 2
            mock_final_state["answers"].append(
                {
                    "question": "지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트는?",
                    "answer": "REST API 서버를 개발한 프로젝트가 가장 인상깊었습니다.",
                    "question_type": "general",
                }
            )
            mock_final_state["pending_questions"] = [
                "앞으로 어떤 개발자가 되고 싶으신가요?"
            ]

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
            mock_final_state["asked_count"] = 3
            mock_final_state["info_ready"] = True
            mock_final_state["step"] = "completed"
            mock_final_state["pending_questions"] = []
            mock_final_state["docx_path"] = "resume/member_1_20240107_143022.docx"
            mock_final_state["resume"] = "# 이력서 내용\n\n생성된 이력서입니다."

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

    @pytest.mark.asyncio
    async def test_agent_init_existing_session(
        self, async_client, sample_agent_init_request, mock_redis
    ):
        """기존 세션이 있는 경우 초기화 테스트"""
        memberId = sample_agent_init_request["memberId"]

        # Redis에 기존 상태 설정
        existing_state_data = {
            "memberId": memberId,
            "pending_questions": ["기존 진행중인 질문입니다."],
            "asked_count": 1,
            "info_ready": False,
            "step": "questioning",
        }

        # Mock Redis에 기존 상태 저장
        redis_key = f"resume_session:{memberId}"
        mock_redis.set(redis_key, json.dumps(existing_state_data))

        with patch("app.utils.redis_client.get_redis_client", return_value=mock_redis):
            # Redis 클라이언트의 load_state 메서드 모킹
            with patch(
                "app.utils.redis_client.get_redis_client().load_state"
            ) as mock_load_state:
                from app.schemas.resume_models import ResumeAgentState

                # 기존 상태 객체 생성
                existing_state = ResumeAgentState(
                    memberId=memberId,
                    inputs=sample_agent_init_request["inputs"],
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
                answers=[{"question": "Q1", "answer": "A1"}],
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
                "major_type": "MAJOR",
            },
        }

        member2_request = {
            "memberId": 2,
            "inputs": {
                "email": "user2@example.com",
                "preferred_job": "프론트엔드 개발자",
                "major_type": "NON_MAJOR",
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
            response1 = await async_client.post(
                "/resume/agent/init", json=member1_request
            )
            response2 = await async_client.post(
                "/resume/agent/init", json=member2_request
            )

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
            mock_save_state.return_value = False  # 저장 실패

            response = await async_client.post(
                "/resume/agent/init", json=sample_agent_init_request
            )

            assert response.status_code == 500
            error_data = response.json()

            assert "상태 저장에 실패했습니다" in error_data["message"]

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

            assert "세션을 찾을 수 없습니다" in error_data["detail"]

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

            assert "이미 진행 중입니다" in error_data["detail"]
