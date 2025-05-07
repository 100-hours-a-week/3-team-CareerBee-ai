# report_loader.py

import pandas as pd
from embedder import add_report_to_chroma

def load_and_embed_reports(csv_path: str = "data/catch_company_details.csv"):
    """
    CSV 파일을 읽고 공시 정보를 Chroma에 저장
    """
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        corp = row.get("기업명")
        summary = row.get("사업현황")
        if isinstance(summary, str) and len(summary.strip()) > 10:
            add_report_to_chroma(summary.strip(), corp)
    print(f"✅ CSV 공시 자료 {len(df)}건 저장 완료.")