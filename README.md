# CareerBee AI Server 🐝

이 Repository는 **CareerBee 서비스의 AI 서버**를 위한 프로젝트입니다.  
LLM을 기반으로 다음과 같은 기능을 제공합니다:

- 사용자의 이력서 PDF에서 정보 추출
- 추출된 정보로 이력서 초안 자동 생성
- 면접 질문 및 답변에 대한 AI 피드백 생성
- 기업 관련 뉴스 및 공시자료 요약

---

## 🔗 References

- [CareerBee Wiki Home](https://github.com/100-hours-a-week/3-team-ssammu-wiki/wiki)
- [CareerBee AI Wiki](https://github.com/100-hours-a-week/3-team-ssammu-wiki/wiki/AI-Wiki)

---

## 💻 Development Environment

- Python 3.11.11  
- FastAPI  
- LangChain / LangGraph  
- Hugging Face Transformers  
- vLLM for optimized LLM inference  
- Redis (에이전트 상태 저장용)

---

## 🧠 LLM (Large Language Model)

- `CohereLabs/aya-expanse-8b`  
  (LoRA 기반 튜닝 가능)

---

## 📂 Project Directory Structure
```
3-TEAM-CAREERBEE-AI/
├── fastapi_project/
│   ├── app/
│   │   ├── agents/          # LangGraph 기반 에이전트 정의
│   │   ├── routes/          # FastAPI API 라우터
│   │   ├── services/        # 핵심 비즈니스 로직
│   │   ├── schemas/         # Pydantic 데이터 모델
│   │   └── utils/           # 보조 함수
│   └── main.py              # FastAPI 앱 진입점
```
---

## 🚀 How to Run

### 1. 가상환경 설정 (선택)

```bash
python -m venv .venv
source .venv/bin/activate
```
### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
.env 파일을 프로젝트 루트에 생성하고 다음 항목을 포함:
```
VLLM_URL=http://<vllm_host>:<port>
REDIS_URL=redis://localhost:6379/0
```

### 4. 서버 실행
```
uvicorn fastapi_project.main:app --host 0.0.0.0 --port 8000
```
※ 개발 환경에서는 --reload 옵션을 추가하면 코드 변경 시 자동 반영됩니다.
