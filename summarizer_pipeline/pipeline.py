import json
from crawler_hankyung import crawl_hankyung
from embedder import add_news_to_chroma, delete_news_by_corp, setup_chroma_collection
from summarizer import generate_latest_issue

def generate_issue_summaries(corp_list):
    print("\n전체 요약 파이프라인 시작")
    setup_chroma_collection()

    results = {}

    for corp in corp_list:
        try:
            print(f"\n[{corp}] 뉴스 처리 중...")

            delete_news_by_corp(corp)
            articles = crawl_hankyung(corp, max_pages=3)
            for text, url in articles:
                if text and len(text) > 100:
                    add_news_to_chroma(text, corp=corp, url=url)

            summary = generate_latest_issue(corp)
            results[corp] = summary
            print(f"요약 완료: {corp}")

        except Exception as e:
            print(f"{corp} 처리 중 오류 발생: {e}")

    # 💾 JSON 저장
    with open("data/latest_issues.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n모든 요약 JSON 저장 완료: data/latest_issues.json")