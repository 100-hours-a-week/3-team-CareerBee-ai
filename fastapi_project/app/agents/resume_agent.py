# resume_agent = build_resume_agent()

from langgraph.graph import StateGraph, END
from app.utils.llm_client import create_llm_client

# from langgraph.tracers.langchain import LangChainTracer
from app.agents.nodes.generate_question import GenerateQuestionNode
from app.agents.nodes.check_completion import CheckCompletionNode
from app.agents.nodes.create_resume import CreateResumeNode
from app.agents.nodes.receive_answer import ReceiveAnswerNode
from app.agents.schema.resume_create_agent import ResumeAgentState
from dotenv import load_dotenv

load_dotenv()

# 트레이서 인스턴스 생성
# tracer = LangChainTracer()


# DAG 노드 정의 및 연결
def build_resume_agent():
    # 통합 LLM 클라이언트 생성 (환경 변수에 따라 자동으로 OpenAI 또는 VLLM 선택)
    llm_client = create_llm_client(temperature=0.3)

    builder = StateGraph(ResumeAgentState)  # name="resume-agent", tracer=tracer

    # LLM이 필요한 노드들에는 llm_client 전달, 필요 없는 노드들은 기본값 사용
    builder.add_node("generate_question", GenerateQuestionNode(llm_client))
    builder.add_node("receive_answer", ReceiveAnswerNode())
    builder.add_node("check_completion", CheckCompletionNode())
    builder.add_node("create_resume", CreateResumeNode(llm_client))

    # ✅ 진입점: 사용자 응답 수신 이후 실행됨
    builder.set_entry_point("receive_answer")

    # ✅ receive_answer → check_completion
    builder.add_edge("receive_answer", "check_completion")

    # ✅ check_completion에서 분기
    builder.add_conditional_edges(
        "check_completion",
        lambda state: state.info_ready,
        {
            True: "create_resume",  # 조건 충족 → 이력서 생성
            False: "generate_question",  # 질문 다시 생성
        },
    )

    # ✅ 질문 생성 이후 다시 사용자 입력 대기하므로 종료
    builder.add_edge("generate_question", END)

    # ✅ 이력서 생성도 마지막 노드
    builder.add_edge("create_resume", END)
    return builder.compile()


resume_agent = build_resume_agent()
