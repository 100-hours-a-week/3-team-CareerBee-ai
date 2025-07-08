# app/routes/resume_create.py
"""
기본 이력서 생성 API - 통합 스키마 적용
"""
import logging
import asyncio
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# 새로운 통합 스키마 사용
from app.schemas import (
    ResumeCreateRequest,
    ResumeCreateResponse,
    create_resume_create_response,
    create_error_response,
)
from app.services.resume_create_service import _generate_resume_doc
from app.utils.upload_file_to_s3 import async_upload_file_to_s3

# 로깅 설정
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/resume/draft", response_model=ResumeCreateResponse)
async def generate_resume_by_agent(request: ResumeCreateRequest):
    """
    기본 이력서 생성 API (하드코딩 템플릿 기반)

    1. 입력 데이터 검증
    2. DOCX 문서 생성
    3. S3 업로드
    4. 기존 형식 응답 반환 (Spring 호환성)
    """
    try:
        logger.info("기본 이력서 생성 요청 들어옴")
        logger.info(f"요청 데이터: {jsonable_encoder(request)}")

        # 1. 입력 데이터 검증
        _validate_request(request)

        # 2. 이력서 문서 생성
        file_obj = await _generate_resume_document(request)

        # 3. 파일명 생성
        filename = _generate_filename()

        # 4. S3 업로드
        file_url = await _upload_to_s3(file_obj, filename)

        # 5. 성공 응답 생성 (기존 형식 유지)
        # datetime 직렬화 문제 해결을 위해 수동으로 응답 구성
        response = create_resume_create_response(
            resume_url=file_url,
            filename=filename,
            message="이력서 초안 생성에 성공하였습니다.",
        )

        logger.info(f"✅ 이력서 생성 및 업로드 완료: {file_url}")

        return JSONResponse(content=response.dict())

    except HTTPException:
        # HTTPException은 그대로 re-raise
        raise

    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())

        # 단순한 에러 응답 (JSON 직렬화 문제 방지)
        error_response = {
            "httpStatusCode": 500,
            "message": "이력서 생성 중 오류가 발생했습니다.",
            "detail": str(e),
        }

        raise HTTPException(status_code=500, detail=error_response)


def _validate_request(request: ResumeCreateRequest) -> None:
    """요청 데이터 검증"""
    if not request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="요청 데이터가 없습니다.",
        )

    # 필수 필드 검증 (통합 스키마의 validation 활용)
    if not request.email or "@" not in request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효한 이메일 주소를 입력해주세요.",
        )

    if not request.preferred_job.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="희망 직무를 입력해주세요.",
        )


async def _generate_resume_document(request: ResumeCreateRequest) -> bytes:
    """이력서 문서 생성"""
    try:
        logger.info("이력서 문서 생성 시작")

        file_obj = await asyncio.to_thread(_generate_resume_doc, request)

        if not file_obj:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이력서 문서 생성에 실패했습니다.",
            )

        logger.info("이력서 문서 생성 완료")
        return file_obj

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이력서 문서 생성 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이력서 문서 생성 실패: {str(e)}",
        )


def _generate_filename() -> str:
    """파일명 생성"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_draft_{timestamp}.docx"
        logger.info(f"생성된 파일명: {filename}")
        return filename

    except Exception as e:
        logger.error(f"파일명 생성 중 오류: {str(e)}")
        # 기본 파일명 사용
        fallback_filename = "resume_draft.docx"
        logger.warning(f"기본 파일명 사용: {fallback_filename}")
        return fallback_filename


async def _upload_to_s3(file_obj: bytes, filename: str) -> str:
    """S3 업로드"""
    try:
        logger.info("S3 업로드 시작")

        file_url = await async_upload_file_to_s3(file_obj, filename)

        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 업로드에 실패했습니다.",
            )

        logger.info(f"S3 업로드 완료: {file_url}")
        return file_url

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"S3 업로드 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 실패: {str(e)}",
        )


# 추가: BaseInputsModel 변환 테스트용 엔드포인트
@router.post("/resume/draft/validate")
async def validate_resume_data(request: ResumeCreateRequest):
    """
    이력서 데이터 검증 및 변환 테스트용 엔드포인트
    """
    try:
        # ResumeCreateRequest를 BaseInputsModel로 변환 테스트
        base_inputs = request.to_base_inputs()

        return {
            "valid": True,
            "original": request.dict(),
            "converted": base_inputs.dict(),
            "message": "데이터 검증 및 변환 성공",
        }

    except Exception as e:
        logger.error(f"데이터 검증 실패: {e}")
        raise HTTPException(status_code=400, detail=f"데이터 검증 실패: {str(e)}")


# 추가: 이력서 생성 상태 확인 API (향후 비동기 처리용)
@router.get("/resume/draft/status/{task_id}")
async def check_resume_draft_status(task_id: str):
    """
    이력서 생성 상태 확인 API
    (향후 비동기 백그라운드 처리 시 사용 예정)
    """
    # 현재는 placeholder 구현
    return {
        "httpStatusCode": 200,
        "message": "작업 상태 조회 성공",
        "data": {
            "taskId": task_id,
            "status": "completed",  # pending, processing, completed, failed
            "progress": 100,
            "result": None,  # 완료된 경우 결과 URL
        },
    }


# 추가: 이력서 템플릿 목록 API (향후 확장용)
@router.get("/resume/templates")
async def get_resume_templates():
    """
    이용 가능한 이력서 템플릿 목록 반환
    (향후 다양한 템플릿 지원 시 사용 예정)
    """
    return {
        "httpStatusCode": 200,
        "message": "템플릿 목록 조회 성공",
        "data": {
            "templates": [
                {
                    "id": "basic",
                    "name": "기본 템플릿",
                    "description": "깔끔하고 전문적인 기본 이력서 템플릿",
                    "preview_url": None,
                    "is_default": True,
                }
            ]
        },
    }
