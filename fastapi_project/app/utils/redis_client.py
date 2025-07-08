# app/utils/redis_client.py
import redis
import asyncio
import json
import logging
from typing import Optional, Dict, Any
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 클라이언트 wrapper class"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.state_ttl = int(os.getenv("REDIS_STATE_TTL", "86400"))  # 24시간
        self.lock_ttl = int(os.getenv("REDIS_LOCK_TTL", "30"))  # 30초

        # Redis 연결 풀 생성
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # 연결 테스트
            self.redis_client.ping()
            logger.info(f"Redis 연결 성공: {self.redis_url}")

        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            self.redis_client = None

        # 메모리 기반 fallback
        self.memory_store: Dict[str, Any] = {}
        self.memory_locks: Dict[str, datetime] = {}

    def _get_state_key(self, member_id: int) -> str:
        """상태 저장용 Redis 키 생성"""
        return f"resume:{member_id}"

    def _get_lock_key(self, member_id: int) -> str:
        """락용 Redis 키 생성"""
        return f"lock:resume:{member_id}"

    # =============================================================================
    # 상태 관리 메서드들 (ResumeAgentState 전용)
    # =============================================================================

    async def save_state(self, member_id: int, state: "ResumeAgentState") -> bool:
        """상태 저장"""
        state_key = self._get_state_key(member_id)

        try:
            # ResumeAgentState를 Redis용 dict로 변환
            state_dict = state.to_redis_dict()
            # default=str 추가로 datetime 등 직렬화 불가능한 객체를 문자열로 변환
            state_json = json.dumps(state_dict, ensure_ascii=False, default=str)

            if self.redis_client:
                try:
                    await asyncio.to_thread(
                        self.redis_client.setex, state_key, self.state_ttl, state_json
                    )
                    logger.info(f"Redis에 상태 저장 완료: {state_key}")
                    return True
                except Exception as e:
                    logger.error(f"Redis 상태 저장 실패: {e}")
                    # fallback to memory
                    pass

            # 메모리 기반 저장 (fallback)
            self.memory_store[state_key] = state_dict
            logger.warning(f"메모리에 상태 저장 (fallback): {state_key}")
            return True

        except Exception as e:
            logger.error(f"상태 저장 실패: {e}")
            # 디버깅을 위한 추가 정보
            logger.error(f"저장하려던 상태: member_id={member_id}")
            logger.error(f"상태 타입: {type(state)}")
            import traceback

            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return False

    async def load_state(self, member_id: int) -> Optional["ResumeAgentState"]:
        """상태 조회"""
        state_key = self._get_state_key(member_id)

        try:
            if self.redis_client:
                try:
                    state_json = await asyncio.to_thread(
                        self.redis_client.get, state_key
                    )
                    if state_json:
                        state_data = json.loads(state_json)
                        logger.info(f"Redis에서 상태 조회 완료: {state_key}")

                        # dict를 ResumeAgentState로 변환
                        from app.schemas import ResumeAgentState

                        return ResumeAgentState.from_redis_dict(state_data)

                except Exception as e:
                    logger.error(f"Redis 상태 조회 실패: {e}")

            # 메모리 기반 조회 (fallback)
            if state_key in self.memory_store:
                state_data = self.memory_store[state_key]
                logger.warning(f"메모리에서 상태 조회 (fallback): {state_key}")

                # dict를 ResumeAgentState로 변환
                from app.schemas import ResumeAgentState

                return ResumeAgentState.from_redis_dict(state_data)

            return None

        except Exception as e:
            logger.error(f"상태 조회 실패: {e}")
            return None

    async def delete_state(self, member_id: int) -> bool:
        """상태 삭제"""
        state_key = self._get_state_key(member_id)

        try:
            deleted = False

            if self.redis_client:
                try:
                    result = await asyncio.to_thread(
                        self.redis_client.delete, state_key
                    )
                    deleted = bool(result)
                    logger.info(f"Redis에서 상태 삭제 완료: {state_key}")
                except Exception as e:
                    logger.error(f"Redis 상태 삭제 실패: {e}")

            # 메모리에서도 삭제 (fallback)
            if state_key in self.memory_store:
                del self.memory_store[state_key]
                deleted = True
                logger.warning(f"메모리에서 상태 삭제 (fallback): {state_key}")

            return deleted

        except Exception as e:
            logger.error(f"상태 삭제 실패: {e}")
            return False

    # =============================================================================
    # 범용 데이터 저장 메서드들 (테스트용)
    # =============================================================================

    async def set_data(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """범용 데이터 저장"""
        try:
            value_json = json.dumps(value, ensure_ascii=False)
            ttl = ttl or self.state_ttl

            if self.redis_client:
                try:
                    await asyncio.to_thread(
                        self.redis_client.setex, key, ttl, value_json
                    )
                    logger.debug(f"Redis에 데이터 저장: {key}")
                    return True
                except Exception as e:
                    logger.error(f"Redis 데이터 저장 실패: {e}")

            # 메모리 기반 저장 (fallback)
            self.memory_store[key] = value
            logger.debug(f"메모리에 데이터 저장 (fallback): {key}")
            return True

        except Exception as e:
            logger.error(f"데이터 저장 실패: {e}")
            return False

    async def get_data(self, key: str) -> Optional[Any]:
        """범용 데이터 조회"""
        try:
            if self.redis_client:
                try:
                    value_json = await asyncio.to_thread(self.redis_client.get, key)
                    if value_json:
                        logger.debug(f"Redis에서 데이터 조회: {key}")
                        return json.loads(value_json)
                except Exception as e:
                    logger.error(f"Redis 데이터 조회 실패: {e}")

            # 메모리 기반 조회 (fallback)
            if key in self.memory_store:
                logger.debug(f"메모리에서 데이터 조회 (fallback): {key}")
                return self.memory_store[key]

            return None

        except Exception as e:
            logger.error(f"데이터 조회 실패: {e}")
            return None

    async def delete_data(self, key: str) -> bool:
        """범용 데이터 삭제"""
        try:
            deleted = False

            if self.redis_client:
                try:
                    result = await asyncio.to_thread(self.redis_client.delete, key)
                    deleted = bool(result)
                    logger.debug(f"Redis에서 데이터 삭제: {key}")
                except Exception as e:
                    logger.error(f"Redis 데이터 삭제 실패: {e}")

            # 메모리에서도 삭제 (fallback)
            if key in self.memory_store:
                del self.memory_store[key]
                deleted = True
                logger.debug(f"메모리에서 데이터 삭제 (fallback): {key}")

            return deleted

        except Exception as e:
            logger.error(f"데이터 삭제 실패: {e}")
            return False

    # =============================================================================
    # 락 (동시성 제어) 메서드들
    # =============================================================================

    async def acquire_lock(self, member_id: int, timeout: Optional[int] = None) -> bool:
        """락 획득"""
        lock_key = self._get_lock_key(member_id)
        lock_value = f"lock:{member_id}:{datetime.now().isoformat()}"
        timeout = timeout or self.lock_ttl

        try:
            if self.redis_client:
                try:
                    # Redis의 SET NX EX 명령 사용 (원자적 연산)
                    result = await asyncio.to_thread(
                        self.redis_client.set,
                        lock_key,
                        lock_value,
                        nx=True,  # key가 존재하지 않을 때만 설정
                        ex=timeout,  # 만료 시간 설정
                    )
                    if result:
                        logger.debug(f"Redis 락 획득 성공: {lock_key}")
                        return True
                    else:
                        logger.debug(f"Redis 락 이미 존재: {lock_key}")
                        return False
                except Exception as e:
                    logger.error(f"Redis 락 획득 실패: {e}")

            # 메모리 기반 락 (fallback)
            current_time = datetime.now()

            # 기존 락 만료 확인
            if lock_key in self.memory_locks:
                lock_time = self.memory_locks[lock_key]
                if current_time - lock_time > timedelta(seconds=timeout):
                    # 만료된 락 제거
                    del self.memory_locks[lock_key]

            # 락 획득 시도
            if lock_key not in self.memory_locks:
                self.memory_locks[lock_key] = current_time
                logger.debug(f"메모리 락 획득 성공 (fallback): {lock_key}")
                return True
            else:
                logger.debug(f"메모리 락 이미 존재 (fallback): {lock_key}")
                return False

        except Exception as e:
            logger.error(f"락 획득 실패: {e}")
            return False

    async def release_lock(self, member_id: int) -> bool:
        """락 해제"""
        lock_key = self._get_lock_key(member_id)

        try:
            released = False

            if self.redis_client:
                try:
                    result = await asyncio.to_thread(self.redis_client.delete, lock_key)
                    released = bool(result)
                    logger.debug(f"Redis 락 해제: {lock_key}")
                except Exception as e:
                    logger.error(f"Redis 락 해제 실패: {e}")

            # 메모리 락 해제 (fallback)
            if lock_key in self.memory_locks:
                del self.memory_locks[lock_key]
                released = True
                logger.debug(f"메모리 락 해제 (fallback): {lock_key}")

            return released

        except Exception as e:
            logger.error(f"락 해제 실패: {e}")
            return False

    # =============================================================================
    # 헬스체크 및 유틸리티 메서드들
    # =============================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Redis 연결 상태 확인"""
        result = {
            "redis_connected": False,
            "memory_fallback_items": len(self.memory_store),
            "memory_locks": len(self.memory_locks),
            "redis_url": self.redis_url,
        }

        if self.redis_client:
            try:
                await asyncio.to_thread(self.redis_client.ping)
                result["redis_connected"] = True

                # Redis 정보 추가
                try:
                    info = await asyncio.to_thread(self.redis_client.info)
                    result["redis_info"] = {
                        "used_memory": info.get("used_memory_human", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                        "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                    }
                except:
                    pass

            except Exception as e:
                logger.error(f"Redis 헬스체크 실패: {e}")
                result["redis_error"] = str(e)

        return result

    async def clear_all_test_data(self) -> int:
        """테스트 데이터 일괄 삭제 (개발용)"""
        deleted_count = 0

        # 메모리 저장소에서 테스트 데이터 삭제
        test_keys = [
            key
            for key in self.memory_store.keys()
            if key.startswith(("test:", "perf_test:"))
        ]
        for key in test_keys:
            del self.memory_store[key]
            deleted_count += 1

        # Redis에서 테스트 데이터 삭제
        if self.redis_client:
            try:
                # 패턴 매칭으로 키 찾기
                test_keys = await asyncio.to_thread(self.redis_client.keys, "test:*")
                perf_keys = await asyncio.to_thread(
                    self.redis_client.keys, "perf_test:*"
                )

                all_test_keys = test_keys + perf_keys
                if all_test_keys:
                    result = await asyncio.to_thread(
                        self.redis_client.delete, *all_test_keys
                    )
                    deleted_count += result

            except Exception as e:
                logger.error(f"Redis 테스트 데이터 삭제 실패: {e}")

        logger.info(f"테스트 데이터 {deleted_count}개 삭제 완료")
        return deleted_count


# 싱글톤 인스턴스
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Redis 클라이언트 싱글톤 인스턴스 반환"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
