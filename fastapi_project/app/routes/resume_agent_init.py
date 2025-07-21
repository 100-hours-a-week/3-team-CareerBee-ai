# app/routes/resume_agent_init.py
"""
이력서 에이전트 초기화 API - Redis 기반 + 새로운 API 형식
"""
import traceback
import logging
import datetime


from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import (
    ResumeAgentInitRequest,
    ResumeAgentInitResponse,
    create_initial_state,
    create_agent_init_response,
    create_error_response,
)
from app.agents.nodes.generate_question import GenerateQuestionNode
from app.utils.llm_client import create_llm_client
from app.utils.redis_client import get_redis_client

# 로깅 기본 설정
logger = logging.getLogger(__name__)

# LLM 및 Redis 클라이언트 초기화
llm_client = create_llm_client(temperature=0.3)
redis_client = get_redis_client()

router = APIRouter()

# 간단한 질문 목록 (LLM 실패 시 fallback용)
FALLBACK_QUESTIONS = [
    "가장 자신있는 기술 스택이나 프로그래밍 언어는 무엇인가요?",
    "지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트에 대해 설명해주세요.",
    "앞으로 어떤 개발자가 되고 싶으신가요?",
]


@router.post("/resume/agent/init", response_model=ResumeAgentInitResponse)
async def initialize_resume_agent(payload: ResumeAgentInitRequest):
    """
    이력서 에이전트 초기화 API

    1. 초기 상태 생성 (Redis 기반)
    2. 첫 번째 질문 생성 (LLM 또는 fallback)
    3. Redis에 상태 저장
    4. 새로운 형식 응답 반환 (memberId + question)
    """
    memberId = payload.memberId
    # 요청 입력값 로깅
    logger.info(f"=== 초기화 요청 ===")
    logger.info(f"memberId: {memberId}")
    logger.info(f"inputs: {payload.inputs}")
    logger.info(f"timestamp: {datetime.now()}")
    try:
        logger.info(f"이력서 에이전트 초기화 요청: memberId={memberId}")

        # 1. 기존 상태 확인 및 정리
        existing_deleted = await redis_client.delete_state(memberId)
        if existing_deleted:
            logger.warning(f"기존 세션 삭제 완료: memberId={memberId}")

        # 2. 새로운 초기 상태 생성
        initial_state = create_initial_state(memberId=memberId, inputs=payload.inputs)
        logger.info(f"초기 상태 생성 완료: memberId={memberId}")

        # 3. 첫 번째 질문 생성
        first_question = await _generate_first_question(initial_state)

        # 4. 상태에 질문 추가
        initial_state.pending_questions = [first_question]
        initial_state.step = "questioning"

        # 5. Redis에 상태 저장
        save_success = await redis_client.save_state(memberId, initial_state)
        if not save_success:
            logger.error(f"상태 저장 실패: memberId={memberId}")
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    message="상태 저장에 실패했습니다.", status_code=500
                ),
            )

        # 6. 새로운 형식 응답 반환
        response = create_agent_init_response(
            memberId=memberId, question=first_question
        )

        logger.info(f"✅ 초기화 완료: memberId={memberId}, question='{first_question}'")
        return JSONResponse(content=response.dict())

    except HTTPException:
        # HTTPException은 그대로 re-raise
        raise

    except Exception as e:
        logger.error(f"초기화 중 오류 발생: memberId={memberId}, error={str(e)}")
        logger.error(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message=f"이력서 에이전트 초기화 실패: {str(e)}", status_code=500
            ),
        )


async def _generate_first_question(state) -> str:
    """첫 번째 질문 생성 (LLM 또는 fallback)"""
    try:
        # LLM으로 질문 생성 시도
        question_node = GenerateQuestionNode(llm_client)
        updated_state = await question_node.execute(state)

        # 생성된 질문 확인
        generated_question = updated_state.get_next_question()
        if generated_question and generated_question.strip():
            logger.info(f"LLM 질문 생성 성공: {generated_question}")
            return generated_question.strip()

        # LLM으로 질문을 생성하지 못했다면 fallback 사용
        logger.warning("LLM에서 질문 생성 실패, fallback 질문 사용")
        return FALLBACK_QUESTIONS[0]

    except Exception as e:
        logger.error(f"질문 생성 중 오류: {e}")
        logger.warning("LLM 질문 생성 실패, fallback 질문 사용")
        return FALLBACK_QUESTIONS[0]


@router.get("/resume/agent/status/{memberId}")
async def get_agent_status(memberId: int):
    """
    에이전트 상태 조회 API (디버깅용)
    """
    try:
        state = await redis_client.load_state(memberId)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"회원 {memberId}의 이력서 생성 세션을 찾을 수 없습니다.",
            )

        # 상태 정보 반환
        status_data = {
            "memberId": memberId,
            "step": state.step,
            "asked_count": state.asked_count,
            "max_questions": state.max_questions,
            "info_ready": state.info_ready,
            "pending_questions": len(state.pending_questions),
            "answers_count": len(state.answers),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

        return JSONResponse(content=status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상태 조회 실패: memberId={memberId}, error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resume/agent/session/{memberId}")
async def delete_agent_session(memberId: int):
    """
    에이전트 세션 삭제 API (관리용)
    """
    try:
        deleted = await redis_client.delete_state(memberId)

        response_data = {
            "memberId": memberId,
            "deleted": deleted,
            "message": (
                "세션이 삭제되었습니다." if deleted else "삭제할 세션이 없습니다."
            ),
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"세션 삭제 실패: memberId={memberId}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")


# 추가: Redis 헬스체크
@router.get("/resume/agent/health")
async def agent_health_check():
    """
    에이전트 및 Redis 상태 확인
    """
    try:
        # Redis 헬스체크
        redis_health = await redis_client.health_check()

        # LLM 클라이언트 상태 (간단 체크)
        llm_status = "available" if llm_client else "unavailable"

        health_data = {
            "agent_status": "healthy",
            "redis": redis_health,
            "llm": {
                "status": llm_status,
                "type": getattr(llm_client, "llm_type", "unknown"),
            },
            "fallback_questions": len(FALLBACK_QUESTIONS),
        }

        return JSONResponse(content=health_data)

    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return JSONResponse(
            status_code=500, content={"agent_status": "unhealthy", "error": str(e)}
        )


@router.post(
    "/resume/agent/reset",
    summary="에이전트 상태 초기화 (Redis 삭제)",
    description="memberId에 해당하는 Redis 상태를 삭제하여 세션을 초기화합니다. 테스트용으로 사용하세요.",
    tags=["ResumeAgent"],
)
async def reset_agent_session(memberId: int):
    """
    특정 memberId에 대한 에이전트 세션 상태 초기화 (Redis 삭제)

    사용 예:
    POST /resume/agent/reset?memberId=3
    """
    try:
        deleted = await redis_client.delete_state(memberId)

        return JSONResponse(
            content={
                "memberId": memberId,
                "deleted": deleted,
                "message": (
                    "세션 상태가 초기화되었습니다."
                    if deleted
                    else "삭제할 세션이 없습니다."
                ),
            }
        )

    except Exception as e:
        logger.error(f"세션 초기화 실패: memberId={memberId}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"세션 초기화 실패: {str(e)}")
