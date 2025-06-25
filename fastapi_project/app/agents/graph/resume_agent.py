# app/agents/resume_agent.py
from langgraph.graph import StateGraph, END

# from langgraph.tracers.langchain import LangChainTracer
from app.agents.nodes.generate_question import generate_question_node
from app.agents.nodes.check_completion import check_completion_node
from app.agents.nodes.create_resume import create_resume_node
from app.agents.nodes.receive_answer import receive_answer_node
from app.agents.schema.resume_create_agent import ResumeAgentState
from dotenv import load_dotenv

load_dotenv()

# 트레이서 인스턴스 생성
# tracer = LangChainTracer()


# DAG 노드 정의 및 연결
def build_resume_agent():
    builder = StateGraph(ResumeAgentState)  # name="resume-agent", tracer=tracer

    builder.add_node("generate_question", generate_question_node)
    builder.add_node("receive_answer", receive_answer_node)
    builder.add_node("check_completion", check_completion_node)
    builder.add_node("create_resume", create_resume_node)

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
