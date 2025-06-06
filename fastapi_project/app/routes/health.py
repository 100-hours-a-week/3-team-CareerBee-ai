from fastapi import APIRouter
import requests

router = APIRouter()


@router.get("/health-check")
def health_check():
    return {"status": "ok"}
