"""
테스트를 위한 Mock 헬퍼 함수들
"""
from unittest.mock import Mock, MagicMock, patch
import io

def create_docx_mock():
    """python-docx Document mock 생성"""
    mock_doc = MagicMock()
    mock_doc.add_paragraph = MagicMock()
    mock_doc.add_heading = MagicMock()
    mock_doc.save = MagicMock()
    return mock_doc

def create_bytesio_mock():
    """BytesIO mock 생성"""
    mock_io = io.BytesIO()
    mock_io.seek = MagicMock()
    mock_io.getvalue = MagicMock(return_value=b"mock file content")
    return mock_io

def patch_docx_properly():
    """python-docx를 올바르게 patch하는 데코레이터"""
    def decorator(func):
        @patch('docx.Document', side_effect=create_docx_mock)
        @patch('io.BytesIO', side_effect=create_bytesio_mock)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
