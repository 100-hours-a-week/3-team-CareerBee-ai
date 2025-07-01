from app.agents.base_node import BaseNode
from app.agents.schema.resume_create_agent import ResumeAgentState


class ReceiveAnswerNode(BaseNode):
    def __init__(self, llm=None):
        """
        ReceiveAnswerNode 초기화
        Args:
            llm: LLM 인스턴스 (사용하지 않지만 일관성을 위해 받음)
        """
        self.llm = llm
        super().__init__() if hasattr(super(), "__init__") else None

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        if not state.pending_questions:
            return state

        question = state.pending_questions[0]
        answer = self._get_answer(state, question)

        # 질문-답변 저장
        state.answers.append({"question": question, "answer": answer})

        # 상태 업데이트
        state.asked_count += 1
        state.pending_questions = []

        return state

    def _get_answer(self, state: ResumeAgentState, question: str) -> str:
        """사용자 답변 획득"""
        return state.user_inputs.get(question, "<미응답>")
