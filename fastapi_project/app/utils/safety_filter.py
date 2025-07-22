# app/utils/safety_filter.py
"""공용 Safety Filter 모듈"""
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

# 전역 변수로 모델 로드 (한 번만 로드)
_tokenizer = None
_model = None


def _load_safety_model():
    """Safety 모델을 로드 (lazy loading)"""
    global _tokenizer, _model
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained("smilegate-ai/kor_unsmile")
        _model = AutoModelForSequenceClassification.from_pretrained(
            "smilegate-ai/kor_unsmile"
        )
    return _tokenizer, _model


class SafetyFilterError(Exception):
    """안전성 필터 관련 에러"""

    pass


def is_toxic(text: str, threshold: float = 0.8) -> Tuple[bool, Dict[str, float]]:
    """
    텍스트의 유해성을 검사합니다.

    Args:
        text: 검사할 텍스트
        threshold: 유해성 판단 임계값

    Returns:
        (is_toxic, scores): 유해성 여부와 각 라벨별 점수
    """
    if not text or not isinstance(text, str):
        return False, {}

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

    try:
        tokenizer, model = _load_safety_model()
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
    """
    사용자 입력의 안전성을 검증합니다.

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
