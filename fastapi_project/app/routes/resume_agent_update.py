import logging
from fastapi import APIRouter
from app.agents.graph.resume_agent import build_resume_agent
from app.schemas.resume_agent import ResumeAgentRequest

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


# 질문-답변 반복시 업데이트 API
@router.post("/resume/agent/update")
async def update_resume_agent(payload: ResumeAgentRequest):
    logging.info("업데이트 요청 들어옴")

    agent = build_resume_agent()
    stream = agent.stream(payload)
    for step in stream:
        logging.info("🌀 Update stream step: %s", step)
        state = step

    node_output = list(state.values())[0]
    return {
        "resume": node_output.get("resume"),
        "docx_path": node_output.get("docx_path"),
        "answers": node_output.get("answers", []),
        "pending_questions": node_output.get("pending_questions", []),
        "info_ready": node_output.get("info_ready", False),
        "asked_count": node_output.get("asked_count", 0),
    }
