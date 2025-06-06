from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)


def generate_question_node(state):

    # 최대 3번까지만 질문
    if state.asked_count >= 3:
        state.info_ready = True
        state.pending_questions = []
        return state

    answers = state.answers

    context = f"""
    현재까지 받은 정보는 다음과 같습니다:
    이메일: {state.inputs.get('email')}
    선호 직무: {state.inputs.get('preferred_job')}
    자격증 개수: {state.inputs.get('certification_count')}
    프로젝트 개수: {state.inputs.get('project_count')}
    전공 여부: {state.inputs.get('major_type')}
    재직 회사: {state.inputs.get('company_name')}
    재직 기간: {state.inputs.get('work_period')}
    직무: {state.inputs.get('position')}
    기타: {state.inputs.get('additional_experience')}

    이전에 받은 추가 질문 답변:
    {answers}
    """

    prompt = f"""
    아래는 사용자가 개발자 이력서를 작성하기 위해 입력한 정보입니다. 
    이를 바탕으로 완성도가 높은 이력서를 작성하기 위해 추가로 필요한 정보를 얻기 위한 질문을 "한 개만" 생성하세요. 
    이력서를 작성하기에 정보가 충분하다고 판단되면 '없음'이라고 출력해도 됩니다. 
    단, 사용자가 만족할 만한 이력서를 만들기 위해서는 최대한 정보를 많이 얻는 것이 좋으니 되도록 질문을 생성하세요.
    
    {context}
    """

    response_content = llm.invoke(prompt).content
    print(f"Response content: {response_content}")  # 반환값 출력

    response = response_content.strip() if isinstance(response_content, str) else "없음"

    if response == "없음":
        state.info_ready = True
    else:
        state.pending_questions = [response]

    return state
