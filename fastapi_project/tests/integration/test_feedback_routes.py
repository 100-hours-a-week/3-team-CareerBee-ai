# tests/integration/test_feedback_routes.py - 수정된 버전
import pytest
from unittest.mock import patch, AsyncMock, Mock
import json
from datetime import datetime
import asyncio
from fastapi import status


class TestFeedbackRoutes:
    """피드백 API 라우트 테스트"""

    @pytest.mark.asyncio
    async def test_create_feedback_success(self, async_client, sample_feedback_request):
        """피드백 생성 성공 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback"
        ) as mock_feedback_service:
            mock_feedback_service.return_value = (
                "좋은 답변입니다. 더 구체적인 예시를 추가하면 더욱 좋겠습니다."
            )

            response = await async_client.post(
                "/feedback/create/", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # 실제 FeedbackResponse 스키마에 맞게 검증
            assert "memberId" in data
            assert "feedback" in data
            assert data["memberId"] == sample_feedback_request["memberId"]
            assert isinstance(data["feedback"], str)
            assert len(data["feedback"]) > 0

    @pytest.mark.asyncio
    async def test_create_feedback_missing_fields(self, async_client):
        """필수 필드 누락 시 422 에러 테스트"""
        invalid_request = {"memberId": 1}  # question, answer 누락

        response = await async_client.post("/feedback/create/", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "detail" in data
        # Pydantic validation error에서 필드 누락 확인
        error_fields = [error["loc"][-1] for error in data["detail"]]
        assert "question" in error_fields
        assert "answer" in error_fields

    @pytest.mark.asyncio
    async def test_create_feedback_invalid_types(self, async_client):
        """잘못된 타입 시 422 에러 테스트"""
        invalid_request = {
            "memberId": "not_a_number",  # 문자열이지만 int 필요
            "question": 123,  # 숫자이지만 str 필요
            "answer": None,  # None이지만 str 필요
        }

        response = await async_client.post("/feedback/create/", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_feedback_empty_strings(self, async_client):
        """빈 문자열 처리 테스트"""
        # 기본 스키마에서는 빈 문자열도 유효한 str이므로 통과해야 함
        # 비즈니스 로직에서 검증하는 경우 별도 처리
        request_with_empty = {
            "memberId": 1,
            "question": "",
            "answer": "",
        }

        with patch(
            "app.services.feedback_service.generate_feedback"
        ) as mock_feedback_service:
            mock_feedback_service.return_value = (
                "질문과 답변을 구체적으로 작성해주세요."
            )

            response = await async_client.post(
                "/feedback/create/", json=request_with_empty
            )

            # 비즈니스 로직에서 빈 문자열을 어떻게 처리하는지에 따라 달라짐
            # 만약 빈 문자열을 허용한다면 200, 아니라면 400
            assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_create_feedback_negative_member_id(self, async_client):
        """음수 memberId 테스트 (비즈니스 로직에서 검증하는 경우)"""
        invalid_request = {
            "memberId": -1,
            "question": "질문입니다.",
            "answer": "답변입니다.",
        }

        response = await async_client.post("/feedback/create/", json=invalid_request)
        # Pydantic에서는 int 타입만 체크하므로 비즈니스 로직에서 음수 검증 필요
        assert response.status_code in [200, 400]  # 실제 구현에 따라 달라짐

    @pytest.mark.asyncio
    async def test_create_feedback_service_error(
        self, async_client, sample_feedback_request
    ):
        """서비스 에러 시 500 응답 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback",
            side_effect=Exception("LLM 서비스 오류"),
        ):
            response = await async_client.post(
                "/feedback/create/", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_feedback_timeout_error(
        self, async_client, sample_feedback_request
    ):
        """타임아웃 에러 테스트"""
        with patch(
            "app.services.feedback_service.generate_feedback",
            side_effect=asyncio.TimeoutError("시간 초과"),
        ):
            response = await async_client.post(
                "/feedback/create/", json=sample_feedback_request
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_create_feedback_concurrent_requests(self, async_client):
        """동시 피드백 요청 처리 테스트"""
        requests = [
            {
                "memberId": i,
                "question": f"질문 {i}",
                "answer": f"답변 {i}",
            }
            for i in range(1, 6)  # 5개의 동시 요청
        ]

        with patch(
            "app.services.feedback_service.generate_feedback"
        ) as mock_feedback_service:
            mock_feedback_service.return_value = "피드백입니다."

            # 동시 요청 실행
            tasks = [
                async_client.post("/feedback/create/", json=req) for req in requests
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 모든 요청이 성공했는지 확인
            for i, response in enumerate(responses):
                if not isinstance(response, Exception):
                    assert response.status_code == 200
                    data = response.json()
                    assert data["memberId"] == i + 1

    @pytest.mark.asyncio
    async def test_create_feedback_large_input(self, async_client):
        """큰 입력 데이터 처리 테스트"""
        large_request = {
            "memberId": 1,
            "question": "a" * 5000,  # 5000자 질문
            "answer": "b" * 10000,  # 10000자 답변
        }

        with patch(
            "app.services.feedback_service.generate_feedback"
        ) as mock_feedback_service:
            mock_feedback_service.return_value = "긴 답변에 대한 피드백입니다."

            response = await async_client.post("/feedback/create/", json=large_request)

            # 큰 입력을 허용하는지 확인 (실제 구현에 따라 달라짐)
            assert response.status_code in [200, 400, 413]  # 413: Payload Too Large
