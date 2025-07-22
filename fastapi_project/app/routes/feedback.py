# fastapi_project/app/routes/feedback.py

from fastapi import APIRouter, status, HTTPException
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import generate_feedback
from fastapi.responses import JSONResponse
from app.schemas.api_responses import create_error_response
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/feedback/create", response_model=FeedbackResponse)
async def create_feedback(request: FeedbackRequest):
    """
    피드백 생성 API

    Args:
        request: 피드백 생성 요청 데이터

    Returns:
        JSONResponse: 성공 또는 오류 응답

    Raises:
        400: 클라이언트 오류 (잘못된 요청)
        500: 서버 내부 오류
    """
    try:
        # 1. 입력 데이터 검증
        validation_error = _validate_request(request)
        if validation_error:
            logger.warning(f"입력 검증 실패: {validation_error}")
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="invalid_request",
                    status_code=400,
                    detail=validation_error,
                ),
            )

        # 2. 피드백 생성 서비스 호출
        feedback = await generate_feedback(request.question, request.answer)

        # 3. 성공 응답
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "httpStatusCode": 200,
                "message": "feedback_success",
                "data": {"memberId": request.memberId, "feedback": feedback},
            },
        )

    except ValueError as e:
        # 비즈니스 로직 검증 실패 (예: 안전하지 않은 피드백 응답 포함)
        logger.warning(f"비즈니스 로직 오류: {e}")
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="invalid_request",
                status_code=400,
                detail=str(e),
            ),
        )

    except ConnectionError as e:
        # 외부 서비스 연결 오류
        logger.error(f"외부 서비스 연결 실패: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="internal_server_error",
                status_code=500,
                detail="외부 서비스 연결에 실패했습니다",
            ),
        )

    except TimeoutError as e:
        # 타임아웃 오류
        logger.error(f"요청 처리 타임아웃: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="internal_server_error",
                status_code=500,
                detail="요청 처리 시간이 초과되었습니다",
            ),
        )

    except Exception as e:
        # 예상치 못한 시스템 오류
        logger.error(f"피드백 생성 실패: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="internal_server_error",
                status_code=500,
                detail="서버 내부 오류가 발생했습니다",
            ),
        )


def _validate_request(request: FeedbackRequest) -> str | None:
    """
    요청 데이터 검증

    Args:
        request: 피드백 생성 요청 데이터

    Returns:
        str | None: 검증 오류 메시지 또는 None (정상)
    """
    # 필수 필드 검증
    if not request.question or not request.question.strip():
        return "질문은 필수입니다"

    if not request.answer or not request.answer.strip():
        return "답변은 필수입니다"

    # 길이 제한 검증
    if len(request.question) > 200:
        return "질문은 최대 200자까지 입력 가능합니다"

    if len(request.answer) > 500:
        return "답변은 최대 500자까지 입력 가능합니다"

    # memberId 검증
    if request.memberId <= 0:
        return "유효하지 않은 회원 ID입니다"

    return None
