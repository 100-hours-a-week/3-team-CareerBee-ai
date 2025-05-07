# crawler_hankyung.py

import requests
from bs4 import BeautifulSoup
import time

def crawl_hankyung(corp_name: str, max_pages: int = 3):
    """
    한경 뉴스 사이트에서 기업명으로 뉴스 본문 크롤링
    """
    base = "https://search.hankyung.com/search/news"
    params = {
        "query": corp_name,
        "period": "WEEK",
        "sort": "DATE/DESC,RANK/DESC",
    }

    seen = set()
    all_articles = []
    page = 1

    while True:
        print(f"🌐 [페이지 {page}] 요청 중...")
        params["page"] = page
        resp = requests.get(base, params=params, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.txt_wrap > a")

        if not items:
            print("📄 더 이상 기사가 없습니다. 중단합니다.")
            break

        for a in items:
            href = a.get("href", "")
            if href.startswith("https://www.hankyung.com") and href not in seen:
                seen.add(href)
                text = extract_article_text(href)
                if text:
                    all_articles.append((text, href))

        page += 1

        if max_pages and page > max_pages:
            break

        time.sleep(0.5)

    print(f"✅ {len(all_articles)}개 뉴스 수집 완료.")
    return all_articles

def extract_article_text(url: str):
    """
    기사 본문 추출
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 광고 제거
        for ad in soup.select("aside, iframe, div[class*=ad], div[id*=ad]"):
            ad.decompose()

        content = soup.select_one("div#articletxt") or soup.select_one("div.article-content")
        return content.get_text("\n", strip=True) if content else None

    except Exception as e:
        print(f"❌ {url} 읽기 실패: {e}")
        return None