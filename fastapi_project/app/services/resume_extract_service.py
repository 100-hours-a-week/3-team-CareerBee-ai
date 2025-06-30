# app/services/resume_extract_service.py
import traceback

from app.utils.file import (
    download_pdf_from_url,
    is_valid_pdf
)
from app.utils.pdf_parser import extract_text_with_formatting
from app.services.llm_handler import extract_info_from_resume
from app.schemas.resume_extract import ResumeInfo

async def extract_resume_info(file_url: str) -> ResumeInfo:
    try:
        print("📥 Step 1: file_url =", file_url)

        # 1. PDF 다운로드
        pdf_bytes = download_pdf_from_url(file_url)
        print("📦 Step 2: PDF 다운로드 성공")
        print("🔥 PDF 첫 100바이트:", pdf_bytes[:100])

        # 2. PDF 유효성 검사
        if not is_valid_pdf(pdf_bytes):
            print("❌ Step 3: PDF 유효성 검사 실패")
            raise ValueError("invalid_file_type")
        print("✅ Step 3: PDF 유효성 검사 통과")

        # 3. 텍스트 추출
        resume_text = extract_text_with_formatting(pdf_bytes)
        print("📄 Step 4: 텍스트 길이:", len(resume_text))
        print("📄 텍스트 앞 600자:\n", resume_text[:600].encode('utf-8', 'replace').decode('utf-8'))

        if len(resume_text.strip()) == 0:
            raise ValueError("resume_text_is_empty")

        # 4. LLM 추론
        result = await extract_info_from_resume(resume_text)
        return ResumeInfo(**result)

    except Exception as e:
        print("❌ extract_resume_info 실패:", e)
        traceback.print_exc()
        # fallback 반환
        return ResumeInfo(
            certification_count=0,
            project_count=0,
            major_type="NON_MAJOR",
            company_name=None,
            work_period=0,
            position=None,
            additional_experiences=None
        )