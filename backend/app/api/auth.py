from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Set
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.security import verify_password, create_access_token, decode_access_token, get_password_hash
from app.models.models import SysUser, SysRole, SysUserRole, SysPermission

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    display_name: str
    is_admin: bool
    permissions: List[str]
    roles: List[str]


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool
    permissions: Set[str] = set()
    roles: Set[str] = set()
    data_scope: str = "all"

    class Config:
        from_attributes = True

    def has_permission(self, perm_code: str) -> bool:
        if self.is_admin:
            return True
        return perm_code in self.permissions

    def has_any_permission(self, *perm_codes: str) -> bool:
        if self.is_admin:
            return True
        return any(p in self.permissions for p in perm_codes)


def get_user_permissions(db: Session, user_id: int) -> tuple[Set[str], Set[str], str]:
    """获取用户的所有权限、角色和数据范围"""
    perms = set()
    roles = set()
    data_scopes = []

    role_records = db.query(SysRole).join(
        SysUserRole, SysUserRole.role_id == SysRole.id
    ).filter(SysUserRole.user_id == user_id).all()

    for role in role_records:
        roles.add(role.name)
        if role.data_scope:
            data_scopes.append(role.data_scope)
        role_perms = db.query(SysPermission).filter(SysPermission.role_id == role.id).all()
        for p in role_perms:
            perms.add(f"{p.module}:{p.action}")

    if "all" in data_scopes:
        effective_scope = "all"
    elif "dept" in data_scopes:
        effective_scope = "dept"
    else:
        effective_scope = "self"

    return perms, roles, effective_scope


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserInfo:
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

    permissions, roles, data_scope = set(), set(), "all"
    if not user.is_admin:
        permissions, roles, data_scope = get_user_permissions(db, user.id)

    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        permissions=permissions,
        roles=roles,
        data_scope=data_scope,
    )


def require_permission(*perm_codes: str):
    """权限检查依赖注入"""
    def checker(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if current_user.is_admin:
            return current_user
        if not current_user.has_any_permission(*perm_codes):
            raise HTTPException(status_code=403, detail="您没有该操作权限，请联系管理员")
        return current_user
    return checker


def require_view_permission(module: str):
    return require_permission(f"{module}:view")


def require_create_permission(module: str):
    return require_permission(f"{module}:create")


def require_edit_permission(module: str):
    return require_permission(f"{module}:edit")


def require_delete_permission(module: str):
    return require_permission(f"{module}:delete")


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(SysUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    permissions = []
    roles = []
    if not user.is_admin:
        perms_set, roles_set, _ = get_user_permissions(db, user.id)
        permissions = sorted(list(perms_set))
        roles = sorted(list(roles_set))

    token = create_access_token(data={"sub": str(user.id)})
    write_log(db, "login", user.id, user.username, "auth", "login", f"用户 {user.username} 登录系统")
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        permissions=permissions,
        roles=roles,
    )


@router.get("/me", response_model=UserInfo)
def get_me(current_user: UserInfo = Depends(get_current_user)):
    return current_user


class ProfileUpdate(BaseModel):
    display_name: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.put("/profile")
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    user = db.query(SysUser).filter(SysUser.id == current_user.id).first()
    user.display_name = data.display_name
    db.commit()
    return {"message": "个人信息更新成功"}


@router.put("/change-password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    user = db.query(SysUser).filter(SysUser.id == current_user.id).first()
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于6位")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"message": "密码修改成功"}


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="用户名长度不能少于3位")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")
    if not data.display_name or len(data.display_name.strip()) == 0:
        raise HTTPException(status_code=400, detail="请输入显示名称")

    existing_user = db.query(SysUser).filter(SysUser.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    guest_role = db.query(SysRole).filter(SysRole.name == "访客").first()
    if not guest_role:
        guest_role = SysRole(
            name="访客",
            description="新注册用户默认角色，仅可查看工作台",
            is_preset=True,
            data_scope="self"
        )
        db.add(guest_role)
        db.flush()

    required_perms = [("dashboard", "view"), ("dashboard", "work_view")]
    for module, action in required_perms:
        existing = db.query(SysPermission).filter(
            SysPermission.role_id == guest_role.id,
            SysPermission.module == module,
            SysPermission.action == action
        ).first()
        if not existing:
            db.add(SysPermission(role_id=guest_role.id, module=module, action=action))

    new_user = SysUser(
        username=data.username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name.strip(),
        is_admin=False,
        is_active=True
    )
    db.add(new_user)
    db.flush()

    user_role = SysUserRole(user_id=new_user.id, role_id=guest_role.id)
    db.add(user_role)

    db.commit()
    write_log(db, "register", new_user.id, new_user.username, "auth", "register", f"用户 {new_user.username} 注册账号")
    return {"message": "注册成功，请登录"}