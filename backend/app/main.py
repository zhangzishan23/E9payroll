from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import CORS_ORIGINS, ROUTE_PREFIX
from app.core.database import engine, Base
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.migrations import run_migrations
from app.core.log_helper import set_current_request_ip
from app.models import models
from app.api import auth, employees, attendance, salary, approval, reports, system, performance, social_insurance, dingtalk, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    from app.core.migrations import _init_default_roles_and_permissions
    _init_default_roles_and_permissions()
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(
    title="E9 Payroll",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    root_path=ROUTE_PREFIX,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def capture_client_ip(request: Request, call_next):
    """记录客户端 IP 到请求上下文，供 write_log 使用"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None
    set_current_request_ip(client_ip)
    response = await call_next(request)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(employees.router, prefix="/api/employees", tags=["人事信息"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["考勤管理"])
app.include_router(salary.router, prefix="/api/salary", tags=["薪资核算"])
app.include_router(approval.router, prefix="/api/approval", tags=["审批流程"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表导出"])
app.include_router(performance.router, prefix="/api/performance", tags=["绩效管理"])
app.include_router(social_insurance.router, prefix="/api/social-insurance", tags=["社保公积金"])
app.include_router(dingtalk.router, prefix="/api/dingtalk", tags=["钉钉同步"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["工作台"])
app.include_router(system.router, prefix="/api/system", tags=["系统管理"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "E9 Payroll 运行正常"}