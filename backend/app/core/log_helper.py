from contextvars import ContextVar
from sqlalchemy.orm import Session
from app.models.models import SysLog

# 存储当前请求上下文的客户端 IP
_current_request_ip: ContextVar[str | None] = ContextVar("_current_request_ip", default=None)


def set_current_request_ip(ip: str | None) -> None:
    """在中间件中调用，记录当前请求的客户端 IP"""
    _current_request_ip.set(ip)


def get_current_request_ip() -> str | None:
    """获取当前请求上下文的客户端 IP"""
    return _current_request_ip.get()


def write_log(
    db: Session,
    log_type: str,
    user_id: int,
    username: str,
    module: str,
    action: str,
    target: str = "",
    detail: dict = None,
    result: str = "成功"
):
    try:
        log = SysLog(
            log_type=log_type,
            user_id=user_id,
            username=username,
            module=module,
            action=action,
            target=target,
            detail=detail,
            result=result,
            ip_address=get_current_request_ip()
        )
        db.add(log)
        db.commit()
    except Exception:
        pass