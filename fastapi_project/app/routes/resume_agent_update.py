# app/routes/resume_agent_update.py

import logging
import traceback
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas import (
    ResumeAgentUpdateRequest,
    ResumeAgentUpdateResponse,
    ResumeAgentState,
    update_state_with_answer,
    create_agent_update_response,
    create_error_response,
)

from app.agents.resume_agent import resume_agent
from app.utils.redis_client import get_redis_client

# 로깅 설정
logger = logging.getLogger(__name__)
redis_client = get_redis_client()
router = APIRouter()


class ResumeAgentUpdateService:
    """이력서 에이전트 업데이트 서비스 클래스"""

    def __init__(self):
        self.redis_client = redis_client
        self.logger = logger

    async def update_resume_agent(
        self, payload: ResumeAgentUpdateRequest
    ) -> ResumeAgentUpdateResponse:
        """
        이력서 에이전트 업데이트 메인 로직

        Args:
            payload: 업데이트 요청 데이터 (memberId, answer)

        Returns:
            ResumeAgentUpdateResponse: 업데이트 결과 응답
        """
        memberId = payload.memberId
        answer = payload.answer

        self.logger.info(f"이력서 에이전트 업데이트 시작: memberId={memberId}")

        # 1. 동시성 제어 - 락 획득
        await self._acquire_lock_or_fail(memberId)

        try:
            # 2. 기존 상태 조회 및 검증
            current_state = await self._get_and_validate_state(memberId)

            # 3. 답변 처리 및 상태 업데이트
            updated_state = self._process_answer(current_state, answer)

            # 4. LangGraph 워크플로우 실행
            final_state = await self._execute_agent_workflow(updated_state)

            # 5. 결과 처리 및 응답 생성
            response = await self._process_result(memberId, final_state)

            self.logger.info(f"이력서 에이전트 업데이트 완료: memberId={memberId}")
            return response

        finally:
            # 6. 락 해제
            await self._safe_release_lock(memberId)

    async def _acquire_lock_or_fail(self, memberId: int) -> None:
        """락 획득 또는 예외 발생"""
        lock_acquired = await self.redis_client.acquire_lock(memberId)
        if not lock_acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"회원 {memberId}의 이력서 생성이 이미 진행 중입니다. 잠시 후 다시 시도해주세요.",
            )

    async def _get_and_validate_state(self, memberId: int) -> ResumeAgentState:
        """기존 상태 조회 및 유효성 검증"""
        current_state = await self.redis_client.load_state(memberId)

        if not current_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"회원 {memberId}의 이력서 생성 세션을 찾을 수 없습니다. 초기화부터 다시 시작해주세요.",
            )

        # 이미 완료된 세션인지 확인
        if current_state.info_ready or current_state.step == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"회원 {memberId}의 이력서 생성이 이미 완료되었습니다.",
            )

        # 답변할 질문이 있는지 확인
        if not current_state.pending_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="답변할 질문이 없습니다.",
            )

        return current_state

    def _process_answer(self, state: ResumeAgentState, answer: str) -> ResumeAgentState:
        """답변 처리 및 상태 업데이트"""
        current_question = state.pending_questions[0]

        self.logger.info(f"답변 처리: question='{current_question}', answer='{answer}'")

        # 상태에 답변 추가
        updated_state = update_state_with_answer(
            state=state, question=current_question, answer=answer
        )

        # pending_questions 클리어 (답변 완료)
        updated_state.pending_questions = []
        self.logger.info(
            f"답변 처리 완료: asked_count={updated_state.asked_count}, "
            f"total_answers={len(updated_state.answers)}"
        )
        return updated_state

    async def _execute_agent_workflow(
        self, state: ResumeAgentState
    ) -> ResumeAgentState:
        """LangGraph 워크플로우 실행"""
        try:
            final_step = None
            step_count = 0

            # LangGraph astream 실행
            async for step in resume_agent.astream(state):
                step_count += 1
                self.logger.debug(
                    f"LangGraph step {step_count}: {list(step.keys()) if isinstance(step, dict) else type(step)}"
                )
                final_step = step

            if final_step is None:
                self.logger.warning("LangGraph에서 반환된 step이 없습니다")
                raise Exception("워크플로우 실행 결과가 없습니다")

            # 최종 상태 추출
            final_state = self._extract_final_state(final_step)
            return final_state

        except Exception as e:
            self.logger.error(f"LangGraph 워크플로우 실행 실패: {str(e)}")
            raise Exception(f"워크플로우 실행 실패: {str(e)}")

    def _extract_final_state(self, final_step) -> ResumeAgentState:
        """LangGraph 결과에서 최종 상태 추출"""
        if not final_step:
            raise Exception("빈 결과가 반환되었습니다")

        # final_step이 dict 형태인지 확인
        if isinstance(final_step, dict):
            # 첫 번째 값을 가져옴 (보통 노드 이름이 키가 됨)
            raw_state = list(final_step.values())[0]
        else:
            raw_state = final_step

        self.logger.debug(f"추출된 raw_state 타입: {type(raw_state)}")

        # ResumeAgentState로 변환
        try:
            if isinstance(raw_state, dict):
                return ResumeAgentState(**raw_state)
            elif isinstance(raw_state, ResumeAgentState):
                return raw_state
            else:
                self.logger.error(f"예상치 못한 raw_state 타입: {type(raw_state)}")
                raise Exception(f"잘못된 상태 타입: {type(raw_state)}")

        except Exception as e:
            self.logger.error(f"ResumeAgentState 변환 실패: {e}")
            raise Exception(f"상태 변환 실패: {str(e)}")

    async def _process_result(
        self, memberId: int, final_state: ResumeAgentState
    ) -> ResumeAgentUpdateResponse:
        """결과 처리 및 응답 생성"""
        if final_state.info_ready and final_state.step == "completed":
            # 완료된 경우: Redis에서 삭제하고 S3 키 반환
            return await self._handle_completion(memberId, final_state)
        else:
            # 추가 질문이 있는 경우: Redis에 저장하고 다음 질문 반환
            return await self._handle_next_question(memberId, final_state)

    async def _handle_completion(
        self, memberId: int, final_state: ResumeAgentState
    ) -> ResumeAgentUpdateResponse:
        """이력서 생성 완료 처리"""
        # Redis에서 상태 삭제
        await self.redis_client.delete_state(memberId)

        # S3 object key 생성
        resumeObjectKey = self._extract_s3_object_key(final_state.docx_path, memberId)

        response = create_agent_update_response(
            memberId=memberId, isComplete=True, resumeObjectKey=resumeObjectKey
        )

        self.logger.info(
            f"이력서 생성 완료: memberId={memberId}, resumeObjectKey={resumeObjectKey}"
        )

        return response

    async def _handle_next_question(
        self, memberId: int, final_state: ResumeAgentState
    ) -> ResumeAgentUpdateResponse:
        """다음 질문 처리"""
        # Redis에 상태 저장
        save_success = await self.redis_client.save_state(memberId, final_state)
        if not save_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="상태 저장에 실패했습니다.",
            )

        # 다음 질문 가져오기
        next_question = final_state.get_next_question()
        if not next_question:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="다음 단계를 결정할 수 없습니다.",
            )

        response = create_agent_update_response(
            memberId=memberId, isComplete=False, question=next_question
        )

        self.logger.info(
            f"다음 질문 생성: memberId={memberId}, question='{next_question}'"
        )

        return response

    def _extract_s3_object_key(self, docx_path: str, memberId: int) -> str:
        """docx_path에서 S3 object key 추출 또는 생성"""
        if not docx_path:
            # docx_path가 없으면 기본 키 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"resume/member_{memberId}_{timestamp}.docx"

        # S3 URL에서 object key 추출
        if docx_path.startswith("http"):
            # presigned URL인 경우 파싱
            try:
                from urllib.parse import urlparse

                parsed = urlparse(docx_path)
                # 첫번째 '/' 제거
                resumeObjectKey = parsed.path.lstrip("/")
                return resumeObjectKey
            except Exception as e:
                self.logger.warning(f"URL 파싱 실패: {docx_path}, error: {e}")

        # 이미 object key 형태라면 그대로 반환
        if docx_path.startswith("resume/"):
            return docx_path

        # 로컬 파일 경로인 경우 파일명 추출해서 새 키 생성
        import os

        filename = os.path.basename(docx_path)
        return f"resume/{filename}"

    async def _safe_release_lock(self, memberId: int) -> None:
        """안전한 락 해제"""
        try:
            await self.redis_client.release_lock(memberId)
        except Exception as e:
            self.logger.error(f"락 해제 실패: memberId={memberId}, error={e}")


# 서비스 인스턴스 생성
resume_update_service = ResumeAgentUpdateService()


@router.post("/resume/agent/update", response_model=ResumeAgentUpdateResponse)
async def update_resume_agent(payload: ResumeAgentUpdateRequest):
    """
    이력서 에이전트 업데이트 API

    - 사용자 답변을 받아 Redis 상태 업데이트
    - LangGraph 실행하여 다음 질문 생성 또는 이력서 완성
    - 결과에 따라 Redis 저장/삭제 및 응답 반환
    """
    try:
        response = await resume_update_service.update_resume_agent(payload)
        return JSONResponse(content=response.dict())

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"업데이트 중 예상치 못한 오류: memberId={payload.memberId}, error={str(e)}"
        )
        logger.error(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message=f"이력서 에이전트 업데이트 실패: {str(e)}",
                status_code=500,
            ),
        )
