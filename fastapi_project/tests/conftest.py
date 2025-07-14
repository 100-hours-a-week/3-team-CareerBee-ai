# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os

# 테스트용 환경변수 설정
os.environ.update(
    {
        "REDIS_URL": os.getenv("REDIS_URL"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
        "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }
)

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client():
    """비동기 HTTP 클라이언트"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """Mock Redis 클라이언트"""

    # 간단한 dict 기반 fake redis
    class FakeRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value
            return True

        def delete(self, key):
            if key in self.data:
                del self.data[key]
                return True
            return False

        def exists(self, key):
            return key in self.data

        def keys(self, pattern="*"):
            return list(self.data.keys())

    fake_redis = FakeRedis()
    with patch("app.utils.redis_client.get_redis_client", return_value=fake_redis):
        yield fake_redis


@pytest.fixture
def mock_s3():
    """Mock S3 클라이언트"""

    class FakeS3:
        def __init__(self):
            self.buckets = {}
            self.objects = {}

        def create_bucket(self, Bucket, **kwargs):
            self.buckets[Bucket] = {}
            return {"Location": f"/{Bucket}"}

        def upload_file(self, filename, bucket, key):
            if bucket not in self.buckets:
                self.buckets[bucket] = {}
            self.objects[f"{bucket}/{key}"] = {"filename": filename}
            return True

        def list_objects_v2(self, Bucket, **kwargs):
            if Bucket not in self.buckets:
                return {}

            objects = []
            for key, value in self.objects.items():
                if key.startswith(f"{Bucket}/"):
                    objects.append({"Key": key.replace(f"{Bucket}/", ""), "Size": 1024})

            if objects:
                return {"Contents": objects}
            return {}

        def generate_presigned_url(self, method, Params, ExpiresIn=3600):
            bucket = Params.get("Bucket", "test-bucket")
            key = Params.get("Key", "test-key")
            return f"https://s3.amazonaws.com/{bucket}/{key}?expires={ExpiresIn}"

    fake_s3 = FakeS3()
    fake_s3.create_bucket(Bucket="test-bucket")

    with patch("boto3.client", return_value=fake_s3):
        yield fake_s3


@pytest.fixture
def mock_llm_client():
    """LLM 클라이언트 모킹"""
    mock_instance = Mock()
    mock_instance.generate_feedback = AsyncMock(return_value="테스트 피드백입니다.")
    mock_instance.generate_resume = AsyncMock(return_value={"title": "테스트 이력서"})
    mock_instance.generate_question = AsyncMock(return_value="테스트 질문입니다.")

    with patch("app.utils.llm_client.LLMClient", return_value=mock_instance):
        with patch(
            "app.utils.llm_client.create_llm_client", return_value=mock_instance
        ):
            yield mock_instance


@pytest.fixture
def sample_feedback_request():
    """피드백 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "question": "자기소개를 해보세요",
        "answer": "안녕하세요. 저는 개발자입니다.",
    }


@pytest.fixture
def sample_resume_data():
    """BaseInputsModel에 맞는 이력서 샘플 데이터"""
    return {
        "email": "hong@example.com",
        "preferred_job": "백엔드 개발자",
        "certification_count": 3,
        "project_count": 5,
        "major_type": "MAJOR",
        "company_name": "테크 스타트업",
        "position": "주니어 개발자",
        "work_period": 24,
        "additional_experiences": "오픈소스 프로젝트 기여, 해커톤 수상 경험",
    }


@pytest.fixture
def sample_resume_data_non_major():
    """비전공자 이력서 샘플 데이터"""
    return {
        "email": "kim@example.com",
        "preferred_job": "프론트엔드 개발자",
        "certification_count": 1,
        "project_count": 3,
        "major_type": "NON_MAJOR",
        "company_name": "",
        "position": "",
        "work_period": 0,
        "additional_experiences": "부트캠프 수료, 개인 프로젝트 다수",
    }


@pytest.fixture
def sample_resume_data_experienced():
    """경력자 이력서 샘플 데이터"""
    return {
        "email": "senior@example.com",
        "preferred_job": "시니어 백엔드 개발자",
        "certification_count": 5,
        "project_count": 10,
        "major_type": "MAJOR",
        "company_name": "대기업",
        "position": "선임 연구원",
        "work_period": 60,
        "additional_experiences": "팀 리드 경험, 아키텍처 설계, 멘토링",
    }


@pytest.fixture
def sample_agent_init_request():
    """이력서 에이전트 초기화 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "inputs": {
            "email": "hong@example.com",
            "preferred_job": "백엔드 개발자",
            "certification_count": 3,
            "project_count": 5,
            "major_type": "MAJOR",
            "company_name": "테크 스타트업",
            "position": "주니어 개발자",
            "work_period": 24,
            "additional_experiences": "오픈소스 프로젝트 기여, 해커톤 수상 경험",
        },
    }


@pytest.fixture
def sample_agent_update_request():
    """이력서 에이전트 업데이트 요청 샘플 데이터"""
    return {
        "memberId": 1,
        "inputs": {
            "answer": "Python과 FastAPI를 주로 사용하며, 3년간의 웹 개발 경험이 있습니다."
        },
    }


@pytest.fixture
def mock_file_upload():
    """파일 업로드 모킹"""
    from fastapi import UploadFile
    from io import BytesIO

    file_content = b"test file content"
    file_obj = BytesIO(file_content)

    return UploadFile(
        filename="test.pdf", file=file_obj, content_type="application/pdf"
    )


@pytest.fixture
def mock_resume_agent_state():
    """Redis에 저장될 ResumeAgentState 모킹 데이터"""
    from datetime import datetime

    return {
        "memberId": 1,
        "inputs": {
            "email": "test@example.com",
            "preferred_job": "개발자",
            "certification_count": 2,
            "project_count": 3,
            "major_type": "MAJOR",
            "company_name": "회사",
            "position": "개발자",
            "work_period": 12,
            "additional_experiences": "경험",
        },
        "user_inputs": {"질문1": "답변1"},
        "answers": [
            {"question": "질문1", "answer": "답변1", "question_type": "general"}
        ],
        "pending_questions": ["다음 질문은 무엇인가요?"],
        "asked_count": 1,
        "max_questions": 3,
        "info_ready": False,
        "resume": "",
        "docx_path": "",
        "step": "questioning",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error_message": None,
        "error_details": None,
    }


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """테스트 후 파일 정리"""
    yield
    import glob

    test_files = glob.glob("test_*.docx") + glob.glob("test_*.pdf")
    for file in test_files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass


@pytest.fixture
def assert_error_response():
    """에러 응답 검증 헬퍼"""

    def _assert_error_response(response, status_code, message=None):
        assert response.status_code == status_code
        data = response.json()
        if "httpStatusCode" in data:
            assert data["httpStatusCode"] == status_code
        if message and "message" in data:
            assert data["message"] == message
        return data

    return _assert_error_response
