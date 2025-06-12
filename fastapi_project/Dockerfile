FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libssl-dev libffi-dev libjpeg-dev zlib1g-dev libpng-dev \
    libpoppler-cpp-dev tesseract-ocr libtesseract-dev \
    curl wget unzip git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /ai

# 의존성 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . /ai

# 포트 열기
EXPOSE 8000

# 직접 실행 (venv 불필요, 이미지에 pip 설치되어 있음)
ENTRYPOINT ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]