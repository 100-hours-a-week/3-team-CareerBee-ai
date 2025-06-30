import os
from datetime import datetime
import asyncio
from langchain_openai import ChatOpenAI
from app.agents.schema.resume_create_agent import ResumeAgentState
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from bs4 import BeautifulSoup
from markdown2 import markdown
from app.agents.base_node import BaseNode


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)


class CreateResumeNode(BaseNode):
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        prompt = self._build_resume_prompt(state)

        # LLM으로 이력서 생성
        content = await self._generate_resume_content(prompt)

        # Word 문서 생성
        docx_path = await self._create_word_document(state, content)

        # 상태 업데이트
        state.docx_path = docx_path
        state.resume = content
        state.step = "completed"

        return state

    def _build_resume_prompt(self, state: ResumeAgentState) -> str:
        # LLM에 보낼 요약 정보
        base_info = f"""
    이메일: {state.inputs.email}
    희망 직무: {state.inputs.preferred_job}
    전공 여부: {state.inputs.major_type}
    재직 회사: {state.inputs.company_name}
    직무명: {state.inputs.position}
    재직 기간: {state.inputs.work_period}개월
    자격증 수: {state.inputs.certification_count}
    프로젝트 수: {state.inputs.project_count}
    추가 경험: {state.inputs.additional_experiences}
        """

        qna_info = "\n".join([f"Q: {a['question']}\nA: {a['answer']}" for a in answers])

        return f"""
    다음은 이력서에 포함될 정보입니다. 아래 정보를 기반으로 고급 이력서 초안을 마크다운 형식으로 작성해주세요. 항목: 경력 사항, 프로젝트, 기술 역량, 자격증 등

    [입력 정보]
    {base_info}

    [질문 응답]
    {qna_info}
    """

    async def _generate_resume_content(self, prompt: str) -> str:
        """LLM으로 이력서 내용 생성"""
        content = await asyncio.to_thread(self.llm.invoke, prompt)
        return content.content.strip()

    async def _create_word_document(self, state: ResumeAgentState, content: str) -> str:
        """Word 문서 생성"""

        def write_to_doc():
            doc = Document()
            doc.add_heading("이력서", level=0).alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

            # 기본 정보 섹션
            self._add_basic_info_section(doc, state.inputs)

            # LLM 생성 내용 섹션
            self._render_llm_content_stylized(content, doc)

            os.makedirs("generated", exist_ok=True)
            doc.save(path)

        path = f"generated/resume_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        await asyncio.to_thread(write_to_doc)
        return path

    def _add_basic_info_section(self, doc: Document, inputs):
        """기본 정보 섹션 추가"""
        doc.add_heading("기본 정보", level=1)
        doc.add_paragraph(f"이메일: {inputs.email}")
        doc.add_paragraph(f"희망 직무: {inputs.preferred_job}")
        doc.add_paragraph(f"전공 여부: {inputs.major_type}")

    def _render_llm_content_stylized(self, markdown_text: str, doc: Document):
        """마크다운 텍스트를 Word 문서에 스타일 적용하여 렌더링"""
        html = markdown(markdown_text)
        soup = BeautifulSoup(html, "html.parser")

        for element in soup.descendants:
            if element.name == "h1":
                section = doc.add_heading(element.get_text(), level=1)
                self._add_horizontal_line(section)
            elif element.name == "h2":
                doc.add_heading(element.get_text(), level=2)
            elif element.name == "p":
                doc.add_paragraph(element.get_text())
            elif element.name == "li":
                doc.add_paragraph("▪ " + element.get_text())

    def _add_horizontal_line(self, paragraph):
        """단락에 수평선 추가"""
        pPr = paragraph._p.get_or_add_pPr()
        border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "0")
        bottom.set(qn("w:color"), "2F5496")
        border.append(bottom)
        pPr.append(border)
