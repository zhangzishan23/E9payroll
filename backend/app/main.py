from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import CORS_ORIGINS
from app.core.database import engine, Base
from app.core.scheduler import start_scheduler, stop_scheduler
from app.models import models
from app.api import auth, employees, attendance, salary, approval, reports, system, performance, social_insurance, dingtalk


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="E9 Payroll", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(employees.router, prefix="/api/employees", tags=["人事信息"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["考勤管理"])
app.include_router(salary.router, prefix="/api/salary", tags=["薪资核算"])
app.include_router(approval.router, prefix="/api/approval", tags=["审批流程"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表导出"])
app.include_router(performance.router, prefix="/api/performance", tags=["绩效管理"])
app.include_router(social_insurance.router, prefix="/api/social-insurance", tags=["社保公积金"])
app.include_router(dingtalk.router, prefix="/api/dingtalk", tags=["钉钉同步"])
app.include_router(system.router, prefix="/api/system", tags=["系统管理"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "E9 Payroll 运行正常"}