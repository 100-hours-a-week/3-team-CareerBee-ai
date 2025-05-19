# resume_extract_service.py 디버깅 버전

from app.utils.file import (
    download_pdf_from_url,
    extract_text_from_pdf,
    is_valid_pdf
)
from app.services.llm_handler import extract_info_from_resume


def extract_resume_info(file_url: str) -> dict:
    # 1. PDF 다운로드
    pdf_bytes = download_pdf_from_url(file_url)
    print("🔥 PDF 첫 100바이트:", pdf_bytes[:100])

    # 2. PDF 유효성 검사
    if not is_valid_pdf(pdf_bytes):
        raise ValueError("invalid_file_type")

    # 3. 텍스트 추출
    resume_text = extract_text_from_pdf(pdf_bytes)
    print("📄 텍스트 길이:", len(resume_text))
    print("📄 텍스트 앞 300자:\n", resume_text[:300])

    if len(resume_text.strip()) == 0:
        raise ValueError("resume_text_is_empty")

    # 4. LLM 추론
    return extract_info_from_resume(resume_text)