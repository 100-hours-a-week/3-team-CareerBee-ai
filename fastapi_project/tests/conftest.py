import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# 테스트 환경 설정 (app import 전에 미리 설정)
os.environ.update({
    "TESTING": "true",
    "DISABLE_DB": "true", 
    "REDIS_URL": "redis://localhost:6379",
    "AWS_ACCESS_KEY_ID": "test_key",
    "AWS_SECRET_ACCESS_KEY": "test_secret",
    "AWS_DEFAULT_REGION": "ap-northeast-2", 
    "S3_BUCKET_NAME": "test-bucket",
    "OPENAI_API_KEY": "test_openai_key",
})

# sys.modules에 mock 모듈들을 미리 등록하여 import 차단
sys.modules['chromadb'] = Mock()
sys.modules['chromadb.api'] = Mock()
sys.modules['chromadb.api.client'] = Mock()
sys.modules['langchain_community.vectorstores'] = Mock()
sys.modules['langchain_community.vectorstores.chroma'] = Mock()

# Chroma 클래스 자체를 mock으로 대체
class MockChroma:
    def __init__(self, *args, **kwargs):
        pass
    def similarity_search(self, query, k=3):
        return []
    def get_or_create_collection(self, *args, **kwargs):
        return Mock()

# langchain_community.vectorstores.Chroma를 mock으로 대체
mock_vectorstores = Mock()
mock_vectorstores.Chroma = MockChroma
sys.modules['langchain_community.vectorstores'] = mock_vectorstores

# 이제 안전하게 app import
try:
    from fastapi.testclient import TestClient
    from httpx import AsyncClient
    from app.main import app
    APP_AVAILABLE = True
except Exception as e:
    print(f"Warning: App import failed: {e}")
    app = None
    APP_AVAILABLE = False

# 기본 fixtures
@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def client():
    """동기 테스트 클라이언트"""
    if APP_AVAILABLE and app:
        return TestClient(app)
    return None

@pytest.fixture
async def async_client():
    """비동기 테스트 클라이언트"""
    if APP_AVAILABLE and app:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    else:
        yield None

# Mock fixtures
@pytest.fixture
def mock_redis():
    """가짜 Redis"""
    class FakeRedis:
        def __init__(self):
            self.data = {}
        def get(self, key):
            return self.data.get(key)
        def set(self, key, value, ex=None):
            self.data[key] = value
            return True
        def delete(self, key):
            return self.data.pop(key, None) is not None
    return FakeRedis()

@pytest.fixture  
def mock_llm_client():
    """LLM 클라이언트 mock"""
    mock = Mock()
    mock.generate_feedback = AsyncMock(return_value="테스트 피드백")
    return mock

# 테스트 데이터 fixtures
@pytest.fixture
def sample_feedback_request():
    return {
        "memberId": 1,
        "question": "자기소개를 해보세요.",
        "answer": "안녕하세요. 저는 개발자입니다."
    }

@pytest.fixture
def sample_agent_init_request():
    return {
        "memberId": 1,
        "inputs": {
            "email": "test@example.com",
            "preferred_job": "백엔드 개발자", 
            "certification_count": 2,
            "project_count": 3,
            "major_type": "MAJOR",
            "company_name": "회사",
            "position": "개발자",
            "work_period": 12,
            "additional_experiences": "경험"
        }
    }

@pytest.fixture
def sample_agent_update_request():
    return {
        "memberId": 1,
        "inputs": {
            "answer": "Python과 FastAPI를 주로 사용합니다."
        }
    }

# 테스트 정리
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """테스트 후 파일 정리"""
    yield
    import glob
    test_patterns = ["test_*.docx", "test_*.pdf", "temp_*"]
    for pattern in test_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
            except (FileNotFoundError, PermissionError):
                pass
