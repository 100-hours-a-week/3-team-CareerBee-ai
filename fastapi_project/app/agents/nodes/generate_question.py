from langchain_openai import ChatOpenAI
from app.agents.schema.resume_create_agent import ResumeAgentState
from app.agents.base_node import LLMBaseNode


class GenerateQuestionNode(LLMBaseNode):
    def __init__(self, llm=None):
        super().__init__(llm)
        self.max_questions = 3

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        # 최대 질문 수 체크
        if state.asked_count >= self.max_questions:
            return self._set_ready_state(state)

        context = self._build_context(state)
        prompt = self._build_prompt(context)

        # 시스템 프롬프트 설정
        system_prompt = """당신은 이력서 작성을 도와주는 전문 컨설턴트입니다.
사용자의 기본 정보를 바탕으로 더 나은 이력서를 작성하기 위해 필요한 추가 정보를 파악하고,
적절한 질문을 하나만 생성해주세요.

질문 생성 가이드라인:
1. 구체적이고 답변 가능한 질문을 만드세요
2. 이전 질문과 중복되지 않도록 하세요  
3. 이력서 품질 향상에 도움이 되는 정보를 얻을 수 있는 질문을 하세요
4. 반드시 "- Q: [질문내용]" 형식으로 출력하세요
5. 정보가 충분하다면 '없음'이라고 답하세요"""

        response = await self._safe_llm_call(prompt, system_prompt, "없음")

        return self._process_response(state, response)

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
        아래는 사용자가 개발자 이력서를 작성하기 위해 입력한 정보입니다. 
        이를 바탕으로 완성도가 높은 이력서를 작성하기 위해 추가로 필요한 정보를 얻기 위한 질문을 "한 개만" 생성하세요. 
        단, 이전에 했던 질문과 겹치지 않도록 하세요.
        생성하는 질문은 반드시 다음과 같은 형식으로 출력하세요:

        - Q: [여기에 질문 내용 작성]
        
        이력서를 작성하기에 정보가 충분하다고 판단되면 '없음'이라고 출력해도 됩니다. 
        
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
