import pytest
from unittest.mock import patch
from app.services.resume_extract_service import extract_resume_info
from app.schemas.resume_extract import ResumeInfo

@pytest.mark.asyncio
@patch("app.services.resume_extract_service.extract_info_from_resume")
async def test_extract_resume_info_mock(mock_llm):
    # 1. mock LLM 응답 세팅
    mock_llm.return_value = {
        "certification_count": 2,
        "project_count": 3,
        "major_type": "MAJOR",
        "company_name": "삼성전자",
        "work_period": 12,
        "position": "AI Engineer",
        "additional_experiences": "동아리 활동"
    }

    # 2. 샘플 파일 URL
    file_url = "https://drive.google.com/uc?export=download&id=1mUnsycTHhF577E1-fkkeh1nI2DFREL7L"

    # 3. 함수 호출
    result: ResumeInfo = await extract_resume_info(file_url)

    # 4. 검증
    assert result.certification_count == 2
    assert result.project_count == 3
    assert result.major_type == "MAJOR"
    assert result.company_name == "삼성전자"
    assert result.work_period == 12
    assert result.position == "AI Engineer"
    assert result.additional_experiences == "동아리 활동"