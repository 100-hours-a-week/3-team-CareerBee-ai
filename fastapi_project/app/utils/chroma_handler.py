from langchain_community.vectorstores import Chroma

# from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

embedding_function = HuggingFaceEmbeddings(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)


def get_chroma():
    return Chroma(
        collection_name="company_issues",
        embedding_function=embedding_function,
        persist_directory="db/chroma",
    )


def add_news_to_chroma(text: str, corp: str, url: str, date: str = "날짜미상"):
    chroma = get_chroma()
    chroma.add_texts(
        texts=[text],
        metadatas=[{"corp": corp, "type": "news", "url": url, "date": date}],
    )
    print(f"📰 뉴스 저장 완료: {url} ({date})")


def add_report_to_chroma(text: str, corp: str):
    chroma = get_chroma()
    chroma.add_texts(
        texts=[text],
        metadatas=[
            {
                "corp": corp,
                "type": "report",
            }
        ],
    )
    print(f"📄 공시 저장 완료: {corp}")


def delete_news_by_corp(corp_name: str):
    chroma = get_chroma()
    try:
        chroma._collection.delete(
            where={"$and": [{"corp": corp_name}, {"type": "news"}]}
        )
        print(f"🗑️ '{corp_name}' 관련 기존 뉴스 삭제 완료!")
    except Exception as e:
        print(f"❌ 뉴스 삭제 실패: {e}")
