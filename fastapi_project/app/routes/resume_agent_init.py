import os
import traceback
import logging
import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.schemas.resume_agent import ResumeAgentInitRequest, ResumeAgentRequest
from app.agents.nodes.generate_question import generate_question_node
from fastapi.encoders import jsonable_encoder

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


@router.post("/resume/agent/init")
async def initialize_resume_stream(payload: ResumeAgentInitRequest):
    logging.info("고급 이력서 생성 요청 들어옴")
    print(payload.inputs)

    initial_state = ResumeAgentRequest(
        inputs=payload.inputs,
        user_inputs={},  # 유저 답변은 초기에는 아직 없음
        answers=[],
        pending_questions=[],
        resume="",
        docx_path="",
        info_ready=False,
        asked_count=0,
    )

    # generate_question_node는 동기 함수 -> asyncio로 비동기 전환
    updated_state = await generate_question_node(initial_state)

    # JSON 직렬화 후 응답 반환
    return jsonable_encoder(updated_state)
