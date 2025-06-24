import os
import requests
import time
import aiohttp
import asyncio

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8001")
MODEL_NAME = "/mnt/ssd/aya-expanse-8b"


def build_feedback_prompt(question: str, answer: str) -> str:
  
    user_prompt = (
        f"[질문]\n{question}\n"
        f"[답변]\n{answer}\n"
        "다음 기준을 바탕으로 친절하고 구체적인 피드백을 3~5문장으로 작성해주세요:\n"
        "- 답변이 질문의 핵심을 이해하고 있는지\n"
        "- 틀린 내용이나 부족한 설명이 있는지\n"
        "- 어떤 내용을 보완하면 더 좋은 답변이 되는지\n"
        "문장 도중에 끊지 말고, 의미 단위로 문장을 마무리한 뒤 출력을 종료해주세요.\n\n"
        "피드백:"
    )

    return f"{user_prompt}"


# async + aiohttp 로 비동기 방식 전환
async def generate_feedback(question: str, answer: str) -> str:
    prompt = build_feedback_prompt(question, answer)

    try:
        print("VLLM_URL:", VLLM_URL)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            async with session.post(
                url=f"{VLLM_URL}/v1/chat/completions",
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 컴퓨터공학 면접관입니다. 당신의 질문에 대한 지원자 답변을 보고 면접에 합격하기 위해 어떤 점이 보완되면 좋겠는지 피드백해주세요.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()

    except aiohttp.ClientError as e:
        return f"피드백 생성 중 오류 발생: {str(e)}"
