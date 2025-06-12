FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential cmake curl unzip \
    libopenblas-dev libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY fastapi_project/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_project/ .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]