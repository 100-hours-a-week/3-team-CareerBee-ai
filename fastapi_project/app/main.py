# app/main.py
import logging
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from starlette.exceptions import HTTPException as StarletteHTTPException


from app.routes.resume_create import router as resume_create_router

from app.routes.health import router as health_router
from app.routes.resume_extract import router as resume_extract_router
from app.routes.feedback import router as feedback_router
from app.routes.summary import router as summary_router
from app.routes.resume_agent_init import router as agent_init_router
from app.routes.resume_agent_update import router as agent_update_router

from app.handlers.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

from app.utils.redis_client import get_redis_client
from app.schemas import HealthCheckResponse

from app.services.summary_service import run_summary_pipeline
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from dotenv import load_dotenv

from prometheus_fastapi_instrumentator import Instrumentator

# ✅ 전역 로깅 설
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv(override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명 주기 관리"""
    logger.info("서버 시작")

    # Redis 연결 확인
    try:
        redis_client = get_redis_client()
        health = await redis_client.health_check()
        logger.info(f"Redis 연결 상태: {health}")
    except Exception as e:
        logger.warning(f"Redis 연결 확인 실패 (fallback 모드): {e}")

    # 외부 서비스 연결 확인
    await check_external_services()

    # 스케줄러 시작
    logger.info("백그라운드 스케줄러 시작")
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_summary_pipeline,
        "cron",
        day_of_week="mon",
        hour=12,
        timezone=timezone("Asia/Seoul"),
    )
    scheduler.start()

    app.state.scheduler = scheduler

    yield

    logger.info("서버 종료")

    # 스케줄러 정리
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        logger.info("백그라운드 스케줄러 종료")


# FastAPI 앱 생성 (lifespan 추가)
app = FastAPI(
    title="FastAPI",
    version="1.0.0",
    description="CareerBee AI 기능",
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# # ✅ HTTP 예외 핸들러
# @app.exception_handler(StarletteHTTPException)
# async def http_exception_handler(request: Request, exc: StarletteHTTPException):
#     logger.warning(
#         f"HTTP Exception: {exc.status_code} - {exc.detail} - "
#         f"Path: {request.url.path} - Client: {request.client.host if request.client else 'unknown'}"
#     )
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "httpStatusCode": exc.status_code,
#             "message": "HTTP 예외 발생",
#             "detail": exc.detail,
#         },
#     )


# # ✅ 요청 유효성 검증 실패 (422) 핸들러
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     body = await request.body()
#     logging.warning("❌ 422 요청 데이터 검증 실패")
#     logging.warning(f"📦 요청 바디: {body.decode('utf-8')}")
#     logging.warning(f"🔍 에러 상세: {exc.errors()}")

#     return JSONResponse(
#         status_code=422,
#         content={
#             "httpStatusCode": 422,
#             "message": "요청 데이터 검증 실패",
#             "detail": exc.errors(),
#         },
#     )


# # ✅ 기타 예외 핸들러
# @app.exception_handler(Exception)
# async def generic_exception_handler(request: Request, exc: Exception):
#     logger.error(
#         f"Unhandled Exception: {type(exc).__name__} - {str(exc)} - "
#         f"Path: {request.url.path} - Client: {request.client.host if request.client else 'unknown'}",
#         exc_info=True,
#     )
#     traceback.print_exc()
#     return JSONResponse(
#         status_code=500,
#         content={
#             "httpStatusCode": 500,
#             "message": "내부 서버 오류입니다.",
#             "detail": str(exc),
#         },
#     )


# 라우터 등록
app.include_router(agent_init_router, prefix="/api/v1", tags=["Resume Agent"])
app.include_router(resume_create_router, tags=["Resume-create"])
app.include_router(resume_extract_router, tags=["Resume-extract"])
app.include_router(health_router, tags=["Health"])
app.include_router(feedback_router, tags=["Feedback"])
app.include_router(summary_router, tags=["Summary"])
app.include_router(agent_update_router, prefix="/api/v1", tags=["Resume Agent"])

# 공통 핸들러 등록
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# ✅ 기본 헬스 체크
@app.get("/health-check")
def health_check():
    return {"status": "ok"}


# 고급 헬스 체크
@app.get("/health/detailed", response_model=HealthCheckResponse, tags=["Health"])
async def detailed_health_check():
    """상세 서비스 헬스 체크 (Redis, LLM, S3 상태 포함)"""
    try:
        redis_client = get_redis_client()
        redis_health = await redis_client.health_check()

        # 전체 서비스 상태 확인
        all_services = await check_external_services()
        all_services.update(redis_health)

        # 스케줄러 상태 추가
        scheduler_status = (
            "running"
            if hasattr(app.state, "scheduler") and app.state.scheduler.running
            else "stopped"
        )
        all_services["scheduler"] = {"status": scheduler_status}

        # 전체적인 건강 상태 판단
        overall_status = "healthy"
        if not redis_health.get("redis_connected", False):
            overall_status = "degraded"  # Redis 없어도 fallback으로 동작

        # LLM 서비스가 실패하면 unhealthy
        if not all_services.get("openai", {}).get("connected", False):
            overall_status = "unhealthy"
        return HealthCheckResponse(
            status=overall_status, services=all_services, version="1.0.0"
        )

    except Exception as e:
        logger.error(f"상세 헬스체크 실패: {e}")
        return HealthCheckResponse(
            status="unhealthy", services={"error": str(e)}, version="1.0.0"
        )


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Resume Agent API + Services",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "basic_health": "/health-check",
            "detailed_health": "/health/detailed",
        },
        "features": [
            "이력서 생성 (기본/고급)",
            "이력서 추출",
            "면접 피드백",
            "기업 정보 요약 서비스",
            "Redis 상태 관리",
        ],
    }


# 외부 서비스 연결 확인 함수
async def check_external_services():
    """외부 서비스 연결 상태 확인"""
    services_status = {}

    try:
        from app.utils.llm_client import create_llm_client

        llm_client = create_llm_client()
        services_status["llm"] = {
            "connected": True,
            "type": getattr(llm_client, "llm_type", "unknown"),
        }
        logger.info("LLM 클라이언트 연결 확인 완료")
    except Exception as e:
        services_status["llm"] = {"connected": False, "error": str(e)}
        logger.warning(f"LLM 클라이언트 연결 실패: {e}")

    # S3 연결 확인
    try:
        import os

        bucket_name = os.getenv("S3_BUCKET_NAME")
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")

        if bucket_name and aws_key:
            services_status["s3"] = {"connected": True, "bucket": bucket_name}
        else:
            services_status["s3"] = {
                "connected": False,
                "error": "Missing S3 credentials",
            }

        logger.info("S3 설정 확인 완료")

    except Exception as e:
        services_status["s3"] = {"connected": False, "error": str(e)}
        logger.warning(f"S3 설정 확인 실패: {e}")

    return services_status


# 개발 서버 실행
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
