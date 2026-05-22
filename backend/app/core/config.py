import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./e9_salary.db")
SECRET_KEY = os.getenv("SECRET_KEY", "e9-salary-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")