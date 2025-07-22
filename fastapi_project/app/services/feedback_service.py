import os
import aiohttp
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
from typing import Tuple, Dict, List
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8001")
MODEL_NAME = "/mnt/ssd/aya-expanse-8b"

# safety model 초기화
tokenizer = AutoTokenizer.from_pretrained("smilegate-ai/kor_unsmile")
model = AutoModelForSequenceClassification.from_pretrained("smilegate-ai/kor_unsmile")

labels = [
    "none",
    "gender",
    "others",
    "origin",
    "religion",
    "age",
    "race",
    "disability",
    "sexual_orientaion",
    "nationality",
]

classifier = pipeline("text-classification", model="smilegate-ai/kor_unsmile")


class SafetyFilterError(Exception):
    """안전성 필터 관련 에러"""

    pass


def is_toxic(text: str, threshold: float = 0.8) -> Tuple[bool, Dict[str, float]]:
    """텍스트의 유해성을 검사합니다.

    Args:
        text: 검사할 텍스트
        threshold: 유해성 판단 임계값

    Returns:
        (is_toxic, scores): 유해성 여부와 각 라벨별 점수
    """
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits)[0]

        scores = {}
        toxic_labels = []

        for label, score in zip(labels, probs):
            score_value = score.item()
            scores[label] = score_value

            if label != "none" and score_value > threshold:
                toxic_labels.append((label, score_value))

        is_toxic_result = len(toxic_labels) > 0

        if is_toxic_result:
            logger.warning(f"유해 콘텐츠 감지: {toxic_labels}")

        return is_toxic_result, scores

    except Exception as e:
        logger.error(f"유해성 검사 중 오류 발생: {str(e)}")
        # 오류 발생 시 안전을 위해 유해하다고 판단
        return True, {}


def validate_input(question: str, answer: str) -> None:
    """사용자 입력의 안전성을 검증합니다.

    Args:
        question: 면접 질문
        answer: 사용자 답변

    Raises:
        SafetyFilterError: 유해한 내용이 감지된 경우
    """
    # 질문 검증
    is_question_toxic, question_scores = is_toxic(question)
    if is_question_toxic:
        raise SafetyFilterError(
            "질문에 부적절한 내용이 포함되어 있습니다. "
            "다른 질문으로 다시 시도해 주세요."
        )

    # 답변 검증
    is_answer_toxic, answer_scores = is_toxic(answer)
    if is_answer_toxic:
        raise SafetyFilterError(
            "답변에 부적절한 내용이 포함되어 있습니다. "
            "답변을 수정한 후 다시 시도해 주세요."
        )


def build_feedback_prompt(question: str, answer: str) -> str:
    """피드백 생성을 위한 프롬프트를 구성합니다."""
    user_prompt = f"[질문]\n{question}\n[답변]\n{answer}\n---\n\
        - 문체: 간결하고 자연스럽게\n- 형식: '긍정적인 점 / 보완할 점' 구조\n\
        - 금지: '피드백:', '분석:' 등의 표현 금지\n- 전체 450자 이내\n\
        - 예시: 프록시 서버의 개념을 이해하고 있으나 몇 가지 핵심 설명이 빠져 있습니다.\n\
        긍정적인 점:\n- 중개자 역할을 인지하고 있음\n보완할 점:\n- 보안 외 기능 예시 부족\n\n\
        이 기준에 따라 피드백을 작성하세요."

    return user_prompt


async def generate_feedback(question: str, answer: str) -> str:
    """
    안전성 검증을 거친 피드백을 생성합니다.

    Args:
        question: 면접 질문
        answer: 사용자 답변

    Returns:
        생성된 피드백 텍스트

    Raises:
        SafetyFilterError: 안전성 검증 실패
        RuntimeError: API 요청 실패
    """
    # 1. 입력 안전성 검증
    try:
        validate_input(question, answer)
    except SafetyFilterError as e:
        logger.error(f"입력 검증 실패: {str(e)}")
        raise

    # 2. 프롬프트 생성
    prompt = build_feedback_prompt(question, answer)

    # 3. LLM API 호출
    try:
        logger.info("피드백 생성 중...")
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
                    "max_tokens": 250,
                    "temperature": 0.7,
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                result = await response.json()
                response_text = result["choices"][0]["message"]["content"].strip()
                # 4. 응답 안전성 검증
                is_response_toxic, response_scores = is_toxic(response_text)
                if is_response_toxic:
                    logger.error("생성된 피드백에 부적절한 내용이 포함되어 있습니다.")
                    # 재시도 또는 기본 응답 반환
                    return (
                        "죄송합니다. 적절한 피드백을 생성하는 데 문제가 발생했습니다. "
                        "다시 시도해주세요."
                    )
                logger.info("피드백 생성 완료")
                return response_text

    except aiohttp.ClientError as e:
        logger.error(f"LLM API 요청 실패: {str(e)}")
        raise RuntimeError(f"피드백 생성 중 오류가 발생했습니다: {str(e)}")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        raise RuntimeError(f"피드백 생성 중 오류가 발생했습니다: {str(e)}")
