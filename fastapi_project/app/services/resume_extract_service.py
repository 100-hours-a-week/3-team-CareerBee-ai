# app/services/resume_extract_service.py
from app.utils.file import (
    download_pdf_from_url,
    is_valid_pdf
)
from app.utils.pdf_parser import extract_text_with_formatting  # ✅ 포맷 고려 텍스트 추출
from app.services.llm_handler import extract_info_from_resume
from app.schemas.resume_extract import ResumeInfo


async def extract_resume_info(file_url: str) -> ResumeInfo:
    try:
        print("📥 Step 1: file_url 전달됨 =", file_url)

        # 1. PDF 다운로드
        pdf_bytes = download_pdf_from_url(file_url)
        print("📦 Step 2: PDF 다운로드 성공")
        print("🔥 PDF 첫 100바이트:", pdf_bytes[:100])
    except Exception as e:
        print("❌ Step 1-2 실패: PDF 다운로드 중 예외 발생:", e)
        raise ValueError("invalid_file_type") from e

    try:
        # 2. PDF 유효성 검사
        if not is_valid_pdf(pdf_bytes):
            print("❌ Step 3: PDF 유효성 검사 실패")
            raise ValueError("invalid_file_type")
        print("✅ Step 3: PDF 유효성 검사 통과")
    except Exception as e:
        print("❌ Step 3 실패: 예외 발생:", e)
        raise ValueError("invalid_file_type") from e

    try:
        # 3. 텍스트 추출 (포맷 고려)
        resume_text = extract_text_with_formatting(pdf_bytes)  # ✅ 핵심 변경
        print("📄 Step 4: 텍스트 길이:", len(resume_text))
        print("📄 텍스트 앞 600자:\n", resume_text[:600])

        if len(resume_text.strip()) == 0:
            raise ValueError("resume_text_is_empty")
    except Exception as e:
        print("❌ Step 4 실패: 텍스트 추출 중 예외 발생:", e)
        raise ValueError("resume_text_extract_failed") from e
        
    # 기본값 정의 (LLM 실패 시 fallback)
    fallback_result = {
        "certification_count": 0,
        "project_count": 0,
        "major_type": "NON_MAJOR",
        "company_name": None,
        "work_period": 0,
        "position": None,
        "additional_experiences": None
    }

    try:
        # 4. LLM 추론 (최대 2회 재시도)
        MAX_RETRY = 2
        for attempt in range(MAX_RETRY):
            try:
                print(f"🧠 Step 5: LLM 추론 시도 {attempt + 1}")
                result = await extract_info_from_resume(resume_text)

                # ✅ Null 방지: work_period은 int이므로 None -> 0 처리
                result["work_period"] = int(result.get("work_period") or 0)

                return ResumeInfo(**result)
            except ValueError as ve:
                print(f"⚠️ LLM 추론 시도 {attempt + 1} 실패: {ve}")
                if attempt == MAX_RETRY - 1:
                    print("LLM 추론 반복 실패. 기본값 반환.")
                    return ResumeInfo(**fallback_result)
    except Exception as e:
        print("❌ Step 5 실패: LLM 추론 중 예외 발생:", e)
        raise ValueError("llm_inference_failed") from e