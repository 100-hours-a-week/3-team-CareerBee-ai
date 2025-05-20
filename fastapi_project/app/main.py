from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from app.routes import health, resume_create, resume_extract, feedback
from dotenv import load_dotenv
import traceback

load_dotenv(override=True)
app = FastAPI()


# HTTPException
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "httpStatusCode": exc.status_code,
            "message": "HTTP 예외 발생",
            "detail": exc.detail,
        },
    )


# 유효성 검증 에러 (Pydantic 모델 에러 등)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "httpStatusCode": 422,
            "message": "요청 데이터 검증 실패",
            "detail": exc.errors(),
        },
    )


# 3. 일반적인 예외 (미처 처리되지 않은 예외)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()  # 서버 콘솔에 에러 로그 출력
    return JSONResponse(
        status_code=500,
        content={
            "httpStatusCode": 500,
            "message": "내부 서버 오류입니다.",
            "detail": str(exc),
        },
    )


app.include_router(resume_create.router, tags=["Resume"])
app.include_router(resume_extract.router, prefix="/resume", tags=["Resume Extract"])
app.include_router(health.router)
app.include_router(feedback.router, tags=["Feedback"])
