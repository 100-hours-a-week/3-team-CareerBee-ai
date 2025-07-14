# app/handlers/exception_handlers.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.schemas.api_responses import create_error_response
import traceback
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"[HTTPException] {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            message="요청 처리 중 오류가 발생했습니다.",
            status_code=exc.status_code,
            detail=exc.detail,
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"[ValidationError] {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content=create_error_response(
            message="요청 유효성 검사 실패",
            status_code=422,
            detail=str(exc.errors()),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"[Unhandled Exception] {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            message="서버 내부 오류가 발생했습니다.",
            status_code=500,
            detail=str(exc),
        ),
    )
