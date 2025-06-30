from typing import Dict, Type
from langchain_openai import ChatOpenAI
from .base_node import BaseNode
from app.agents.nodes.generate_question import GenerateQuestionNode
from app.agents.nodes.receive_answer import ReceiveAnswerNode
from app.agents.nodes.check_completion import CheckCompletionNode
from app.agents.nodes.create_resume import CreateResumeNode


class NodeFactory:
    """노드 생성을 위한 팩토리 클래스"""

    _node_registry: Dict[str, Type[BaseNode]] = {
        "generate_question": GenerateQuestionNode,
        "receive_answer": ReceiveAnswerNode,
        "check_completion": CheckCompletionNode,
        "create_resume": CreateResumeNode,
    }

    @classmethod
    def create_node(cls, node_type: str, **kwargs) -> BaseNode:
        """노드 타입에 따른 노드 인스턴스 생성"""
        if node_type not in cls._node_registry:
            raise ValueError(f"Unknown node type: {node_type}")

        node_class = cls._node_registry[node_type]
        return node_class(**kwargs)

    @classmethod
    def create_all_nodes(cls, llm: ChatOpenAI) -> Dict[str, BaseNode]:
        """모든 노드 인스턴스를 한번에 생성"""
        return {
            "generate_question": cls.create_node("generate_question", llm=llm),
            "receive_answer": cls.create_node("receive_answer"),
            "check_completion": cls.create_node("check_completion"),
            "create_resume": cls.create_node(
                "create_resume", llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)
            ),
        }
