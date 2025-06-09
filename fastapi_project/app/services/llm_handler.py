import httpx
import json
import re
import time

VLLM_API_URL = "http://localhost:8001/v1/chat/completions"

SYSTEM_PROMPT = """
너는 사용자의 이력서를 분석하는 인공지능이야. 다음 항목을 추출해서 딱 JSON 형식으로만 응답해. 주석이나 설명은 절대 하지 마.

- certification_count: 자격증 또는 인증 관련 항목 개수
- project_count: 프로젝트, 과제, 구현 경험 등 개수
- major_type: 컴퓨터/소프트웨어/AI/IT 관련 전공이면 "MAJOR", 아니면 "NON_MAJOR"
- work_period: 최근 회사 근무 기간 (월 단위), 없으면 0
- company_type: 최근 회사의 유형 ("ENTERPRISE", "MID_SIZED", "SME", "STARTUP"), 없으면 null
- position: 최근 회사에서의 직무명, 없으면 null
- additional_experiences: 자격증/프로젝트/경력 외 활동 내용, 없으면 null

조건:
- 불확실한 값은 null 또는 0으로 처리
- JSON 외 텍스트는 절대 출력하지 마
- 모든 응답은 한국어로 작성
"""

async def extract_info_from_resume(resume_text: str) -> dict:
    payload = {
        "model": "CohereLabs/aya-expanse-8b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": resume_text.strip()[:3500]},
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(VLLM_API_URL, json=payload)

        end = time.time()
        response.raise_for_status()

        result = response.json()

        # 응답 content 추출
        content = result.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise ValueError("LLM 응답에서 'content'를 찾을 수 없음")

        print(f"⏱️ 응답 시간: {end - start:.2f}초")
        print("🧠 LLM 응답 원문:\n", content)

        # JSON 추출
        match = re.search(r"\{[\s\S]*?\}", content)
        if not match:
            raise ValueError("LLM 응답에서 JSON이 감지되지 않음")

        return json.loads(match.group(0))

    except httpx.HTTPStatusError as e:
        print("❌ HTTP 오류:", e.response.status_code, e.response.text)
        raise ValueError("LLM API 호출 오류") from e
    except json.JSONDecodeError as e:
        print("❌ JSON 파싱 오류:", e)
        raise ValueError("LLM 응답 파싱 실패") from e
    except Exception as e:
        print("❌ 일반 예외 발생:", e)
        raise