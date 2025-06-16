# app/agents/resume_agent.py
from langgraph.graph import StateGraph, END
from app.agents.nodes.generate_question import generate_question_node
from app.agents.nodes.check_completion import check_completion_node
from app.agents.nodes.create_resume import create_resume_node
from app.agents.nodes.receive_answer import receive_answer_node
from app.agents.schema.resume_create_agent import ResumeAgentState


# DAG 노드 정의 및 연결


def build_resume_agent():
    builder = StateGraph(ResumeAgentState)

    builder.add_node("generate_question", generate_question_node)
    builder.add_node("receive_answer", receive_answer_node)
    builder.add_node("check_completion", check_completion_node)
    builder.add_node("create_resume", create_resume_node)

    builder.set_entry_point("receive_answer")

    builder.add_edge("receive_answer", "check_completion")

    builder.add_conditional_edges(
        "check_completion",
        lambda state: state.info_ready,
        {True: "create_resume", False: "generate_question"},
    )
    builder.add_edge("generate_question", "receive_answer")

    builder.add_edge("create_resume", END)
    return builder.compile()


resume_agent = build_resume_agent()
