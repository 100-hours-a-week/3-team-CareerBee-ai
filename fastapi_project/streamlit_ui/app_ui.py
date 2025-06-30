# # app_ui.py
# import streamlit as st
# import httpx
# import asyncio
# import requests
# from copy import deepcopy
# from app.schemas.resume_agent import InputsModel
# import os

# BASE_URL = "http://localhost:8000"  # FastAPI 서버 주소


# def ensure_inputs_dict(inputs):
#     if not isinstance(inputs, dict):
#         return InputsModel(**inputs).model_dump()
#     return inputs


# # 상태 저장 초기화 (state dict 관리 → 안정화)
# if "state" not in st.session_state:
#     st.session_state["state"] = {
#         "inputs": {},
#         "user_inputs": {},
#         "answers": [],
#         "pending_questions": [],
#         "resume": "",
#         "docx_path": "",
#         "info_ready": False,
#         "asked_count": 0,
#         "step": "init",
#     }
# state = st.session_state["state"]
# step = state.get("step", "init")  # 방어적 접근

# st.title("LangGraph 이력서 생성 테스트")


# # 1️⃣ 초기 사용자 정보 입력 단계
# if step == "init":
#     with st.form("init_form"):
#         email = st.text_input("이메일")
#         preferred_job = st.text_input("선호 직무")
#         certification_count = st.number_input("자격증 개수", min_value=0, step=1)
#         project_count = st.number_input("프로젝트 개수", min_value=0, step=1)
#         major_type = st.selectbox("전공 여부", ["MAJOR", "NON_MAJOR"])
#         company_name = st.text_input("재직 회사")
#         position = st.text_input("직무")
#         work_period = st.number_input("재직 기간", min_value=0)
#         additional_experience = st.text_input("추가 경험이 있다면 알려주세요.")

#         if st.form_submit_button("이력서 생성"):
#             inputs = {
#                 "email": email,
#                 "preferred_job": preferred_job,
#                 "certification_count": int(certification_count),
#                 "project_count": int(project_count),
#                 "major_type": major_type,
#                 "company_name": company_name,
#                 "position": position,
#                 "work_period": int(work_period),
#                 "additional_experiences": additional_experience,
#             }

#             try:
#                 response = requests.post(
#                     f"{BASE_URL}/resume/agent/init", json={"inputs": inputs}
#                 )
#                 response.raise_for_status()
#                 result = response.json()
#                 result["inputs"] = ensure_inputs_dict(result["inputs"])
#                 result["step"] = "questioning"
#                 st.session_state["state"] = result
#                 st.rerun()
#             except Exception as e:
#                 st.error(f"초기 요청 실패: {e}")

# # 2️⃣ 질문-답변 반복 단계
# elif step == "questioning":
#     pending = state.get("pending_questions", [])
#     if not pending:
#         payload = deepcopy(state)
#         payload["inputs"] = ensure_inputs_dict(payload["inputs"])

#         try:
#             response = requests.post(f"{BASE_URL}/resume/agent/update", json=payload)
#             response.raise_for_status()
#             result = response.json()
#             result["inputs"] = ensure_inputs_dict(result["inputs"])
#             result["step"] = "questioning"
#             st.session_state["state"] = result
#             st.rerun()
#         except Exception as e:
#             st.error(f"질문 생성 중 오류 발생: {e}")

#     else:
#         current_question = pending[0]
#         st.write(f"🤖 질문: {current_question}")

#         user_answer = st.text_input(
#             "답변을 입력하세요:", key=f"user_answer_{state['asked_count']}"
#         )

#         if st.button("답변 전송"):
#             state["user_inputs"][current_question] = user_answer
#             state["answers"].append(
#                 {"question": current_question, "answer": user_answer}
#             )
#             state["pending_questions"] = pending[1:]
#             state["asked_count"] += 1

#             payload = deepcopy(state)
#             payload["inputs"] = ensure_inputs_dict(payload["inputs"])

#             try:
#                 response = requests.post(
#                     f"{BASE_URL}/resume/agent/update", json=payload
#                 )
#                 response.raise_for_status()
#                 result = response.json()
#                 result["inputs"] = ensure_inputs_dict(result["inputs"])
#                 result["step"] = (
#                     "completed" if result.get("info_ready") else "questioning"
#                 )
#                 st.session_state["state"] = result
#                 st.rerun()
#             except Exception as e:
#                 st.error(f"답변 처리 실패: {e}")

# # 3️⃣ 이력서 생성 완료 단계
# elif step == "completed":
#     docx_path = state.get("docx_path")
#     st.write("📁 DEBUG - docx_path:", docx_path)

#     if not docx_path:
#         st.warning("docx_path가 비어 있습니다.")
#     elif not os.path.exists(docx_path):
#         st.error(f"❌ 파일이 존재하지 않습니다: {docx_path}")
#     else:
#         st.success("이력서 생성이 완료되었습니다!")
#         st.code(state.get("resume", ""))
#         with open(docx_path, "rb") as file:
#             st.download_button(
#                 label="📥 이력서 다운로드",
#                 data=file,
#                 file_name=os.path.basename(docx_path),
#                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#             )

"""
Streamlit UI for LangGraph Resume Generator
FastAPI와 연결된 이력서 생성 인터페이스
"""

import streamlit as st
import requests
import logging
import os
from copy import deepcopy
from typing import Dict, Any, Optional
from app.schemas.resume_agent import InputsModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 설정
FASTAPI_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30  # 30초 타임아웃


class ResumeAppUI:
    """이력서 생성 Streamlit 앱 클래스"""

    def __init__(self):
        self.init_session_state()

    def init_session_state(self):
        """세션 상태 초기화"""
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

    @staticmethod
    def ensure_inputs_dict(inputs: Any) -> Dict[str, Any]:
        """inputs를 딕셔너리 형태로 변환"""
        try:
            if not isinstance(inputs, dict):
                if hasattr(inputs, "model_dump"):
                    return inputs.model_dump()
                elif hasattr(inputs, "__dict__"):
                    return inputs.__dict__
                else:
                    return InputsModel(**inputs).model_dump()
            return inputs
        except Exception as e:
            logger.error(f"inputs 변환 실패: {e}")
            st.error(f"데이터 변환 중 오류가 발생했습니다: {str(e)}")
            return {}

    def make_api_request(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """API 요청을 보내고 결과를 반환"""
        url = f"{FASTAPI_BASE_URL}{endpoint}"

        try:
            logger.info(f"API 요청: {endpoint}")
            logger.debug(f"페이로드: {payload}")

            with st.spinner(f"처리 중..."):
                response = requests.post(
                    url,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                    headers={"Content-Type": "application/json"},
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"API 응답 성공: {endpoint}")
                return result

        except requests.exceptions.Timeout:
            error_msg = "요청 시간이 초과되었습니다. 다시 시도해주세요."
            logger.error(f"타임아웃 오류: {endpoint}")
            st.error(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = "서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
            logger.error(f"연결 오류: {endpoint}")
            st.error(error_msg)

        except requests.exceptions.HTTPError as e:
            error_msg = f"서버 오류가 발생했습니다: {e.response.status_code}"
            if e.response.status_code == 400:
                try:
                    error_detail = e.response.json().get("detail", "잘못된 요청입니다.")
                    error_msg = f"요청 오류: {error_detail}"
                except:
                    pass
            logger.error(f"HTTP 오류: {endpoint} - {e}")
            st.error(error_msg)

        except Exception as e:
            error_msg = f"예상치 못한 오류가 발생했습니다: {str(e)}"
            logger.error(f"예상치 못한 오류: {endpoint} - {e}")
            st.error(error_msg)

        return None

    def validate_initial_inputs(self, inputs: Dict[str, Any]) -> bool:
        """초기 입력 데이터 검증"""
        required_fields = ["email", "preferred_job"]

        for field in required_fields:
            if not inputs.get(field, "").strip():
                st.error(f"{field}는 필수 입력 항목입니다.")
                return False

        # 이메일 간단 검증
        email = inputs.get("email", "")
        if "@" not in email or "." not in email:
            st.error("올바른 이메일 형식을 입력해주세요.")
            return False

        return True

    def render_init_form(self):
        """초기 사용자 정보 입력 폼"""
        st.header("🚀 이력서 생성을 시작합니다")
        st.write("아래 정보를 입력하여 맞춤형 이력서를 생성해보세요.")

        with st.form("init_form"):
            col1, col2 = st.columns(2)

            with col1:
                email = st.text_input("이메일 *", placeholder="example@email.com")
                preferred_job = st.text_input(
                    "선호 직무 *", placeholder="백엔드 개발자"
                )
                certification_count = st.number_input(
                    "자격증 개수", min_value=0, step=1, value=0
                )
                project_count = st.number_input(
                    "프로젝트 개수", min_value=0, step=1, value=0
                )
                major_type = st.selectbox("전공 여부", ["MAJOR", "NON_MAJOR"])

            with col2:
                company_name = st.text_input(
                    "재직 회사", placeholder="현재 재직중인 회사명"
                )
                position = st.text_input("직무", placeholder="현재 담당하고 있는 직무")
                work_period = st.number_input("재직 기간 (개월)", min_value=0, value=0)
                additional_experience = st.text_area(
                    "추가 경험",
                    placeholder="기타 경험이나 특이사항을 입력해주세요.",
                    height=100,
                )

            submitted = st.form_submit_button(
                "✨ 이력서 생성 시작", use_container_width=True
            )

            if submitted:
                inputs = {
                    "email": email.strip(),
                    "preferred_job": preferred_job.strip(),
                    "certification_count": int(certification_count),
                    "project_count": int(project_count),
                    "major_type": major_type,
                    "company_name": company_name.strip(),
                    "position": position.strip(),
                    "work_period": int(work_period),
                    "additional_experiences": additional_experience.strip(),
                }

                if self.validate_initial_inputs(inputs):
                    result = self.make_api_request(
                        "/resume/agent/init", {"inputs": inputs}
                    )
                    if result:
                        result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                        result["step"] = "questioning"
                        st.session_state["state"] = result
                        st.rerun()

    def render_questioning_phase(self, state: Dict[str, Any]):
        """질문-답변 단계"""
        pending = state.get("pending_questions", [])

        if not pending:
            # 새로운 질문 생성 요청
            st.info("새로운 질문을 생성하고 있습니다...")
            payload = deepcopy(state)
            payload["inputs"] = self.ensure_inputs_dict(payload["inputs"])

            result = self.make_api_request("/resume/agent/update", payload)
            if result:
                result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                result["step"] = "questioning"
                st.session_state["state"] = result
                st.rerun()
        else:
            current_question = pending[0]

            # 진행 상황 표시
            st.progress(
                (state["asked_count"]) / 3, text=f"질문 {state['asked_count'] + 1}/3"
            )

            # 이전 답변들 표시
            if state.get("answers"):
                with st.expander("이전 답변 보기", expanded=False):
                    for i, qa in enumerate(state["answers"], 1):
                        st.write(f"**Q{i}:** {qa['question']}")
                        st.write(f"**A{i}:** {qa['answer']}")
                        st.divider()

            # 현재 질문
            st.header("🤖 질문")
            st.write(current_question)

            # 답변 입력
            with st.form(f"answer_form_{state['asked_count']}"):
                user_answer = st.text_area(
                    "답변을 입력하세요:",
                    height=100,
                    placeholder="상세하게 답변해주시면 더 좋은 이력서를 만들 수 있습니다.",
                )

                col1, col2 = st.columns([1, 4])
                with col1:
                    submitted = st.form_submit_button(
                        "📝 답변 전송", use_container_width=True
                    )

                if submitted:
                    if not user_answer.strip():
                        st.error("답변을 입력해주세요.")
                    else:
                        # 상태 업데이트
                        state["user_inputs"][current_question] = user_answer.strip()
                        state["answers"].append(
                            {
                                "question": current_question,
                                "answer": user_answer.strip(),
                            }
                        )
                        state["pending_questions"] = pending[1:]
                        state["asked_count"] += 1

                        payload = deepcopy(state)
                        payload["inputs"] = self.ensure_inputs_dict(payload["inputs"])

                        result = self.make_api_request("/resume/agent/update", payload)
                        if result:
                            result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                            result["step"] = (
                                "completed"
                                if result.get("info_ready")
                                else "questioning"
                            )
                            st.session_state["state"] = result
                            st.rerun()

    def render_completed_phase(self, state: Dict[str, Any]):
        """이력서 생성 완료 단계"""
        st.header("🎉 이력서 생성 완료!")

        # 답변 요약 표시
        if state.get("answers"):
            with st.expander("입력한 정보 요약", expanded=True):
                st.write("**기본 정보:**")
                inputs = state.get("inputs", {})
                st.write(f"- 이메일: {inputs.get('email', 'N/A')}")
                st.write(f"- 선호 직무: {inputs.get('preferred_job', 'N/A')}")
                st.write(f"- 자격증: {inputs.get('certification_count', 0)}개")
                st.write(f"- 프로젝트: {inputs.get('project_count', 0)}개")

                st.write("\n**추가 답변:**")
                for i, qa in enumerate(state["answers"], 1):
                    st.write(f"**Q{i}:** {qa['question']}")
                    st.write(f"**A{i}:** {qa['answer']}")
                    st.write("")

        # 생성된 이력서 내용 표시
        resume_content = state.get("resume", "")
        if resume_content:
            st.subheader("📄 생성된 이력서 내용")
            st.text_area("", value=resume_content, height=300, disabled=True)

        # 파일 다운로드
        docx_path = state.get("docx_path", "")
        if docx_path and os.path.exists(docx_path):
            try:
                with open(docx_path, "rb") as file:
                    st.download_button(
                        label="📥 이력서 다운로드 (DOCX)",
                        data=file,
                        file_name=f"resume_{state.get('inputs', {}).get('email', 'user')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
            except Exception as e:
                logger.error(f"파일 다운로드 오류: {e}")
                st.error("파일 다운로드 중 오류가 발생했습니다.")
        else:
            st.warning("다운로드할 파일이 준비되지 않았습니다.")

        # 다시 시작 버튼
        if st.button("🔄 새 이력서 만들기", use_container_width=True):
            # 세션 상태 초기화
            for key in list(st.session_state.keys()):
                if key.startswith("user_answer_"):
                    del st.session_state[key]

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
            st.rerun()

    def run(self):
        """메인 앱 실행"""
        st.set_page_config(
            page_title="LangGraph 이력서 생성기", page_icon="📄", layout="wide"
        )

        st.title("📄 LangGraph 이력서 생성기")
        st.markdown("---")

        # 현재 상태 가져오기
        state = st.session_state.get("state", {})
        step = state.get("step", "init")

        # 디버그 정보 (개발 모드에서만)
        if os.getenv("DEBUG", "false").lower() == "true":
            with st.sidebar:
                st.subheader("🔧 디버그 정보")
                st.json({"step": step, "asked_count": state.get("asked_count", 0)})

        # 단계별 렌더링
        try:
            if step == "init":
                self.render_init_form()
            elif step == "questioning":
                self.render_questioning_phase(state)
            elif step == "completed":
                self.render_completed_phase(state)
            else:
                st.error(f"알 수 없는 단계: {step}")
                if st.button("초기화"):
                    self.init_session_state()
                    st.rerun()

        except Exception as e:
            logger.error(f"렌더링 오류: {e}")
            st.error("페이지 렌더링 중 오류가 발생했습니다.")
            if st.button("다시 시도"):
                st.rerun()


# 앱 실행
if __name__ == "__main__":
    app = ResumeAppUI()
    app.run()
