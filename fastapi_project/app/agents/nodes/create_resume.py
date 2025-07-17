# app/agents/nodes/create_resume.py
import os
from datetime import datetime
import asyncio
from typing import Optional, Union
from app.utils.llm_client import LLMClient, create_llm_client
from app.schemas import ResumeAgentState, ResumeAgentUpdateRequest
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from bs4 import BeautifulSoup
from markdown2 import markdown
from app.agents.base_node import LLMBaseNode


class CreateResumeNode(LLMBaseNode):
    def __init__(self, llm_client: Optional[Union[LLMClient, object]] = None):
        """
        CreateResumeNode 초기화

        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        # LLM 클라이언트가 없으면 자동 생성
        if llm_client is None:
            llm_client = create_llm_client(temperature=0.3)

        super().__init__(llm_client)

        # 환경 설정
        self.environment = os.getenv(
            "ENVIRONMENT", "development"
        )  # development, production
        self.use_s3 = os.getenv("USE_S3", "false").lower() == "true"

        # AWS S3 관련 환경변수 체크
        self.s3_available = self._check_s3_availability()

        self.logger.info(
            f"환경: {self.environment}, S3 사용: {self.use_s3}, S3 가용: {self.s3_available}"
        )

    def preprocess_state_data(self, state: ResumeAgentState) -> ResumeAgentState:
        """이력서 생성 전 데이터 전처리"""

        # 빈 값 처리
        if state.inputs.company_name in ["", "없음", None, "backend"]:
            state.inputs.company_name = "신입"

        # 직무명 표준화
        job_mapping = {
            "BACKEND": "Backend Engineer",
            "FRONTEND": "Frontend Engineer",
            "FULLSTACK": "Full-stack Engineer",
            "백엔드": "Backend Engineer",
            "프론트엔드": "Frontend Engineer",
            "풀스택": "Full-stack Engineer",
        }
        state.inputs.preferred_job = job_mapping.get(
            state.inputs.preferred_job.upper(), state.inputs.preferred_job
        )
        # 전공 여부 명확화
        if state.inputs.major_type == "MAJOR":
            state.inputs.major_type = "컴퓨터공학 전공"
        elif state.inputs.major_type == "NON_MAJOR":
            state.inputs.major_type = "비전공자"

        return state

    def _format_work_period(self, months: int) -> str:
        """근무 기간을 읽기 쉬운 형식으로 변환"""
        if not months or months == 0:
            return "신입"

        years = months // 12
        remaining_months = months % 12

        if years > 0:
            return (
                f"{years}년 {remaining_months}개월"
                if remaining_months > 0
                else f"{years}년"
            )
        else:
            return f"{remaining_months}개월"

    def categorize_qna(self, answers):
        """질문-응답을 카테고리별로 분류"""
        categories = {
            "기술역량": [],
            "프로젝트": [],
            "경력": [],
            "교육": [],
            "기타": [],
        }

        for qa in answers:
            question = qa["question"].lower()
            if any(
                word in question
                for word in ["기술", "스택", "언어", "프레임워크", "툴", "tool"]
            ):
                categories["기술역량"].append(qa)
            elif any(
                word in question for word in ["프로젝트", "개발", "구현", "서비스"]
            ):
                categories["프로젝트"].append(qa)
            elif any(word in question for word in ["경력", "회사", "직무", "업무"]):
                categories["경력"].append(qa)
            elif any(word in question for word in ["교육", "학습", "공부", "강의"]):
                categories["교육"].append(qa)
            else:
                categories["기타"].append(qa)

        return categories

    def _check_s3_availability(self) -> bool:
        """S3 업로드 기능 사용 가능 여부 확인"""
        try:
            # S3 업로드 함수 import 테스트
            from app.utils.upload_file_to_s3 import async_upload_file_to_s3

            # 필수 환경변수 확인
            required_vars = [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_DEFAULT_REGION",
            ]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars:
                self.logger.warning(f"S3 관련 환경변수 누락: {missing_vars}")
                return False

            return True

        except ImportError as e:
            self.logger.warning(f"S3 업로드 모듈 import 실패: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"S3 가용성 체크 실패: {e}")
            return False

    async def execute(self, state: ResumeAgentState) -> ResumeAgentState:
        try:
            state = self.preprocess_state_data(state)
            prompt = self._build_resume_prompt(state)

            # 시스템 프롬프트 정의
            system_prompt = """당신은 10년 이상의 경력을 가진 전문 이력서 작성 컨설턴트입니다. 
            
            다음 원칙을 반드시 지켜주세요:

            1. 형식:
                - 표준 이력서 형식 준수 (Contacts -> 지원 직무 -> 보유 역량 -> 경력 -> 프로젝트 -> 교육 -> 기타)
                - 마크다운 헤딩은 # (대제목), ## (중제목), ### (소제목)만 사용
                - 불렛 포인트는 '-' 사용
            2. 금지 사항:
                - "기본 정보", "개인 정보" 등의 중복 섹션 생성 금지
                - 동일한 정보를 여러 섹션에 반복하지 않음

            2. 내용:
                - 구체적이고 측정 가능한 성과 위주로 작성
                - 기술 스택은 정확한 명칭 사용 (예: Spring Framework, Docker, AWS EC2)
                - 모든 경험에 기간 명시
                - 정보가 없는 섹션은 제목 생성 후 작성할 수 있는 칸만 생성
                - 가상의 내용이나 예시 작성시 [예시] 명시 후 작성
            
            3. 문체:
                - 간결하고 임팩트 있는 동사 사용
                - 수동태보다 능동태 선호
                - 전문 용어는 업계 표준 사용"""

            # LLM으로 이력서 생성 (시스템 프롬프트 포함)
            content = await self._safe_llm_call(
                prompt, system_prompt, "이력서 생성 중 오류가 발생했습니다."
            )

            # S3 업로드 시도 (가용한 경우에만)
            if self.use_s3 and self.s3_available:
                try:
                    # 프로덕션: S3 업로드 시도
                    docx_path = await self._create_and_upload_document(state, content)
                    self.logger.info(f"S3 업로드 성공: {docx_path}")
                except Exception as e:
                    self.logger.error(f"S3 업로드 실패, 로컬 저장으로 fallback: {e}")
                    # S3 실패시 로컬 저장으로 fallback
                    docx_path = await self._create_local_document(state, content)
            else:
                # 개발 환경 또는 S3 불가용: 로컬 저장
                docx_path = await self._create_local_document(state, content)

            # 상태 업데이트
            state.docx_path = docx_path
            state.resume = content
            state.step = "completed"
            state.info_ready = True  # 완료 플래그 설정

            return state

        except Exception as e:
            self.logger.error(f"CreateResumeNode 실행 중 오류: {e}")

            # 에러가 발생해도 기본적인 이력서 내용은 제공
            if (
                hasattr(self, "_last_generated_content")
                and self._last_generated_content
            ):
                state.resume = self._last_generated_content
            else:
                # LLM 내용도 없다면 기본 이력서 생성
                state.resume = self._create_fallback_resume(state)

            # 에러 상태 설정
            state.step = "completed_with_error"
            state.docx_path = ""  # 파일 생성 실패

            return state

    async def _create_and_upload_document(
        self, state: ResumeAgentState, content: str
    ) -> str:
        """Word 문서 생성 후 S3 업로드 (프로덕션용)"""

        # 1. 임시 로컬 파일 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"resume_agent_{timestamp}.docx"
        temp_dir = "/tmp" if os.path.exists("/tmp") else "temp"
        os.makedirs(temp_dir, exist_ok=True)
        local_path = os.path.join(temp_dir, local_filename)

        # 2. Word 문서 생성
        def create_doc():
            doc = Document()
            # doc.add_heading("이력서", level=0).alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

            # 기본 정보 섹션
            # self._add_basic_info_section(doc, state.inputs)

            # LLM 생성 내용 섹션
            self._render_llm_content_stylized(content, doc)

            doc.save(local_path)

        await asyncio.to_thread(create_doc)

        # 3. S3 업로드
        try:
            from app.utils.upload_file_to_s3 import async_upload_file_to_s3
            from io import BytesIO

            # 파일을 BytesIO로 읽기
            def read_file_to_bytes():
                with open(local_path, "rb") as f:
                    return f.read()

            file_bytes = await asyncio.to_thread(read_file_to_bytes)
            file_obj = BytesIO(file_bytes)
            file_obj.name = local_filename

            s3_url = await async_upload_file_to_s3(file_obj, local_filename)

            if not s3_url:
                self.logger.error("S3 업로드 실패")
                raise Exception("S3 업로드에 실패했습니다")

            self.logger.info(f"S3 업로드 성공: {s3_url}")

            # 4. 임시 파일 정리
            try:
                os.remove(local_path)
                self.logger.info(f"임시 파일 정리 완료: {local_path}")
            except Exception as e:
                self.logger.warning(f"임시 파일 정리 실패: {e}")

            return s3_url

        except Exception as e:
            self.logger.error(f"S3 업로드 중 오류: {e}")
            # S3 업로드 실패시 로컬 경로 반환 (fallback)
            return local_path

    async def _create_local_document(
        self, state: ResumeAgentState, content: str
    ) -> str:
        """Word 문서 로컬 생성 (개발용)"""

        # 절대 경로 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_final_{timestamp}.docx"

        # 프로젝트 루트의 generated 폴더에 저장
        current_dir = os.getcwd()
        abs_dir = os.path.join(current_dir, "generated")
        abs_path = os.path.join(abs_dir, filename)

        def write_to_doc():
            try:
                # 디렉토리 생성
                os.makedirs(abs_dir, exist_ok=True)

                # 문서 생성
                doc = Document()
                doc.add_heading("이력서", level=0).alignment = (
                    WD_PARAGRAPH_ALIGNMENT.LEFT
                )

                # 기본 정보 섹션
                # self._add_basic_info_section(doc, state.inputs)

                # LLM 생성 내용 섹션
                self._render_llm_content_stylized(content, doc)

                # 파일 저장 (abs_path 사용)
                doc.save(abs_path)

                # 파일 생성 확인
                if os.path.exists(abs_path):
                    file_size = os.path.getsize(abs_path)
                    print(
                        f"✅ 로컬 파일 생성 성공: {abs_path} (크기: {file_size} bytes)"
                    )
                else:
                    print(f"❌ 로컬 파일 생성 실패: {abs_path}")

            except Exception as e:
                print(f"❌ 문서 생성 중 오류: {e}")
                raise

        await asyncio.to_thread(write_to_doc)

        # 생성 후 다시 한번 확인
        if os.path.exists(abs_path):
            self.logger.info(f"로컬 이력서 파일 생성 완료: {abs_path}")
            return abs_path
        else:
            self.logger.error(f"로컬 파일 생성 실패: {abs_path}")
            raise FileNotFoundError(f"파일을 생성할 수 없습니다: {abs_path}")

    def _build_resume_prompt(self, state: ResumeAgentState) -> str:
        # QnA 카테고리화
        categorized_qa = self.categorize_qna(state.answers)
        # 카테고리별 QnA 포맷팅
        formatted_qa = ""
        for category, qas in categorized_qa.items():
            if qas:  # 해당 카테고리에 QnA가 있는 경우만
                formatted_qa += f"\n[{category}]\n"
                for qa in qas:
                    formatted_qa += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

        work_period_display = self._format_work_period(state.inputs.work_period)

        base_info = f"""
    이메일: {state.inputs.email}
    희망 직무: {state.inputs.preferred_job}
    전공: {state.inputs.major_type}
    재직 회사: {state.inputs.company_name}
    직무: {state.inputs.position}
    경력 기간: {work_period_display}
    보유 자격증: {state.inputs.certification_count}개
    수행 프로젝트: {state.inputs.project_count}개
    추가 경험: {state.inputs.additional_experiences}
        """

        return f"""
    다음 정보를 바탕으로 전문적인 이력서를 작성해주세요. 

    [작성 원칙] 
    1. **문서 최상단에 "# 이력서" 제목을 한 번만 작성**
    2. 구체적이고 정량적인 성과 중심으로 작성
    3. 기술 스택과 도구를 명확히 명시
    4. 프로젝트 경험은 문제-해결-성과 구조로 작성
    5. 비어있는 섹션(0개 프로젝트, 0개 자격증 등)은 '프로젝트', '자격증' 칸만 생성. 
    6. 가상의 내용이나 예시는 [예시]라고 표시 후 작성. 
    7. "기본 정보" 섹션은 절대 만들지 말 것. 

    [이력서 구조]
    # 이력서  ← 최상단 제목 (한 번만)

    ## Contacts
    - 이메일: {state.inputs.email}

    ## 지원 직무
    - {state.inputs.preferred_job}

    ## 보유 역량 요약
    - 기술별로 그룹핑하여 작성

    ## Careers
    - 회사명 / 직무 @ 팀명 (기간)
    - 주요 업무 및 성과를 불렛 포인트로 작성

    ## Projects  
    - 프로젝트명 / 간단한 설명 [링크]
    - 사용 기술, 역할, 성과를 구체적으로 작성

    ## Education
    - 학교명 / 전공 (기간)

    ## ETC
    - 자격증, 수상 경력, 오픈소스 기여 등

    **중요: "기본 정보"라는 섹션은 만들지 마세요. 이메일은 Contacts 섹션에, 희망 직무는 '지원 직무' 섹션에만 포함하세요.**

    [입력된 기본 정보]
    {base_info}

    [카테고리별 상세 정보]
    {formatted_qa}


    위 정보를 바탕으로 표준 이력서 형식에 맞춰 작성하되, 
    - 정보가 부족한 부분은 [예시]를 생성해서 작성
    - 신입인 경우 Projects, Education 등에 더 집중
    - 경력자인 경우 Careers 섹션을 상세히 작성
    """

    async def _generate_resume_content(self, prompt: str) -> str:
        """LLM으로 이력서 내용 생성"""
        content = await self._safe_llm_call(
            prompt, "이력서 생성 중 오류가 발생했습니다."
        )
        return content

    # def _add_basic_info_section(self, doc: Document, inputs):
    #     """기본 정보 섹션 추가"""
    #     doc.add_heading("기본 정보", level=1)
    #     doc.add_paragraph(f"이메일: {inputs.email}")
    #     doc.add_paragraph(f"희망 직무: {inputs.preferred_job}")
    #     doc.add_paragraph(f"전공 여부: {inputs.major_type}")

    def _render_llm_content_stylized(self, markdown_text: str, doc: Document):
        """마크다운 텍스트를 Word 문서에 스타일 적용하여 렌더링"""
        html = markdown(markdown_text)
        soup = BeautifulSoup(html, "html.parser")

        # 스타일 정의
        styles = {
            "h1": {"size": Pt(16), "bold": True, "space_after": Pt(12)},
            "h2": {"size": Pt(14), "bold": True, "space_after": Pt(10)},
            "h3": {"size": Pt(12), "bold": True, "space_after": Pt(8)},
            "p": {"size": Pt(11), "space_after": Pt(6)},
            "li": {"size": Pt(11), "space_after": Pt(4)},
        }

        for element in soup.descendants:
            if element.name == "h1":
                paragraph = doc.add_heading(element.get_text(), level=1)
                paragraph.runs[0].font.size = styles["h1"]["size"]
                paragraph.paragraph_format.space_after = styles["h1"]["space_after"]
                # 섹션 구분선 추가
                self._add_horizontal_line(paragraph)

            elif element.name == "h2":
                paragraph = doc.add_heading(element.get_text(), level=2)
                paragraph.runs[0].font.size = styles["h2"]["size"]
                paragraph.paragraph_format.space_after = styles["h2"]["space_after"]

            elif element.name == "p":
                paragraph = doc.add_paragraph(element.get_text())
                paragraph.runs[0].font.size = styles["p"]["size"]
                paragraph.paragraph_format.space_after = styles["p"]["space_after"]

            elif element.name == "li":
                # 들여쓰기와 함께 불렛 포인트 추가
                paragraph = doc.add_paragraph(element.get_text(), style="List Bullet")
                paragraph.runs[0].font.size = styles["li"]["size"]
                paragraph.paragraph_format.left_indent = Pt(20)

    def _create_fallback_resume(self, state: ResumeAgentState) -> str:
        """파일 생성 실패시 기본 이력서 텍스트 생성"""

        inputs = state.inputs
        answers = state.answers

        fallback_content = f"""# 이력서

## 기본 정보
- **이메일**: {inputs.email}
- **희망 직무**: {inputs.preferred_job}
- **전공 여부**: {inputs.major_type}
- **재직 회사**: {inputs.company_name}
- **현재 직무**: {inputs.position}
- **재직 기간**: {inputs.work_period}개월
- **자격증 수**: {inputs.certification_count}개
- **프로젝트 수**: {inputs.project_count}개

## 추가 경험
{inputs.additional_experiences}

## 상세 정보
"""

        for i, qa in enumerate(answers, 1):
            fallback_content += f"\n### Q{i}: {qa['question']}\n{qa['answer']}\n"

        fallback_content += f"\n\n---\n 파일 생성 중 오류가 발생하여 텍스트 형태로 제공됩니다.\n텍스트를 복사하여 별도 문서로 저장해주세요."

        return fallback_content

    def _add_horizontal_line(self, paragraph):
        """단락에 수평선 추가"""
        pPr = paragraph._p.get_or_add_pPr()
        border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "0")
        bottom.set(qn("w:color"), "2F5496")
        border.append(bottom)
        pPr.append(border)
