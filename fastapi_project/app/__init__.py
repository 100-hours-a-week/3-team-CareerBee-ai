import os
# 테스트 환경에서는 DB 비활성화
if os.getenv("TESTING", "false").lower() == "true":
    os.environ["DISABLE_DB"] = "true"
