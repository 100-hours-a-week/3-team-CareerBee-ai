import os
from docx import Document
from docx.shared import Pt
from datetime import datetime
from app.schemas.resume_create import ResumeCreateRequest


def generate_resume_draft(data: ResumeCreateRequest) -> str:
    doc = Document()
    doc.add_heading("이력서 초안 (자동 생성 템플릿)", level=0)

    # 기본 정보
    doc.add_heading("기본 정보", level=1)

    def add_underlined_paragraph(label: str, length: int = 40):
        p = doc.add_paragraph()
        p.add_run(f"{label}: ")
        run = p.add_run(" " * length)
        run.font.underline = True
        run.font.size = Pt(11)

    add_underlined_paragraph("이름")
    add_underlined_paragraph("이메일")
    add_underlined_paragraph("전화번호")
    add_underlined_paragraph("지원 포지션")

    if data.major_type == "MAJOR":
        add_underlined_paragraph("전공", 20)
    add_underlined_paragraph("재직 회사", 30)

    if data.work_period is not None:
        doc.add_heading("경력 사항", level=1)
        doc.add_paragraph(
            f"총 경력 기간: {data.work_period // 12}년 {data.work_period % 12} 개월"
        )
        for i in range(max(data.work_period // 12, 1)):
            doc.add_paragraph(f"[경력 {i + 1}]")
            add_underlined_paragraph("회사명", 40)
            if data.position:
                doc.add_paragraph(f"직무명: {data.position}")
            add_underlined_paragraph("근무기간", 40)
            doc.add_paragraph("담당 업무:")
            doc.add_paragraph("• " + " " * 100)
            doc.add_paragraph("• " + " " * 100)

    doc.add_paragraph(f"기타: {data.additional_experiences}")

    # 프로젝트 경험
    doc.add_heading("프로젝트 경험", level=1)
    for i in range(data.project_count):
        doc.add_paragraph(f"[프로젝트 {i + 1}]")
        add_underlined_paragraph("제목", 40)
        add_underlined_paragraph("기간", 40)
        doc.add_paragraph("프로젝트 요약:")
        doc.add_paragraph("• " + " " * 100)
        doc.add_paragraph("맡은 역할:")
        doc.add_paragraph("• " + " " * 100)
        doc.add_paragraph("성과:")
        doc.add_paragraph("• " + " " * 100)

    # 자격증
    doc.add_heading("자격증", level=1)
    for i in range(data.certification_count):
        add_underlined_paragraph(f"자격증 {i + 1}", 50)

    # 저장
    filename = f"resume_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    save_dir = "./generated_resumes"
    os.makedirs(save_dir, exist_ok=True)  # 폴더가 없으면 생성
    filepath = os.path.join(save_dir, filename)
    doc.save(filepath)

    return filename
