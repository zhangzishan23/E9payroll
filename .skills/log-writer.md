# Skill: 操作日志记录（log-writer）

## 描述
将系统中的关键操作记录到数据库日志表（sys_logs）中，用于审计追溯和安全监控。
已实现于 `backend/app/core/log_helper.py`，本 Skill 补充增强版。

## 代码（Python）
```python
from datetime import datetime
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
    ip_address: str = "",
    result: str = "成功"
) -> bool:
    """
    写入一条操作日志。

    参数：
      - log_type: 日志类型（login / data_change / ai_chat / export / import / error）
      - user_id: 操作用户ID
      - username: 操作用户名
      - module: 操作模块（auth / employee / attendance / salary / system 等）
      - action: 操作动作（create / edit / delete / login / chat / export 等）
      - target: 操作对象描述，如 "新增员工 张三"
      - detail: JSON格式的详细信息
      - ip_address: 客户端IP（可选）
      - result: 操作结果（"成功" / "失败"）

    返回：True（成功）/ False（失败，静默不抛异常）

    设计原则：日志写入失败不应影响主业务流程
    """
    try:
        log = SysLog(
            log_type=log_type,
            user_id=user_id,
            username=username,
            module=module,
            action=action,
            target=target[:200] if target else "",
            detail=detail,
            ip_address=ip_address,
            result=result,
            created_at=datetime.now()
        )
        db.add(log)
        db.commit()
        return True
    except Exception:
        return False


LOG_ACTIONS = {
    "login": "登录",
    "logout": "退出",
    "create": "新增",
    "edit": "编辑",
    "delete": "删除",
    "export": "导出",
    "import": "导入",
    "chat": "AI对话",
    "calculate": "核算",
    "approve": "审批",
}

LOG_MODULES = {
    "auth": "认证",
    "employee": "人事信息",
    "attendance": "考勤管理",
    "performance": "绩效管理",
    "salary": "薪资核算",
    "approval": "审批流程",
    "report": "报表导出",
    "system": "系统管理",
    "ai_assistant": "AI助手",
}


def format_log_target(module: str, action: str, subject: str) -> str:
    """生成可读的操作描述，如「人事信息 - 新增员工 张三」"""
    mod_name = LOG_MODULES.get(module, module)
    act_name = LOG_ACTIONS.get(action, action)
    return f"{mod_name} - {act_name}{' ' + subject if subject else ''}"
```

## 外部依赖与错误处理
- 依赖：SQLAlchemy Session、SysLog 模型
- 日志写入失败会静默吞掉异常（try/except pass），不影响主业务
- target 字段自动截断至 200 字符，防止超长文本
- 不要在日志中记录密码、Token 等敏感信息

## 调用示例
```python
# 记录登录
write_log(db, "login", user.id, user.username, "auth", "login",
          format_log_target("auth", "login", f"用户 {user.username}"))

# 记录数据变更
write_log(db, "data_change", current_user.id, current_user.username,
          "employee", "create",
          format_log_target("employee", "create", f"员工 {name}"),
          detail={"employee_no": "E90001"})

# 记录AI对话
write_log(db, "ai_chat", user.id, user.username,
          "ai_assistant", "chat",
          f"用户询问：{message[:100]}")
```

## 使用场景
- [log_helper.py](file:///d:/devtool/cm/backend/app/core/log_helper.py) - 核心实现
- [auth.py](file:///d:/devtool/cm/backend/app/api/auth.py) - 登录/登出日志
- [employees.py](file:///d:/devtool/cm/backend/app/api/employees.py) - 员工增删改日志
- [system.py](file:///d:/devtool/cm/backend/app/api/system.py) - 系统管理操作日志
- [ai_assistant.py](file:///d:/devtool/cm/backend/app/api/ai_assistant.py) - AI对话日志