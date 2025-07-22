# app/schemas/feedback
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    memberId: int
    question: str
    answer: str


class FeedbackResponse(BaseModel):
    memberId: int
    feedback: str
