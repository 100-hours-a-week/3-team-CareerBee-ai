from fastapi import FastAPI
from app.routes import health, resume_create, resume_extract, feedback
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()

app.include_router(resume_create.router, tags=["Resume"])
app.include_router(resume_extract.router, prefix="/resume", tags=["Resume Extract"])
app.include_router(health.router)
app.include_router(feedback.router, tags=["Feedback"])
