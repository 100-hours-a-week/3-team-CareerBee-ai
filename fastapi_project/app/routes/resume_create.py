import os
import traceback
import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.schemas.resume_create import ResumeCreateRequest
from app.services.resume_create_service import generate_resume_draft


# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


@router.post("/resume/draft")
async def generate_resume_by_agent(request: ResumeCreateRequest):
    logging.info("[1] 요청 들어옴")

    filename = generate_resume_draft(request)
    # file_url = f"https://storage.googleapis.com/gcs-ssmu-dev-static/resume-create/{filename}"
    file_url = f"generated_resumes/{filename}"  # 또는 GCS 등 외부 URL이면 해당 경로로

    logging.info("[2] 이력서 생성 완료: %s", file_url)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "httpStatusCode": 200,
            "message": "이력서 초안 생성에 성공하였습니다.",
            "data": {"resumeUrl": file_url},
        },
    )
