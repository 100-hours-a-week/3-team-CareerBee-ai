import pytest
from datetime import datetime
from app.schemas.resume_models import (
    ResumeAgentState,
    create_initial_state,
    update_state_with_answer,
)
from app.schemas.base import BaseInputsModel


class TestResumeAgentModels:
    """ResumeAgentState 모델 단위 테스트"""

    def test_create_initial_state(self):
        """초기 상태 생성 테스트"""
        memberId = 123
        inputs = BaseInputsModel(
            email="test@example.com", preferred_job="개발자", major_type="MAJOR"
        )

        state = create_initial_state(memberId, inputs)

        assert state.memberId == memberId
        assert state.inputs == inputs
        assert state.asked_count == 0
        assert state.max_questions == 3
        assert state.info_ready == False
        assert state.step == "questioning"
        assert state.user_inputs == {}
        assert state.answers == []
        assert state.pending_questions == []

    def test_add_answer(self):
        """답변 추가 테스트"""
        inputs = BaseInputsModel(
            email="test@example.com", preferred_job="개발자", major_type="MAJOR"
        )
        state = create_initial_state(1, inputs)

        question = "좋아하는 프로그래밍 언어는?"
        answer = "Python입니다."

        state.add_answer(question, answer)

        assert state.asked_count == 1
        assert len(state.answers) == 1
        assert state.answers[0]["question"] == question
        assert state.answers[0]["answer"] == answer
        assert state.user_inputs[question] == answer

    def test_mark_completed(self):
        """완료 상태 설정 테스트"""
        inputs = BaseInputsModel(
            email="test@example.com", preferred_job="개발자", major_type="MAJOR"
        )
        state = create_initial_state(1, inputs)

        resume_content = "# 생성된 이력서"
        docx_path = "resume/test.docx"

        state.mark_completed(resume_content, docx_path)

        assert state.info_ready == True
        assert state.step == "completed"
        assert state.resume == resume_content
        assert state.docx_path == docx_path
        assert state.pending_questions == []

    def test_redis_serialization(self):
        """Redis 직렬화/역직렬화 테스트"""
        inputs = BaseInputsModel(
            email="test@example.com", preferred_job="개발자", major_type="MAJOR"
        )
        original_state = create_initial_state(1, inputs)
        original_state.add_answer("질문", "답변")

        # Redis dict로 변환
        redis_dict = original_state.to_redis_dict()

        # dict에서 다시 객체로 변환
        restored_state = ResumeAgentState.from_redis_dict(redis_dict)

        assert restored_state.memberId == original_state.memberId
        assert restored_state.inputs.email == original_state.inputs.email
        assert restored_state.asked_count == original_state.asked_count
        assert len(restored_state.answers) == len(original_state.answers)

    def test_is_complete(self):
        """완료 여부 확인 테스트"""
        inputs = BaseInputsModel(
            email="test@example.com", preferred_job="개발자", major_type="MAJOR"
        )
        state = create_initial_state(1, inputs)

        # 초기 상태는 미완료
        assert state.is_complete() == False

        # info_ready가 True면 완료
        state.info_ready = True
        assert state.is_complete() == True

        # info_ready가 False여도 최대 질문 수에 도달하면 완료
        state.info_ready = False
        state.asked_count = 3  # max_questions와 같음
        assert state.is_complete() == True
