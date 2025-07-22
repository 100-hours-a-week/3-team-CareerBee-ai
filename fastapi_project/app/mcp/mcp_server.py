# app/mcp/mcp_server.py
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource, Prompt, PromptMessage, PromptArgument

# CareerBee 모듈들 import
from app.utils.redis_client import get_redis_client
from app.utils.llm_client import create_llm_client
from app.schemas import (
    ResumeAgentState,
    BaseInputsModel,
    create_initial_state,
    update_state_with_answer,
)
from app.agents.resume_agent import resume_agent
from app.agents.nodes.generate_question import GenerateQuestionNode

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CareerBeeMCPServer:
    def __init__(self):
        self.server = Server("careerbee-mcp")

        # 클라이언트 초기화
        self.redis_client = get_redis_client()
        self.llm_client = create_llm_client(temperature=0.3)

        # MCP 핸들러 등록
        self.setup_handlers()

    def setup_handlers(self):
        """MCP 서버 핸들러 설정"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """사용 가능한 도구 목록 반환"""
            return [
                # 1. 이력서 에이전트 초기화
                Tool(
                    name="resume_agent_init",
                    description="이력서 에이전트 초기화 - 사용자 정보 기반 이력서 생성 시작",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memberId": {"type": "integer", "description": "회원 ID"},
                            "user_info": {
                                "type": "object",
                                "description": "사용자 기본 정보",
                                "properties": {
                                    "email": {"type": "string"},
                                    "preferred_job": {"type": "string"},
                                    "certification_count": {"type": "integer"},
                                    "project_count": {"type": "integer"},
                                    "major_type": {
                                        "type": "string",
                                        "enum": ["MAJOR", "NON_MAJOR"],
                                    },
                                    "company_name": {"type": "string"},
                                    "position": {"type": "string"},
                                    "work_period": {"type": "integer"},
                                    "additional_experiences": {"type": "string"},
                                },
                                "required": ["email", "preferred_job", "major_type"],
                            },
                        },
                        "required": ["memberId", "user_info"],
                    },
                ),
                # 2. 이력서 에이전트 업데이트
                Tool(
                    name="resume_agent_update",
                    description="이력서 에이전트 업데이트 - 대화를 통한 이력서 개선",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memberId": {"type": "integer", "description": "회원 ID"},
                            "answer": {"type": "string", "description": "사용자 답변"},
                        },
                        "required": ["memberId", "answer"],
                    },
                ),
                # 3. 기본 이력서 생성 (템플릿 기반)
                Tool(
                    name="resume_create_basic",
                    description="기본 이력서 생성 - 하드코딩 템플릿 기반 즉시 생성",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "preferred_job": {"type": "string"},
                            "certification_count": {"type": "integer"},
                            "project_count": {"type": "integer"},
                            "major_type": {
                                "type": "string",
                                "enum": ["MAJOR", "NON_MAJOR"],
                            },
                            "company_name": {"type": "string"},
                            "position": {"type": "string"},
                            "work_period": {"type": "integer"},
                            "additional_experiences": {"type": "string"},
                        },
                        "required": ["email", "preferred_job", "major_type"],
                    },
                ),
                # 4. 이력서 정보 추출
                Tool(
                    name="resume_extract",
                    description="이력서 파일에서 구조화된 정보 추출",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_url": {
                                "type": "string",
                                "description": "이력서 파일 URL",
                            }
                        },
                        "required": ["file_url"],
                    },
                ),
                # 5. 면접 피드백 생성
                Tool(
                    name="interview_feedback",
                    description="면접 답변에 대한 AI 피드백 생성",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memberId": {"type": "integer", "description": "회원 ID"},
                            "question": {"type": "string", "description": "면접 질문"},
                            "answer": {
                                "type": "string",
                                "description": "사용자의 답변",
                            },
                        },
                        "required": ["memberId", "question", "answer"],
                    },
                ),
                # 6. 기업 정보 요약 업데이트
                Tool(
                    name="company_summary_update",
                    description="기업 정보 요약 파이프라인 실행",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                ),
                # 7. 에이전트 상태 조회
                Tool(
                    name="get_agent_status",
                    description="이력서 에이전트 상태 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memberId": {"type": "integer", "description": "회원 ID"}
                        },
                        "required": ["memberId"],
                    },
                ),
                # 8. 에이전트 세션 삭제
                Tool(
                    name="delete_agent_session",
                    description="이력서 에이전트 세션 삭제",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memberId": {"type": "integer", "description": "회원 ID"}
                        },
                        "required": ["memberId"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[TextContent]:
            """도구 실행 핸들러"""
            try:
                result = None

                # 1. 이력서 에이전트 초기화
                if name == "resume_agent_init":
                    result = await self.handle_resume_agent_init(arguments)

                # 2. 이력서 에이전트 업데이트
                elif name == "resume_agent_update":
                    result = await self.handle_resume_agent_update(arguments)

                # 3. 기본 이력서 생성
                elif name == "resume_create_basic":
                    result = await self.handle_resume_create_basic(arguments)

                # 4. 이력서 정보 추출
                elif name == "resume_extract":
                    result = await self.handle_resume_extract(arguments)

                # 5. 면접 피드백
                elif name == "interview_feedback":
                    result = await self.handle_interview_feedback(arguments)

                # 6. 기업 요약 업데이트
                elif name == "company_summary_update":
                    result = await self.handle_company_summary_update()

                # 7. 상태 조회
                elif name == "get_agent_status":
                    result = await self.handle_get_agent_status(arguments)

                # 8. 세션 삭제
                elif name == "delete_agent_session":
                    result = await self.handle_delete_session(arguments)

                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            except Exception as e:
                import traceback

                logger.error(f"Tool execution error: {str(e)}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(e), "traceback": traceback.format_exc()},
                            ensure_ascii=False,
                        ),
                    )
                ]

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """사용 가능한 리소스 목록"""
            return [
                Resource(
                    uri="careerbee://sessions/active",
                    name="Active Sessions",
                    description="현재 진행 중인 이력서 생성 세션",
                    mimeType="application/json",
                ),
                Resource(
                    uri="careerbee://questions/fallback",
                    name="Fallback Questions",
                    description="LLM 실패 시 사용할 기본 질문들",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """리소스 읽기"""
            if uri == "careerbee://sessions/active":
                # Redis에서 활성 세션 목록 조회
                # 실제 구현은 redis_client의 기능에 따라 달라질 수 있음
                return json.dumps({"sessions": [], "total": 0})

            elif uri == "careerbee://questions/fallback":
                return json.dumps(
                    {
                        "questions": [
                            "가장 자신있는 기술 스택이나 프로그래밍 언어는 무엇인가요?",
                            "지금까지 진행한 프로젝트 중 가장 인상 깊었던 프로젝트에 대해 설명해주세요.",
                            "앞으로 어떤 개발자가 되고 싶으신가요?",
                        ]
                    }
                )
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """사용 가능한 프롬프트 템플릿"""
            return [
                Prompt(
                    name="resume_question",
                    description="이력서 질문 생성 프롬프트",
                    arguments=[
                        PromptArgument(
                            name="user_type",
                            description="사용자 유형 (신입/경력)",
                            required=True,
                        ),
                        PromptArgument(
                            name="job_type", description="희망 직무", required=True
                        ),
                    ],
                ),
                Prompt(
                    name="interview_feedback",
                    description="면접 피드백 프롬프트",
                    arguments=[
                        PromptArgument(
                            name="question", description="면접 질문", required=True
                        ),
                        PromptArgument(
                            name="answer", description="사용자 답변", required=True
                        ),
                    ],
                ),
            ]

    # 도구 핸들러 구현
    async def handle_resume_agent_init(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """이력서 에이전트 초기화"""
        memberId = args.get("memberId")
        user_info = args.get("user_info", {})

        try:
            # BaseInputsModel 생성
            inputs = BaseInputsModel(**user_info)

            # 기존 상태 확인
            existing_state = await self.redis_client.load_state(memberId)
            if existing_state:
                # 기존 세션이 있으면 삭제
                await self.redis_client.delete_state(memberId)

            # 초기 상태 생성
            initial_state = create_initial_state(memberId=memberId, inputs=inputs)

            # 첫 번째 질문 생성
            question_node = GenerateQuestionNode(self.llm_client)
            updated_state = await question_node.execute(initial_state)

            # 생성된 질문 확인
            first_question = updated_state.get_next_question()
            if not first_question:
                # Fallback 질문 사용
                first_question = (
                    "가장 자신있는 기술 스택이나 프로그래밍 언어는 무엇인가요?"
                )
                updated_state.pending_questions = [first_question]

            updated_state.step = "questioning"

            # Redis에 저장
            await self.redis_client.save_state(memberId, updated_state)

            return {
                "memberId": memberId,
                "question": first_question,
                "status": "initialized",
            }

        except Exception as e:
            logger.error(f"Resume agent init failed: {e}")
            raise

    async def handle_resume_agent_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """이력서 에이전트 업데이트"""
        memberId = args.get("memberId")
        answer = args.get("answer")

        try:
            # 상태 로드
            current_state = await self.redis_client.load_state(memberId)
            if not current_state:
                return {
                    "error": f"회원 {memberId}의 세션을 찾을 수 없습니다",
                    "status": "not_found",
                }

            # 락 획득
            lock_acquired = await self.redis_client.acquire_lock(memberId)
            if not lock_acquired:
                return {"error": "세션이 이미 처리 중입니다", "status": "locked"}

            try:
                # 답변 처리
                current_question = (
                    current_state.pending_questions[0]
                    if current_state.pending_questions
                    else ""
                )
                updated_state = update_state_with_answer(
                    current_state, current_question, answer
                )
                updated_state.pending_questions = []

                # LangGraph 실행
                final_state = None
                async for step in resume_agent.astream(updated_state):
                    final_state = step

                # 최종 상태 추출
                if isinstance(final_state, dict):
                    raw_state = list(final_state.values())[0]
                else:
                    raw_state = final_state

                if isinstance(raw_state, dict):
                    final_state = ResumeAgentState(**raw_state)
                elif isinstance(raw_state, ResumeAgentState):
                    final_state = raw_state
                else:
                    raise Exception(f"Invalid state type: {type(raw_state)}")

                # 완료 여부 확인
                if final_state.info_ready and final_state.step == "completed":
                    # 완료: Redis에서 삭제
                    await self.redis_client.delete_state(memberId)

                    # S3 키 추출
                    resumeObjectKey = self._extract_s3_key(
                        final_state.docx_path, memberId
                    )

                    return {
                        "memberId": memberId,
                        "isComplete": True,
                        "resumeObjectKey": resumeObjectKey,
                    }
                else:
                    # 계속: Redis에 저장
                    await self.redis_client.save_state(memberId, final_state)

                    next_question = final_state.get_next_question()
                    return {
                        "memberId": memberId,
                        "isComplete": False,
                        "question": next_question,
                    }

            finally:
                await self.redis_client.release_lock(memberId)

        except Exception as e:
            logger.error(f"Resume agent update failed: {e}")
            raise

    async def handle_resume_create_basic(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """기본 이력서 생성 (템플릿 기반)"""
        try:
            from app.schemas import ResumeCreateRequest
            from app.services.resume_create_service import _generate_resume_doc
            from app.utils.upload_file_to_s3 import async_upload_file_to_s3

            # 요청 데이터 생성
            request = ResumeCreateRequest(**args)

            # 문서 생성
            file_obj = await asyncio.to_thread(_generate_resume_doc, request)

            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resume_draft_{timestamp}.docx"

            # S3 업로드
            file_url = await async_upload_file_to_s3(file_obj, filename)

            return {
                "message": "resume_draft_success",
                "data": {"file_url": file_url, "file_name": filename},
            }

        except Exception as e:
            logger.error(f"Basic resume creation failed: {e}")
            raise

    async def handle_resume_extract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """이력서 정보 추출"""
        try:
            from app.services.resume_extract_service import extract_resume_info
            from app.schemas.resume_extract import ResumeInfo

            file_url = args.get("file_url")

            # URL 검증
            if not file_url:
                return {"error": "file_url은 필수입니다", "status": "invalid_request"}

            # 이력서 정보 추출
            result = await extract_resume_info(file_url)

            # ResumeInfo 객체를 dict로 변환
            if isinstance(result, ResumeInfo):
                data = result.dict()
            else:
                data = result

            return {"message": "extraction_success", "data": data}

        except ValueError as e:
            logger.warning(f"Resume extraction validation error: {e}")
            # 특정 에러 메시지에 따른 처리
            error_msg = str(e)
            if "invalid_file_type" in error_msg:
                return {
                    "message": "extraction_failed",
                    "error": "유효하지 않은 파일 형식입니다",
                    "data": self._get_fallback_resume_info(),
                }
            elif "resume_text_is_empty" in error_msg:
                return {
                    "message": "extraction_failed",
                    "error": "PDF에서 텍스트를 추출할 수 없습니다",
                    "data": self._get_fallback_resume_info(),
                }
            else:
                return {
                    "message": "extraction_failed",
                    "error": error_msg,
                    "data": self._get_fallback_resume_info(),
                }

        except Exception as e:
            logger.error(f"Resume extraction failed: {e}")
            # 모든 예외에서 fallback 반환
            return {
                "message": "extraction_failed",
                "error": "이력서 정보 추출 중 오류가 발생했습니다",
                "data": self._get_fallback_resume_info(),
            }

    def _get_fallback_resume_info(self) -> Dict[str, Any]:
        """이력서 추출 실패 시 반환할 기본값"""
        return {
            "certification_count": 0,
            "project_count": 0,
            "major_type": "NON_MAJOR",
            "company_name": None,
            "work_period": 0,
            "position": None,
            "additional_experiences": None,
        }

    async def handle_interview_feedback(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """면접 피드백 생성"""
        try:
            from app.services.feedback_service import generate_feedback

            question = args.get("question")
            answer = args.get("answer")
            memberId = args.get("memberId")

            # 입력 검증
            if not question or not question.strip():
                return {"error": "질문은 필수입니다", "status": "invalid_request"}

            if not answer or not answer.strip():
                return {"error": "답변은 필수입니다", "status": "invalid_request"}

            if len(question) > 200:
                return {
                    "error": "질문은 최대 200자까지 입력 가능합니다",
                    "status": "invalid_request",
                }

            if len(answer) > 500:
                return {
                    "error": "답변은 최대 500자까지 입력 가능합니다",
                    "status": "invalid_request",
                }

            # 피드백 생성
            feedback = await generate_feedback(question, answer)

            return {
                "httpStatusCode": 200,
                "message": "feedback_success",
                "data": {"memberId": memberId, "feedback": feedback},
            }

        except ValueError as e:
            # 안전하지 않은 피드백 등
            logger.warning(f"Feedback validation error: {e}")
            return {"error": str(e), "status": "unsafe_content"}
        except RuntimeError as e:
            # LLM API 요청 실패
            logger.error(f"LLM API error: {e}")
            return {"error": "LLM 서비스 연결 실패", "status": "service_error"}
        except Exception as e:
            logger.error(f"Interview feedback failed: {e}")
            raise

    async def handle_company_summary_update(self) -> Dict[str, Any]:
        """기업 요약 업데이트"""
        try:
            from app.services.summary_service import run_summary_pipeline

            # 동기 함수를 비동기로 실행
            await asyncio.to_thread(run_summary_pipeline)

            return {
                "message": "요약 파이프라인 완료",
                "status": "completed",
                "details": {
                    "description": "기업 정보 요약이 업데이트되었습니다",
                    "next_update": "다음 월요일 12시 (Asia/Seoul)",
                },
            }

        except FileNotFoundError as e:
            logger.error(f"Company data file not found: {e}")
            return {
                "error": "기업 데이터 파일을 찾을 수 없습니다",
                "status": "file_not_found",
                "details": "app/data/catch_company_details.csv 파일이 필요합니다",
            }
        except Exception as e:
            logger.error(f"Company summary update failed: {e}")
            return {
                "error": f"요약 파이프라인 실행 실패: {str(e)}",
                "status": "pipeline_error",
            }

    async def handle_get_agent_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 상태 조회"""
        memberId = args.get("memberId")

        try:
            state = await self.redis_client.load_state(memberId)

            if not state:
                return {
                    "error": f"회원 {memberId}의 세션을 찾을 수 없습니다",
                    "status": "not_found",
                }

            return {
                "memberId": memberId,
                "step": state.step,
                "asked_count": state.asked_count,
                "max_questions": state.max_questions,
                "info_ready": state.info_ready,
                "pending_questions": len(state.pending_questions),
                "answers_count": len(state.answers),
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Get agent status failed: {e}")
            raise

    async def handle_delete_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """세션 삭제"""
        memberId = args.get("memberId")

        try:
            deleted = await self.redis_client.delete_state(memberId)

            return {
                "memberId": memberId,
                "deleted": deleted,
                "message": (
                    "세션이 삭제되었습니다." if deleted else "삭제할 세션이 없습니다."
                ),
            }

        except Exception as e:
            logger.error(f"Delete session failed: {e}")
            raise

    def _extract_s3_key(self, docx_path: str, memberId: int) -> str:
        """S3 키 추출"""
        if not docx_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"resume/member_{memberId}_{timestamp}.docx"

        if docx_path.startswith("http"):
            try:
                from urllib.parse import urlparse

                parsed = urlparse(docx_path)
                return parsed.path.lstrip("/")
            except:
                pass

        if docx_path.startswith("resume/"):
            return docx_path

        import os

        filename = os.path.basename(docx_path)
        return f"resume/{filename}"

    async def run(self):
        """MCP 서버 실행"""
        async with self.server.run_stdio():
            initialization_options = InitializationOptions(
                server_name="careerbee-mcp", server_version="1.0.0"
            )
            await self.server.initialized(initialization_options)
            await asyncio.Event().wait()


if __name__ == "__main__":
    # MCP 서버 실행
    server = CareerBeeMCPServer()
    asyncio.run(server.run())
