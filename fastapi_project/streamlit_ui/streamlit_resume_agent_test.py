# streamlit_resume_agent_test.py
import streamlit as st
from app.agents.graph.resume_agent import build_resume_agent
from app.agents.schema.resume_create_agent import ResumeAgentState

st.set_page_config(page_title="LangGraph 이력서 Agent", layout="wide")
st.title("🧠 LangGraph 기반 이력서 생성 테스트")

from dotenv import load_dotenv

load_dotenv()

# 세션 상태 초기화
if "state" not in st.session_state:
    st.session_state.state = ResumeAgentState(
        inputs={
            "email": "test@example.com",
            "preferred_job": "백엔드 개발자",
            "certification_count": 2,
            "project_count": 3,
            "major_type": "전공자",
            "company_name": "AI Tech",
            "work_period": 18,
            "position": "백엔드",
            "additional_experiences": "Docker, Kubernetes 경험 있음",
        },
        user_inputs={},
        pending_questions=[],
        answers=[],
        resume="",
        info_ready=False,
        chat_history=[],
        asked_count=0,
    )

state = st.session_state.state
agent = build_resume_agent()

# 1️⃣ 에이전트 실행
if st.button("🚀 에이전트 실행하기 (질문 생성 포함)"):
    stream = agent.stream(state)
    for step in stream:
        state = step
    st.success("✅ LangGraph 에이전트 실행 완료!")

# 2️⃣ 생성된 질문 보기
if state.pending_questions:
    st.subheader("❓ LLM이 생성한 질문")
    current_question = state.pending_questions[0]
    st.markdown(f"**➡️ {current_question}**")

    # 3️⃣ 사용자 답변 입력 받기
    answer = st.text_input("✏️ 답변을 입력하세요", key="answer_input")
    if st.button("📩 답변 제출"):
        state.user_inputs[current_question] = answer
        state.pending_questions.pop(0)
        state.answers.append({"question": current_question, "answer": answer})
        state.asked_count += 1
        st.success("✅ 답변 저장 완료")

# 4️⃣ 이력서 생성 여부
if state.resume:
    st.subheader("📄 생성된 이력서 초안")
    st.text(state.resume)

# 5️⃣ 상태 확인용 디버그 출력
with st.expander("🧪 디버그용 상태 보기"):
    st.json(
        {
            "user_inputs": state.user_inputs,
            "answers": state.answers,
            "pending_questions": state.pending_questions,
            "resume": state.resume,
            "info_ready": state.info_ready,
        }
    )
