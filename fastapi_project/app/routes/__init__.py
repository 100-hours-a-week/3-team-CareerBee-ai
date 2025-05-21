# app/routes/__init__.py
from .summary import router as update_summary
from .resume_extract import router as resume_extract
from .resume_create import router as resume_create
from .health import router as health
from .feedback import router as feedback