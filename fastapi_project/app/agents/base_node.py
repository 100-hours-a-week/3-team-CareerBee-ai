from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional
from app.agents.schema.resume_create_agent import ResumeAgentState


class BaseNode(ABC):
    """모든 노드의 기본 인터페이스"""

    def __init__(self):
        """기본 초기화 - 로거 설정"""
        self.logger = logging.getLogger(self.__class__.__name__)

    async def __call__(self, state: ResumeAgentState) -> ResumeAgentState:
        """
        LangGraph 호환 진입점
        - 에러 핸들링과 로깅을 포함한 래퍼 메서드
        """
        node_name = self.__class__.__name__

        # 방어적 로거 초기화
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(node_name)

        self.logger.info(f"🚀 {node_name} 실행 시작")
        self.logger.debug(
            f"입력 상태: asked_count={state.asked_count}, info_ready={state.info_ready}"
        )

        try:
            # 상태 유효성 검증
            self._validate_state(state)

            # 실제 노드 로직 실행
            result_state = await self.execute(state)

            # 결과 검증
            self._validate_result(result_state)

            self.logger.info(f"✅ {node_name} 실행 완료")
            self.logger.debug(
                f"출력 상태: asked_count={result_state.asked_count}, info_ready={result_state.info_ready}"
            )

            return result_state

        except Exception as e:
            self.logger.error(f"❌ {node_name} 실행 실패: {str(e)}")
            # 에러 발생시 원본 상태에 에러 정보 추가
            return self._handle_error(state, e)

    @abstractmethod
    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        """
        실제 노드 로직을 구현하는 메서드
        각 노드에서 반드시 구현해야 함
        """
        pass

    def _validate_state(self, state: ResumeAgentState) -> None:
        """
        입력 상태 유효성 검증
        필요시 각 노드에서 오버라이드
        """
        if not isinstance(state, ResumeAgentState):
            raise TypeError(f"Expected ResumeAgentState, got {type(state)}")

        # 기본 필수 필드 검증
        if not hasattr(state, "inputs") or state.inputs is None:
            raise ValueError("State must have valid inputs")

    def _validate_result(self, state: ResumeAgentState) -> None:
        """
        출력 상태 유효성 검증
        필요시 각 노드에서 오버라이드
        """
        if not isinstance(state, ResumeAgentState):
            raise TypeError(f"Node must return ResumeAgentState, got {type(state)}")

    def _handle_error(
        self, state: ResumeAgentState, error: Exception
    ) -> ResumeAgentState:
        """
        에러 처리 - 상태에 에러 정보 추가
        """
        self.logger.error(f"노드 실행 중 오류 발생: {str(error)}")

        # 상태를 복사하여 에러 정보 추가
        if hasattr(state, "model_copy"):
            error_state = state.model_copy()
        elif hasattr(state, "copy"):
            error_state = state.copy()
        else:
            # 기본적으로 원본 상태 사용
            error_state = state

        # 에러 정보를 step에 기록
        error_state.step = f"error_in_{self.__class__.__name__.lower()}"

        # CreateResumeNode에서 에러가 발생한 경우 특별 처리
        if self.__class__.__name__ == "CreateResumeNode":
            # 에러 발생해도 resume 내용이 있다면 유지
            if not error_state.resume and hasattr(self, "_last_generated_content"):
                error_state.resume = self._last_generated_content

            # 에러 정보를 resume에 추가
            error_message = (
                f"\n\n⚠️ 이력서 파일 생성 중 오류가 발생했습니다: {str(error)}"
            )
            if error_state.resume:
                error_state.resume += error_message
            else:
                error_state.resume = f"이력서 생성 완료{error_message}"

        return error_state

    def _log_state_change(
        self, before: ResumeAgentState, after: ResumeAgentState
    ) -> None:
        """
        상태 변화 로깅 (디버깅용)
        """
        changes = []

        if before.asked_count != after.asked_count:
            changes.append(f"asked_count: {before.asked_count} → {after.asked_count}")

        if before.info_ready != after.info_ready:
            changes.append(f"info_ready: {before.info_ready} → {after.info_ready}")

        if len(before.answers) != len(after.answers):
            changes.append(
                f"answers count: {len(before.answers)} → {len(after.answers)}"
            )

        if before.pending_questions != after.pending_questions:
            changes.append(
                f"pending_questions: {len(before.pending_questions)} → {len(after.pending_questions)}"
            )

        if changes:
            self.logger.debug(f"상태 변화: {', '.join(changes)}")


class LLMBaseNode(BaseNode):
    """
    LLM을 사용하는 노드들의 기본 클래스
    공통 LLM 관련 기능 제공
    """

    def __init__(self, llm=None):
        super().__init__()

        # LLM 클라이언트 설정
        if llm is None:
            from app.utils.llm_client import create_llm_client

            self.llm = create_llm_client(temperature=0.3)
        else:
            # 기존 ChatOpenAI 객체인 경우 래핑
            if hasattr(llm, "model_name") or hasattr(llm, "model"):
                from app.utils.llm_client import ChatLLM

                self.llm = ChatLLM(temperature=getattr(llm, "temperature", 0.3))
            else:
                self.llm = llm

    def _validate_state(self, state: ResumeAgentState) -> None:
        """LLM 노드 전용 검증"""
        super()._validate_state(state)

        if self.llm is None:
            raise ValueError(f"{self.__class__.__name__} requires LLM instance")

    async def _safe_llm_call(
        self,
        prompt: str,
        system_prompt: str = None,
        fallback_response: str = "처리 중 오류가 발생했습니다.",
    ) -> str:
        """
        안전한 LLM 호출 - 에러 핸들링 포함
        """
        try:
            # LLM 클라이언트 타입에 따른 호출 방식 결정
            if hasattr(self.llm, "client") and hasattr(self.llm.client, "ainvoke"):
                # 새로운 LLMClient 또는 ChatLLM 사용
                response = await self.llm.ainvoke(prompt, system_prompt)
            elif hasattr(self.llm, "ainvoke"):
                # 직접 LLMClient 사용하거나 기존 ChatOpenAI
                if system_prompt:
                    # system_prompt 파라미터를 지원하는지 확인
                    import inspect

                    sig = inspect.signature(self.llm.ainvoke)
                    if len(sig.parameters) > 1:  # self 제외하고 2개 이상 파라미터
                        response = await self.llm.ainvoke(prompt, system_prompt)
                    else:
                        # system_prompt를 지원하지 않으면 prompt에 합침
                        full_prompt = f"{system_prompt}\n\n{prompt}"
                        response = await self.llm.ainvoke(full_prompt)
                else:
                    response = await self.llm.ainvoke(prompt)
            else:
                self.logger.error(f"지원되지 않는 LLM 타입: {type(self.llm)}")
                return fallback_response

            # 응답 내용 추출
            if hasattr(response, "content"):
                return response.content.strip()
            else:
                return str(response).strip()

        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {str(e)}")
            return fallback_response
