import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 尝试从多个可能的位置加载 .env 文件
_env_paths = [
    PROJECT_ROOT / ".env",
    Path.cwd() / ".env",
    Path("/.env"),
]
for _env_path in _env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://e9salary:e9salary2024@localhost:5432/e9_salary")
SECRET_KEY = os.getenv("SECRET_KEY", "e9-salary-dev-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
_cors_env = os.getenv("CORS_ORIGINS", "*")
if _cors_env == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

# 钉钉配置
DINGTALK_CLIENT_ID = os.getenv("DINGTALK_CLIENT_ID", "")
DINGTALK_CLIENT_SECRET = os.getenv("DINGTALK_CLIENT_SECRET", "")
DINGTALK_AGENT_ID = os.getenv("DINGTALK_AGENT_ID", "")
DINGTALK_ROBOT_CODE = os.getenv("DINGTALK_ROBOT_CODE", "")

# 路由前缀（服务器多项目部署时使用，如 /e9salary；本地开发留空）
ROUTE_PREFIX = os.getenv("ROUTE_PREFIX", "").strip()
if ROUTE_PREFIX and not ROUTE_PREFIX.startswith("/"):
    ROUTE_PREFIX = "/" + ROUTE_PREFIX
if ROUTE_PREFIX.endswith("/"):
    ROUTE_PREFIX = ROUTE_PREFIX[:-1]

# 时区
TZ = os.getenv("TZ", "Asia/Shanghai")

# 统一目录配置（本地开发和 Docker 保持一致）
# 本地开发: 相对于项目根目录
# Docker: 通过 volume 挂载到容器内对应路径
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data" / "app")))
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(PROJECT_ROOT / "temp")))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(PROJECT_ROOT / "backups")))

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)