#!/bin/bash

echo "🚀 테스트 커버리지 측정을 시작합니다..."

# 이전 커버리지 데이터 정리
echo "📁 이전 커버리지 데이터 정리 중..."
rm -rf htmlcov/
rm -f .coverage
rm -f coverage.xml
rm -rf reports/

# 디렉토리 생성
mkdir -p reports htmlcov

echo "🧪 테스트 실행 및 커버리지 측정 중..."

# 전체 테스트 실행
pytest \
    --cov=app \
    --cov-report=html:htmlcov \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-fail-under=80 \
    --html=reports/pytest_report.html \
    --self-contained-html \
    --verbose

# 커버리지 결과 확인
echo "📊 커버리지 결과:"
coverage report --show-missing

echo "✅ 커버리지 측정 완료!"
echo "📋 HTML 리포트: htmlcov/index.html"
echo "📋 pytest 리포트: reports/pytest_report.html"
echo "📋 XML 리포트: coverage.xml"
