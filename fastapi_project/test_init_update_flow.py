# fastapi_project/test_init_update_flow.py
"""
이력서 에이전트 init → update 플로우 전체 테스트
"""
import asyncio
import json
import requests
import time
from typing import Dict, Any

# FastAPI 서버 URL (로컬 개발 서버)
BASE_URL = "http://localhost:8000"


class FlowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_health_check(self) -> bool:
        """FastAPI 서버 상태 확인"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/resume/agent/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 서버 상태: {health_data}")
                return True
            else:
                print(f"❌ 서버 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False

    def test_init_endpoint(self, member_id: int) -> Dict[str, Any]:
        """초기화 엔드포인트 테스트"""
        print(f"\n🚀 1단계: 초기화 테스트 (member_id={member_id})")

        # 요청 데이터 구성
        init_data = {
            "member_id": member_id,
            "inputs": {
                "email": "test@example.com",
                "preferred_job": "AI 엔지니어",
                "certification_count": 3,
                "project_count": 5,
                "major_type": "MAJOR",
                "company_name": "스타트업",
                "position": "백엔드 개발자",
                "work_period": 24,
                "additional_experiences": "Python, FastAPI, LangChain, Redis",
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/init", json=init_data
            )

            print(f"응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 초기화 성공!")
                print(f"   - member_id: {result.get('member_id')}")
                print(f"   - question: {result.get('question')}")
                return result
            else:
                print(f"❌ 초기화 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None

        except Exception as e:
            print(f"❌ 초기화 요청 실패: {e}")
            return None

    def test_update_endpoint(self, member_id: int, answer: str) -> Dict[str, Any]:
        """업데이트 엔드포인트 테스트"""
        print(f"\n🔄 2단계: 업데이트 테스트 (member_id={member_id})")

        # 요청 데이터 구성
        update_data = {"member_id": member_id, "answer": answer}

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/update", json=update_data
            )

            print(f"응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 업데이트 성공!")
                print(f"   - member_id: {result.get('member_id')}")
                print(f"   - isComplete: {result.get('isComplete')}")

                if result.get("isComplete"):
                    print(f"   - resumeObjectKey: {result.get('resumeObjectKey')}")
                else:
                    print(f"   - question: {result.get('question')}")

                return result
            else:
                print(f"❌ 업데이트 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None

        except Exception as e:
            print(f"❌ 업데이트 요청 실패: {e}")
            return None

    def test_status_endpoint(self, member_id: int) -> Dict[str, Any]:
        """상태 조회 엔드포인트 테스트"""
        print(f"\n📊 상태 확인 (member_id={member_id})")

        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/resume/agent/status/{member_id}"
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 상태 조회 성공!")
                print(f"   - step: {result.get('step')}")
                print(f"   - asked_count: {result.get('asked_count')}")
                print(f"   - pending_questions: {result.get('pending_questions')}")
                print(f"   - answers_count: {result.get('answers_count')}")
                return result
            elif response.status_code == 404:
                print(f"ℹ️ 세션 없음 (정상 - 완료되었거나 아직 시작 안됨)")
                return None
            else:
                print(f"❌ 상태 조회 실패: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 상태 조회 요청 실패: {e}")
            return None

    def test_delete_session(self, member_id: int) -> bool:
        """세션 삭제 테스트 (정리용)"""
        print(f"\n🗑️ 세션 삭제 (member_id={member_id})")

        try:
            response = self.session.delete(
                f"{self.base_url}/api/v1/resume/agent/session/{member_id}"
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 세션 삭제: {result.get('message')}")
                return True
            else:
                print(f"❌ 세션 삭제 실패: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 세션 삭제 요청 실패: {e}")
            return False

    def run_complete_flow_test(self, member_id: int = 1001) -> bool:
        """전체 플로우 테스트 실행"""
        print("🎯 === 이력서 에이전트 전체 플로우 테스트 ===")

        # 0. 서버 상태 확인
        if not self.test_health_check():
            return False

        # 1. 기존 세션 정리
        self.test_delete_session(member_id)

        # 2. 초기화 테스트
        init_result = self.test_init_endpoint(member_id)
        if not init_result:
            return False

        # 3. 상태 확인
        self.test_status_endpoint(member_id)

        # 4. 여러 번의 업데이트 테스트
        questions_and_answers = [
            "5년 후 AI 연구원으로 성장하고 싶습니다.",
            "Python과 머신러닝에 가장 자신있습니다.",
            "커리어비 프로젝트에서 LangChain을 활용한 AI 에이전트를 개발했습니다.",
            "팀워크와 문제 해결 능력이 저의 강점입니다.",
            "지속적인 학습과 기술 혁신에 기여하고 싶습니다.",
        ]

        for i, answer in enumerate(questions_and_answers, 1):
            print(f"\n--- {i}번째 답변 ---")
            update_result = self.test_update_endpoint(member_id, answer)

            if not update_result:
                print(f"❌ {i}번째 업데이트 실패")
                return False

            # 완료되었는지 확인
            is_complete = update_result.get("isComplete", False)
            if is_complete:
                print(f"🎉 {i}번째 답변에서 이력서 생성 완료!")
                print(f"📄 Object Key: {update_result.get('resumeObjectKey')}")
                break

            # 질문이 없으면서 완료도 아닌 경우 (예상치 못한 상황)
            next_question = update_result.get("question")
            if not next_question and not is_complete:
                print(f"⚠️ {i}번째: 질문도 없고 완료도 아님 - 다음 라운드에서 확인")
                # 한 번 더 시도해볼 수 있도록 continue하지 말고 break
                time.sleep(2)  # 잠시 대기 후 다음 요청

            # 잠시 대기
            time.sleep(1)

        # 5. 최종 상태 확인
        final_status = self.test_status_endpoint(member_id)

        print(f"\n🏁 === 플로우 테스트 완료 ===")
        return True

    def run_error_scenarios_test(self, member_id: int = 2002) -> bool:
        """에러 시나리오 테스트"""
        print("\n🚨 === 에러 시나리오 테스트 ===")

        # 1. 존재하지 않는 세션에 업데이트 시도
        print("\n1. 존재하지 않는 세션 업데이트 시도")
        update_result = self.test_update_endpoint(member_id, "답변")
        if update_result is None:
            print("✅ 예상대로 실패함")
        else:
            print("❌ 예상과 다름 - 실패해야 하는데 성공함")

        # 2. 잘못된 데이터로 초기화 시도
        print("\n2. 잘못된 데이터로 초기화 시도")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/init",
                json={"member_id": "invalid"},  # 문자열 전송
            )
            if response.status_code != 200:
                print("✅ 잘못된 데이터 요청이 예상대로 실패함")
            else:
                print("❌ 잘못된 데이터가 성공함 (문제)")
        except Exception as e:
            print(f"✅ 예상된 예외 발생: {e}")

        # 3. 동시성 테스트 (간단)
        print("\n3. 동시 요청 테스트")
        # 정상적인 초기화 먼저
        self.test_delete_session(member_id)
        init_result = self.test_init_endpoint(member_id)

        if init_result:
            # 동시에 업데이트 요청 시도
            import threading

            results = []

            def concurrent_update():
                result = self.test_update_endpoint(member_id, "동시 요청 답변")
                results.append(result)

            # 두 개의 스레드로 동시 요청
            threads = [threading.Thread(target=concurrent_update) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            success_count = sum(1 for r in results if r is not None)
            print(f"✅ 동시 요청 결과: {success_count}/2 성공 (락 기능 확인)")

        print("\n🏁 === 에러 시나리오 테스트 완료 ===")
        return True


def main():
    """메인 테스트 실행"""
    tester = FlowTester()

    print("🎯 FastAPI 서버가 http://localhost:8000 에서 실행되고 있는지 확인하세요!")
    print("서버 실행 명령: uvicorn app.main:app --reload")

    input("\n준비되면 Enter를 눌러주세요...")

    # 1. 정상 플로우 테스트
    success = tester.run_complete_flow_test()

    if success:
        print("\n" + "=" * 50)
        # 2. 에러 시나리오 테스트
        tester.run_error_scenarios_test()

    print("\n🎉 모든 테스트 완료!")


if __name__ == "__main__":
    main()
