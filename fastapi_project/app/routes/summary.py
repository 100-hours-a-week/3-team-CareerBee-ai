from fastapi import APIRouter
from app.services.summary_service import run_summary_pipeline

router = APIRouter()

@router.post("/summary/update-summary")
def update_summary():
    run_summary_pipeline()
    return {"message": "요약 파이프라인 완료"}