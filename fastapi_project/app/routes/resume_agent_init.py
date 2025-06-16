import os
import traceback
import logging

from fastapi import APIRouter, status, Request, Body
from fastapi.responses import JSONResponse
from app.services.resume_create_service import generate_resume_draft
from app.agents.graph.resume_agent import build_resume_agent
from app.agents.schema.resume_create_agent import ResumeAgentState
from app.schemas.resume_agent import ResumeAgentInitRequest, ResumeAgentRequest
from app.agents.nodes.generate_question import generate_question_node

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
    # agent = build_resume_agent()

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

    # stream = agent.stream(initial_state)
    # first_step = next(stream)

    updated_state = generate_question_node(initial_state)

    return {
        "resume": updated_state.resume,
        "docx_path": updated_state.docx_path,
        "answers": updated_state.answers,
        "pending_questions": updated_state.pending_questions,
        "info_ready": updated_state.info_ready,
        "asked_count": updated_state.asked_count,
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
