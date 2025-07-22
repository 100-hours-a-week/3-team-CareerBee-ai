# app/agents/nodes/generate_question.py
from app.schemas import ResumeAgentState
from app.agents.base_node import LLMBaseNode
from app.utils.llm_client import LLMClient, create_llm_client
from typing import Optional, Union


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
        # 최대 질문 수 체크
        if state.asked_count >= self.max_questions:
            self.logger.info(
                f"최대 질문 수({self.max_questions})에 도달. 정보 수집 완료."
            )
            return self._set_ready_state(state)

        context = self._build_context(state)
        prompt = self._build_prompt(context)

        # 시스템 프롬프트 설정
        system_prompt = """너는 이력서 작성을 돕는 전문가야. 사용자 정보 기반으로 이력서에 도움이 되는 질문을 **하나만** 생성해.

- 자연스럽게 질문 내용만 출력 (예: 어떤 프로젝트를 수행하며 기술을 활용하셨나요?)
- "질문:"이나 해설, 설명 붙이지 마
- 이전 질문과 겹치지 않게
- 정보가 충분하면 '없음'만 출력
"""

        try:
            response = await self._safe_llm_call(prompt, system_prompt, "없음")
            self.logger.debug(f"LLM 응답: {response}")

            return self._process_response(state, response)

        except Exception as e:
            self.logger.error(f"질문 생성 중 오류: {e}")
            # 에러 발생시 정보 수집 완료로 처리
            return self._set_ready_state(state)

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

    def _process_response(
        self, state: ResumeAgentState, response: str
    ) -> ResumeAgentState:
        """LLM 응답 처리"""
        self.logger.info(f"질문 생성 응답: {response}")

        if response == "없음" or "없음" in response:
            return self._set_ready_state(state)
        else:
            state.pending_questions = [response]
            return state
