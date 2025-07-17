# app/services/llm_handler.py
import time
import traceback
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
    ResponseSchema(name="position", description="실제 근무 이력이 명확히 기재된 경력 중 가장 최근 회사에서의 직무명 (없으면 null)"),
    ResponseSchema(name="additional_experiences", description="자격증/프로젝트/경력 이외의 기타 대외 활동 정리 (없으면 null)")
]

parser = StructuredOutputParser.from_response_schemas(response_schemas)

# 2. 프롬프트 템플릿 정의
prompt = ChatPromptTemplate.from_messages([
    ("system", """
너는 사용자의 이력서를 분석해 **정확히 하나의 JSON 객체**만 출력하는 AI야. 반드시 아래 기준을 지켜줘.

📌 출력 형식은 아래 7개 항목의 **단일 값**이며, 절대 리스트 금지:

- certification_count: 자격증 개수 (정수)
- project_count: 프로젝트 또는 구현 경험 개수 (정수)
- major_type: 컴퓨터/AI/IT 계열 전공이면 "MAJOR", 아니면 "NON_MAJOR"
- company_name: 근무/인턴/재직/소속 등의 표현이 명확히 언급된 **최근 회사명 1개** (없으면 null)
- work_period: 위 회사의 최근 이력 근무기간 총 개월 수 (예: 2023.01~2024.01 → 13)
- position: 위 회사에서 맡은 직무명 (없으면 null)
- additional_experiences: 자격증/프로젝트/근무 외 경험 (동아리, 수상, 대외활동 등). 없으면 null

❗️주의사항 (반드시 지킬 것):

- 단순 기업 언급/협업/수상/세미나는 절대 근무로 판단하지 마세요.
- 근무/인턴으로 확실히 언급된 경우만 company_name, work_period, position을 추출하세요.
- certification_count에는 '자격증', '기사', 'SQLD', '컴활', 'TOEIC', '운전면허' 등과 점수/등급이 함께 있는 항목만 포함하세요.
- additional_experiences에는 반드시 성과 기반의 외부 활동만 포함하고, 자격증/근무/프로젝트 내용은 절대 포함하지 마세요.

📅 기준일은 2025년. "현재"는 2025년으로 계산합니다.
"""),
    ("user", "{text}"),
    ("system", "{format_instructions}")
])

# 3. 모델 정의
llm = ChatOpenAI(
    model="/mnt/ssd/aya-expanse-8b",
    openai_api_base="http://localhost:8001/v1",
    openai_api_key="NULL",
    temperature=0.3,
    max_tokens=512
)

# 4. 안전한 정수 파싱 함수
def safe_int(val):
    try:
        return int(val)
    except:
        return 0

# 5. LLM 추론 함수
async def extract_info_from_resume(resume_text: str) -> dict:
    fallback_result = {
        "certification_count": 0,
        "project_count": 0,
        "major_type": "NON_MAJOR",
        "company_name": None,
        "work_period": 0,
        "position": None,
        "additional_experiences": None
    }

    MAX_RETRY = 2
    for attempt in range(MAX_RETRY):
        try:
            format_instructions = parser.get_format_instructions()
            filled_prompt = prompt.format_messages(
                text=resume_text.strip()[:6000],
                format_instructions=format_instructions
            )

            start = time.time()
            response = await llm.ainvoke(filled_prompt)
            end = time.time()

            content = response.content
            print(f"\n⏱️ 응답 시간: {end - start:.2f}초")
            print("🧠 LLM 응답 원문:\n", content)

            parsed_dict = parser.parse(content)

            # position 필드 정리
            position_raw = parsed_dict.get("position")
            position = position_raw[0] if isinstance(position_raw, list) and position_raw else position_raw or None

            # additional_experiences 필드 정리
            add_exp = parsed_dict.get("additional_experiences")
            if isinstance(add_exp, list):
                add_exp = "\n".join(add_exp)
            elif not isinstance(add_exp, str):
                add_exp = None

            return ResumeInfo(
                certification_count=safe_int(parsed_dict.get("certification_count")),
                project_count=safe_int(parsed_dict.get("project_count")),
                major_type=parsed_dict.get("major_type", "NON_MAJOR"),
                company_name=parsed_dict.get("company_name") or None,
                work_period=safe_int(parsed_dict.get("work_period")),
                position=position,
                additional_experiences=add_exp
            ).dict()

        except Exception as e:
            print(f"⚠️ LLM 추론 시도 {attempt + 1} 실패:", e)
            traceback.print_exc()
            if attempt == MAX_RETRY - 1:
                print("⚠️ LLM 추론 2회 실패. fallback 반환")
                return fallback_result