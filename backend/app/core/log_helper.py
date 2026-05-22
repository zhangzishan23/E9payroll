from sqlalchemy.orm import Session
from app.models.models import SysLog


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
            result=result
        )
        db.add(log)
        db.commit()
    except Exception:
        pass