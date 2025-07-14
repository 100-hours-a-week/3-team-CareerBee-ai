# tests/integration/test_feedback_routes.py
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import status


class TestFeedbackRoutes:
    """피드백 API 라우트 테스트"""

    @pytest.mark.asyncio
    async def test_create_feedback_success(
        self, async_client, sample_feedback_request, mock_llm_client
    ):
        """피드백 생성 성공 테스트"""
        response = await async_client.post(
            "/feedback/create", json=sample_feedback_request
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["httpStatusCode"] == 200
        assert data["message"] == "feedback_success"
        assert "data" in data
        assert "feedback" in data["data"]
        assert "memberId" in data["data"]
        assert data["data"]["memberId"] == sample_feedback_request["memberId"]

    @pytest.mark.asyncio
    async def test_create_feedback_missing_question(self, async_client):
        """질문 누락 시 400 에러 테스트"""
        invalid_request = {"memberId": 1, "answer": "답변만 있습니다."}

        response = await async_client.post("/feedback/create", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_feedback_empty_question(self, async_client):
        """빈 질문 시 400 에러 테스트"""
        invalid_request = {"memberId": 1, "question": "", "answer": "답변입니다."}

        response = await async_client.post("/feedback/create", json=invalid_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["message"] == "invalid_request"
        assert "질문은 필수입니다" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_feedback_empty_answer(self, async_client):
        """빈 답변 시 400 에러 테스트"""
        invalid_request = {
            "memberId": 1,
            "question": "질문입니다.",
            "answer": "   ",  # 공백만 있는 경우
        }

        response = await async_client.post("/feedback/create", json=invalid_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["message"] == "invalid_request"
        assert "답변은 필수입니다" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_feedback_invalid_member_id(self, async_client):
        """잘못된 memberId 테스트"""
        invalid_request = {
            "memberId": -1,
            "question": "질문입니다.",
            "answer": "답변입니다.",
        }

        response = await async_client.post("/feedback/create", json=invalid_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_feedback_question_too_long(self, async_client):
        """질문이 너무 긴 경우 테스트"""
        long_question = "a" * 1001  # 1000자 초과

        invalid_request = {
            "memberId": 1,
            "question": long_question,
            "answer": "답변입니다.",
        }

        response = await async_client.post("/feedback/create", json=invalid_request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert "질문은 최대 1000자까지" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_feedback_service_error(
        self, async_client, sample_feedback_request
    ):
        """서비스 에러 시 500 응답 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback",
            side_effect=Exception("서비스 오류"),
        ):
            response = await async_client.post(
                "/feedback/create", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["message"] == "internal_server_error"

    @pytest.mark.asyncio
    async def test_create_feedback_timeout_error(
        self, async_client, sample_feedback_request
    ):
        """타임아웃 에러 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback",
            side_effect=TimeoutError("시간 초과"),
        ):
            response = await async_client.post(
                "/feedback/create", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "요청 처리 시간이 초과되었습니다" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_feedback_connection_error(
        self, async_client, sample_feedback_request
    ):
        """연결 에러 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback",
            side_effect=ConnectionError("연결 실패"),
        ):
            response = await async_client.post(
                "/feedback/create", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "외부 서비스 연결에 실패했습니다" in data["detail"]
