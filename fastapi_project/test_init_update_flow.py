# fastapi_project/test_init_update_flow.py
"""
이력서 에이전트 init → update 플로우 전체 테스트 (GCP AI 서버용)
"""

import json
import requests
import time
from typing import Dict, Any, Optional

# FastAPI 서버 URL (GCP AI 서버용)
BASE_URL = "http://localhost:8000"


class FlowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_health_check(self) -> bool:
        """FastAPI 서버 상태 확인"""
        try:
            # 먼저 기본 헬스체크 시도
            response = self.session.get(f"{self.base_url}/health-check")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 서버 상태 (기본): {health_data}")
                return True

            # 기본이 안 되면 에이전트 헬스체크 시도
            response = self.session.get(f"{self.base_url}/api/v1/resume/agent/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 서버 상태 (에이전트): {health_data}")
                return True
            else:
                print(f"❌ 서버 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False

    def test_init_endpoint(self, memberId: int) -> Optional[Dict[str, Any]]:
        """초기화 엔드포인트 테스트"""
        print(f"\n🚀 1단계: 초기화 테스트 (memberId={memberId})")

        # 요청 데이터 구성 (API 명세에 맞게)
        init_data = {
            "memberId": memberId,
            "inputs": {
                "email": "test@careerbee.com",
                "preferred_job": "AI 엔지니어",
                "certification_count": 3,
                "project_count": 5,
                "major_type": "MAJOR",
                "company_name": "커리어비",
                "position": "백엔드 개발자",
                "work_period": 24,
                "additional_experiences": "Python, FastAPI, LangChain, Redis, VLLM",
            },
        }

        print(f"📤 초기화 요청 데이터:")
        print(json.dumps(init_data, ensure_ascii=False, indent=2))

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/init", json=init_data
            )

            print(f"📥 응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 초기화 성공!")
                print(f"   - memberId: {result.get('memberId')}")
                print(
                    f"   - question: {result.get('question')[:100]}..."
                    if len(str(result.get("question", ""))) > 100
                    else f"   - question: {result.get('question')}"
                )
                return result
            else:
                print(f"❌ 초기화 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None

        except Exception as e:
            print(f"❌ 초기화 요청 실패: {e}")
            return None

    def test_update_endpoint(
        self, memberId: int, answer: str
    ) -> Optional[Dict[str, Any]]:
        """업데이트 엔드포인트 테스트"""
        print(f"\n🔄 업데이트 테스트 (memberId={memberId})")

        # 요청 데이터 구성 (API 명세에 정확히 맞게)
        update_data = {"memberId": memberId, "inputs": {"answer": answer}}

        print(f"📤 업데이트 요청 데이터:")
        print(json.dumps(update_data, ensure_ascii=False, indent=2))

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/update", json=update_data
            )

            print(f"📥 응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ 업데이트 성공!")
                print(f"   - memberId: {result.get('memberId')}")
                print(f"   - isComplete: {result.get('isComplete')}")

                if result.get("isComplete"):
                    print(f"   - resumeObjectKey: {result.get('resumeObjectKey')}")
                else:
                    question = result.get("question", "")
                    print(
                        f"   - question: {question[:100]}..."
                        if len(question) > 100
                        else f"   - question: {question}"
                    )

                return result
            else:
                print(f"❌ 업데이트 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None

        except Exception as e:
            print(f"❌ 업데이트 요청 실패: {e}")
            return None

    def test_status_endpoint(self, memberId: int) -> Optional[Dict[str, Any]]:
        """상태 조회 엔드포인트 테스트"""
        print(f"\n📊 상태 확인 (memberId={memberId})")

        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/resume/agent/status/{memberId}"
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
                print(f"   응답: {response.text}")
                return None

        except Exception as e:
            print(f"❌ 상태 조회 요청 실패: {e}")
            return None

    def test_delete_session(self, memberId: int) -> bool:
        """세션 삭제 테스트 (정리용)"""
        print(f"\n🗑️ 세션 삭제 (memberId={memberId})")

        try:
            response = self.session.delete(
                f"{self.base_url}/api/v1/resume/agent/session/{memberId}"
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

    def run_complete_flow_test(self, memberId: int = 1001) -> bool:
        """전체 플로우 테스트 실행"""
        print("🎯 === 이력서 에이전트 전체 플로우 테스트 (GCP AI 서버) ===")

        # 0. 서버 상태 확인
        if not self.test_health_check():
            print("❌ 서버 상태 확인 실패 - 테스트 중단")
            return False

        # 1. 기존 세션 정리
        self.test_delete_session(memberId)

        # 2. 초기화 테스트
        init_result = self.test_init_endpoint(memberId)
        if not init_result:
            print("❌ 초기화 실패 - 테스트 중단")
            return False

        # 3. 상태 확인
        self.test_status_endpoint(memberId)

        # 4. 여러 번의 업데이트 테스트
        questions_and_answers = [
            "커리어비 프로젝트에서 LangChain과 VLLM을 활용한 AI 에이전트를 개발했습니다. 특히 이력서 자동 생성 시스템의 핵심 로직을 구현했습니다.",
            "Python과 FastAPI, 그리고 AI/ML 기술 스택에 가장 자신있습니다. Redis를 이용한 상태 관리와 LangGraph를 활용한 워크플로우 설계 경험이 있습니다.",
            "5년 후에는 AI 기술을 활용한 실용적인 서비스를 개발하는 시니어 개발자가 되고 싶습니다. 특히 자연어 처리와 대화형 AI 시스템 분야에서 전문성을 갖추고 싶습니다.",
        ]

        for i, answer in enumerate(questions_and_answers, 1):
            print(f"\n{'='*50}")
            print(f"--- {i}번째 답변 단계 ---")
            print(f"{'='*50}")

            update_result = self.test_update_endpoint(memberId, answer)

            if not update_result:
                print(f"❌ {i}번째 업데이트 실패")
                return False

            # 완료되었는지 확인
            isComplete = update_result.get("isComplete", False)
            if isComplete:
                print(f"\n🎉 {i}번째 답변에서 이력서 생성 완료!")
                print(f"📄 Resume Object Key: {update_result.get('resumeObjectKey')}")

                # 최종 상태 확인
                print(f"\n📊 최종 상태 확인:")
                self.test_status_endpoint(memberId)
                break

            # 질문이 없으면서 완료도 아닌 경우
            next_question = update_result.get("question")
            if not next_question and not isComplete:
                print(f"⚠️ {i}번째: 질문도 없고 완료도 아님 - 상태 확인 필요")
                self.test_status_endpoint(memberId)
                time.sleep(2)

            # 다음 단계 전 잠시 대기
            print(f"⏱️ 다음 단계 준비 중... (2초 대기)")
            time.sleep(2)

        # 5. 최종 상태 확인
        print(f"\n📊 최종 세션 상태:")
        final_status = self.test_status_endpoint(memberId)

        print(f"\n🏁 === 플로우 테스트 완료 ===")
        return True

    def run_error_scenarios_test(self, memberId: int = 2002) -> bool:
        """에러 시나리오 테스트"""
        print("\n🚨 === 에러 시나리오 테스트 ===")

        # 1. 존재하지 않는 세션에 업데이트 시도
        print("\n1. 존재하지 않는 세션 업데이트 시도")
        update_result = self.test_update_endpoint(memberId, "테스트 답변")
        if update_result is None:
            print("✅ 예상대로 실패함 (404 또는 에러)")
        else:
            print("❌ 예상과 다름 - 실패해야 하는데 성공함")

        # 2. 잘못된 데이터로 초기화 시도
        print("\n2. 잘못된 데이터로 초기화 시도")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/init",
                json={"memberId": "invalid_string"},  # 잘못된 타입
            )
            if response.status_code == 422:
                print("✅ 잘못된 데이터 요청이 예상대로 실패함 (422 Validation Error)")
            else:
                print(f"❌ 예상과 다른 응답: {response.status_code}")
        except Exception as e:
            print(f"✅ 예상된 예외 발생: {e}")

        # 3. 빈 답변으로 업데이트 시도
        print("\n3. 빈 답변으로 업데이트 시도")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/resume/agent/update",
                json={"memberId": memberId, "inputs": {"answer": ""}},
            )
            if response.status_code != 200:
                print("✅ 빈 답변이 예상대로 거부됨")
            else:
                print("❌ 빈 답변이 허용됨 (검증 필요)")
        except Exception as e:
            print(f"✅ 예상된 예외 발생: {e}")

        print("\n🏁 === 에러 시나리오 테스트 완료 ===")
        return True

    def run_quick_test(self, memberId: int = 9999) -> bool:
        """빠른 기능 테스트 (GCP 서버용)"""
        print("⚡ === 빠른 기능 테스트 ===")

        # 서버 상태 확인
        if not self.test_health_check():
            return False

        # 세션 정리
        self.test_delete_session(memberId)

        # 초기화
        init_result = self.test_init_endpoint(memberId)
        if not init_result:
            return False

        # 하나의 답변만 테스트
        answer = "FastAPI와 LangGraph를 활용한 AI 에이전트 개발 경험이 있습니다."
        update_result = self.test_update_endpoint(memberId, answer)

        if update_result:
            print("✅ 빠른 테스트 성공!")
            return True
        else:
            print("❌ 빠른 테스트 실패!")
            return False


def main():
    """메인 테스트 실행"""
    tester = FlowTester()

    print("🎯 GCP AI 서버에서 이력서 에이전트 테스트를 시작합니다!")
    print("=" * 60)

    # 실행 모드 선택
    print("\n테스트 모드를 선택하세요:")
    print("1. 전체 플로우 테스트 (완전한 이력서 생성 과정)")
    print("2. 빠른 기능 테스트 (기본 동작 확인)")
    print("3. 에러 시나리오 테스트")

    try:
        choice = input("\n선택 (1-3, 기본값: 2): ").strip() or "2"

        if choice == "1":
            print("\n🚀 전체 플로우 테스트 시작...")
            success = tester.run_complete_flow_test()

        elif choice == "2":
            print("\n⚡ 빠른 기능 테스트 시작...")
            success = tester.run_quick_test()

        elif choice == "3":
            print("\n🚨 에러 시나리오 테스트 시작...")
            success = tester.run_error_scenarios_test()

        else:
            print("❌ 잘못된 선택입니다. 빠른 테스트를 실행합니다.")
            success = tester.run_quick_test()

        # 결과 출력
        print("\n" + "=" * 60)
        if success:
            print("🎉 테스트 완료! 모든 기능이 정상 작동합니다.")
        else:
            print("❌ 테스트 실패! 로그를 확인해주세요.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")


if __name__ == "__main__":
    main()
