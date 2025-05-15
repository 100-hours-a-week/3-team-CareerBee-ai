import requests
from bs4 import BeautifulSoup
import time

def crawl_hankyung(corp_name: str, top_k: int = 15, max_pages: int = 5):
    """
    한경 뉴스 사이트에서 기업명으로 정확도순 정렬된 상위 top_k개 뉴스 본문 수집
    """
    base = "https://search.hankyung.com/search/news"
    seen = set()
    all_articles = []
    page = 1

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    while len(all_articles) < top_k and page <= max_pages:
        print(f"🌐 [페이지 {page}] 요청 중...")

        params = {
            "query": corp_name,
            "period": "YEAR",
            "sort": "RANK/DESC,DATE/DESC",
            "page": page
        }

        try:
            resp = requests.get(base, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            print(f"🔗 요청 URL: {resp.url}")
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.txt_wrap > a")

        if not items:
            print("📄 더 이상 기사가 없습니다. 중단합니다.")
            break

        for a in items:
            href = a.get("href", "")
            if href.startswith("https://www.hankyung.com") and href not in seen:
                seen.add(href)
                text, date = extract_article_text(href, headers)
                if text:
                    all_articles.append((text, href, date))
                if len(all_articles) >= top_k:
                    break

        page += 1
        time.sleep(0.3)

    print(f"✅ 정확도순 상위 {len(all_articles)}개 뉴스 수집 완료.")
    return all_articles


def extract_article_text(url: str, headers: dict):
    """
    한경 기사 본문 텍스트와 날짜 추출
    """
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 날짜 추출
        date_tag = soup.select_one("span.txt-date")
        date_text = date_tag.get_text(strip=True) if date_tag else "unknown"

        # 광고 제거
        for ad in soup.select("aside, iframe, div[class*=ad], div[id*=ad]"):
            ad.decompose()

        # 본문 추출
        content = soup.select_one("div#articletxt") or soup.select_one("div.article-content")
        text = content.get_text("\n", strip=True) if content else None

        return (text, date_text)

    except Exception as e:
        print(f"❌ 본문 읽기 실패: {url} → {e}")
        return (None, "unknown")