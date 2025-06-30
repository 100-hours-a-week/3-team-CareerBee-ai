from app.agents.schema.resume_create_agent import ResumeAgentState
from app.agents.nodes.generate_question import GenerateQuestionNode
from app.agents.nodes.receive_answer import ReceiveAnswerNode
from app.agents.nodes.check_completion import CheckCompletionNode
from app.agents.nodes.create_resume import CreateResumeNode
from langchain_openai import ChatOpenAI


class ResumeAgent:
    def __init__(self, state: ResumeAgentState):
        self.state = state
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        self._setup_nodes()

    def _setup_nodes(self):
        """노드들 초기화"""
        self.generate_question_node = GenerateQuestionNode(self.llm)
        self.receive_answer_node = ReceiveAnswerNode()
        self.check_completion_node = CheckCompletionNode()
        self.create_resume_node = CreateResumeNode(
            ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        )

    async def generate_question(self):
        """질문 생성 단계"""
        self.state = await self.generate_question_node.execute(self.state)

    async def receive_answer(self):
        """답변 수신 단계"""
        self.state = await self.receive_answer_node.execute(self.state)

    async def check_completion(self):
        """완료 체크 단계"""
        self.state = await self.check_completion_node.execute(self.state)

    async def create_resume(self):
        """이력서 생성 단계"""
        self.state = await self.create_resume_node.execute(self.state)

    async def run(self):
        """전체 프로세스 실행"""
        while not self.state.info_ready:
            await self.generate_question()
            await self.receive_answer()
            await self.check_completion()

        await self.create_resume()
        return self.state
