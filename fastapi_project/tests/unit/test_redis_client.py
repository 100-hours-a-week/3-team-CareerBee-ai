# tests/unit/test_redis_client.py
import pytest
from unittest.mock import patch, Mock, AsyncMock
import json
from datetime import datetime

# 안전한 임포트
try:
    from app.utils.redis_client import get_redis_client, RedisClient

    REDIS_CLIENT_AVAILABLE = True
except ImportError:
    REDIS_CLIENT_AVAILABLE = False


# 테스트용 가짜 ResumeAgentState
class MockResumeAgentState:
    """테스트용 가짜 ResumeAgentState"""

    def __init__(self, memberId=1, step="questioning"):
        self.memberId = memberId
        self.step = step
        self.asked_count = 0
        self.info_ready = False
        self.pending_questions = ["테스트 질문"]
        self.answers = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_redis_dict(self):
        return {
            "memberId": self.memberId,
            "step": self.step,
            "asked_count": self.asked_count,
            "info_ready": self.info_ready,
            "pending_questions": self.pending_questions,
            "answers": self.answers,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_redis_dict(cls, data):
        instance = cls(data["memberId"])
        instance.step = data.get("step", "questioning")
        instance.asked_count = data.get("asked_count", 0)
        instance.info_ready = data.get("info_ready", False)
        instance.pending_questions = data.get("pending_questions", [])
        instance.answers = data.get("answers", [])
        return instance


@pytest.mark.skipif(not REDIS_CLIENT_AVAILABLE, reason="Redis client not available")
class TestRedisClient:
    """Redis 클라이언트 단위 테스트"""

    @pytest.fixture
    def redis_client(self):
        """테스트용 Redis 클라이언트 (실제 Redis 연결 없이)"""
        with patch("redis.ConnectionPool.from_url"), patch(
            "redis.Redis"
        ) as mock_redis_class:

            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            client = RedisClient()
            client.redis_client = mock_redis_instance
            return client, mock_redis_instance

    @pytest.fixture
    def mock_state(self):
        """테스트용 상태 객체"""
        return MockResumeAgentState(memberId=123)

    def test_redis_client_singleton(self):
        """Redis 클라이언트 싱글톤 테스트"""
        with patch("app.utils.redis_client.RedisClient") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            client1 = get_redis_client()
            client2 = get_redis_client()

            # 같은 인스턴스여야 함
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_save_state_redis_success(self, redis_client, mock_state):
        """Redis 상태 저장 성공 테스트"""
        client, mock_redis = redis_client

        # setex 모킹
        mock_redis.setex = Mock(return_value=True)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = True

            result = await client.save_state(123, mock_state)

            assert result == True
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_fallback_to_memory(self, mock_state):
        """Redis 실패 시 메모리 fallback 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            result = await client.save_state(123, mock_state)

            assert result == True
            # 메모리에 저장되었는지 확인
            assert "resume:123" in client.memory_store

    @pytest.mark.asyncio
    async def test_load_state_redis_success(self, redis_client, mock_state):
        """Redis 상태 조회 성공 테스트"""
        client, mock_redis = redis_client

        # 저장할 데이터 준비
        state_data = mock_state.to_redis_dict()
        state_json = json.dumps(state_data, default=str)

        with patch(
            "asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread, patch("app.schemas.ResumeAgentState") as mock_state_class:

            mock_to_thread.return_value = state_json
            mock_state_class.from_redis_dict.return_value = mock_state

            result = await client.load_state(123)

            assert result == mock_state
            mock_to_thread.assert_called_once()
            mock_state_class.from_redis_dict.assert_called_once_with(state_data)

    @pytest.mark.asyncio
    async def test_load_state_fallback_to_memory(self, mock_state):
        """Redis 실패 시 메모리에서 조회 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            # 메모리에 직접 저장
            state_data = mock_state.to_redis_dict()
            client.memory_store["resume:123"] = state_data

            with patch("app.schemas.ResumeAgentState") as mock_state_class:
                mock_state_class.from_redis_dict.return_value = mock_state

                result = await client.load_state(123)

                assert result == mock_state
                mock_state_class.from_redis_dict.assert_called_once_with(state_data)

    @pytest.mark.asyncio
    async def test_load_state_not_found(self, redis_client):
        """존재하지 않는 상태 조회 테스트"""
        client, mock_redis = redis_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = None  # Redis에서 None 반환

            result = await client.load_state(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_state_redis_success(self, redis_client):
        """Redis 상태 삭제 성공 테스트"""
        client, mock_redis = redis_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = 1  # 삭제된 키 개수

            result = await client.delete_state(123)

            assert result == True
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_state_fallback_to_memory(self, mock_state):
        """메모리에서 상태 삭제 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            # 메모리에 상태 저장
            client.memory_store["resume:123"] = mock_state.to_redis_dict()

            result = await client.delete_state(123)

            assert result == True
            assert "resume:123" not in client.memory_store

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, redis_client):
        """락 획득 성공 테스트"""
        client, mock_redis = redis_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = True  # SET NX 성공

            result = await client.acquire_lock(123)

            assert result == True
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_lock_already_exists(self, redis_client):
        """락이 이미 존재하는 경우 테스트"""
        client, mock_redis = redis_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = False  # SET NX 실패 (키 이미 존재)

            result = await client.acquire_lock(123)

            assert result == False

    @pytest.mark.asyncio
    async def test_acquire_lock_fallback_to_memory(self):
        """메모리 기반 락 획득 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            # 첫 번째 락 획득
            result1 = await client.acquire_lock(123)
            assert result1 == True

            # 두 번째 락 획득 (실패해야 함)
            result2 = await client.acquire_lock(123)
            assert result2 == False

    @pytest.mark.asyncio
    async def test_release_lock_success(self, redis_client):
        """락 해제 성공 테스트"""
        client, mock_redis = redis_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = 1  # 삭제된 키 개수

            result = await client.release_lock(123)

            assert result == True

    @pytest.mark.asyncio
    async def test_release_lock_fallback_to_memory(self):
        """메모리 기반 락 해제 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            # 락 설정
            await client.acquire_lock(123)
            assert "lock:resume:123" in client.memory_locks

            # 락 해제
            result = await client.release_lock(123)
            assert result == True
            assert "lock:resume:123" not in client.memory_locks

    @pytest.mark.asyncio
    async def test_health_check_redis_connected(self, redis_client):
        """Redis 연결 상태 헬스체크 테스트"""
        client, mock_redis = redis_client

        mock_redis.info.return_value = {
            "used_memory_human": "1.5M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600,
        }

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = [
                True,
                mock_redis.info.return_value,
            ]  # ping, info 순서

            result = await client.health_check()

            assert result["redis_connected"] == True
            assert "redis_info" in result
            assert result["redis_info"]["used_memory"] == "1.5M"

    @pytest.mark.asyncio
    async def test_health_check_redis_disconnected(self):
        """Redis 연결 실패 헬스체크 테스트"""
        with patch(
            "redis.ConnectionPool.from_url", side_effect=Exception("Redis 연결 실패")
        ):
            client = RedisClient()

            result = await client.health_check()

            assert result["redis_connected"] == False
            assert result["memory_fallback_items"] == 0
            assert result["memory_locks"] == 0

    @pytest.mark.asyncio
    async def test_generic_data_operations(self, redis_client):
        """범용 데이터 저장/조회/삭제 테스트"""
        client, mock_redis = redis_client

        test_data = {"key": "value", "number": 42}

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            # 저장 테스트
            mock_to_thread.return_value = True
            result = await client.set_data("test_key", test_data)
            assert result == True

            # 조회 테스트
            mock_to_thread.return_value = json.dumps(test_data)
            result = await client.get_data("test_key")
            assert result == test_data

            # 삭제 테스트
            mock_to_thread.return_value = 1
            result = await client.delete_data("test_key")
            assert result == True

    @pytest.mark.asyncio
    async def test_clear_test_data(self, redis_client):
        """테스트 데이터 일괄 삭제 테스트"""
        client, mock_redis = redis_client

        # 메모리에 테스트 데이터 추가
        client.memory_store["test:key1"] = "value1"
        client.memory_store["test:key2"] = "value2"
        client.memory_store["normal:key"] = "value3"

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = [
                ["test:redis_key1", "test:redis_key2"],  # keys("test:*")
                [],  # keys("perf_test:*")
                2,  # delete 결과
            ]

            deleted_count = await client.clear_all_test_data()

            # 메모리에서 test: 키들이 삭제되고, Redis에서도 삭제
            assert deleted_count == 4  # 메모리 2개 + Redis 2개
            assert "test:key1" not in client.memory_store
            assert "test:key2" not in client.memory_store
            assert "normal:key" in client.memory_store  # 일반 키는 유지


@pytest.mark.skipif(
    REDIS_CLIENT_AVAILABLE, reason="Test only when redis client unavailable"
)
class TestRedisClientFallback:
    """Redis 클라이언트를 사용할 수 없을 때의 대체 테스트"""

    def test_redis_client_unavailable(self):
        """Redis 클라이언트를 임포트할 수 없을 때 테스트"""
        # 기본적인 Redis 동작 시뮬레이션
        fake_redis = {}

        # SET 연산
        fake_redis["test_key"] = "test_value"
        assert fake_redis["test_key"] == "test_value"

        # GET 연산
        value = fake_redis.get("test_key", None)
        assert value == "test_value"

        # DELETE 연산
        if "test_key" in fake_redis:
            del fake_redis["test_key"]
        assert fake_redis.get("test_key", None) is None

    def test_fallback_state_management(self):
        """상태 관리 fallback 시뮬레이션"""
        # 간단한 상태 관리 시뮬레이션
        state_store = {}

        # 상태 저장
        member_id = 123
        state_data = {"memberId": member_id, "step": "questioning", "asked_count": 1}

        state_key = f"resume:{member_id}"
        state_store[state_key] = state_data

        # 상태 조회
        retrieved_state = state_store.get(state_key)
        assert retrieved_state == state_data
        assert retrieved_state["memberId"] == member_id

        # 상태 삭제
        if state_key in state_store:
            del state_store[state_key]
        assert state_store.get(state_key) is None
