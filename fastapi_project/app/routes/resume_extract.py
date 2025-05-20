# app/routes/resume_extract.py
from fastapi import APIRouter, HTTPException
from app.schemas.resume_extract import ResumeExtractRequest, ResumeExtractResponse
from app.services.resume_extract_service import extract_resume_info

router = APIRouter()

@router.post("/extract", response_model=ResumeExtractResponse)
def extract_resume(request: ResumeExtractRequest):
    try:
        result = extract_resume_info(request.file_url)
        return ResumeExtractResponse(message="extraction_success", data=result)
    except ValueError as ve:
        raise HTTPException(status_code=500, detail={
            "message": "llm_response_decode_failed",
            "data": str(ve)
        })
    except Exception:
        raise HTTPException(status_code=400, detail={
            "message": "invalid_file_type",
            "data": None
        })