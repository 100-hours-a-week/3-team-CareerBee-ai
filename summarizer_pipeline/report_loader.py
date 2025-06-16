import os
import shutil
import pandas as pd
from embedder import add_report_to_chroma

# ChromaDB 컬렉션 초기화
if os.path.exists("db/chroma"):
    shutil.rmtree("db/chroma")
    print("🧹 기존 Chroma 디렉토리 삭제 완료.")
else:
    print("ℹ️ 기존 Chroma 디렉토리가 없어서 삭제 생략.")


def load_and_embed_reports(
    csv_path: str = "fastapi_project/app/data/catch_company_details.csv",
):
    """
    CSV 파일을 읽고 공시 정보를 Chroma에 저장
    """
    df = pd.read_csv(csv_path)
    count = 0
    for _, row in df.iterrows():
        corp = row.get("기업명")
        summary = row.get("사업현황")
        if isinstance(summary, str) and len(summary.strip()) > 10:
            add_report_to_chroma(summary.strip(), corp)
            count += 1
    print(f"✅ CSV 공시 자료 {count}건 저장 완료.")


# 실행
if __name__ == "__main__":
    load_and_embed_reports()
