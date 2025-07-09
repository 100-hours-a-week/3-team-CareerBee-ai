# fastapi_project/test_redis_connection.py

"""
Redis 연결 및 기본 기능 테스트 스크립트
"""
import asyncio
import json
from datetime import datetime
from app.utils.redis_client import get_redis_client
from app.schemas import ResumeAgentState, BaseInputsModel


async def test_redis_connection():
    """Redis 기본 연결 및 기능 테스트"""
    print("🚀 Redis 연결 테스트 시작...")

    redis_client = get_redis_client()

    # 1. 기본 연결 테스트
    print("\n1. Redis 기본 연결 테스트")
    try:
        health = await redis_client.health_check()
        print(f"✅ Redis 헬스체크: {health}")
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        return False

    # 2. 기본 SET/GET 테스트
    print("\n2. 기본 SET/GET 테스트")
    try:
        test_key = "test:connection"
        test_value = {"message": "hello", "timestamp": datetime.now().isoformat()}

        # SET 테스트
        await redis_client.set_data(test_key, test_value)
        print(f"✅ SET 성공: {test_key} = {test_value}")

        # GET 테스트
        retrieved = await redis_client.get_data(test_key)
        print(f"✅ GET 성공: {retrieved}")

        # 데이터 일치 확인
        if retrieved == test_value:
            print("✅ 데이터 일치 확인됨")
        else:
            print("❌ 데이터 불일치")
            return False

        # 정리
        await redis_client.delete_data(test_key)
        print("✅ 테스트 데이터 정리 완료")

    except Exception as e:
        print(f"❌ 기본 SET/GET 테스트 실패: {e}")
        return False

    # 3. ResumeAgentState 저장/로드 테스트
    print("\n3. ResumeAgentState 저장/로드 테스트")
    try:
        member_id = 999  # 테스트용 ID

        # 테스트용 입력 데이터 생성
        test_inputs = BaseInputsModel(
            email="test@example.com",
            preferred_job="백엔드 개발자",
            certification_count=2,
            project_count=3,
            major_type="MAJOR",
            company_name="테스트 회사",
            position="주니어 개발자",
            work_period=12,
            additional_experiences="Python, FastAPI, Redis 테스트",  # 문자열로 수정
        )

        # 초기 상태 생성
        from app.schemas import create_initial_state

        initial_state = create_initial_state(member_id=member_id, inputs=test_inputs)
        initial_state.pending_questions = ["첫 번째 테스트 질문입니다."]
        initial_state.step = "questioning"

        print(f"📝 테스트 상태 생성: member_id={member_id}")

        # 상태 저장
        save_success = await redis_client.save_state(member_id, initial_state)
        if save_success:
            print("✅ 상태 저장 성공")
        else:
            print("❌ 상태 저장 실패")
            return False

        # 상태 로드
        loaded_state = await redis_client.load_state(member_id)
        if loaded_state:
            print("✅ 상태 로드 성공")
            print(f"   - member_id: {loaded_state.member_id}")
            print(f"   - step: {loaded_state.step}")
            print(f"   - pending_questions: {loaded_state.pending_questions}")
            print(f"   - inputs.email: {loaded_state.inputs.email}")
        else:
            print("❌ 상태 로드 실패")
            return False

        # 데이터 검증
        if (
            loaded_state.member_id == member_id
            and loaded_state.step == "questioning"
            and loaded_state.inputs.email == "test@example.com"
        ):
            print("✅ 상태 데이터 검증 성공")
        else:
            print("❌ 상태 데이터 검증 실패")
            return False

        # 상태 삭제
        delete_success = await redis_client.delete_state(member_id)
        if delete_success:
            print("✅ 상태 삭제 성공")
        else:
            print("❌ 상태 삭제 실패")
            return False

        # 삭제 확인
        deleted_state = await redis_client.load_state(member_id)
        if deleted_state is None:
            print("✅ 상태 삭제 확인됨")
        else:
            print("❌ 상태가 완전히 삭제되지 않음")
            return False

    except Exception as e:
        print(f"❌ ResumeAgentState 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 4. 락(Lock) 기능 테스트
    print("\n4. 락(Lock) 기능 테스트")
    try:
        test_member_id = 888

        # 락 획득
        lock_acquired = await redis_client.acquire_lock(test_member_id)
        if lock_acquired:
            print("✅ 락 획득 성공")
        else:
            print("❌ 락 획득 실패")
            return False

        # 중복 락 시도 (실패해야 정상)
        duplicate_lock = await redis_client.acquire_lock(test_member_id)
        if not duplicate_lock:
            print("✅ 중복 락 방지 확인")
        else:
            print("❌ 중복 락이 허용됨 (문제)")
            return False

        # 락 해제
        await redis_client.release_lock(test_member_id)
        print("✅ 락 해제 완료")

        # 락 해제 후 재획득 (성공해야 정상)
        lock_reacquired = await redis_client.acquire_lock(test_member_id)
        if lock_reacquired:
            print("✅ 락 해제 후 재획득 성공")
            await redis_client.release_lock(test_member_id)
        else:
            print("❌ 락 해제 후 재획득 실패")
            return False

    except Exception as e:
        print(f"❌ 락 기능 테스트 실패: {e}")
        return False

    print("\n🎉 모든 Redis 테스트 통과!")
    return True


async def test_redis_performance():
    """Redis 성능 간단 테스트"""
    print("\n📊 Redis 성능 테스트...")

    redis_client = get_redis_client()

    # 연속 저장/로드 테스트
    import time

    start_time = time.time()

    for i in range(10):
        test_data = {"iteration": i, "timestamp": datetime.now().isoformat()}
        await redis_client.set_data(f"perf_test:{i}", test_data)
        retrieved = await redis_client.get_data(f"perf_test:{i}")
        await redis_client.delete_data(f"perf_test:{i}")

    end_time = time.time()
    duration = end_time - start_time

    print(f"✅ 10회 SET/GET/DELETE: {duration:.3f}초 (평균 {duration/10:.3f}초/회)")


if __name__ == "__main__":

    async def main():
        success = await test_redis_connection()
        if success:
            await test_redis_performance()
        else:
            print("\n❌ 기본 테스트 실패로 성능 테스트 건너뜀")

    asyncio.run(main())
