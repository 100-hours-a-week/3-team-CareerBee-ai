# embedder.py

from chromadb import Client
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# 1️⃣ 임베딩 함수 준비
embedding_function = SentenceTransformerEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)

# 2️⃣ ChromaDB 연결
chroma = Chroma(persist_directory="db/chroma", embedding_function=embedding_function)

# 3️⃣ 뉴스 저장 함수
def add_news_to_chroma(text: str, corp: str, url: str):
    chroma.add_texts(
        texts=[text],
        metadatas=[{
            "corp": corp,
            "type": "뉴스",
            "url": url
        }]
    )
    print(f"📰 뉴스 저장 완료: {url}")

# 4️⃣ 공시 저장 함수
def add_report_to_chroma(text: str, corp: str):
    chroma.add_texts(
        texts=[text],
        metadatas=[{
            "corp": corp,
            "type": "공시",
        }]
    )
    print(f"📄 공시 저장 완료: {corp}")

# 5️⃣ 특정 기업 뉴스 삭제 함수
def delete_news_by_corp(corp_name: str):
    """
    특정 기업의 기존 뉴스 데이터만 삭제
    """
    client = Client()
    collection = client.get_collection(name="langchain")
    try:
        collection.delete(
            where={
                "$and": [
                    {"corp": corp_name},
                    {"type": "뉴스"}
                ]
            }
        )
        print(f"🗑️ '{corp_name}' 관련 기존 뉴스 삭제 완료!")
    except Exception as e:
        print(f"❌ 뉴스 삭제 실패: {e}")

# 6️⃣ (⭐추가) 컬렉션 초기화 함수
def setup_chroma_collection(collection_name: str = "langchain"):
    client = Client()
    try:
        client.delete_collection(name=collection_name)
    except:
        pass  # 없으면 무시

    client.create_collection(name=collection_name)
    print(f"✅ '{collection_name}' 컬렉션 생성 완료!")