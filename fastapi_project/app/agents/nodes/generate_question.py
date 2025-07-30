# app/agents/nodes/generate_question.py
from app.schemas import ResumeAgentState
from app.agents.base_node import LLMBaseNode
from app.utils.llm_client import LLMClient, create_llm_client
from app.utils.safety_filter import is_toxic, SafetyFilterError  # safety filter import
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class GenerateQuestionNode(LLMBaseNode):
    def __init__(self, llm_client: Optional[Union[LLMClient, object]] = None):
        """
        GenerateQuestionNode 초기화

        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        # LLM 클라이언트가 없으면 자동 생성
        if llm_client is None:
            llm_client = create_llm_client(
                temperature=0.7
            )  # 질문 생성에는 좀 더 창의적으로

        super().__init__(llm_client)
        self.max_questions = 3

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        """이력서 정보 기반 추가 질문 생성"""
        # 최대 질문 수 체크
        if state.asked_count >= self.max_questions:
            self.logger.info(
                f"최대 질문 수({self.max_questions})에 도달. 정보 수집 완료."
            )
            return self._set_ready_state(state)

        try:
            # 1. 입력 데이터 안전성 검증
            self._validate_user_inputs(state)

            # 2. 컨텍스트 구성
            context = self._build_context(state)
            prompt = self._build_prompt(context)

            # 시스템 프롬프트 설정 (안전한 질문 생성 강조)
            system_prompt = """너는 이력서 작성을 돕는 전문가야. 사용자 정보 기반으로 이력서에 도움이 되는 질문을 **하나만** 생성해.

- 자연스럽게 질문 내용만 출력 (예: 어떤 프로젝트를 수행하며 기술을 활용하셨나요?)
- "질문:"이나 해설, 설명 붙이지 마
- 이전 질문과 겹치지 않게
- 정보가 충분하면 '없음'만 출력
- 개인의 프라이버시를 존중하고, 차별적이거나 부적절한 질문은 절대 하지 마
- 전문적이고 건설적인 질문만 생성"""

            # 3. LLM 호출
            response = await self._safe_llm_call(prompt, system_prompt, "없음")
            self.logger.debug(f"LLM 응답: {response}")

            # 4. 생성된 질문 안전성 검증
            return await self._process_response_with_safety(state, response)

        except SafetyFilterError as e:
            self.logger.warning(f"안전성 필터 감지: {e}")
            # 안전성 문제 발생 시 기본 질문 생성 또는 정보 수집 완료
            return self._handle_safety_error(state)

        except Exception as e:
            self.logger.error(f"질문 생성 중 오류: {e}")
            # 에러 발생시 정보 수집 완료로 처리
            return self._set_ready_state(state)

    def _validate_user_inputs(self, state: ResumeAgentState) -> None:
        """사용자 입력 데이터의 안전성 검증"""
        # 검증할 필드들
        fields_to_check = [
            ("이메일", state.inputs.email),
            ("선호 직무", state.inputs.preferred_job),
            ("회사명", state.inputs.company_name),
            ("직무", state.inputs.position),
            ("추가 경험", state.inputs.additional_experiences),
        ]

        # 이전 답변들도 검증
        for answer_data in state.answers:
            fields_to_check.append(
                (f"답변_{answer_data['question'][:20]}", answer_data["answer"])
            )

        # 각 필드 검증
        for field_name, field_value in fields_to_check:
            if field_value and isinstance(field_value, str):
                is_toxic_result, scores = is_toxic(field_value)
                if is_toxic_result:
                    raise SafetyFilterError(
                        f"{field_name} 필드에 부적절한 내용이 포함되어 있습니다. "
                        "이력서 정보를 다시 확인해 주세요."
                    )

    def _set_ready_state(self, state: ResumeAgentState) -> ResumeAgentState:
        """정보 수집 완료 상태로 설정"""
        state.info_ready = True
        state.pending_questions = []
        return state

    def _build_context(self, state: ResumeAgentState) -> str:
        """현재 상태 기반 컨텍스트 구성"""
        formatted_answers = "\n".join(
            [f"- Q: {a['question']}\n  A: {a['answer']}" for a in state.answers]
        )

        return f"""
        현재까지 받은 정보는 다음과 같습니다:
        이메일: {state.inputs.email}
        선호 직무: {state.inputs.preferred_job}
        자격증 개수: {state.inputs.certification_count}
        프로젝트 개수: {state.inputs.project_count}
        전공 여부: {state.inputs.major_type}
        재직 회사: {state.inputs.company_name}
        재직 기간: {state.inputs.work_period}
        직무: {state.inputs.position}
        기타: {state.inputs.additional_experiences}
        
        이전에 받은 추가 질문 답변:
        {formatted_answers}
        """

    def _build_prompt(self, context: str) -> str:
        """LLM용 프롬프트 구성"""
        return f"""
        다음은 사용자가 입력한 이력서 정보야. 여기에 기반해서 **추가 질문 1개만 출력**해 줘.
        {context}
        """

    async def _process_response_with_safety(
        self, state: ResumeAgentState, response: str
    ) -> ResumeAgentState:
        """LLM 응답 처리 (안전성 검증 포함)"""
        self.logger.info(f"질문 생성 응답: {response}")

        if response == "없음" or "없음" in response:
            return self._set_ready_state(state)

        # 생성된 질문 안전성 검증
        is_toxic_result, scores = is_toxic(response)
        if is_toxic_result:
            self.logger.warning(f"생성된 질문이 부적절함: {response[:50]}...")
            # 부적절한 질문인 경우 안전한 대체 질문 사용
            return self._use_safe_fallback_question(state)

        # 안전한 질문인 경우 정상 처리
        state.pending_questions = [response]
        return state

    def _process_response(
        self, state: ResumeAgentState, response: str
    ) -> ResumeAgentState:
        """LLM 응답 처리 (기존 메서드 - 하위 호환성 유지)"""
        return self._process_response_with_safety(state, response)

    def _handle_safety_error(self, state: ResumeAgentState) -> ResumeAgentState:
        """안전성 문제 발생 시 처리"""
        # 이미 질문을 한 번 이상 했다면 정보 수집 완료
        if state.asked_count > 0:
            self.logger.info("안전성 문제로 인해 추가 질문 생성 중단")
            return self._set_ready_state(state)

        # 첫 질문인 경우 안전한 기본 질문 사용
        return self._use_safe_fallback_question(state)

    def _use_safe_fallback_question(self, state: ResumeAgentState) -> ResumeAgentState:
        """안전한 대체 질문 사용 - 개발자 직군 전용"""
        # 개발자 직군에 맞는 안전한 기본 질문
        safe_developer_question = (
            "최근에 사용하신 기술 스택이나 개발 프로젝트에 대해 설명해 주시겠어요?"
        )

        state.pending_questions = [safe_developer_question]
        return state
