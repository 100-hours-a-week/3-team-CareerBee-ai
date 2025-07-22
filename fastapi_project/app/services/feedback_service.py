import os
import aiohttp
import re
from transformers import pipeline

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8001")
MODEL_NAME = "/mnt/ssd/aya-expanse-8b"

classifier = pipeline("text-classification", model="smilegate-ai/kor_unsmile")


def is_safe_with_model(text: str) -> bool:
    predictions = classifier(text)
    for pred in predictions:
        if pred["label"] == "toxicity" and pred["score"] > 0.8:
            return False
    return True


def build_feedback_prompt(question: str, answer: str) -> str:

    user_prompt = (
        f"[질문]\n{question}\n"
        f"[답변]\n{answer}\n"
        "**다음 기준에 따라 문체는 간결하게, 문장 도중에 끊기지 않도록 의미 단위로 마무리해 주세요.**\n"
        "답변은 항상 정중하고 전문적인 언어를 사용해야 하며, 비하, 모욕, 차별적 표현은 절대 포함하지 마세요.\n"
        "전체 피드백은 한글 기준 띄어쓰기 포함 450자 이내여야 하며, 다음 형식을 참고해 주세요: \n\n"
        "프록시 서버의 개념을 이해하고 있으나 몇 가지 핵심 설명이 빠져 있습니다.\n"
        "**긍정적인 점:**\n- 중개자 역할을 인지하고 있음\n"
        "**보완할 점:**\n- 보안 외의 주요 기능 예시 부족, 구체적인 사용 사례 추가 필요\n\n"
        "위와 같이 자연스러운 글 형태로 피드백을 작성하세요. '답변 분석:', '피드백:' 같은 표현은 생략해주세요.\n\n"
        "피드백:"
    )

    return f"{user_prompt}"


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
                            "content": "당신은 컴퓨터공학 전문가이며, 컴퓨터공학 관련 질문에 대한 답변을 평가하고 개선 방향을 제안하는 역할을 합니다. 답변이 핵심을 잘 짚었는지, 부족하거나 부정확한 점은 없는지 파악한 후, 문장 도중 끊김 없이 자연스럽고 간결한 문체로 피드백을 작성하세요. '피드백:'이나 '분석:' 같은 메타 표현은 쓰지 말고, 긍정적인 점과 보완할 점을 구분해 작성하면 좋습니다. 피드백은 한글 기준 450자 이내여야 합니다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 350,
                    "temperature": 0.7,
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                result = await response.json()
                repsonse_text = result["choices"][0]["message"]["content"].strip()
                if not is_safe_with_model(repsonse_text):
                    raise ValueError("안전하지 않은 응답이 감지되었습니다.")
                return repsonse_text

    except aiohttp.ClientError as e:
        raise RuntimeError(f"LLM API 요청 실패: {str(e)}")
