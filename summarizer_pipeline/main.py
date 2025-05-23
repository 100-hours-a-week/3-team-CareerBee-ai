# main.py (✅ crontab 실행용으로 수정된 버전)

import pandas as pd
from pipeline import generate_issue_summaries  # 요약 생성 함수
from batch_update import update_issues_in_batches  # DB 업데이트 함수


def main():
    print("\n📆 요약 및 업데이트 파이프라인 시작...")

    # 1. 기업명 목록 로딩
    df = pd.read_csv("data/catch_company_details.csv")
    corp_list = df["기업명"].dropna().unique()

    # 2. 요약 생성 및 JSON 저장
    generate_issue_summaries(corp_list)

    # 3. JSON 기반 DB 업데이트 (10개 단위 배치)
    update_issues_in_batches(batch_size=10)

    print("\n✅ 모든 작업 완료!")


if __name__ == "__main__":
    main()