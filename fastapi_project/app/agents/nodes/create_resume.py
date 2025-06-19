import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from app.agents.schema.resume_create_agent import ResumeAgentState
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from bs4 import BeautifulSoup
from markdown2 import markdown

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)


# 구분선
def add_horizontal_line(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), "2F5496")
    border.append(bottom)
    pPr.append(border)


# 밑줄 라벨
def add_underlined_paragraph(doc, label, length=40):
    p = doc.add_paragraph()
    p.add_run(f"{label}: ")
    run = p.add_run(" " * length)
    run.font.underline = True
    run.font.size = Pt(11)


# 마크다운 파싱 결과를 고급 스타일로 변환
def render_llm_content_stylized(markdown_text: str, doc: Document):
    html = markdown(markdown_text)
    soup = BeautifulSoup(html, "html.parser")
    current_section = None
    for element in soup.descendants:
        if element.name == "h1":
            current_section = doc.add_heading(element.get_text(), level=1)
            add_horizontal_line(current_section)
        elif element.name == "h2":
            current_section = doc.add_heading(element.get_text(), level=2)
        elif element.name == "p":
            doc.add_paragraph(element.get_text())
        elif element.name == "li":
            doc.add_paragraph("▪ " + element.get_text())


def create_resume_node(state: ResumeAgentState):
    doc = Document()
    doc.add_heading("이력서", level=0).alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    inputs = state.inputs
    answers = state.answers

    # 👉 LLM에 보낼 요약 정보
    base_info = f"""
이메일: {inputs.email}
희망 직무: {inputs.preferred_job}
전공 여부: {inputs.major_type}
재직 회사: {inputs.company_name}
직무명: {inputs.position}
재직 기간: {inputs.work_period}개월
자격증 수: {inputs.certification_count}
프로젝트 수: {inputs.project_count}
추가 경험: {inputs.additional_experiences}
    """

    qna_info = "\n".join([f"Q: {a['question']}\nA: {a['answer']}" for a in answers])

    prompt = f"""
다음은 이력서에 포함될 정보입니다. 아래 정보를 기반으로 고급 이력서 초안을 마크다운 형식으로 작성해주세요. 항목: 경력 사항, 프로젝트, 기술 역량, 자격증 등

[입력 정보]
{base_info}

[질문 응답]
{qna_info}
"""

    # ▶ LLM 응답
    content = llm.invoke(prompt).content.strip()

    # ✍ 기본 정보는 기존 스타일로 작성
    doc.add_heading("기본 정보", level=1)
    doc.add_paragraph(f"이메일: {inputs.email}")
    doc.add_paragraph(f"희망 직무: {inputs.preferred_job}")
    doc.add_paragraph(f"전공 여부: {inputs.major_type}")

    # ✨ LLM 응답 기반 섹션
    render_llm_content_stylized(content, doc)

    # 저장
    filename = f"resume_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    os.makedirs("generated", exist_ok=True)
    path = os.path.join("generated", filename)
    doc.save(path)

    state.docx_path = path
    state.resume = content
    state.step = "completed"
    return state
