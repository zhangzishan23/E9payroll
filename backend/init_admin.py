import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.models import SysUser, SysRole, SysUserRole


def wait_for_db(max_retries=30, retry_interval=2):
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("数据库连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"等待数据库就绪... ({i+1}/{max_retries}) - {e}")
                time.sleep(retry_interval)
            else:
                print(f"数据库连接失败，已重试 {max_retries} 次")
                return False
    return False


def init_admin():
    db = SessionLocal()
    try:
        admin = db.query(SysUser).filter(SysUser.username == "admin").first()
        if admin:
            print("管理员账号 admin 已存在，跳过初始化")
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
    if wait_for_db():
        init_admin()
    else:
        print("警告: 数据库未就绪，跳过管理员账号初始化")
