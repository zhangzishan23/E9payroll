# Skill: 认证与权限校验（auth-guard）

## 描述
封装 JWT Token 验证和用户身份解析流程，是所有 API 端点的第一道防线。同时提供基于角色+模块的细粒度权限校验。

## 代码（Python）
```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import SysUser, SysRole, SysUserRole, SysPermission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserInfo(BaseModel):
    """当前请求用户的基本信息"""
    id: int
    username: str
    display_name: str
    is_admin: bool

    class Config:
        from_attributes = True


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserInfo:
    """
    从请求头中解析 JWT Token，返回当前用户信息。

    异常：
      - 401: Token 过期或无效
      - 403: 账号已被禁用
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录凭证无效，请重新登录")

    user = db.query(SysUser).filter(SysUser.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
    )


def check_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """校验当前用户是否为管理员，否则返回 403"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return current_user


def check_permission(module: str, action: str):
    """
    校验当前用户是否拥有指定模块的指定操作权限。

    使用方式（作为 FastAPI 依赖）：
      @router.post("/employees")
      def create_employee(
          db: Session = Depends(get_db),
          current_user: UserInfo = Depends(get_current_user),
          _perm = Depends(check_permission("employee", "create"))
      ):

    权限逻辑：
      1. 管理员（is_admin=True）直接通过
      2. 否则查询用户角色的权限表
    """
    def checker(
        db: Session = Depends(get_db),
        current_user: UserInfo = Depends(get_current_user),
    ) -> bool:
        if current_user.is_admin:
            return True

        user_roles = db.query(SysUserRole).filter(
            SysUserRole.user_id == current_user.id
        ).all()
        role_ids = [ur.role_id for ur in user_roles]
        if not role_ids:
            raise HTTPException(
                status_code=403,
                detail=f"您没有「{module}」模块的「{action}」权限，请联系管理员"
            )

        perm = db.query(SysPermission).filter(
            SysPermission.role_id.in_(role_ids),
            SysPermission.module == module,
            SysPermission.action == action,
        ).first()

        if perm is None:
            raise HTTPException(
                status_code=403,
                detail=f"您没有「{module}」模块的「{action}」权限，请联系管理员"
            )

        return True

    return checker


def get_user_roles(user_id: int, db: Session) -> list:
    """获取用户的所有角色"""
    roles = db.query(SysRole).join(
        SysUserRole, SysRole.id == SysUserRole.role_id
    ).filter(SysUserRole.user_id == user_id).all()
    return [{"id": r.id, "name": r.name} for r in roles]


def get_user_permissions(user_id: int, db: Session) -> list:
    """获取用户的所有权限（角色权限的并集）"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if user and user.is_admin:
        return [{"module": "*", "action": "*"}]

    user_roles = db.query(SysUserRole).filter(
        SysUserRole.user_id == user_id
    ).all()
    role_ids = [ur.role_id for ur in user_roles]
    if not role_ids:
        return []

    perms = db.query(SysPermission).filter(
        SysPermission.role_id.in_(role_ids)
    ).all()
    return [{"module": p.module, "action": p.action} for p in perms]
```

## 外部依赖与错误处理
- 依赖：FastAPI（Depends、HTTPException、OAuth2PasswordBearer）、SQLAlchemy Session、JWT 解码函数、SysUser/SysRole/SysUserRole/SysPermission 模型
- 所有错误提示使用中文
- Token 解析失败统一返回 401
- 权限不足返回 403，提示"请联系管理员"
- `check_permission` 是工厂函数，通过闭包捕获 module 和 action 参数

## 调用示例
```python
# 最简用法：只要登录就行
@router.get("/employees")
def get_employees(current_user: UserInfo = Depends(get_current_user)):
    ...

# 管理员专属接口
@router.delete("/dict/{dict_id}")
def delete_dict(current_user: UserInfo = Depends(check_admin)):
    ...

# 细粒度权限控制
@router.post("/employees")
def create_employee(
    _perm = Depends(check_permission("employee", "create")),
    ...
):
    ...
```

## 使用场景
- [auth.py](file:///d:/devtool/cm/backend/app/api/auth.py) - `get_current_user` + `UserInfo` 定义
- 所有 API 文件的端点 - 通过 `Depends(get_current_user)` 保护
- [system.py](file:///d:/devtool/cm/backend/app/api/system.py) - 管理员检查 `if not current_user.is_admin`
- [ai_assistant.py](file:///d:/devtool/cm/backend/app/api/ai_assistant.py) - AI 权限检查 `has_ai_permission()`