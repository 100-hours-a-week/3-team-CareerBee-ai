# summarizer.py

import requests
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document

# 1️⃣ 임베딩 함수 준비
embedding_function = SentenceTransformerEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)

# 2️⃣ ChromaDB 연결
chroma = Chroma(
    collection_name="company_issues",
    embedding_function=embedding_function,
    persist_directory="db/chroma",
)


# 3️⃣ vLLM 서버 호출 함수
def call_vllm(prompt: str) -> str:
    url = "http://localhost:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "너는 취준생을 위한 한국어 기업 분석 요약 도우미야.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1800,
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# 4️⃣ 프롬프트 생성 함수 (공시 중심 요약 지시 포함)
def make_prompt(corp_name: str, context: str) -> str:
    return (
        f"[역할] 너는 취업 준비생을 위한 기업 이슈 요약 AI야.\n"
        f"[목표] 아래는 {corp_name}의 공시 및 뉴스 정보야. 이 정보를 바탕으로 해당 기업의 최근 이슈를 단 하나의 문단으로, 취업 준비생이 이해하기 쉽게 요약해줘.\n"
        f"[중요] 공시 내용은 기업이 작성한 공식 문서이므로 반드시 요약에 포함하고, 뉴스는 공시를 보완하는 수준에서 간결히 포함해줘.\n"
        f"[조건]\n"
        f"- 반드시 한국어로 작성하고, 모든 문장은 '~입니다', '~하였습니다' 등 정중한 문어체로 통일해주세요.\n"
        f"- 항목 나열이나 번호 형식 없이, 하나의 자연스러운 단락으로 작성해주세요.\n"
        f"- 다른 기업이나 관련 없는 내용은 절대 포함하지 말고, 반드시 {corp_name}과 직접 관련된 내용만 포함해주세요.\n"
        f"- 전체 문장은 500자 이내로 유지해주세요.\n"
        f"[본문]\n{context}"
    )


# 5️⃣ 최종 요약 생성 함수
def generate_latest_issue(corp_name: str, return_docs: bool = False):
    queries = ["채용 전략", "인사 정책", "조직 개편", "미래 성장성", "시장 경쟁력"]

    # 공시: 무조건 1개 포함
    all_data = chroma.get(include=["metadatas", "documents"])
    report_doc_obj = None
    for meta, doc in zip(all_data["metadatas"], all_data["documents"]):
        if meta.get("corp") == corp_name and meta.get("type") == "report":
            report_doc_obj = Document(
                page_content=doc, metadata={"type": "report", "corp": corp_name}
            )
            break

    # 뉴스: 의미 기반 검색
    news_docs = []
    for q in queries:
        result = chroma.similarity_search(
            q,
            k=3,
            filter={"$and": [{"corp": {"$eq": corp_name}}, {"type": {"$eq": "news"}}]},
        )
        news_docs.extend(result)

    # 중복 제거
    seen = set()
    unique_news_docs = []
    for doc in news_docs:
        if doc.page_content not in seen:
            unique_news_docs.append(doc)
            seen.add(doc.page_content)

    # 아무 것도 없으면 종료
    if report_doc_obj is None and not unique_news_docs:
        msg = f"최근 이슈가 없어요. {corp_name}는 평화롭군요."
        return (msg, []) if return_docs else msg

    # 6️⃣ context 구성
    context_parts = []
    used_docs = []

    if report_doc_obj:
        context_parts.append("[공시 정보]\n" + report_doc_obj.page_content)
        used_docs.append(report_doc_obj)

    if unique_news_docs:
        formatted_news = []
        for doc in unique_news_docs:
            date = doc.metadata.get("date", "날짜미상")
            formatted_news.append(f"[{date}] {doc.page_content}")
        context_parts.append("[뉴스 정보]\n" + "\n\n".join(formatted_news))
        used_docs.extend(unique_news_docs)

    context = "\n\n".join(context_parts)

    # 7️⃣ LLM 요약 실행
    MAX_LEN = 4000
    if len(context) > MAX_LEN:
        chunks = [context[i : i + MAX_LEN] for i in range(0, len(context), MAX_LEN)]
        partial_summaries = [
            call_vllm(make_prompt(corp_name, chunk)) for chunk in chunks
        ]
        final_prompt = (
            f"[통합 요약 지시]\n아래는 {corp_name}에 대한 부분 요약이야. 공시 내용을 중심으로 정리해줘.\n\n"
            + "\n\n".join(partial_summaries)
        )
        result = call_vllm(final_prompt)
    else:
        result = call_vllm(make_prompt(corp_name, context))

    return (result, used_docs) if return_docs else result
