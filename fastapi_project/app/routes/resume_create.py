import os
import traceback

from fastapi import APIRouter, status
from app.schemas.resume_create import ResumeCreateRequest
from app.services.resume_create_service import generate_resume_draft
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/resume/draft")
async def generate_resume_by_agent(request: ResumeCreateRequest):
    try:
        print("🚀 [1] 요청 들어옴")

        filename = generate_resume_draft(request)
        # file_url = f"https://storage.googleapis.com/gcs-ssmu-dev-static/resume-create/{filename}"
        file_url = (
            f"generated_resumes/{filename}"  # 또는 GCS 등 외부 URL이면 해당 경로로
        )

        print("✅ [2] 이력서 생성 완료:", file_url)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "httpStatusCode": 200,
                "message": "이력서 초안 생성에 성공하였습니다.",
                "data": {"resumeUrl": file_url},
            },
        )

    except Exception as e:
        print("❗ [3] 예외 발생:", str(e))
        import traceback

        traceback.print_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "httpStatusCode": 500,
                "message": "내부 서버 오류입니다.",
                "data": None,
            },
        )
