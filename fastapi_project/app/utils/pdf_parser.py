import fitz  # PyMuPDF
import numpy as np

BULLET_CHARS = {"●", "-", "·", "•", "▪", "※", "▶", "‣", "■"}
TITLE_EXCLUDE_KEYWORDS = {"intern", "project", "engineer", "developer", "assistant", "news", "digital", "data", "team"}

def is_probably_bullet(text: str) -> bool:
    return text and (text[0] in BULLET_CHARS)

def is_title_candidate(text: str) -> bool:
    word_count = len(text.strip().split())
    return word_count >= 2 or len(text.strip()) >= 5

def is_probably_not_title(text: str) -> bool:
    lower = text.lower()
    if (
        "@" in text or
        "." in text or
        any(keyword in lower for keyword in TITLE_EXCLUDE_KEYWORDS) or
        len(text.split()) > 5
    ):
        return True
    return False

def extract_text_with_formatting(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    output_lines = []

    for page in doc:
        font_sizes = []
        all_spans = []
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_sizes.append(span["size"])
                    all_spans.append(span)

        font_threshold = np.percentile(font_sizes, 90) if font_sizes else 0

        for block in blocks:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                full_text = " ".join(span["text"].strip() for span in spans).strip()
                if not full_text:
                    continue

                all_bold = all("Bold" in span["font"] for span in spans)
                avg_font_size = np.mean([span["size"] for span in spans])

                if (
                    all_bold and
                    avg_font_size >= font_threshold and
                    not is_probably_bullet(full_text) and
                    is_title_candidate(full_text) and
                    not is_probably_not_title(full_text)
                ):
                    output_lines.append(f"[📌 제목 추정] {full_text}")
                else:
                    output_lines.append(full_text)

    return "\n".join(output_lines)