#!/bin/bash

# 사용법 함수
usage() {
    echo "사용법: $0 [옵션]"
    echo "옵션:"
    echo "  unit        - 단위 테스트만 실행"
    echo "  integration - 통합 테스트만 실행"
    echo "  smoke       - 스모크 테스트만 실행"
    echo "  fast        - 빠른 테스트만 실행 (slow 마커 제외)"
    echo "  coverage    - 전체 커버리지 측정"
    echo "  schemas     - 스키마 테스트만 실행"
    echo "  routes      - 라우트 테스트만 실행"
    echo "  services    - 서비스 테스트만 실행"
    echo "  all         - 모든 테스트 실행 (기본값)"
    exit 1
}

# 기본값 설정
TEST_TYPE=${1:-"all"}

echo "🧪 테스트 타입: $TEST_TYPE"

case $TEST_TYPE in
    "unit")
        echo "📝 단위 테스트 실행 중..."
        pytest tests/unit/ tests/schemas/ -v --cov=app --cov-report=term-missing
        ;;
    "integration")
        echo "🔗 통합 테스트 실행 중..."
        pytest tests/integration/ -v --cov=app --cov-report=term-missing
        ;;
    "smoke")
        echo "💨 스모크 테스트 실행 중..."
        pytest -m smoke -v
        ;;
    "fast")
        echo "⚡ 빠른 테스트 실행 중..."
        pytest -m "not slow" -v --cov=app --cov-report=term-missing
        ;;
    "coverage")
        echo "📊 전체 커버리지 측정 중..."
        ./scripts/run_coverage.sh
        ;;
    "schemas")
        echo "📋 스키마 테스트 실행 중..."
        pytest tests/schemas/ -v --cov=app.schemas --cov-report=term-missing
        ;;
    "routes")
        echo "🛣️  라우트 테스트 실행 중..."
        pytest tests/integration/test_*_routes.py -v --cov=app.routes --cov-report=term-missing
        ;;
    "services")
        echo "⚙️  서비스 테스트 실행 중..."
        pytest tests/unit/ -k "service" -v --cov=app.services --cov-report=term-missing
        ;;
    "all"|*)
        echo "🎯 모든 테스트 실행 중..."
        pytest -v --cov=app --cov-report=term-missing
        ;;
esac

echo "✅ 테스트 완료!"
