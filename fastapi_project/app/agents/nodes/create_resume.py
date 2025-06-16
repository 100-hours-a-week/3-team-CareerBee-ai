from datetime import date
from langchain_openai import ChatOpenAI
from app.utils.create_docx import save_resume_to_docx

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)


def create_resume_node(state):
    today = date.today().strftime("%Y-%m-%d")
    inputs = state.inputs
    answers = state.answers

    # 1️⃣ 기본 입력 정보를 문자열로 정리
    base_info = f"""
[기본 입력 정보]
- 이메일: {inputs.get('email', '')}
- 선호 직무: {inputs.get('preferred_job', '')}
- 전공 여부: {inputs.get('major_type', '')}
- 재직 회사: {inputs.get('company_name', '')}
- 직무: {inputs.get('position', '')}
- 재직 기간: {inputs.get('work_period', '0')}개월
- 자격증 개수: {inputs.get('certification_count', 0)}
- 프로젝트 개수: {inputs.get('project_count', 0)}
- 추가 경험: {inputs.get('additional_experiences', '')}
"""

    # 2️⃣ LLM 추가 질문에 대한 답변을 정리
    additional_info = "[추가 질문에 대한 답변]\n"
    if answers:
        for a in answers:
            additional_info += f"- {a['question']} → {a['answer']}\n"
    else:
        additional_info += "- 추가 질문 없음\n"

    # 3️⃣ 최종 LLM input으로 구성
    full_context = f"""
아래는 이력서를 작성하기 위한 사용자 정보입니다. 이 정보를 참고하여 간결하고 깔끔한 이력서 초안(text)를 작성해주세요. 헤더, 항목, 마크다운 스타일을 반영해 깔끔하게 작성하세요.

{base_info}
{additional_info}
    """

    # 4️⃣ LLM 호출
    response = llm.invoke(full_context)
    generated_resume = str(response.content).strip()

    full_resume_text = f"[이력서 초안]\n 생성일: {today}\n\n{generated_resume}"

    # 5️⃣ state에 결과 저장
    state.resume = full_resume_text
    docx_path = save_resume_to_docx(full_resume_text)
    state.docx_path = docx_path

    return state
