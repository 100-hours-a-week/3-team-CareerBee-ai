import os
import traceback
import logging
import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from langchain_openai import ChatOpenAI

from app.schemas.resume_agent import (
    ResumeAgentInitRequest,
    ResumeAgentRequest,
    InputsModel,
)
from app.agents.nodes.generate_question import GenerateQuestionNode
from app.agents.schema.resume_create_agent import ResumeAgentState

# 로깅 기본 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# LLM 초기화
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

router = APIRouter()


@router.post("/resume/agent/init")
async def initialize_resume_stream(payload: ResumeAgentInitRequest):
    try:
        logging.info("고급 이력서 생성 요청 들어옴")
        logging.info(f"입력 데이터: {payload.inputs}")

        # inputs 형 변환
        inputs_data = payload.inputs
        if isinstance(inputs_data, dict):
            try:
                inputs_data = InputsModel(**inputs_data)
            except Exception as e:
                logging.error(f"InputsModel 변환 실패: {e}")
                raise HTTPException(
                    status_code=400, detail=f"inputs 데이터 형식 오류: {str(e)}"
                )
        elif not isinstance(inputs_data, InputsModel):
            raise HTTPException(
                status_code=400, detail="inputs must be a dict or InputsModel"
            )

        # ResumeAgentState 초기 상태 생성 (ResumeAgentRequest 대신 사용)
        initial_state = ResumeAgentState(
            inputs=inputs_data,
            user_inputs={},  # 유저 답변은 초기에는 아직 없음
            answers=[],
            pending_questions=[],
            resume="",
            docx_path="",
            info_ready=False,
            asked_count=0,
        )

        # GenerateQuestionNode 인스턴스 생성 및 실행
        question_node = GenerateQuestionNode(llm)
        updated_state = await question_node.execute(initial_state)

        # JSON 직렬화 후 응답 반환
        result = jsonable_encoder(updated_state)

        # inputs가 올바르게 직렬화되었는지 확인
        if hasattr(updated_state, "inputs") and not isinstance(
            result.get("inputs"), dict
        ):
            result["inputs"] = jsonable_encoder(updated_state.inputs)

        logging.info(f"초기화 완료: {result}")

        return JSONResponse(content=result)

    except HTTPException:
        # HTTPException은 그대로 re-raise
        raise
    except Exception as e:
        logging.error(f"초기화 중 오류 발생: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"초기화 실패: {str(e)}")
