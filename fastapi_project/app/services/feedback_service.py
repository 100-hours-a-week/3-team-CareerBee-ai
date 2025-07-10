import os
import requests
import time
import aiohttp
import asyncio

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8001")
MODEL_NAME = "/mnt/ssd/aya-expanse-8b"


def build_feedback_prompt(question: str, answer: str) -> str:
    few_shot_examples = [
        # {
        #     "question": "LSTM이 기울기 소실 문제를 해결하는 핵심 구조적 특징을 설명해주세요.",
        #     "answer": "LSTM은 RNN보다 좋아서 기울기 소실이 안 생깁니다.",
        #     "feedback": "피드백: LSTM이 RNN보다 개선된 점을 언급했지만, 질문의 핵심인 구조적 특징에 대한 설명이 없습니다. "
        #     "LSTM은 셀 상태(cell state)와 게이트 메커니즘(입력 게이트, 삭제 게이트, 출력 게이트)을 통해 정보 흐름을 조절함으로써 기울기 소실 문제를 완화합니다. "
        #     "이러한 핵심 구조에 대한 이해와 설명을 하면 더 좋은 답변이 될 것입니다.",
        # },
        # {
        #     "question": "자바의 가비지 컬렉션과 어떤 차이점이 있을까요?",
        #     "answer": "자바의 가비지 컬렉션은 자동 메모리 관리 시스템으로, 개발자가 명시적으로 메모리를 해제할 필요 없이 사용되지 않는 객체를 자동으로 제거합니다.  반면 C++은 가비지 컬렉션을 제공하지 않으며, 개발자가 `new` 연산자로 동적으로 할당한 메모리를 `delete` 연산자를 사용하여 수동으로 해제해야 합니다.  이러한 차이로 인해 자바는 메모리 관리에 대한 부담이 줄어들지만, 가비지 컬렉션의 오버헤드가 발생할 수 있으며, C++은 메모리 관리에 대한 세밀한 제어가 가능하지만, 메모리 누수나 메모리 접근 위험이 존재합니다.  결론적으로, 메모리 관리 방식의 차이는 개발 편의성과 성능, 안정성 측면에서 상호 트레이드오프 관계를 가지고 있습니다.",
        #     "feedback": "피드백: 답변은 자바와 C++의 메모리 관리 차이점을 잘 설명했습니다.  자바의 자동 가비지 컬렉션과 C++의 수동 메모리 관리의 장단점을 명확하게 비교하여 트레이드오프 관계를 제시한 점이 좋습니다.\n\n하지만,  '가비지 컬렉션의 오버헤드'에 대한 설명이 추상적입니다.  어떤 종류의 오버헤드가 발생하는지 (예: 성능 저하, 일시적인 정지 등) 구체적으로 설명하고,  C++의 메모리 누수 및 메모리 접근 위험에 대한 예시를 추가하면 더욱 설득력 있는 답변이 됩니다.  또한,  다른 언어(예: Python, Go)의 가비지 컬렉션 방식과 비교하여 자바의 특징을 더욱 명확히 설명하면 좋습니다.",
        # },
        # {
        #     "question": "LSTM이 기울기 소실 문제를 해결하는 핵심 구조적 특징을 설명해주세요.",
        #     "answer": "LSTM은 셀 상태(cell state)를 유지하면서 정보를 장기간 보존할 수 있는 구조로, 기울기 소실 문제를 완화합니다. "
        #     "특히 입력 게이트, 삭제 게이트, 출력 게이트로 구성된 게이트 메커니즘이 중요 정보를 선택적으로 전달하거나 차단하여 안정적인 역전파가 가능합니다.",
        #     "feedback": "피드백: LSTM의 핵심 구조와 기울기 소실 완화 방식에 대해 정확히 설명했습니다. "
        #     "특히 셀 상태 유지와 게이트 메커니즘의 기능을 명확히 짚은 점이 인상적입니다. "
        #     "추가로, 왜 일반 RNN에서는 이러한 구조가 없는지 비교 관점에서 설명을 덧붙이면 더욱 설득력 있는 답변이 될 것입니다.",
        # },
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

    return f"{few_shot_prompt}" f"{user_prompt}"


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
                            "content": "당신은 컴퓨터공학 면접관입니다. 당신이 질문한 컴퓨터공학 개념에 대해 지원자의 답변을 보고 어떤 점이 보완되면 좋겠는지 친절하게 피드백해주세요.",
                            # "아래는 예시 질문과 답변, 그리고 그에 대한 피드백입니다."
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
