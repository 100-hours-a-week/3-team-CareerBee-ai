FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

WORKDIR /ai

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r fastapi_project/requirements.txt

COPY ./fastapi_project /ai

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]