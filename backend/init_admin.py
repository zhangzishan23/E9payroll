import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import SysUser, SysRole, SysUserRole


def init_admin():
    db = SessionLocal()
    try:
        admin = db.query(SysUser).filter(SysUser.username == "admin").first()
        if admin:
            print("管理员账号 admin 已存在，重置密码为 admin123")
            admin.password_hash = get_password_hash("admin123")
            admin.is_active = True
            admin.is_admin = True
            admin.display_name = "系统管理员"
            db.commit()
            print("密码重置成功！")
            return

        print("正在创建初始管理员账号...")
        admin = SysUser(
            username="admin",
            password_hash=get_password_hash("admin123"),
            display_name="系统管理员",
            is_admin=True,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        admin_role = db.query(SysRole).filter(SysRole.name == "系统管理员").first()
        if not admin_role:
            admin_role = SysRole(
                name="系统管理员",
                description="拥有系统全部权限",
                is_preset=True,
                data_scope="all"
            )
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        user_role = SysUserRole(user_id=admin.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()

        print("=" * 50)
        print("初始管理员账号创建成功！")
        print("用户名: admin")
        print("密码:   admin123")
        print("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    init_admin()
