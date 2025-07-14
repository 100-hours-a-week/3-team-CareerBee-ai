# tests/integration/test_resume_routes.py
import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import status
import json


class TestResumeRoutes:
    """이력서 관련 API 라우트 테스트"""

    @pytest.mark.asyncio
    async def test_resume_agent_init_success(self, async_client, mock_redis):
        """이력서 에이전트 초기화 성공 테스트"""
        request_data = {"memberId": 1}

        response = await async_client.post("/resume/agent/init", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "sessionId" in data
        assert data["message"] == "에이전트 초기화 완료"

        # Redis에 세션이 저장되었는지 확인
        session_id = data["sessionId"]
        stored_data = mock_redis.get(f"resume_session:{session_id}")
        assert stored_data is not None

    @pytest.mark.asyncio
    async def test_resume_agent_update_success(
        self, async_client, mock_redis, sample_resume_data
    ):
        """이력서 에이전트 업데이트 성공 테스트"""
        # 먼저 세션 초기화
        init_response = await async_client.post(
            "/resume/agent/init", json={"memberId": 1}
        )
        session_id = init_response.json()["sessionId"]

        # 업데이트 요청
        update_data = {
            "sessionId": session_id,
            "action": "add_experience",
            "data": sample_resume_data["experiences"][0],
        }

        response = await async_client.post("/resume/agent/update", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "에이전트 상태 업데이트 완료"

    @pytest.mark.asyncio
    async def test_resume_create_success(
        self, async_client, sample_resume_data, mock_s3, mock_redis
    ):
        """이력서 생성 성공 테스트"""
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
                "/resume/create", json=sample_resume_data
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["message"] == "이력서 생성 완료"
            assert "downloadUrl" in data["data"]
            assert data["data"]["downloadUrl"].startswith("https://")

            # 서비스 함수들이 호출되었는지 확인
            mock_create_docx.assert_called_once()
            mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_create_invalid_data(self, async_client):
        """잘못된 이력서 데이터로 생성 요청 시 400 에러 테스트"""
        invalid_data = {
            "memberId": 1
            # personal_info 누락
        }

        response = await async_client.post("/resume/create", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_resume_agent_init_invalid_member_id(self, async_client):
        """잘못된 memberId로 에이전트 초기화 시 400 에러 테스트"""
        invalid_data = {"memberId": -1}

        response = await async_client.post("/resume/agent/init", json=invalid_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_resume_agent_update_invalid_session(self, async_client):
        """존재하지 않는 세션으로 업데이트 시 400 에러 테스트"""
        update_data = {
            "sessionId": "non-existent-session",
            "action": "add_experience",
            "data": {},
        }

        response = await async_client.post("/resume/agent/update", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert "세션을 찾을 수 없습니다" in data["detail"]

    @pytest.mark.asyncio
    async def test_resume_create_docx_error(self, async_client, sample_resume_data):
        """DOCX 생성 오류 시 500 에러 테스트"""
        with patch(
            "app.utils.create_docx.create_resume_docx",
            side_effect=Exception("DOCX 생성 오류"),
        ):
            response = await async_client.post(
                "/resume/create", json=sample_resume_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["message"] == "internal_server_error"

    @pytest.mark.asyncio
    async def test_resume_create_s3_upload_error(
        self, async_client, sample_resume_data
    ):
        """S3 업로드 오류 시 500 에러 테스트"""
        with patch(
            "app.utils.create_docx.create_resume_docx", return_value="test.docx"
        ), patch(
            "app.utils.upload_file_to_s3.upload_file",
            side_effect=Exception("S3 업로드 오류"),
        ):

            response = await async_client.post(
                "/resume/create", json=sample_resume_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
