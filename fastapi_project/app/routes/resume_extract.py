# app/routes/resume_extract.py
from fastapi import APIRouter
from app.schemas.resume_extract import ResumeExtractRequest, ResumeExtractResponse, ResumeInfo
from app.services.resume_extract_service import extract_resume_info
import logging
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

# fallback 기본값 정의
fallback_result = ResumeInfo(
    certification_count=0,
    project_count=0,
    major_type="NON_MAJOR",
    company_name=None,
    work_period=0,
    position=None,
    additional_experiences=None
)

@router.post("/resume/extract", response_model=ResumeExtractResponse)
async def extract_resume(request: ResumeExtractRequest):
    logger.info(f"📥 [resume/extract] file_url received: {request.file_url}")

    try:
        result = await extract_resume_info(request.file_url)
        return ResumeExtractResponse(message="extraction_success", data=result)

    except Exception as e:
        # 모든 예외에서 fallback 반환
        logger.error("❌ 이력서 정보 추출 실패. 기본값 반환")
        traceback.print_exc()
        return ResumeExtractResponse(message="extraction_failed", data=fallback_result)