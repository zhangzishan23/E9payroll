import os
from pathlib import Path
from dotenv import load_dotenv

# 从项目根目录加载 .env
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./e9_salary.db")
SECRET_KEY = os.getenv("SECRET_KEY", "e9-salary-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
_cors_env = os.getenv("CORS_ORIGINS", "*")
if _cors_env == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# 钉钉配置
DINGTALK_CLIENT_ID = os.getenv("DINGTALK_CLIENT_ID", "")
DINGTALK_CLIENT_SECRET = os.getenv("DINGTALK_CLIENT_SECRET", "")
DINGTALK_AGENT_ID = os.getenv("DINGTALK_AGENT_ID", "")
DINGTALK_ROBOT_CODE = os.getenv("DINGTALK_ROBOT_CODE", "")
# 需要同步的部门名称（逗号分隔），为空则同步全部
DINGTALK_SYNC_DEPT_NAMES = [
    name.strip()
    for name in os.getenv("DINGTALK_SYNC_DEPT_NAMES", "").split(",")
    if name.strip()
]