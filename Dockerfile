FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    make \
    libpoppler-cpp-dev \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    curl wget unzip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ai

# 전체 프로젝트를 먼저 복사한 후 requirements 설치
COPY ./fastapi_project /ai

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]