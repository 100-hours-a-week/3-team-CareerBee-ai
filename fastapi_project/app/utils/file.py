# app/utils/file.py
import requests
import io
import pdfplumber
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
import pytesseract


def download_pdf_from_url(file_url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(file_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"PDF 다운로드 실패 (status code: {response.status_code})")
    print(f"\U0001F4C5 PDF 다운로드 성공 - Content-Type: {response.headers.get('Content-Type')}, 파일크기: {len(response.content)} bytes")
    return response.content

def is_valid_pdf(pdf_bytes: bytes) -> bool:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages) > 0
    except Exception as e:
        print("❌ PyPDF2 PDF 유효성 검사 실패:", e)
        return False


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    1. pdfplumber로 텍스트 추출 시도 → 성공 시 그걸 반환
    2. 실패하거나 텍스트가 거의 없으면 → 이미지로 변환 후 pytesseract OCR 사용
    """
    try:
        # 1단계: pdfplumber 시도
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if len(text.strip()) >= 50:
                print("✅ pdfplumber로 텍스트 추출 성공")
                return text.strip()
            else:
                print("⚠️ 텍스트가 부족하여 OCR로 대체")
    except Exception as e:
        print("❌ pdfplumber 실패:", e)

    # 2단계: 이미지 변환 + OCR
    try:
        images = convert_from_bytes(pdf_bytes)
        ocr_text = "\n".join(pytesseract.image_to_string(img, lang='kor+eng') for img in images)
        print("🔍 pytesseract로 OCR 추출 완료")
        return ocr_text.strip()
    except Exception as e:
        print("❌ OCR 처리 실패:", e)
        return ""
