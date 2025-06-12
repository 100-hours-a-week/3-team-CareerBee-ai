ARG BASE_IMAGE_URI
FROM ${BASE_IMAGE_URI}

WORKDIR /ai
COPY ./fastapi_project /ai
EXPOSE 8000
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]