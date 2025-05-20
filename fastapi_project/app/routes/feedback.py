from fastapi import APIRouter, status
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import generate_feedback
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

router = APIRouter()


@router.post("/feedback/create", response_model=FeedbackResponse)
async def create_feedback(request: FeedbackRequest):
    feedback = await run_in_threadpool(
        generate_feedback, request.question, request.answer
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "httpStatusCode": 200,
            "message": "피드백 생성 성공",
            "data": {"feedback": feedback},
        },
    )
