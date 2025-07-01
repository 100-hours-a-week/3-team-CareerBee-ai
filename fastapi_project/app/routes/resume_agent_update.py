import logging
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.agents.resume_agent import resume_agent
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

    try:
        logging.info("업데이트 요청 들어옴")
        logging.info(f"받은 페이로드: {payload}")

        # inputs형 변환 - 더 안전한 방식으로 수정
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

        try:
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
            logging.info(f"상태 변환 완료: {converted_state}")
        except Exception as e:
            logging.error(f"상태 변환 실패: {e}")
            raise HTTPException(status_code=400, detail=f"상태 변환 오류: {str(e)}")

        # stream 실행을 별도 스레드에서
        async def run_async_stream_from_state(state: ResumeAgentState):
            try:
                final_step = None
                step_count = 0

                # atream 사용 (비동기)
                async for step in resume_agent.astream(state):
                    step_count += 1
                    logging.info(f"Update stream step #{step_count}: {step}")
                    final_step = step

                if final_step is None:
                    logging.warning("스트림에서 반환된 step이 없습니다")
                    return None

                return final_step
            except Exception as e:
                logging.error(f"스트림 실행 중 오류: {e}")
                logging.error(traceback.format_exc())
                raise e

        # 비동기로 스트림 실행
        final_step = await run_async_stream_from_state(converted_state)

        if final_step is None:
            raise HTTPException(
                status_code=500, detail="스트림 처리 중 결과를 받지 못했습니다"
            )

        # final_step에서 상태 추출
        if not final_step:
            raise HTTPException(status_code=500, detail="빈 결과가 반환되었습니다")

        # final_step이 dict 형태인지 확인
        if isinstance(final_step, dict):
            # 첫 번째 값을 가져옴 (보통 노드 이름이 키가 됨)
            raw_state = list(final_step.values())[0]
        else:
            raw_state = final_step

        logging.info(f"추출된 raw_state: {raw_state}")

        # ResumeAgentState로 변환
        try:
            if isinstance(raw_state, dict):
                resume_state = ResumeAgentState(**raw_state)
            elif isinstance(raw_state, ResumeAgentState):
                resume_state = raw_state
            else:
                logging.error(f"예상치 못한 raw_state 타입: {type(raw_state)}")
                raise HTTPException(
                    status_code=500, detail=f"잘못된 상태 타입: {type(raw_state)}"
                )
        except Exception as e:
            logging.error(f"ResumeAgentState 변환 실패: {e}")
            raise HTTPException(status_code=500, detail=f"상태 변환 실패: {str(e)}")

        # dict로 직렬화
        try:
            result = jsonable_encoder(resume_state)

            # inputs가 올바르게 직렬화되었는지 확인
            if hasattr(resume_state, "inputs") and not isinstance(
                result.get("inputs"), dict
            ):
                result["inputs"] = jsonable_encoder(resume_state.inputs)

            logging.info(f"✅ 최종 응답 데이터: {result}")
            return JSONResponse(content=result)

        except Exception as e:
            logging.error(f"JSON 직렬화 실패: {e}")
            raise HTTPException(status_code=500, detail=f"응답 생성 실패: {str(e)}")

    except HTTPException:
        # HTTPException은 그대로 re-raise
        raise
    except Exception as e:
        logging.error(f"예상치 못한 오류 발생: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
