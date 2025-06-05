import httpx
import json
import re
import time

VLLM_API_URL = "http://localhost:8001/v1/chat/completions"

SYSTEM_PROMPT = """
너는 사용자의 이력서를 분석하는 인공지능이야. 다음 항목만 JSON 형식으로 정확히 추출해. 아래 항목 외에는 절대 포함하지 마. 설명도 하지 마.

추출 항목:
- certification_count: 자격증 또는 인증 관련 항목 개수
- project_count: 프로젝트, 과제, 구현 경험 등 개수
- major_type: 컴퓨터/소프트웨어/AI/IT 관련 전공이면 "MAJOR", 아니면 "NON_MAJOR"
- company_name: 경력이 있는 경우 최근 회사 기준 회사 이름, 없으면 null
- work_period: 경력이 있는 경우 최근 회사 기준 근무 기간 (월 단위), 없으면 0
- position: 경력이 있는 경우 최근 회사에서의 직무명, 없으면 null
- additional_experiences: 자격증/프로젝트/경력 외 활동 외 기타 경험 내용, 없으면 null

❗ 조건:
- 위 항목 외에는 절대 포함하지 마 (예: education, name, etc)
- 불확실한 값은 null 또는 0으로 처리
- JSON 외 텍스트 절대 출력하지 마
- 모든 응답은 한국어로 작성

출력 예시:
{
  "certification_count": 2,
  "project_count": 3,
  "major_type": "MAJOR",
  "company_name": "회사명",
  "work_period": 18,
  "position": "백엔드 개발자",
  "additional_experiences": "동아리 활동 및 외부 해커톤 참여"
}
"""

async def extract_info_from_resume(resume_text: str) -> dict:
    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.3",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text.strip()[:3500]},
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.post(VLLM_API_URL, json=payload)
        end = time.time()

        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        print(f"⏱️ 응답 시간: {end - start:.2f}초")
        print("🧠 LLM 응답 원문:\n", content)

        match = re.search(r"\{[\s\S]*?\}", content)
        if not match:
            raise ValueError("LLM 응답에서 JSON이 감지되지 않음")

        return json.loads(match.group(0))

    except Exception as e:
        print("❌ LLM 처리 오류:", e)
        raise