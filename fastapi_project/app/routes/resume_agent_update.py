import logging
import asyncio
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.agents.graph.resume_agent import resume_agent
from app.schemas.resume_agent import ResumeAgentRequest, InputsModel
from app.agents.schema.resume_create_agent import ResumeAgentState

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()


# 질문-답변 반복시 업데이트 API
@router.post("/resume/agent/update")
async def update_resume_agent(payload: ResumeAgentRequest):
    logging.info("업데이트 요청 들어옴")
    # inputs 형 변환
    inputs_data = payload.inputs
    if isinstance(inputs_data, dict):
        inputs_data = InputsModel(**inputs_data)
    elif not isinstance(inputs_data, InputsModel):
        raise ValueError("inputs must be a dict or InputsModel")

    # 상태 구성
    converted_state = ResumeAgentState(
        inputs=inputs_data,
        user_inputs=payload.user_inputs,
        answers=payload.answers,
        pending_questions=payload.pending_questions,
        resume=payload.resume,
        docx_path=payload.docx_path,
        info_ready=payload.info_ready,
        asked_count=payload.asked_count,
    )

    # stream 실행을 별도 스레드에서
    def run_stream_from_state(state: ResumeAgentState):
        final_step = None
        for step in resume_agent.stream(state):
            logging.info("Update stream step: %s", step)
            final_step = step
        return final_step

    final_step = await asyncio.to_thread(run_stream_from_state, converted_state)

    raw_state = list(final_step.values())[0]
    resume_state = (
        ResumeAgentState(**raw_state) if isinstance(raw_state, dict) else raw_state
    )

    # dict로 직렬화
    result = jsonable_encoder(resume_state)
    if not isinstance(result["inputs"], dict):
        result["inputs"] = jsonable_encoder(resume_state.inputs)

    logging.info(f"✅ 최종 응답 데이터: {result}")
    return JSONResponse(content=result)
