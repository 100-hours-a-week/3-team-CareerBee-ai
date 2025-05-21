import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer  # CountVectorizer 임포트
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import openai
from openai import OpenAI
import google.generativeai as genai

df = pd.read_csv(
    "data/catch_company_details.csv",
    encoding="utf-8",
)

# Openai API 호출 함수
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "API 키가 로드되지 않았습니다. .env 파일 또는 변수명을 확인해주세요."
    )
client = OpenAI(api_key=api_key)

if "기업 키워드" not in df.columns or "기업 소개" not in df.columns:
    raise KeyError("'기업 키워드' 또는 '기업 소개' 열이 데이터프레임에 없습니다.")

import re


def clean_keywords(keywords):
    stop = [
        "와",
        "과",
        "을",
        "를",
        "이",
        "가",
        "은",
        "는",
        "에",
        "의",
        "로",
        "으로",
        "에서",
        "하며",
        "이며",
        "으로",
        "에게",
    ]
    stop_word = [
        "높은",
        "있습니다",
        "있는",
        "구축하며",
        "진행하며",
        "다양한",
        "대한",
        "위한",
        "전략적",
        "사용자에게",
        "기반의",
        "개발하고",
        "게임을",
        "분야에",
        "기업으로",
        "기획을",
        "고객의",
        "구현을",
        "높입니다",
        "공간에서의",
        "데이터를",
        "개인",
        "nit서비스는",
        "구하다는",
        "klaytn" "극대화합니다",
        "가치를",
        "담당하는",
        "모듈을",
        "데이타헤븐은",
        "소통하고",
        "장르의",
        "부합하는",
        "2009년",
        "93",
        "1994년",
        "1997년",
    ]

    result = []

    for kw in keywords:
        kw = kw.strip()

        if not kw:
            continue

        # 조사 제거 후 저장
        for josa in stop:
            if kw.endswith(josa) and len(kw) > len(josa):
                kw = kw[: -len(josa)]
                break

        # 숫자, 년/월 포함 제거
        if re.search(r"\d", kw) or "년" in kw or "월" in kw:
            continue

        # 금지어 제거
        if kw in stop_word:
            continue

        result.append(kw)

    return list(dict.fromkeys(result))[:4]


def get_keywords_from_openai(text, top_n=10):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "너는 키워드 추출을 도와주는 어시스턴트야.",
                },
                {
                    "role": "user",
                    "content": f"""다음 텍스트에서 회사를 **대표하는 서로 다른 키워드 4개만** 추출해줘.

            조건:
            1. 반드시 **명사**여야 해 (형용사, 동사, 조사 등은 절대 안 돼)
            2. **숫자**, **년/월/일**, **형용사** 같은 말은 절대 포함하지 마
            3. 조사(으로, 은, 는, 를, 을, 이, 가, 에, 의, 에게 등)나 동사 활용형(~하는, ~한)은 제거하고 **기본형 명사만** 남겨줘
            4. 회사 이름을 키워드로 추출하면 안돼. 

            예시:
            입력: "오아시스는 2011년에 설립된 신선식품 유통 기업입니다"
            출력: 신선식품, 유통
            입력: "에스트래픽은 스마트시티 구축을 위한 핵심 기술을 보유하고 있습니다."
            출력: 스마트시티

            입력: "{text}"
            출력 형식: 쉼표로 구분된 단어들 (예: 유통, AI, 플랫폼, 게임)
            """,
                },
            ],
            max_tokens=100,
            temperature=0.5,
        )
        # response = model.generate_content(prompt)
        content = response.choices[0].message.content
        keywords = content.strip().split(",")
        return keywords

    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        return []


# '기업 키워드' 열을 4개로 채우는 함수
def fill_keywords(row, top_n=4):
    try:
        기업명 = row.get("회사이름", "알 수 없음")

        # 기존 키워드는 그대로 사용 (정제 X)
        existing_keywords = (
            row["기업 키워드"].split(",") if pd.notna(row["기업 키워드"]) else []
        )
        existing_keywords = [kw.strip() for kw in existing_keywords if kw.strip()]
        existing_keywords = list(dict.fromkeys(existing_keywords))  # 중복 제거

        # 기존 키워드 수가 부족할 경우에만 LLM 호출
        if len(existing_keywords) < top_n:
            combined_text = f"{row.get('공시자료', '')}\n{row.get('기업 소개', '')}"
            llm_keywords_raw = get_keywords_from_openai(combined_text, top_n=10)
            print(f"llm_keywords_raw: {llm_keywords_raw}")
            llm_keywords = clean_keywords(llm_keywords_raw)  # ✅ GPT 결과만 정제
            print(f"clean_keywords_raw: {llm_keywords}")
            for kw in llm_keywords:
                if kw not in existing_keywords:
                    existing_keywords.append(kw)
                if len(existing_keywords) == top_n:
                    break

        while len(existing_keywords) < top_n:
            existing_keywords.append("")

        print(f"▶{기업명}: 최종 키워드 : {', '.join(existing_keywords)}")
        return ",".join(existing_keywords)

    except Exception as e:
        print(f"{기업명}: 오류 발생 -> {e}")
        return ",".join([""] * top_n)


df["기업 키워드"] = df.apply(fill_keywords, axis=1)

output_path = (
    "data/catch_company_details.csv"
)
df.to_csv(output_path, index=False, encoding="utf-8-sig")

# print(df)
