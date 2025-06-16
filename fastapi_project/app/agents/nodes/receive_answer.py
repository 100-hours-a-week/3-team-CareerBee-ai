def receive_answer_node(state):
    if state.pending_questions:
        question = state.pending_questions[0]
        answer = state.user_inputs.get(question)

        # 사용자 응답이 있으면 그 응답 사용, 없으면 "<미응답>" 처리
        answer = state.user_inputs.get(question, "<미응답>")

        # 질문-답변 페어 저장
        state.answers.append({"question": question, "answer": answer})

        # 질문 완료 처리
        state.asked_count += 1
        state.pending_questions = []

    return state
