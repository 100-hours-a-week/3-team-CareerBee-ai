from fastapi import APIRouter
import requests

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


# @router.get("/health")
# def health_check():
#     try:
#         # LLM 서버 상태 확인
#         res = requests.post("http://localhost:8000/v1/", timeout=1)
#         if res.status_code != 200:
#             raise Exception("LLM not responding")
#         return {"status": "ok"}
#     except:
#         return {"status": "unhealthy"}
