import logging
import asyncio
from datetime import datetime
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.schemas.resume_create import ResumeCreateRequest
from app.services.resume_create_service import _generate_resume_doc
from app.utils.upload_file_to_s3 import async_upload_file_to_s3


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


@router.post("/resume/draft")
async def generate_resume_by_agent(request: ResumeCreateRequest):
    logging.info("기본 이력서 생성 요청 들어옴")

    # 비동기적으로 docx 생성
    file_obj = await asyncio.to_thread(_generate_resume_doc, request)

    # 비동기적으로 S3 업로드
    filename = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    print(f"파일 이름 생성: {filename}")
    # S3로 업로드
    file_url = await async_upload_file_to_s3(file_obj, filename)

    logging.info("이력서 생성 완료 및 S3 업로드: %s", file_url)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "httpStatusCode": 200,
            "message": "이력서 초안 생성에 성공하였습니다.",
            "data": {"resumeUrl": file_url},
        },
    )
