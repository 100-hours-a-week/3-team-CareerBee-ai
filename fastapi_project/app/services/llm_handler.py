import httpx
import json
import time

from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from app.schemas.resume_extract import ResumeInfo

# 1. 응답 스키마 정의
response_schemas = [
    ResponseSchema(name="certification_count", description="자격증 또는 인증 개수 (정수)"),
    ResponseSchema(name="project_count", description="프로젝트 또는 구현 경험 개수 (정수)"),
    ResponseSchema(name="major_type", description="전공이 컴퓨터/소프트웨어/AI/IT 관련이면 'MAJOR', 아니면 'NON_MAJOR'"),
    ResponseSchema(name="company_name", description="실제 근무 이력이 명확히 기재된 가장 최근 회사명 (없으면 null)"),
    ResponseSchema(name="work_period", description="실제 근무 이력이 명확히 기재된 가장 최근 회사에서의 근무 기간을 월 단위 정수로 계산 (없으면 0)"),
    ResponseSchema(name="position", description="실제 근무 이력이 명확히 기재된 경력 중 가장 최근 회사에서의 직무명 (예시: '2020.01 ~ 2021.03'이면 14 또는 '2022년 4월 ~ 현재'이면 38, 없으면 0)"),
    ResponseSchema(name="additional_experiences", description="자격증/프로젝트/경력 이외의 기타 대외 활동 정리 (없으면 null)")
]

parser = StructuredOutputParser.from_response_schemas(response_schemas)

# 2. 프롬프트 템플릿 정의
prompt = ChatPromptTemplate.from_messages([
    ("system", """
너는 사용자의 이력서를 분석해 단 하나의 JSON 객체만 출력하는 AI야. 아래 항목을 반드시 지키고, **정확한 기준에 따라 JSON 형식으로만 출력해.**

📅 현재 기준일은 2025년이야. "현재"라고 표시된 종료일은 이 날짜로 계산해.

반드시 추출할 항목 (모두 단일 값)
- certification_count: 자격증 개수 (정수)
- project_count: 프로젝트 또는 구현 경험 개수 (정수)
- major_type: 컴퓨터/소프트웨어/AI/IT 계열 전공이면 "MAJOR", 아니면 "NON_MAJOR"
- company_name: 실제 '근무' 이력이 명확히 기재된 가장 최근 회사명 1개 추출 (없으면 반드시 null)
- work_period: 위 회사에서 가장 최근 경력 1건에 대해 정식 근무한 개월 수 (예시: 2021.03 ~ 2023.04 → 26)
- position: 위 회사에서 맡았던 직무명 1개만 선택 (가장 최근 기준, 없으면 반드시 null)
- additional_experiences: 자격증/프로젝트/근무경력 이외에 **동아리, 교육, 대외활동, 발표, 수상 등 이력서에 등장한 기타 경험 중 실제 성과 기반 내용 문자열로 정리** (없으면 null)

아래 조건을 반드시 지켜
- 절대 리스트 금지! 모든 항목은 단일 값
- 복수 값이 있어도 하나만 선택 (가장 최근 기준)
- 추측 금지: 이력서에 **명확하게 근무/인턴/재직/소속 등**이 쓰여 있지 않으면 company_name, position, work_period는 무조건 null 또는 0
- 단순한 기업명 언급은 무시할 것 (공모전 참가, 세미나 수강, 수상, 참고 등은 근무 아님)
"""),
    ("user", "{text}"),
    ("system", "{format_instructions}")
])

# 3. 모델 정의
llm = ChatOpenAI(
    model="CohereLabs/aya-expanse-8b",
    openai_api_base="http://localhost:8001/v1",
    openai_api_key="NULL",
    temperature=0.3,
    max_tokens=512
)

# 4. LLM 추론 함수
async def extract_info_from_resume(resume_text: str) -> dict:
    try:
        format_instructions = parser.get_format_instructions()
        filled_prompt = prompt.format_messages(
            text=resume_text.strip()[:3500],
            format_instructions=format_instructions
        )

        start = time.time()
        response = await llm.ainvoke(filled_prompt)
        end = time.time()

        content = response.content
        print(f"⏱️ 응답 시간: {end - start:.2f}초")
        print("🧠 LLM 응답 원문:\n", content)

        parsed_dict = parser.parse(content)
        return ResumeInfo(**parsed_dict).dict()

    except httpx.HTTPStatusError as e:
        print("❌ HTTP 오류:", e.response.status_code, e.response.text)
        raise ValueError("LLM API 호출 오류") from e

    except json.JSONDecodeError as e:
        print("❌ JSON 파싱 오류:", e)
        raise ValueError("LLM 응답 파싱 실패") from e

    except Exception as e:
        print("❌ 일반 예외 발생:", e)
        raise ValueError("LLM 응답 처리 실패") from e 