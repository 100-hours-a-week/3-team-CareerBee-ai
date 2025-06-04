import os
import traceback
import logging

from fastapi import APIRouter, status, Request, Body
from fastapi.responses import JSONResponse
from app.services.resume_create_service import generate_resume_draft
from app.agents.graph.resume_agent import build_resume_agent
from app.schemas.resume_agent import ResumeAgentRequest, ResumeAgentInitRequest

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


@router.post("/resume/agent/init")
async def initialize_resume_stream(payload: ResumeAgentInitRequest):
    logging.info("고급 이력서 생성 요청 들어옴")
    print(payload.inputs)

    # inputs만 받아서 ResumeAgentState 만들어서 stream 실행
    agent = build_resume_agent()

    initial_state = ResumeAgentRequest(
        inputs=payload.inputs.model_dump(),
        user_inputs={},  # 유저 답변은 초기에는 아직 없음
        answers=[],
        pending_questions=[],
        resume="",
        docx_path="",
        info_ready=False,
        asked_count=0,
    )

    stream = agent.stream(initial_state)
    result = None

    for step in stream:
        logging.info("🌀 Agent stream step: %s", step)
        result = step

    node_output = list(result.values())[0]
    return {
        "resume": node_output.get("resume"),
        "docx_path": node_output.get("docx_path"),
        "answers": node_output.get("answers", []),
        "pending_questions": node_output.get("pending_questions", []),
        "info_ready": node_output.get("info_ready", False),
        "asked_count": node_output.get("asked_count", 0),
    }


# # 3️⃣ 공통 응답 포맷 생성 함수
# def extract_state_response(state_obj):
#     return {
#         "resume": state_obj.get("resume"),
#         "docx_path": state_obj.get("docx_path"),
#         "answers": state_obj.get("answers", []),
#         "pending_questions": state_obj.get("pending_questions", []),
#         "info_ready": state_obj.get("info_ready", False),
#         "asked_count": state_obj.get("asked_count", 0),
#     }
