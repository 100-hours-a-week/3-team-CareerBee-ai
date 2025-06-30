import logging
import asyncio
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.schemas.resume_create import ResumeCreateRequest
from app.services.resume_create_service import _generate_resume_doc
from app.utils.upload_file_to_s3 import async_upload_file_to_s3


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


@router.post("/resume/draft")
async def generate_resume_by_agent(request: ResumeCreateRequest):
    try:
        logging.info("기본 이력서 생성 요청 들어옴")
        logging.info(f"요청 데이터: {jsonable_encoder(request)}")

        # 입력 데이터 검증
        if not request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="요청 데이터가 없습니다.",
            )

        # 비동기적으로 docx 생성
        try:
            logging.info("이력서 문서 생성 시작")
            file_obj = await asyncio.to_thread(_generate_resume_doc, request)

            if not file_obj:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="이력서 문서 생성에 실패했습니다.",
                )

            logging.info("이력서 문서 생성 완료")

        except Exception as e:
            logging.error(f"이력서 문서 생성 중 오류: {str(e)}")
            logging.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"이력서 문서 생성 실패: {str(e)}",
            )

        # 파일명 생성
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resume_{timestamp}.docx"
            logging.info(f"생성된 파일명: {filename}")

        except Exception as e:
            logging.error(f"파일명 생성 중 오류: {str(e)}")
            # 기본 파일명 사용
            filename = "resume_draft.docx"
            logging.warning(f"기본 파일명 사용: {filename}")

        # 비동기적으로 S3 업로드
        try:
            logging.info("S3 업로드 시작")
            file_url = await async_upload_file_to_s3(file_obj, filename)

            if not file_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="S3 업로드에 실패했습니다.",
                )

            logging.info(f"S3 업로드 완료: {file_url}")

        except Exception as e:
            logging.error(f"S3 업로드 중 오류: {str(e)}")
            logging.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 업로드 실패: {str(e)}",
            )

        # 성공 응답
        response_data = {
            "httpStatusCode": 200,
            "message": "이력서 초안 생성에 성공하였습니다.",
            "data": {
                "resumeUrl": file_url,
                "filename": filename,
                "createdAt": datetime.now().isoformat(),
            },
        }

        logging.info(f"✅ 이력서 생성 및 업로드 완료: {response_data}")

        return JSONResponse(status_code=status.HTTP_200_OK, content=response_data)

    except HTTPException:
        # HTTPException은 그대로 re-raise
        raise
    except Exception as e:
        logging.error(f"예상치 못한 오류 발생: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류가 발생했습니다: {str(e)}",
        )
