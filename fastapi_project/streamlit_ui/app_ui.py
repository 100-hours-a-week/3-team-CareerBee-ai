# app_ui.py
import streamlit as st
import requests
from copy import deepcopy
from app.schemas.resume_agent import InputsModel

BASE_URL = "http://localhost:8000"  # FastAPI 서버 주소

st.title("LangGraph 이력서 생성 테스트")

# 상태 저장 초기화 (state dict 관리 → 안정화)
if "state" not in st.session_state:
    """
    streamlit 세션이 새로 시작될 때마다 state 초기값을 세팅
    이게 없다면 사용자가 처음 들어올 때 st.session_state.state가 존재하지 않아서 KeyError 발생
    초기화 안 해주면 상태관리가 불안정해짐
    """
    st.session_state.state = {
        "inputs": {},
        "user_inputs": {},
        "answers": [],
        "pending_questions": [],
        "resume": "",
        "docx_path": "",
        "info_ready": False,
        "asked_count": 0,
    }

# ✅ 초기 사용자 정보 입력 단계
if not st.session_state.state["inputs"]:
    with st.form("init_form"):
        email = st.text_input("이메일", key="email_input")
        preferred_job = st.text_input("선호 직무", key="preferred_job_input")
        certification_count = st.number_input(
            "자격증 개수", min_value=0, step=1, key="cert_count_input"
        )
        project_count = st.number_input(
            "프로젝트 개수", min_value=0, step=1, key="proj_count_input"
        )
        major_type = st.selectbox(
            "전공 여부", ["MAJOR", "NON_MAJOR"], key="major_type_input"
        )
        company_name = st.text_input("재직 회사", key="company_name_input")
        position = st.text_input("직무", key="position_input")
        work_period = st.number_input("재직 기간", min_value=0, key="work_period_input")
        additional_experience = st.text_input(
            "추가 경험이 있다면 알려주세요.", key="add_exp_input"
        )
        submitted = st.form_submit_button("이력서 생성")

        if submitted:
            # 입력값 수집
            st.session_state.state["inputs"] = {
                "email": email,
                "preferred_job": preferred_job,
                "certification_count": int(certification_count),
                "project_count": int(project_count),
                "major_type": major_type,
                "company_name": company_name,
                "position": position,
                "work_period": int(work_period),
                "additional_experiences": additional_experience,
            }
            # 서버 호출
            response = requests.post(
                f"{BASE_URL}/resume/agent/init",
                json={"inputs": st.session_state.state["inputs"]},
            )
            result = response.json()
            st.session_state.state.update(result)

# ✅ LangGraph 질문-답변 반복 단계
if st.session_state.state["inputs"] and not st.session_state.state["resume"]:

    pending = st.session_state.state.get("pending_questions", [])

    if pending:
        current_question = pending[0]
        st.write(f"🤖 질문: {current_question}")

        # 핵심 안정화: 위젯 key 부여
        user_answer = st.text_input(
            "답변을 입력하세요:",
            key=f"user_answer_{st.session_state.state['asked_count']}",
        )

        if st.button("답변 전송"):
            # 답변 누적
            st.session_state.state["user_inputs"][current_question] = user_answer
            st.session_state.state["answers"].append(
                {"question": current_question, "answer": user_answer}
            )
            st.session_state.state["pending_questions"] = pending[1:]  # pop

            # dict로 확실히 직렬화
            payload = deepcopy(st.session_state.state)

            if isinstance(payload["inputs"], InputsModel):
                payload["inputs"] = payload["inputs"].dict()

            response = requests.post(
                "/resume/agent/update",
                json=payload,  # FastAPI가 JSON → dict로 자동 역직렬화
            )

            st.session_state.state.update(response.json())


# ✅ 이력서 생성 완료 시
if st.session_state.state.get("resume"):
    st.success("이력서 생성이 완료되었습니다!")
    st.code(st.session_state.state["resume"])

    if st.session_state.state.get("docx_path"):
        with open(st.session_state.state["docx_path"], "rb") as file:
            st.download_button(
                label="📥 이력서 다운로드",
                data=file,
                file_name=st.session_state.state["docx_path"].split("/")[-1],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
