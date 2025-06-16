import os
import traceback
import logging
import asyncio
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, status, Request, Body
from fastapi.responses import JSONResponse
from app.schemas.resume_create import ResumeCreateRequest
from app.services.resume_create_service import _generate_resume_doc
from app.utils.upload_file_to_s3 import upload_file_to_s3


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
router = APIRouter()


@router.post("/resume/draft")
async def generate_resume_by_agent(request: ResumeCreateRequest):
    logging.info("기본 이력서 생성 요청 들어옴")

    # 메모리에서 바로 docx 생성
    file_obj = _generate_resume_doc(request)

    # 파일명 생성
    filename = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

    print(f"generate filename : {filename}")
    print("upload util call")
    # S3로 업로드
    file_url = upload_file_to_s3(file_obj, filename)

    logging.info("이력서 생성 완료 및 S3 업로드: %s", file_url)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "httpStatusCode": 200,
            "message": "이력서 초안 생성에 성공하였습니다.",
            "data": {"resumeUrl": file_url},
        },
    )
