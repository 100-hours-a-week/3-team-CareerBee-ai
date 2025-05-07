import json
import time
from db_writer import update_issue_for_company

def update_issues_in_batches(batch_size=10):
    with open("data/latest_issues.json", "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    items = list(issue_data.items())
    total = len(items)
    print(f"\n총 {total}개 기업 요약 DB 업데이트 시작")

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        print(f"\n[{i} ~ {i+len(batch)-1}] 배치 처리 중...")

        for corp, summary in batch:
            try:
                update_issue_for_company(corp, summary)
                print(f"DB 업데이트 완료: {corp}")
            except Exception as e:
                print(f"{corp} 업데이트 실패: {e}")

        time.sleep(1)  # 과도한 부하 방지용 sleep (선택)