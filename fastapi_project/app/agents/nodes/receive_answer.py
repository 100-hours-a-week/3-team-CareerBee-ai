def receive_answer_node(state):
    if state.pending_questions:
        question = state.pending_questions[0]
        answer = state.user_inputs.get(question, "<미응답>")
        state.answers.append({"question": question, "answer": answer})
        state.asked_count += 1
    return state
