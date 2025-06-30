import os
import asyncio
import aiohttp
import logging
from typing import Optional, Union
from langchain_openai import ChatOpenAI


class LLMClient:
    """OpenAI와 VLLM을 통합하여 사용할 수 있는 LLM 클라이언트"""

    def __init__(self, temperature: float = 0.3):
        self.temperature = temperature
        self.logger = logging.getLogger(self.__class__.__name__)

        # 환경 변수 설정
        self.llm_type = os.getenv("LLM_TYPE", "openai")  # openai, vllm
        self.vllm_url = os.getenv("VLLM_URL", "http://localhost:8000")
        self.model_name = os.getenv("MODEL_NAME", "CohereLabs/aya-expanse-8b")

        self.logger.info(f"LLM 타입: {self.llm_type}")

        # OpenAI 클라이언트 초기화 (fallback용)
        if self.llm_type == "openai":
            self.openai_client = ChatOpenAI(
                model="gpt-3.5-turbo", temperature=temperature
            )
        else:
            self.openai_client = None

        self.logger.info(
            f"LLM 초기화 완료 - 타입: {self.llm_type}, 모델: {self.model_name}"
        )

    async def ainvoke(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> "LLMResponse":
        """비동기 LLM 호출"""

        if self.llm_type == "vllm":
            return await self._call_vllm(prompt, system_prompt)
        else:
            return await self._call_openai(prompt, system_prompt)

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> "LLMResponse":
        """동기 LLM 호출 (비동기 래핑)"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.ainvoke(prompt, system_prompt))
        except RuntimeError:
            # 이미 이벤트 루프가 실행 중인 경우
            import nest_asyncio

            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.ainvoke(prompt, system_prompt))

    async def _call_vllm(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> "LLMResponse":
        """VLLM API 호출"""

        # 시스템 프롬프트 설정
        if system_prompt is None:
            system_prompt = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 요청에 정확하고 상세하게 답변해주세요."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            self.logger.debug(f"VLLM 호출: {self.vllm_url}")

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            ) as session:
                async with session.post(
                    url=f"{self.vllm_url}/v1/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "max_tokens": 1024,
                        "temperature": self.temperature,
                    },
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    content = result["choices"][0]["message"]["content"].strip()
                    self.logger.debug(f"VLLM 응답 길이: {len(content)} 글자")

                    return LLMResponse(content)

        except aiohttp.ClientError as e:
            self.logger.error(f"VLLM 호출 실패: {e}")
            error_msg = f"VLLM 호출 중 오류 발생: {str(e)}"
            return LLMResponse(error_msg)
        except Exception as e:
            self.logger.error(f"예상치 못한 VLLM 오류: {e}")
            error_msg = f"LLM 처리 중 오류 발생: {str(e)}"
            return LLMResponse(error_msg)

    async def _call_openai(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> "LLMResponse":
        """OpenAI API 호출"""

        try:
            if system_prompt:
                # 시스템 프롬프트가 있는 경우
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

            self.logger.debug("OpenAI 호출 시작")
            response = await self.openai_client.ainvoke(full_prompt)

            content = (
                response.content.strip()
                if hasattr(response, "content")
                else str(response)
            )
            self.logger.debug(f"OpenAI 응답 길이: {len(content)} 글자")

            return LLMResponse(content)

        except Exception as e:
            self.logger.error(f"OpenAI 호출 실패: {e}")
            error_msg = f"OpenAI 호출 중 오류 발생: {str(e)}"
            return LLMResponse(error_msg)


class LLMResponse:
    """LLM 응답을 표준화하는 클래스"""

    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"LLMResponse(content='{self.content[:50]}...')"


# 전역 LLM 클라이언트 팩토리
def create_llm_client(temperature: float = 0.3) -> LLMClient:
    """LLM 클라이언트 생성 팩토리 함수"""
    return LLMClient(temperature=temperature)


# 기존 ChatOpenAI 호환성을 위한 래퍼
class ChatLLM:
    """기존 ChatOpenAI와 호환되는 인터페이스"""

    def __init__(self, model: str = "gpt-3.5-turbo", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        self.client = create_llm_client(temperature)

    async def ainvoke(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """시스템 프롬프트를 지원하는 ainvoke 메서드"""
        return await self.client.ainvoke(prompt, system_prompt)

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """시스템 프롬프트를 지원하는 invoke 메서드"""
        return self.client.invoke(prompt, system_prompt)
