# app/main.py
from fastapi import FastAPI
from app.routes import resume_extract

app = FastAPI()
app.include_router(resume_extract.router, prefix="/resume", tags=["Resume Extract"])