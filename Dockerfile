FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 필수 빌드 도구 및 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libssl-dev libffi-dev libjpeg-dev zlib1g-dev libpng-dev \
    libpoppler-cpp-dev tesseract-ocr libtesseract-dev \
    curl wget unzip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ai

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY ./fastapi_project /ai

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]