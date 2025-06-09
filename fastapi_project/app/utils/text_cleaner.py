import re

# 기업명에 따라 제외할 키워드
EXCLUDE_KEYWORDS_BY_CORP = {
    "케이크": ["디저트", "레터링", "주문 제작", "크림", "기념", "빵집", "부티끄", "커피", "초콜랏", "아이스크림", "크리스마스", "수건 케이크", "망고", "생크림", "파리바게뜨", "편의점", "크레이프"],
    "구름": ["날씨", "기상", "구름 물리", "인공 강우", "기상청", "기후", "하늘", "증발", "스카이", "인공 구름", "PLP", "지진운", "기온", "소나기", "구름다리", "구름 위", "구름빵"],
    "숲": ["도시숲", "치유의 숲", "산림청", "삼림", "자연", "초록", "생태", "산림", "숲속", "산림욕", "나무", "휴양림", "휴양", "도시숲", "국립공원", "도심숲"],
    "상상인": ["KLPGA", "골프 대회", "프로", "골프"],
    "다우기술": ["다우지수", "뉴욕증시", "증권", "나스닥", "미국"],
    "크림": ["보습 크림", "올리브영", "티트리", "스킨케어", "화장품", "진정 크림", "수딩 크림", "보습 제품", "H&B", "피부 장벽", "피부", "크림반도", "선크림", "크림대교", "쿠키 앤 크림", "크림빵", "아이스크림에듀", "크림 스킨", "클렌징", "수분크림", "보습", "아이스크림", "크림소스", "핸드크림", "아이스크림미디어"]
}

def clean_summary(summary: str, corp_name: str, max_len: int = 1500) -> str:
    # 1. 제목 형태 제거 (본문 시작 부분에 위치)
    summary = re.sub(r"^(?:\s*#*\s*)?[^\n.]*요약[^\n.:-]*[:\-]?\s*", "", summary, flags=re.IGNORECASE)

	# 2. 본문 내 '요약'이 들어간 한 문장 전체 제거 (예: "다음은 요약한 내용입니다.")
    summary = re.sub(r"[^\n.]*요약[^\n.]*\.", "", summary, flags=re.IGNORECASE)
			
	# 마크다운 및 불필요 기호 제거 (선택)
    summary = re.sub(r"\*\*(.*?)\*\*", r"\1", summary)  # **볼드체**
    summary = re.sub(r"\n+", " ", summary)              # \n 제거
    summary = re.sub(r"\*+", "", summary)               # * 리스트 기호 제거
    summary = re.sub(r"#.*?:", "", summary)             # ## 제목 제거
    summary = re.sub(r"\s{2,}", " ", summary)           # 중복 공백 제거
		
    # 문장 단위 자르기 (종결어미 '다.' 기준)
    sentences = re.split(r"(.*?다\.)", summary)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # max_len 이내로 잘라서 연결
    trimmed = ""
    total_len = 0
    for sent in sentences:
        if total_len + len(sent) > max_len:
            break
        trimmed += sent + " "
        total_len += len(sent) + 1

    return trimmed.strip()

def contains_excluded_keyword(text: str, corp: str) -> bool:
    exclude_keywords = EXCLUDE_KEYWORDS_BY_CORP.get(corp, [])
    return any(keyword in text for keyword in exclude_keywords)