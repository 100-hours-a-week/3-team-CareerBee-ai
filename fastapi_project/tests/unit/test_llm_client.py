# tests/unit/test_llm_client.py
import pytest
from unittest.mock import patch, AsyncMock
from app.utils.llm_client import LLMClient


class TestLLMClient:
    """LLM 클라이언트 단위 테스트"""

    @pytest.fixture
    def llm_client(self):
        return LLMClient()

    @pytest.mark.asyncio
    async def test_generate_feedback_success(self, llm_client):
        """피드백 생성 성공 테스트"""
        with patch("openai.ChatCompletion.acreate") as mock_openai:
            mock_openai.return_value = {
                "choices": [{"message": {"content": "좋은 답변입니다."}}]
            }

            result = await llm_client.generate_feedback("질문", "답변")

            assert result == "좋은 답변입니다."
            mock_openai.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_feedback_api_error(self, llm_client):
        """OpenAI API 오류 테스트"""
        with patch("openai.ChatCompletion.acreate", side_effect=Exception("API 오류")):
            with pytest.raises(Exception):
                await llm_client.generate_feedback("질문", "답변")
