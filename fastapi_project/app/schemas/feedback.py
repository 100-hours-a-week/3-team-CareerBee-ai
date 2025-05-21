from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    question: str
    answer: str


class FeedbackResponse(BaseModel):
    feedback: str
