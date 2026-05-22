from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.security import verify_password, create_access_token, decode_access_token, get_password_hash
from app.models.models import SysUser

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str
    is_admin: bool


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool

    class Config:
        from_attributes = True


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
    return UserInfo(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(SysUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")
    token = create_access_token(data={"sub": str(user.id)})
    write_log(db, "login", user.id, user.username, "auth", "login", f"用户 {user.username} 登录系统")
    return TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin
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