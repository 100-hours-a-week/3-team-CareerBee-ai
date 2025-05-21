# app/utils/file.py
import requests
import io
import pdfplumber
from PyPDF2 import PdfReader


def download_pdf_from_url(file_url: str) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(file_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"PDF 다운로드 실패 (status code: {response.status_code})")
    print(f"📅 PDF 다운로드 성공 - Content-Type: {response.headers.get('Content-Type')}, 파일크기: {len(response.content)} bytes")
    return response.content


def is_valid_pdf(pdf_bytes: bytes) -> bool:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages) > 0
    except Exception as e:
        print("❌ PyPDF2 PDF 유효성 검사 실패:", e)
        return False


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            return text.strip()
    except Exception as e:
        print("❌ pdfplumber 텍스트 추출 실패:", e)
        return ""