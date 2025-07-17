# fastapi_project/streamlit_ui/streamlit_resume_agent_test.py
import streamlit as st
import sys
import os
import asyncio

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.resume_agent import build_resume_agent
from app.schemas import (
    ResumeAgentState,
    BaseInputsModel,
)  # InputsModel → BaseInputsModel
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="LangGraph 이력서 Agent", layout="wide")
st.title("🧠 LangGraph 기반 이력서 생성 테스트")


def get_or_create_state() -> ResumeAgentState:
    """세션 상태를 가져오거나 생성합니다."""
    if "state" not in st.session_state:
        # BaseInputsModel 사용 (기존 InputsModel 대신)
        inputs = BaseInputsModel(
            email="test@example.com",
            preferred_job="백엔드 개발자",
            certification_count=2,
            project_count=3,
            major_type="MAJOR",  # "MAJOR" 또는 "NON_MAJOR"
            company_name="AI Tech",
            position="백엔드 엔지니어",
            work_period=18,
            additional_experiences="Docker, Kubernetes 경험 있음",
        )

        st.session_state.state = ResumeAgentState(
            memberId=3,  # 필수 필드 추가
            inputs=inputs,  # BaseInputsModel 인스턴스 전달
            user_inputs={},
            pending_questions=[],
            answers=[],
            resume="",
            docx_path="",
            info_ready=False,
            asked_count=0,
            step="questioning",  # "init" → "questioning"으로 변경
        )

    return st.session_state.state


# 상태 가져오기
state = get_or_create_state()
agent = build_resume_agent()


async def run_agent_async(agent, state):
    """비동기로 에이전트 실행"""
    async for event in agent.astream(state):
        for node_name, node_state in event.items():
            yield node_name, node_state


# 현재 상태 표시
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("질문 횟수", f"{state.asked_count}/{state.max_questions}")
with col2:
    st.metric("현재 단계", state.step)
with col3:
    st.metric("완료 여부", "✅" if state.info_ready else "❌")

# 1️⃣ 에이전트 실행
if st.button("🚀 에이전트 실행하기", type="primary"):
    with st.spinner("에이전트 실행 중..."):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process():
                results = []
                async for node_name, node_state in run_agent_async(agent, state):
                    results.append((node_name, node_state))

                return results

            results = loop.run_until_complete(process())

            for node_name, node_state in results:
                st.write(f"{node_name} 노드 실행 완료")
                state = node_state

            st.session_state.state = state
            st.success("✅ LangGraph 에이전트 실행 완료!")
            st.rerun()

        except Exception as e:
            st.error(f"에러 발생: {str(e)}")
            st.exception(e)

# 2️⃣ 생성된 질문 처리
if state.pending_questions and not state.info_ready:
    st.subheader("❓ AI가 생성한 질문")
    current_question = state.get_next_question()  # 새로운 메서드 사용

    if current_question:
        # 질문 표시
        st.info(f"**질문 {state.asked_count + 1}:** {current_question}")

        # 답변 입력
        with st.form(f"answer_form_{state.asked_count}"):
            answer = st.text_area(
                "답변을 입력하세요:",
                height=150,
                placeholder="상세하게 답변해주시면 더 좋은 이력서를 만들 수 있습니다.",
            )

            col1, col2 = st.columns([1, 4])
            with col1:
                submitted = st.form_submit_button("📩 답변 제출", type="primary")

            if submitted and answer:
                # 새로운 방식으로 답변 추가
                state.add_answer(current_question, answer)
                state.pending_questions.pop(0)  # 처리된 질문 제거

                # 다시 에이전트 실행 (receive_answer 노드부터)
                with st.spinner("답변 처리 중..."):
                    try:
                        for event in agent.stream(state):
                            for node_name, node_state in event.items():
                                state = node_state
                    except Exception as e:
                        st.error(f"답변 처리 중 오류: {str(e)}")
                        state.mark_error(f"답변 처리 중 오류: {str(e)}")

                st.session_state.state = state
                st.success("✅ 답변 저장 및 처리 완료")
                st.rerun()

# 3️⃣ 이전 답변 표시
if state.answers:
    with st.expander("📝 이전 답변 보기"):
        for i, qa in enumerate(state.answers, 1):
            # 새로운 답변 구조에 맞게 수정
            if isinstance(qa, dict):
                question = qa.get("question", "")
                answer = qa.get("answer", "")
            else:
                question = getattr(qa, "question", "")
                answer = getattr(qa, "answer", "")

            st.write(f"**Q{i}:** {question}")
            st.write(f"**A{i}:** {answer}")
            st.divider()

# 4️⃣ 이력서 생성 완료
if state.info_ready and state.resume:
    st.subheader("📄 생성된 이력서")

    # 이력서 내용 표시
    with st.container():
        st.markdown(state.resume)

    # 파일 다운로드 처리
    if state.docx_path:
        st.success(f"✅ 이력서 파일 생성 완료: {state.docx_path}")

        # 로컬 파일인 경우
        if os.path.exists(state.docx_path):
            with open(state.docx_path, "rb") as file:
                st.download_button(
                    label="📥 이력서 다운로드 (DOCX)",
                    data=file.read(),
                    file_name=f"resume_{state.inputs.email.split('@')[0]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

# 5️⃣ 에러 상태 처리
if state.step == "error":
    st.error("❌ 에러가 발생했습니다!")
    if state.error_message:
        st.error(f"에러 메시지: {state.error_message}")
    if state.error_details:
        with st.expander("🔍 에러 상세 정보"):
            st.json(state.error_details)

# 6️⃣ 상태 초기화
if st.button("🔄 처음부터 다시 시작"):
    if "state" in st.session_state:
        del st.session_state.state
    st.rerun()

# 7️⃣ 수동 완료 처리 (테스트용)
if st.button("🏁 강제 완료 (테스트용)"):
    test_resume = """
# 이력서
    
## 기본 정보
- 이메일: test@example.com
- 희망 직무: 백엔드 개발자
    
## 경력
- AI Tech - 백엔드 엔지니어 (18개월)
    
## 기술 스택
- Docker, Kubernetes 경험
"""
    state.mark_completed(test_resume, "test_resume.docx")
    st.session_state.state = state
    st.success("✅ 강제 완료 처리됨")
    st.rerun()

# 8️⃣ 디버그 정보
with st.expander("🔧 디버그 정보"):
    debug_info = {
        "memberId": state.memberId,
        "step": state.step,
        "asked_count": state.asked_count,
        "max_questions": state.max_questions,
        "info_ready": state.info_ready,
        "pending_questions": len(state.pending_questions),
        "pending_questions_list": state.pending_questions,
        "answers_count": len(state.answers),
        "docx_path": state.docx_path,
        "resume_length": len(state.resume) if state.resume else 0,
        "error_message": state.error_message,
        "created_at": (
            state.created_at.isoformat() if hasattr(state, "created_at") else None
        ),
        "updated_at": (
            state.updated_at.isoformat() if hasattr(state, "updated_at") else None
        ),
    }
    st.json(debug_info)
