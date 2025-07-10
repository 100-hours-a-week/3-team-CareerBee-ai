# app/utils/batch.py
import json
import requests

def update_issues_in_batches():
    with open("app/data/latest_issues.json", "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    items = list(issue_data.items())
    total = len(items)
    print(f"\n총 {total}개 기업 요약 Spring 서버로 한번에 전송 시작")

    # 1. Spring API 요구 payload 형식으로 변환
    payload = []
    for corp, summary in items:
        payload.append({
            "companyName": corp,
            "newRecentIssue": summary
        })
    try:
        # 2. PATCH 요청 (배치 분할 없이 한번에)
        SPRING_SERVER_URL = "https://api.careerbee.co.kr"
        resp = requests.patch(
            f"{SPRING_SERVER_URL}/api/v1/companies/recent-issue",
            json=payload,
            timeout=30  # 대량 전송이므로 timeout 여유있게
        )
        resp.raise_for_status()
        
        # 3. 정상 응답 처리
        if resp.status_code == 202:
            print(f"✅ Spring 업데이트 수락됨 (총 {total}개 기업)")
        else:
            print(f"⚠️ 예상치 못한 상태코드: {resp.status_code}, 응답: {resp.text}")
    
    except Exception as e:
        print(f"❌ Spring 업데이트 실패 (총 {total}개 기업), 오류: {e}")