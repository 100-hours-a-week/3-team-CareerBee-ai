# app/schemas/resume_extract.py
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any

class ResumeExtractRequest(BaseModel):
    file_url: HttpUrl

class ResumeExtractResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]]