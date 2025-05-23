# embedder.py

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# 1️⃣ 임베딩 함수는 그대로
embedding_function = SentenceTransformerEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)

# 2️⃣ Chroma 연결을 함수로 바꿈 (지연 실행)
def get_chroma():
    return Chroma(
        collection_name="company_issues",
        embedding_function=embedding_function,
        persist_directory="db/chroma"
    )

# 3️⃣ 뉴스 저장 함수
def add_news_to_chroma(text: str, corp: str, url: str, date: str = "날짜미상"):
    chroma = get_chroma()
    chroma.add_texts(
        texts=[text],
        metadatas=[{
            "corp": corp,
            "type": "news",
            "url": url,
            "date": date
        }]
    )
    print(f"📰 뉴스 저장 완료: {url} ({date})")

# 4️⃣ 공시 저장 함수
def add_report_to_chroma(text: str, corp: str):
    chroma = get_chroma()
    chroma.add_texts(
        texts=[text],
        metadatas=[{
            "corp": corp,
            "type": "report",
        }]
    )
    print(f"📄 공시 저장 완료: {corp}")

# 5️⃣ 삭제 함수도 동일하게
def delete_news_by_corp(corp_name: str):
    chroma = get_chroma()
    try:
        chroma._collection.delete(
            where={
                "$and": [
                    {"corp": corp_name},
                    {"type": "news"}
                ]
            }
        )
        print(f"🗑️ '{corp_name}' 관련 기존 뉴스 삭제 완료!")
    except Exception as e:
        print(f"❌ 뉴스 삭제 실패: {e}")