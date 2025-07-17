# fastapi_project/streamlit_ui/app_ui.py
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
import logging
import requests

from copy import deepcopy
from typing import Dict, Any, Optional
from app.schemas import InputsModel, BaseInputsModel

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 설정
FASTAPI_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30  # 30초 타임아웃

# base_dir = Path(__file__).resolve().parent  # 현재 스크립트 위치
# resume_dir = base_dir / "resume"
# resume_dir.mkdir(exist_ok=True)


class ResumeAppUI:
    """이력서 생성 Streamlit 앱 클래스"""

    def __init__(self):
        self.init_session_state()

    def init_session_state(self):
        """세션 상태 초기화"""
        if "state" not in st.session_state:
            st.session_state["state"] = {
                "memberId": None,
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
                    timeout=300,
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

    def download_file_from_url(self, url: str, filename: str) -> Optional[bytes]:
        """URL에서 파일을 다운로드하여 bytes로 반환"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            with st.spinner("파일을 준비하고 있습니다..."):
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                logger.info(f"파일 다운로드 완료: {len(response.content)} bytes")
                return response.content

        except requests.exceptions.Timeout:
            st.error("파일 다운로드 시간이 초과되었습니다.")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"파일 다운로드 실패: {e}")
            st.error(f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 다운로드 오류: {e}")
            st.error("파일 다운로드 중 예상치 못한 오류가 발생했습니다.")
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
                        "/api/v1/resume/agent/init",
                        {"inputs": inputs, "memberId": 3},
                    )
                    if result:
                        # ✅ inputs는 응답에 없으므로 원래 값 사용
                        st.session_state["state"] = {
                            "memberId": result.get("memberId", 3),
                            "inputs": inputs,  # 원래 입력값 유지
                            "step": "questioning",
                            "pending_questions": [result.get("question", "")],
                            "answers": [],
                            "asked_count": 0,
                            "user_inputs": {},
                            "info_ready": False,
                            "resume": "",
                            "docx_path": "",
                        }
                        st.rerun()

    def render_questioning_phase(self, state: Dict[str, Any]):
        """질문-답변 단계"""
        pending = state.get("pending_questions", [])

        # ✅ asked_count가 3 이상이면 강제로 info_ready 설정
        if state.get("asked_count", 0) >= 3:
            st.info("💡 3개 이상의 질문에 답변했으므로 이력서를 생성합니다...")
            payload = deepcopy(state)
            payload["inputs"] = self.ensure_inputs_dict(payload["inputs"])
            payload["info_ready"] = True  # 강제로 완료 플래그 설정

            result = self.make_api_request("/api/v1/resume/agent/update", payload)
            if result:
                result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                result["step"] = "completed"
                st.session_state["state"] = result
                st.rerun()
            return  # 완료되었으니 이후 진행 생략

        if not pending:
            # 새로운 질문 생성 요청
            st.info("새로운 질문을 생성하고 있습니다...")
            payload = deepcopy(state)
            payload["inputs"] = self.ensure_inputs_dict(payload["inputs"])

            result = self.make_api_request("/api/v1/resume/agent/update", payload)
            if result:
                result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                result["memberId"] = state.get("memberId", 3)  # memberId 저장
                result["step"] = "questioning"
                result["pending_questions"] = [result.get("question", "")]
                result["answers"] = []
                result["asked_count"] = 0
                result["user_inputs"] = {}
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

                        # API 요청
                        request_data = {
                            "memberId": state.get("memberId", 3),
                            "inputs": {"answer": user_answer.strip()},
                        }
                        result = self.make_api_request(
                            "/api/v1/resume/agent/update", request_data
                        )

                        if result:
                            if result.get("isComplete"):
                                result["info_ready"] = True
                                result["step"] = "completed"

                                # ✅ resumeObjectKey → docx_path로 저장
                                result["docx_path"] = result.get("resumeObjectKey", "")

                                # ✅ resume 내용도 state에 저장
                                result["resume"] = result.get("resume", "")
                            else:
                                next_question = result.get("question")
                                if next_question:
                                    result["pending_questions"] = [next_question]
                                    result["step"] = "questioning"

                            # ✅ 이전 상태 병합
                            result["asked_count"] = state["asked_count"]
                            result["answers"] = state["answers"]
                            result["user_inputs"] = state["user_inputs"]

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
            # 마크다운으로 렌더링
            with st.container():
                st.markdown(resume_content)

            # 원본 마크다운도 확인할 수 있도록
            with st.expander("📝 마크다운 원본 보기"):
                st.text_area("", value=resume_content, height=300, disabled=True)
        # ✅ 간단한 로컬 파일 다운로드 처리
        docx_path = state.get("docx_path", "")
        if docx_path:
            # 파일 경로 정보 표시 (디버그용)
            with st.expander("파일 정보", expanded=False):
                st.text(f"원본 경로: {docx_path}")
                is_url = docx_path.startswith(("http://", "https://"))
                st.text(f"URL 형태: {is_url}")

                if not is_url:
                    st.text(f"파일 존재: {os.path.exists(docx_path)}")
                    if not os.path.isabs(docx_path):
                        abs_path = os.path.abspath(docx_path)
                        st.text(f"절대 경로: {abs_path}")
                        st.text(f"절대 경로 존재: {os.path.exists(abs_path)}")

            # URL인지 로컬 파일인지 판단
            if docx_path.startswith(("http://", "https://")):
                # S3 URL 처리 (프로덕션)
                try:
                    st.info("🌐 클라우드에서 파일을 준비하고 있습니다...")

                    # 파일명 생성
                    user_email = state.get("inputs", {}).get("email", "user")
                    safe_email = (
                        user_email.split("@")[0] if "@" in user_email else user_email
                    )
                    filename = f"resume_{safe_email}.docx"

                    # URL에서 파일 다운로드
                    file_data = self.download_file_from_url(docx_path, filename)

                    if file_data:
                        file_size = len(file_data)
                        st.success(f"✅ 파일 준비 완료! (크기: {file_size:,} bytes)")

                        # 다운로드 버튼
                        st.download_button(
                            label="📥 이력서 다운로드 (DOCX)",
                            data=file_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"download_s3_{state.get('asked_count', 0)}",
                        )

                        # 브라우저에서 직접 열기 옵션
                        st.markdown(
                            f"**또는** [🔗 브라우저에서 바로 다운로드]({docx_path})"
                        )
                        st.info(f"💡 다운로드 파일명: {filename}")
                    else:
                        st.error("파일 다운로드에 실패했습니다.")

                except Exception as e:
                    logger.error(f"S3 파일 처리 오류: {e}")
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")

            else:
                # 📁 로컬 파일 처리 (개발환경)
                from pathlib import Path

                # 기본 프로젝트 루트 경로 기준으로 상대경로를 절대경로로 변환
                project_root = (
                    Path(__file__).resolve().parents[2]
                )  # fastapi_project 루트
                actual_path = project_root / docx_path

                # 디버깅 정보 출력
                with st.expander("🔍 경로 디버깅", expanded=False):
                    st.text(f"문자열 경로: {docx_path}")
                    st.text(f"실제 절대경로: {actual_path}")
                    st.text(f"파일 존재 여부: {actual_path.exists()}")

                if actual_path.exists():
                    try:
                        # 안전한 파일명 생성
                        user_email = state.get("inputs", {}).get("email", "user")
                        safe_email = (
                            user_email.split("@")[0]
                            if "@" in user_email
                            else user_email
                        )
                        filename = f"resume_{safe_email}.docx"

                        # 파일 읽기
                        file_data = actual_path.read_bytes()

                        # 다운로드 버튼
                        st.success(
                            f"✅ 파일 준비 완료! (크기: {len(file_data):,} bytes)"
                        )
                        st.download_button(
                            label="📥 이력서 다운로드 (DOCX)",
                            data=file_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"download_local_{state.get('asked_count', 0)}",
                        )
                    except Exception as e:
                        logger.error(f"[파일 열기 오류] {e}")
                        st.error(f"파일을 여는 중 오류가 발생했습니다: {str(e)}")

                else:
                    st.error("📁 파일을 찾을 수 없습니다!")
                    st.warning(
                        "🔧 가능한 원인:\n1. 파일 생성 실패\n2. 경로 계산 오류\n3. 권한 문제"
                    )

                    if st.button("🔄 이력서 다시 생성"):
                        payload = deepcopy(state)
                        payload["inputs"] = self.ensure_inputs_dict(payload["inputs"])
                        payload["info_ready"] = True
                        result = self.make_api_request(
                            "/api/v1/resume/agent/update", payload
                        )
                        if result:
                            result["inputs"] = self.ensure_inputs_dict(result["inputs"])
                            result["step"] = "completed"
                            st.session_state["state"] = result
                            st.rerun()

                    else:
                        st.warning("⚠️ 다운로드할 파일 경로가 설정되지 않았습니다.")

                        if st.button("🔄 이력서 생성 다시 시도"):
                            payload = deepcopy(state)
                            payload["inputs"] = self.ensure_inputs_dict(
                                payload["inputs"]
                            )
                            payload["info_ready"] = True

                            result = self.make_api_request(
                                "/api/v1/resume/agent/update", payload
                            )
                            if result:
                                result["inputs"] = self.ensure_inputs_dict(
                                    result["inputs"]
                                )
                                result["step"] = "completed"
                                st.session_state["state"] = result
                                st.rerun()

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
                st.json(
                    {
                        "step": step,
                        "asked_count": state.get("asked_count", 0),
                        "docx_path": state.get("docx_path", ""),  # 추가
                        "info_ready": state.get("info_ready", False),  # 추가
                    }
                )
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
