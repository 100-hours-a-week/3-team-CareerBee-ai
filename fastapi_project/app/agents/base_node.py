from abc import ABC, abstractmethod
from app.agents.schema.resume_create_agent import ResumeAgentState


class BaseNode(ABC):
    """모든 노드의 기본 인터페이스"""

    @abstractmethod
    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        """노드 실행 메서드"""
        pass
