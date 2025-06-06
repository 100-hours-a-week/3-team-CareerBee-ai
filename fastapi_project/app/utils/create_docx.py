# fastapi_project/app/utils/create_docx.py

from docx import Document
from datetime import datetime
import os


def save_resume_to_docx(resume_text: str, save_dir: str = "generated_resumes") -> str:

    # docx 변환
    doc = Document()
    for line in resume_text.split("\n"):
        doc.add_paragraph(line)

    os.makedirs("./generated_resumes", exist_ok=True)

    # 파일 이름 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_{timestamp}.docx"
    doc.save(filename)

    return filename
