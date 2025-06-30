from app.agents.base_node import BaseNode
from app.agents.schema.resume_create_agent import ResumeAgentState


class CheckCompletionNode(BaseNode):
    def __init__(self, max_questions: int = 3):
        self.max_questions = max_questions

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:

        if self._is_completed(state):
            state.info_ready = True
        return state

    def _is_completed(self, state: ResumeAgentState) -> bool:
        """완료 조건 체크"""
        return not state.pending_questions and state.asked_count >= self.max_questions
