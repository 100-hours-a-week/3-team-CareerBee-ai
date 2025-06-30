import sys
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from app.routes import (
    health,
    resume_create,
    resume_extract,
    feedback,
    update_summary,
)
from app.routes.resume_agent_init import router as resume_agent_init_router
from app.routes.resume_agent_update import router as resume_agent_update_router

from app.services.summary_service import run_summary_pipeline
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from dotenv import load_dotenv
import traceback

# ✅ 전역 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)

# 환경변수 로드
load_dotenv(override=True)

app = FastAPI()

# 📌 스케줄러 등록 (매주 월요일 정오에 요약 실행)
scheduler = BackgroundScheduler()
scheduler.add_job(
    run_summary_pipeline,
    "cron",
    day_of_week="mon",
    hour=12,
    timezone=timezone("Asia/Seoul"),
)
scheduler.start()

# ✅ HTTP 예외 핸들러
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

# ✅ 요청 유효성 검증 실패 (422) 핸들러
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logging.warning("❌ 422 요청 데이터 검증 실패")
    logging.warning(f"📦 요청 바디: {body.decode('utf-8')}")
    logging.warning(f"🔍 에러 상세: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={
            "httpStatusCode": 422,
            "message": "요청 데이터 검증 실패",
            "detail": exc.errors(),
        },
    )

# ✅ 기타 예외 핸들러
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "httpStatusCode": 500,
            "message": "내부 서버 오류입니다.",
            "detail": str(exc),
        },
    )

# ✅ 라우터 등록
app.include_router(resume_create, tags=["Resume-create"])
app.include_router(resume_agent_init_router, tags=["Resume-agent-init"])
app.include_router(resume_agent_update_router, tags=["Resume-agent-update"])
app.include_router(resume_extract, tags=["Resume-extract"])
app.include_router(health)
app.include_router(feedback, tags=["Feedback"])
app.include_router(update_summary, tags=["Summary"])

# ✅ 기본 헬스 체크
@app.get("/health-check")
def health_check():
    return {"status": "ok"}