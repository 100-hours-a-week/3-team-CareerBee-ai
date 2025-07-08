import pandas as pd
from app.utils.summarizer import generate_issue_summaries
from app.utils.batch import update_issues_in_batches


def run_summary_pipeline():
    print("\n📈 기업 요약 파이프라인 시작")
    df = pd.read_csv("app/data/catch_company_details.csv")
    corp_list = df["기업명"].dropna().unique().tolist()

    generate_issue_summaries(corp_list)
    update_issues_in_batches(batch_size=10)
    print("✅ 파이프라인 완료")
