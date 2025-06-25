# app_ui.py
import streamlit as st
import requests
from copy import deepcopy
from app.schemas.resume_agent import InputsModel
import os

BASE_URL = "http://localhost:8000"  # FastAPI 서버 주소


def ensure_inputs_dict(inputs):
    if not isinstance(inputs, dict):
        return InputsModel(**inputs).model_dump()
    return inputs


# 상태 저장 초기화 (state dict 관리 → 안정화)
if "state" not in st.session_state:
    st.session_state["state"] = {
        "inputs": {},
        "user_inputs": {},
        "answers": [],
        "pending_questions": [],
        "resume": "",
        "docx_path": "",
        "info_ready": False,
        "asked_count": 0,
        "step": "init",
    }
state = st.session_state["state"]
step = state.get("step", "init")  # 방어적 접근

st.title("LangGraph 이력서 생성 테스트")


# 1️⃣ 초기 사용자 정보 입력 단계
if step == "init":
    with st.form("init_form"):
        email = st.text_input("이메일")
        preferred_job = st.text_input("선호 직무")
        certification_count = st.number_input("자격증 개수", min_value=0, step=1)
        project_count = st.number_input("프로젝트 개수", min_value=0, step=1)
        major_type = st.selectbox("전공 여부", ["MAJOR", "NON_MAJOR"])
        company_name = st.text_input("재직 회사")
        position = st.text_input("직무")
        work_period = st.number_input("재직 기간", min_value=0)
        additional_experience = st.text_input("추가 경험이 있다면 알려주세요.")

        if st.form_submit_button("이력서 생성"):
            inputs = {
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

            try:
                response = requests.post(
                    f"{BASE_URL}/resume/agent/init", json={"inputs": inputs}
                )
                response.raise_for_status()
                result = response.json()
                result["inputs"] = ensure_inputs_dict(result["inputs"])
                result["step"] = "questioning"
                st.session_state["state"] = result
                st.rerun()
            except Exception as e:
                st.error(f"초기 요청 실패: {e}")

# 2️⃣ 질문-답변 반복 단계
elif step == "questioning":
    pending = state.get("pending_questions", [])
    if not pending:
        payload = deepcopy(state)
        payload["inputs"] = ensure_inputs_dict(payload["inputs"])

        try:
            response = requests.post(f"{BASE_URL}/resume/agent/update", json=payload)
            response.raise_for_status()
            result = response.json()
            result["inputs"] = ensure_inputs_dict(result["inputs"])
            result["step"] = "questioning"
            st.session_state["state"] = result
            st.rerun()
        except Exception as e:
            st.error(f"질문 생성 중 오류 발생: {e}")

    else:
        current_question = pending[0]
        st.write(f"🤖 질문: {current_question}")

        user_answer = st.text_input(
            "답변을 입력하세요:", key=f"user_answer_{state['asked_count']}"
        )

        if st.button("답변 전송"):
            state["user_inputs"][current_question] = user_answer
            state["answers"].append(
                {"question": current_question, "answer": user_answer}
            )
            state["pending_questions"] = pending[1:]
            state["asked_count"] += 1

            payload = deepcopy(state)
            payload["inputs"] = ensure_inputs_dict(payload["inputs"])

            try:
                response = requests.post(
                    f"{BASE_URL}/resume/agent/update", json=payload
                )
                response.raise_for_status()
                result = response.json()
                result["inputs"] = ensure_inputs_dict(result["inputs"])
                result["step"] = (
                    "completed" if result.get("info_ready") else "questioning"
                )
                st.session_state["state"] = result
                st.rerun()
            except Exception as e:
                st.error(f"답변 처리 실패: {e}")

# 3️⃣ 이력서 생성 완료 단계
elif step == "completed":
    docx_path = state.get("docx_path")
    st.write("📁 DEBUG - docx_path:", docx_path)

    if not docx_path:
        st.warning("docx_path가 비어 있습니다.")
    elif not os.path.exists(docx_path):
        st.error(f"❌ 파일이 존재하지 않습니다: {docx_path}")
    else:
        st.success("이력서 생성이 완료되었습니다!")
        st.code(state.get("resume", ""))
        with open(docx_path, "rb") as file:
            st.download_button(
                label="📥 이력서 다운로드",
                data=file,
                file_name=os.path.basename(docx_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
