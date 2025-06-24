import os
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from io import BytesIO
from datetime import datetime
from app.schemas.resume_create import ResumeCreateRequest
from app.agents.schema.resume_create_agent import ResumeAgentState
from app.agents.nodes.create_resume import create_resume_node
import asyncio
from app.utils.upload_file_to_s3 import upload_file_to_s3


# ------------------------- 스타일 관련 도우미 함수들 -------------------------
# 구분선 넣기 함수
def add_horizontal_line(paragraph, before=6, after=6):
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)

    pPr = paragraph._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")  # 실선
    bottom.set(qn("w:sz"), "8")  # 굵기 (2~24까지 조절)
    bottom.set(qn("w:space"), "0")  # 줄과 간격
    bottom.set(qn("w:color"), "2F5496")  # 색상
    border.append(bottom)
    pPr.append(border)


# 밑줄 있는 빈칸 라벨 생성 헬퍼
def add_underlined_paragraph(doc, label: str, length: int = 40):
    p = doc.add_paragraph()
    p.add_run(f"{label}: ")
    run = p.add_run(" " * length)
    run.font.underline = True
    run.font.size = Pt(11)


# ------------------------- 이력서 생성 핵심 로직 -------------------------
def _generate_resume_doc(data: ResumeCreateRequest) -> BytesIO:
    doc = Document()

    # 제목
    doc.add_heading("OOO 이력서", level=0).alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    doc.add_heading("기본 정보", level=1)
    doc.add_paragraph(f"지원 분야: {data.preferred_job}")
    doc.add_paragraph("생년월일:")
    doc.add_paragraph(f"이메일: {data.email}")
    doc.add_paragraph("전화번호: ")
    doc.add_paragraph("GitHub URL:")
    if data.major_type == "MAJOR":
        doc.add_paragraph("전공 : 컴퓨터 공학 관련 전공")
    else:
        doc.add_paragraph("전공 : ")
    doc.add_paragraph(" " + " " * 100)

    # 경력 사항
    if data.work_period is not None:
        heading_paragraph = doc.add_heading("경력 사항", level=1)
        add_horizontal_line(heading_paragraph)  # 구분선

        if data.work_period < 12:
            period_text = f"{data.work_period}개월"
        else:
            years = data.work_period // 12
            months = data.work_period % 12
            period_text = f"{years}년 {months}개월" if months > 0 else f"{years}년"
        add_underlined_paragraph(doc, f"회사명: {data.company_name}")
        if data.position:
            doc.add_paragraph(f"직무명: {data.position}")
        add_underlined_paragraph(doc, f"근무기간: {period_text}")
        doc.add_paragraph("담당 업무:")
        doc.add_paragraph("▪ " + " " * 100)
        doc.add_paragraph("▪ " + " " * 100)

    # 프로젝트 경험
    heading_paragraph = doc.add_heading("프로젝트", level=1)
    add_horizontal_line(heading_paragraph)  # 구분선
    for i in range(data.project_count):
        doc.add_paragraph(f"[프로젝트 {i + 1} 제목]")
        add_underlined_paragraph(doc, "기간", 40)
        doc.add_paragraph("프로젝트 요약:")
        doc.add_paragraph("▪ " + " " * 100)
        doc.add_paragraph("맡은 역할:")
        doc.add_paragraph("▪ " + " " * 100)
        doc.add_paragraph("▪ " + " " * 100)
        doc.add_paragraph("성과:")
        doc.add_paragraph("▪ " + " " * 100)

    # 자격증
    heading_paragraph = doc.add_heading("자격증", level=1)
    add_horizontal_line(heading_paragraph)  # 구분선
    for i in range(data.certification_count):
        add_underlined_paragraph(doc, f"▪ ", 50)

    # 기타
    heading_paragraph = doc.add_heading("기타", level=1)
    add_horizontal_line(heading_paragraph)  # 구분선
    doc.add_paragraph(f"{data.additional_experiences}")

    byte_io = BytesIO()
    doc.save(byte_io)
    byte_io.seek(0)
    return byte_io


# ------------------------- 외부 호출용 async 함수들 -------------------------
async def generate_resume_draft(data: ResumeCreateRequest) -> str:
    filename = f"resume_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

    # docx 생성 (비동기 스레드 오프로드)
    byte_stream = await asyncio.to_thread(_generate_resume_doc, data)

    # S3 업로드 오프로드
    s3_file_path = f"resume/{filename}"
    file_url = await asyncio.to_thread(upload_file_to_s3, byte_stream, s3_file_path)

    return file_url


async def save_agent_resume_to_docx(state: ResumeAgentState) -> str:
    filename = f"resume_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    save_dir = "./generated_resumes"
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)

    # LLM 결과 생성 + 저장 로직도 오프로드
    def _write_to_docx():
        updated_state = create_resume_node(state)
        resume_text = updated_state.get("resume", "")
        doc = Document()
        for line in resume_text.split("\n"):
            doc.add_paragraph(line)
        doc.save(filepath)

    await asyncio.to_thread(_write_to_docx)
    return filepath
