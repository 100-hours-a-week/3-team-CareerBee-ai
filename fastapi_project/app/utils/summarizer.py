import json
from app.utils.crawler import crawl_hankyung
from app.utils.chroma_handler import add_news_to_chroma, delete_news_by_corp
from app.utils.summarizer_core import generate_latest_issue
from app.utils.text_cleaner import contains_excluded_keyword 

def generate_issue_summaries(corp_list):
    print("\n전체 요약 파이프라인 시작")

    results = {}

    for corp in corp_list:
        try:
            print(f"\n[{corp}] 뉴스 처리 중...")

            delete_news_by_corp(corp)
            articles = crawl_hankyung(corp, max_pages=3)

            for text, url, date in articles:
                if (
                    corp in text and
                    len(text) > 100 and
                    text.count(corp) >= 2 and
                    not contains_excluded_keyword(text, corp)
                ):
                    add_news_to_chroma(text, corp=corp, url=url, date=date)

            summary = generate_latest_issue(corp, return_docs=True)
            results[corp] = summary
            print(f"요약 완료: {corp}")

        except Exception as e:
            print(f"{corp} 처리 중 오류 발생: {e}")

    # JSON 저장
    with open("app/data/latest_issues.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n모든 요약 JSON 저장 완료: app/data/latest_issues.json")