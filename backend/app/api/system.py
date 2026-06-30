from datetime import datetime
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional, List
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.config import DATABASE_URL
from app.core.security import get_password_hash
from app.models.models import SysUser, SysRole, SysUserRole, SysPermission, SysDictBase, SysLog
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class DictItemOut(BaseModel):
    id: int
    category: str
    code: str
    name: str
    parent_id: Optional[int] = None
    sort_order: int
    is_enabled: bool
    extra: Optional[dict] = None

    class Config:
        from_attributes = True


class DictItemCreate(BaseModel):
    category: str
    code: str
    name: str
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_enabled: bool = True
    extra: Optional[dict] = None


class DictItemUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    extra: Optional[dict] = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_preset: bool
    data_scope: str

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    data_scope: str = "all"


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data_scope: Optional[str] = None


class PermissionAssign(BaseModel):
    permissions: List[dict]


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: Optional[str] = None

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    is_admin: bool = False
    role_ids: List[int] = []


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class LogOut(BaseModel):
    id: int
    log_type: str
    username: Optional[str] = None
    module: Optional[str] = None
    action: Optional[str] = None
    target: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    result: Optional[str] = None
    created_at: Optional[str] = None

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True


class DictTreeNode(BaseModel):
    id: int
    category: str
    code: str
    name: str
    parent_id: Optional[int] = None
    sort_order: int
    is_enabled: bool
    extra: Optional[dict] = None
    children: List["DictTreeNode"] = []

    class Config:
        from_attributes = True


DictTreeNode.model_rebuild()


@router.get("/dict/{category}", response_model=List[DictItemOut])
def get_dict(category: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    items = db.query(SysDictBase).filter(
        SysDictBase.category == category,
    ).order_by(SysDictBase.sort_order).all()
    return items


@router.get("/dict/{category}/tree", response_model=List[DictTreeNode])
def get_dict_tree(category: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """返回指定分类的树形结构数据，支持层级展示"""
    items = db.query(SysDictBase).filter(
        SysDictBase.category == category,
    ).order_by(SysDictBase.sort_order).all()

    # 构建 id -> node 映射
    node_map = {}
    for item in items:
        node_map[item.id] = {
            "id": item.id,
            "category": item.category,
            "code": item.code,
            "name": item.name,
            "parent_id": item.parent_id,
            "sort_order": item.sort_order,
            "is_enabled": item.is_enabled,
            "extra": item.extra,
            "children": []
        }

    # 构建树形结构
    roots = []
    for item in items:
        node = node_map[item.id]
        if item.parent_id and item.parent_id in node_map:
            node_map[item.parent_id]["children"].append(node)
        else:
            roots.append(node)

    # 清理空 children 数组
    def clean_children(nodes):
        for node in nodes:
            if not node["children"]:
                node["children"] = []
            else:
                clean_children(node["children"])

    clean_children(roots)
    return roots


@router.get("/dict", response_model=List[DictItemOut])
def get_all_dicts(db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    items = db.query(SysDictBase).order_by(SysDictBase.category, SysDictBase.sort_order).all()
    return items


@router.post("/dict", response_model=DictItemOut)
def create_dict(item: DictItemCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    existing = db.query(SysDictBase).filter(
        SysDictBase.category == item.category,
        SysDictBase.code == item.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"字典项 [{item.code}] 已存在")
    db_item = SysDictBase(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "create", f"新增字典项 {item.category}/{item.code}")
    return db_item


@router.put("/dict/{dict_id}/toggle")
def toggle_dict(dict_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """切换字典项的启用/禁用状态"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    db_item = db.query(SysDictBase).filter(SysDictBase.id == dict_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    db_item.is_enabled = not db_item.is_enabled
    db.commit()
    db.refresh(db_item)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "toggle",
              f"{'启用' if db_item.is_enabled else '禁用'}字典项 {db_item.name} (id={dict_id})")
    return {"id": db_item.id, "is_enabled": db_item.is_enabled}


@router.put("/dict/{dict_id}", response_model=DictItemOut)
def update_dict(dict_id: int, item: DictItemUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    db_item = db.query(SysDictBase).filter(SysDictBase.id == dict_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    update_data = item.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "edit", f"编辑字典项 (id={dict_id})")
    return db_item


@router.delete("/dict/{dict_id}")
def delete_dict(dict_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    db_item = db.query(SysDictBase).filter(SysDictBase.id == dict_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    db.delete(db_item)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "delete", f"删除字典项 (id={dict_id})")
    return {"message": "删除成功"}


@router.post("/dict/batch-delete")
def batch_delete_dict(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的字典项ID列表")
    items = db.query(SysDictBase).filter(SysDictBase.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=404, detail="未找到指定的字典项")
    for item in items:
        db.delete(item)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "delete", f"批量删除 {len(items)} 个字典项")
    return {"message": f"成功删除 {len(items)} 个字典项", "deleted_count": len(items)}


@router.post("/dict/import")
async def import_dict(
    file: UploadFile = File(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作数据字典")
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

    try:
        contents = await file.read()
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(contents), read_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法读取 Excel 文件：{str(e)}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel 文件为空或只有表头，没有数据行")

    headers = [str(h).strip() if h else "" for h in rows[0]]
    header_map = {}
    for i, h in enumerate(headers):
        if "编码" in h:
            header_map["code"] = i
        elif "名称" in h:
            header_map["name"] = i
        elif "排序" in h:
            header_map["sort_order"] = i
        elif "启用" in h:
            header_map["is_enabled"] = i

    if "code" not in header_map or "name" not in header_map:
        raise HTTPException(status_code=400, detail="Excel 表头缺少「编码」或「名称」列")

    created = 0
    updated = 0
    errors = []

    for row_idx, row in enumerate(rows[1:], start=2):
        try:
            code = str(row[header_map["code"]]).strip() if row[header_map["code"]] else ""
            name = str(row[header_map["name"]]).strip() if row[header_map["name"]] else ""
            if not code or not name:
                errors.append(f"第{row_idx}行：编码或名称为空，跳过")
                continue

            sort_order = 0
            if "sort_order" in header_map and row[header_map["sort_order"]] is not None:
                try:
                    sort_order = int(row[header_map["sort_order"]])
                except (ValueError, TypeError):
                    sort_order = 0

            is_enabled = True
            if "is_enabled" in header_map and row[header_map["is_enabled"]] is not None:
                val = str(row[header_map["is_enabled"]]).strip().lower()
                is_enabled = val in ("是", "true", "1", "yes", "启用")

            existing = db.query(SysDictBase).filter(
                SysDictBase.category == category,
                SysDictBase.code == code
            ).first()

            if existing:
                existing.name = name
                existing.sort_order = sort_order
                existing.is_enabled = is_enabled
                updated += 1
            else:
                db_item = SysDictBase(
                    category=category, code=code, name=name,
                    sort_order=sort_order, is_enabled=is_enabled
                )
                db.add(db_item)
                created += 1
        except Exception as e:
            errors.append(f"第{row_idx}行：处理失败 - {str(e)}")

    db.commit()
    wb.close()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "import", f"导入字典数据：新增{created}条，更新{updated}条")

    return {
        "message": f"导入完成：新增 {created} 条，更新 {updated} 条",
        "created": created,
        "updated": updated,
        "errors": errors
    }


@router.get("/dict/export/{category}")
def export_dict(
    category: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    items = db.query(SysDictBase).filter(
        SysDictBase.category == category
    ).order_by(SysDictBase.sort_order).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"数据字典_{category}"
    ws.append(["编码", "名称", "排序", "启用"])

    for item in items:
        ws.append([
            item.code,
            item.name,
            item.sort_order,
            "是" if item.is_enabled else "否"
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=dict_{category}.xlsx"}
    )


@router.get("/roles", response_model=List[RoleOut])
def get_roles(db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    return db.query(SysRole).all()


@router.post("/roles", response_model=RoleOut)
def create_role(role: RoleCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作角色")
    existing = db.query(SysRole).filter(SysRole.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"角色 [{role.name}] 已存在")
    db_role = SysRole(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "create", f"新增角色 {role.name}")
    return db_role


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作角色")
    db_role = db.query(SysRole).filter(SysRole.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    update_data = role.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_role, key, value)
    db.commit()
    db.refresh(db_role)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "edit", f"编辑角色 (id={role_id})")
    return db_role


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作角色")
    db_role = db.query(SysRole).filter(SysRole.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if db_role.is_preset:
        raise HTTPException(status_code=400, detail="预置角色不可删除")
    db.query(SysUserRole).filter(SysUserRole.role_id == role_id).delete()
    db.query(SysPermission).filter(SysPermission.role_id == role_id).delete()
    db.delete(db_role)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "delete", f"删除角色 {db_role.name}")
    return {"message": "删除成功"}


@router.post("/roles/batch-delete")
def batch_delete_roles(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可操作角色")
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的角色ID列表")
    roles = db.query(SysRole).filter(SysRole.id.in_(ids)).all()
    if not roles:
        raise HTTPException(status_code=404, detail="未找到指定的角色")
    preset_roles = [r.name for r in roles if r.is_preset]
    if preset_roles:
        raise HTTPException(status_code=400, detail=f"预置角色不可删除：{', '.join(preset_roles)}")
    for role in roles:
        db.query(SysUserRole).filter(SysUserRole.role_id == role.id).delete()
        db.query(SysPermission).filter(SysPermission.role_id == role.id).delete()
        db.delete(role)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "delete", f"批量删除 {len(roles)} 个角色")
    return {"message": f"成功删除 {len(roles)} 个角色", "deleted_count": len(roles)}


@router.get("/roles/{role_id}/permissions")
def get_role_permissions(role_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    perms = db.query(SysPermission).filter(SysPermission.role_id == role_id).all()
    return [{"module": p.module, "action": p.action} for p in perms]


@router.post("/roles/{role_id}/permissions")
def assign_permissions(role_id: int, data: PermissionAssign, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可配置权限")
    db.query(SysPermission).filter(SysPermission.role_id == role_id).delete()
    for perm in data.permissions:
        db.add(SysPermission(role_id=role_id, module=perm["module"], action=perm["action"]))
    db.commit()
    return {"message": "权限配置成功"}


@router.get("/users", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    users = db.query(SysUser).all()
    return users


@router.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可创建用户")
    existing = db.query(SysUser).filter(SysUser.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"用户名 [{user.username}] 已存在")
    db_user = SysUser(
        username=user.username,
        password_hash=get_password_hash(user.password),
        display_name=user.display_name,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.flush()
    for role_id in user.role_ids:
        db.add(SysUserRole(user_id=db_user.id, role_id=role_id))
    db.commit()
    db.refresh(db_user)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "create", f"新增用户 {user.username}")
    return db_user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可编辑用户")
    db_user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    update_data = user.model_dump(exclude_unset=True)
    role_ids = update_data.pop("role_ids", None)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    if role_ids is not None:
        db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()
        for role_id in role_ids:
            db.add(SysUserRole(user_id=user_id, role_id=role_id))
    db.commit()
    db.refresh(db_user)
    write_log(db, "data_change", current_user.id, current_user.username, "system", "edit", f"编辑用户 (id={user_id})")
    return db_user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可删除用户")
    db_user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(db_user)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "system", "delete", f"删除用户 {db_user.username}")
    return {"message": "删除成功"}


@router.get("/logs", response_model=List[LogOut])
def get_logs(
    log_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(SysLog)
    if log_type:
        query = query.filter(SysLog.log_type == log_type)
    return query.order_by(SysLog.created_at.desc()).limit(limit).all()


# ========== 数据备份 ==========

def _parse_db_url() -> dict:
    """解析 DATABASE_URL，返回数据库类型和连接信息"""
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        rel_path = url.replace("sqlite:///", "")
        db_path = Path(__file__).parent.parent.parent / rel_path
        return {"type": "sqlite", "path": db_path.resolve()}
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        parsed = urlparse(url)
        return {
            "type": "postgresql",
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "user": parsed.username or "",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") or "",
        }
    return {"type": "unknown"}


def _get_backup_dir() -> Path:
    """获取备份目录路径"""
    return Path(__file__).parent.parent.parent.parent / "backups"


@router.get("/backups")
def list_backups(current_user: UserInfo = Depends(get_current_user)):
    """列出所有备份文件"""
    backup_dir = _get_backup_dir()
    if not backup_dir.exists():
        return {"backups": []}
    files = []
    # 支持 .db (SQLite) 和 .sql (PostgreSQL) 两种备份格式
    for pattern in ["e9_salary_*.db", "e9_salary_*.sql"]:
        for f in sorted(backup_dir.glob(pattern), reverse=True):
            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_display": f"{stat.st_size / 1024:.1f} KB",
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    # 按时间倒序排列
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return {"backups": files}


@router.post("/backup")
def create_backup(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """手动创建数据库备份"""
    db_info = _parse_db_url()
    db_type = db_info["type"]

    backup_dir = _get_backup_dir()
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if db_type == "sqlite":
        db_path = db_info["path"]
        if not db_path.exists():
            raise HTTPException(status_code=404, detail=f"数据库文件不存在: {db_path}")
        backup_file = backup_dir / f"e9_salary_{timestamp}.db"
        shutil.copy2(db_path, backup_file)

    elif db_type == "postgresql":
        backup_file = backup_dir / f"e9_salary_{timestamp}.sql"
        env = {"PGPASSWORD": db_info["password"]}
        cmd = [
            "pg_dump",
            "-h", db_info["host"],
            "-p", db_info["port"],
            "-U", db_info["user"],
            "-d", db_info["database"],
            "-f", str(backup_file),
            "--no-owner",
            "--no-acl",
        ]
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"数据库备份失败: {result.stderr.strip()}"
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="pg_dump 命令不可用，请确认后端容器已安装 PostgreSQL 客户端工具"
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="数据库备份超时，请稍后重试")

    else:
        raise HTTPException(status_code=400, detail="当前数据库类型不支持自动备份，请手动导出")

    write_log(db, "data_change", current_user.id, current_user.username, "system", "backup",
              f"数据库备份完成: {backup_file.name}")

    return {
        "success": True,
        "message": "备份成功",
        "filename": backup_file.name,
        "size": backup_file.stat().st_size,
        "size_display": f"{backup_file.stat().st_size / 1024:.1f} KB",
    }