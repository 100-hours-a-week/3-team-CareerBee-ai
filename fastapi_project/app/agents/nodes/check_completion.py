def check_completion_node(state):
    if state.pending_questions == [] and state.asked_count >= 3:
        state.info_ready = True
    return state
