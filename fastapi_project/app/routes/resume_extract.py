# app/routes/resume_extract.py
from fastapi import APIRouter, HTTPException
from app.schemas.resume_extract import ResumeExtractRequest, ResumeExtractResponse
from app.services.resume_extract_service import extract_resume_info

router = APIRouter()

@router.post("/resume/extract", response_model=ResumeExtractResponse)
async def extract_resume(request: ResumeExtractRequest):
    try:
        result = await extract_resume_info(request.file_url)
        return ResumeExtractResponse(message="extraction_success", data=result)
    except ValueError as ve:
        # LLM 추론/파싱 실패 등
        raise HTTPException(status_code=500, detail={
            "message": "llm_response_decode_failed",
            "error_detail": str(ve)
        })
    except Exception:
        # PDF 자체 문제 등
        raise HTTPException(status_code=400, detail={
            "message": "invalid_file_type",
            "error_detail": None
        })