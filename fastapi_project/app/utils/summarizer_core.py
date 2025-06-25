import requests
from langchain.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from app.utils.text_cleaner import clean_summary

embedding_function = HuggingFaceEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS", model_kwargs={"device": "cpu"}
)

chroma = Chroma(
    collection_name="company_issues",
    embedding_function=embedding_function,
    persist_directory="db/chroma",
)

examples = [
    {
        "corp_name": "카카오",
        "context": "[공시 정보]\n카카오는 최근 AI 기술을 활용한 신규 서비스를 출시하며 사업 확장을 시도하고 있으며...\n\n[뉴스 정보]\n[2025-06-01] 카카오는 자회사 카카오헬스케어를 통해 의료 AI 사업을 본격화하고 있습니다.",
        "summary": "카카오는 최근 AI 기술을 접목한 신규 서비스 출시와 의료 분야 자회사인 카카오헬스케어를 통한 사업 확장을 추진하고 있습니다. 공시를 통해 기술 투자에 대한 의지를 밝히며, 시장에서는 해당 전략이 미래 성장 동력으로 주목받고 있습니다.",
    },
    {
        "corp_name": "삼성전자",
        "context": "[공시 정보]\n삼성전자는 반도체 시장의 회복을 기대하며 신규 생산라인 투자 계획을 발표했으며...\n\n[뉴스 정보]\n[2025-06-02] 삼성전자는 美 텍사스에 반도체 공장을 신설하기로 결정했습니다.",
        "summary": "삼성전자는 반도체 시장의 회복 가능성에 주목하며 미국 텍사스 지역에 신규 공장 설립을 추진하고 있습니다. 이러한 행보는 글로벌 시장 내 경쟁력 강화를 위한 전략으로 해석되고 있으며, 향후 사업 성장에 긍정적 영향을 줄 것으로 기대됩니다.",
    },
]

example_template = PromptTemplate(
    input_variables=["corp_name", "context", "summary"],
    template=("기업명: {corp_name}\n" "자료:\n{context}\n" "요약:\n{summary}"),
)

fewshot_prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_template,
    prefix=(
        "너는 기업의 공시 및 뉴스 정보를 분석하여 최근 이슈를 요약하는 AI야.\n"
        "요약 조건은 다음과 같아:\n"
        "- 반드시 줄바꿈 없이 하나의 문단으로 작성해.\n"
        "- 항목 구분(번호, 글머리표, 기호 등)을 쓰지 마.\n"
        "- '~합니다' 형태의 정중한 문어체로 작성해.\n"
        "- 마크다운이나 특수기호를 쓰지 마.\n"
        "- 회사명과 직접 관련 없는 내용은 제외해.\n"
        "- 500자 이내로 작성해.\n"
        "다음은 예시야:\n"
    ),
    suffix=("기업명: {corp_name}\n" "자료:\n{context}\n" "요약:"),
    input_variables=["corp_name", "context"],
)


def call_vllm(prompt: str) -> str:
    url = "http://localhost:8001/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "/mnt/ssd/aya-expanse-8b",
        "messages": [
            {
                "role": "system",
                "content": "너는 취준생을 위한 한국어 기업 분석 요약 도우미야.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def has_batchim(korean_word: str) -> bool:
    if not korean_word:
        return False
    last_char = korean_word[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def generate_latest_issue(corp_name: str, return_docs: bool = False):
    queries = ["채용 전략", "인사 정책", "조직 개편", "미래 성장성", "시장 경쟁력"]

    all_data = chroma.get(include=["metadatas", "documents"])
    report_doc_obj = None
    for meta, doc in zip(all_data["metadatas"], all_data["documents"]):
        if meta.get("corp") == corp_name and meta.get("type") == "report":
            report_doc_obj = Document(
                page_content=doc, metadata={"type": "report", "corp": corp_name}
            )
            break

    news_docs = []
    for q in queries:
        result = chroma.similarity_search(
            q,
            k=3,
            filter={"$and": [{"corp": {"$eq": corp_name}}, {"type": {"$eq": "news"}}]},
        )
        news_docs.extend(result)

    seen = set()
    unique_news_docs = []
    for doc in news_docs:
        if doc.page_content not in seen:
            unique_news_docs.append(doc)
            seen.add(doc.page_content)

    if report_doc_obj is None and not unique_news_docs:
        particle = "은" if has_batchim(corp_name) else "는"
        msg = f"최근 이슈가 없어요. {corp_name}{particle} 평화롭군요."
        return (msg, []) if return_docs else msg

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

    MAX_LEN = 4000
    if len(context) > MAX_LEN:
        chunks = [context[i : i + MAX_LEN] for i in range(0, len(context), MAX_LEN)]
        partial_summaries = [
            call_vllm(fewshot_prompt.format(corp_name=corp_name, context=chunk))
            for chunk in chunks
        ]
        merged_context = "\n\n".join(
            [f"부분 요약 {i+1}: {s}" for i, s in enumerate(partial_summaries)]
        )
        final_prompt = fewshot_prompt.format(
            corp_name=corp_name, context=merged_context
        )
        result = call_vllm(final_prompt)
    else:
        prompt = fewshot_prompt.format(corp_name=corp_name, context=context)
        result = call_vllm(prompt)
        prompt = fewshot_prompt.format(corp_name=corp_name, context=context)
        result = call_vllm(prompt)

    cleaned = clean_summary(result, corp_name)
    return (cleaned, used_docs) if return_docs else cleaned
