import requests
import os
import time

VLLM_URL = os.getenv("VLLM_URL", "http://34.170.200.212:8000")
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"


def build_feedback_prompt(question: str, answer: str) -> str:
    few_shot_examples = [
        {
            "question": "LSTM이 기울기 소실 문제를 해결하는 핵심 구조적 특징을 설명해주세요.",
            "answer": "LSTM은 RNN보다 좋아서 기울기 소실이 안 생깁니다.",
            "feedback": "피드백: LSTM이 RNN보다 개선된 점을 언급했지만, 질문의 핵심인 구조적 특징에 대한 설명이 없습니다. "
            "LSTM은 셀 상태(cell state)와 게이트 메커니즘(입력 게이트, 삭제 게이트, 출력 게이트)을 통해 정보 흐름을 조절함으로써 기울기 소실 문제를 완화합니다. "
            "이러한 핵심 구조에 대한 이해와 설명을 하면 더 좋은 답변이 될 것입니다.",
        },
        {
            "question": "LSTM이 기울기 소실 문제를 해결하는 핵심 구조적 특징을 설명해주세요.",
            "answer": "LSTM은 게이트를 사용해서 정보를 잘 조절하니까 기울기 소실 문제가 덜해요. 그래서 일반 RNN보다 긴 시퀀스 학습에 더 적합합니다.",
            "feedback": "피드백: LSTM이 게이트를 통해 정보를 조절한다는 점을 언급하여 핵심 개념의 일부를 이해한 것으로 보입니다. "
            "하지만 ‘게이트’가 무엇이며, 어떻게 기울기 소실을 완화하는지에 대한 구체적인 설명이 부족합니다. "
            "입력 게이트, 삭제 게이트, 출력 게이트의 역할을 함께 언급하면 더 완성도 높은 답변이 될 것입니다.",
        },
        {
            "question": "LSTM이 기울기 소실 문제를 해결하는 핵심 구조적 특징을 설명해주세요.",
            "answer": "LSTM은 셀 상태(cell state)를 유지하면서 정보를 장기간 보존할 수 있는 구조로, 기울기 소실 문제를 완화합니다. "
            "특히 입력 게이트, 삭제 게이트, 출력 게이트로 구성된 게이트 메커니즘이 중요 정보를 선택적으로 전달하거나 차단하여 안정적인 역전파가 가능합니다.",
            "feedback": "피드백: LSTM의 핵심 구조와 기울기 소실 완화 방식에 대해 정확히 설명했습니다. "
            "특히 셀 상태 유지와 게이트 메커니즘의 기능을 명확히 짚은 점이 인상적입니다. "
            "추가로, 왜 일반 RNN에서는 이러한 구조가 없는지 비교 관점에서 설명을 덧붙이면 더욱 설득력 있는 답변이 될 것입니다.",
        },
    ]

    few_shot_prompt = ""
    for ex in few_shot_examples:
        few_shot_prompt += (
            f"[질문]\n{ex['question']}\n"
            f"[답변]\n{ex['answer']}\n"
            f"[피드백]\n{ex['feedback']}\n\n"
        )

    user_prompt = (
        f"[질문]\n{question}\n"
        f"[답변]\n{answer}\n"
        "이 답변에 대해 다음 기준을 바탕으로 간결하게 구체적인 피드백을 3~5문장으로 작성해주세요:\n"
        "- 답변이 질문의 핵심을 이해하고 있는지\n"
        "- 틀린 내용이나 부족한 설명이 있는지\n"
        "- 어떤 내용을 보완하면 더 좋은 답변이 되는지\n"
        "문장 도중에 끊지 말고, 의미 단위로 문장을 마무리한 뒤 출력을 종료해주세요.\n\n"
        "피드백:"
    )

    return (
        "당신은 컴퓨터공학 면접관입니다. 아래는 예시 질문과 답변, 그리고 그에 대한 피드백입니다.\n\n"
        f"{few_shot_prompt}"
        "아래는 새로운 질문과 답변입니다. 피드백을 생성해주세요.\n\n"
        f"{user_prompt}"
    )


def generate_feedback(question: str, answer: str) -> str:
    prompt = build_feedback_prompt(question, answer)

    try:
        print("VLLM_URL:", os.getenv("VLLM_URL"))
        start_time = time.time()

        response = requests.post(
            f"{VLLM_URL}/v1/completions",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "max_tokens": 512,
                "temperature": 0.7,
            },
            # timeout=30,
        )

        end_time = time.time()
        elapsed = round(end_time - start_time, 2)
        print(f"응답 시간: {elapsed}초")

        response.raise_for_status()
        return response.json()["choices"][0]["text"].strip()

    except requests.exceptions.RequestException as e:
        return f"피드백 생성 중 오류 발생: {str(e)}"
