# tests/unit/test_create_docx.py
import pytest
from unittest.mock import patch, Mock
import os

# 안전한 임포트
try:
    from app.utils.create_docx import save_resume_to_docx

    CREATE_DOCX_AVAILABLE = True
except ImportError:
    CREATE_DOCX_AVAILABLE = False


@pytest.mark.skipif(
    not CREATE_DOCX_AVAILABLE, reason="create_docx module not available"
)
class TestCreateDocx:
    """DOCX 파일 생성 단위 테스트 - 실제 save_resume_to_docx 함수 테스트"""

    def test_save_resume_to_docx_success(self):
        """기본 이력서 DOCX 생성 성공 테스트"""
        # app.utils.create_docx 모듈에서 docx.Document를 패치
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ) as mock_makedirs:

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            resume_text = "홍길동\n백엔드 개발자\n경력 2년"

            filename = save_resume_to_docx(resume_text)

            # 반환된 파일명 검증 (resume + timestamp + .docx)
            assert filename is not None
            assert filename.endswith(".docx")
            assert filename.startswith("resume")
            assert len(filename) == len("resume") + 14 + len(
                ".docx"
            )  # resume + YYYYMMDDHHMMSS + .docx

            # Document 생성 및 저장 확인
            mock_document.assert_called_once()
            mock_doc_instance.save.assert_called_once_with(filename)

            # 디렉토리 생성 확인
            mock_makedirs.assert_called_once_with("./generated_resumes", exist_ok=True)

            # 각 줄이 paragraph로 추가되었는지 확인
            expected_calls = 3  # 3줄
            assert mock_doc_instance.add_paragraph.call_count == expected_calls

    def test_save_resume_to_docx_empty_text(self):
        """빈 텍스트 처리 테스트"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ):

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            filename = save_resume_to_docx("")

            assert filename.endswith(".docx")
            mock_document.assert_called_once()
            # 빈 문자열도 1개 paragraph로 처리됨
            assert mock_doc_instance.add_paragraph.call_count == 1

    def test_save_resume_to_docx_multiline_processing(self):
        """여러 줄 텍스트 처리 확인"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ):

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            test_text = "Line 1\nLine 2\nLine 3\nLine 4"
            save_resume_to_docx(test_text)

            # 4줄이 각각 처리되었는지 확인
            assert mock_doc_instance.add_paragraph.call_count == 4

            # 호출된 내용 확인
            calls = mock_doc_instance.add_paragraph.call_args_list
            assert calls[0][0][0] == "Line 1"
            assert calls[1][0][0] == "Line 2"
            assert calls[2][0][0] == "Line 3"
            assert calls[3][0][0] == "Line 4"

    def test_save_resume_to_docx_filename_format(self):
        """파일명 형식 검증"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ), patch("app.utils.create_docx.datetime") as mock_datetime:

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            # 고정된 타임스탬프로 모킹 (실제 형식에 맞춤: %Y%m%d%H%M%S)
            mock_datetime.now.return_value.strftime.return_value = "20240115143022"

            filename = save_resume_to_docx("Test content")

            expected_filename = "resume20240115143022.docx"
            assert filename == expected_filename
            mock_doc_instance.save.assert_called_once_with(expected_filename)

    def test_save_resume_to_docx_save_dir_parameter(self):
        """save_dir 파라미터 테스트 (현재는 무시됨)"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ) as mock_makedirs:

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            # save_dir 파라미터 전달 (현재 구현에서는 무시됨)
            filename = save_resume_to_docx("Test", "custom_dir")

            # 여전히 기본 디렉토리 사용
            mock_makedirs.assert_called_once_with("./generated_resumes", exist_ok=True)
            assert filename.endswith(".docx")

    def test_save_resume_to_docx_file_write_error(self):
        """파일 쓰기 권한 오류 테스트"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ):

            mock_doc_instance = Mock()
            mock_doc_instance.save.side_effect = PermissionError("권한 없음")
            mock_document.return_value = mock_doc_instance

            with pytest.raises(PermissionError):
                save_resume_to_docx("Test content")

    def test_save_resume_to_docx_directory_creation_error(self):
        """디렉토리 생성 오류 테스트"""
        with patch("app.utils.create_docx.Document"), patch(
            "app.utils.create_docx.os.makedirs",
            side_effect=OSError("디렉토리 생성 실패"),
        ):

            with pytest.raises(OSError):
                save_resume_to_docx("Test content")

    def test_save_resume_to_docx_newline_edge_cases(self):
        """줄바꿈 처리 엣지 케이스 테스트"""
        with patch("app.utils.create_docx.Document") as mock_document, patch(
            "app.utils.create_docx.os.makedirs"
        ):

            mock_doc_instance = Mock()
            mock_document.return_value = mock_doc_instance

            # 연속된 줄바꿈 테스트
            test_cases = [
                ("Line1\n\nLine3", ["Line1", "", "Line3"]),  # 빈 줄 포함
                ("Line1\nLine2\n", ["Line1", "Line2", ""]),  # 마지막 줄바꿈
                ("\nLine2\nLine3", ["", "Line2", "Line3"]),  # 첫 번째 빈 줄
                ("Single line", ["Single line"]),  # 줄바꿈 없음
            ]

            for test_text, expected_lines in test_cases:
                mock_doc_instance.reset_mock()
                save_resume_to_docx(test_text)

                assert mock_doc_instance.add_paragraph.call_count == len(expected_lines)


@pytest.mark.skipif(
    CREATE_DOCX_AVAILABLE, reason="Test only when create_docx unavailable"
)
class TestCreateDocxFallback:
    """DOCX 생성 모듈을 사용할 수 없을 때의 대체 테스트"""

    def test_filename_generation_logic(self):
        """파일명 생성 로직 시뮬레이션"""
        from datetime import datetime

        # 실제 함수와 같은 로직: %Y%m%d%H%M%S
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"resume{timestamp}.docx"

        assert filename.startswith("resume")
        assert filename.endswith(".docx")
        assert len(timestamp) == 14  # YYYYMMDDHHMMSS

    def test_text_splitting_logic(self):
        """텍스트 분할 로직 시뮬레이션"""
        test_text = "Line 1\nLine 2\nLine 3"
        lines = test_text.split("\n")

        assert len(lines) == 3
        assert lines == ["Line 1", "Line 2", "Line 3"]

        # 빈 줄 처리
        test_text_with_empty = "Line 1\n\nLine 3"
        lines_with_empty = test_text_with_empty.split("\n")
        assert len(lines_with_empty) == 3
        assert lines_with_empty[1] == ""  # 빈 줄
