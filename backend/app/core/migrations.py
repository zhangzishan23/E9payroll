"""
数据库迁移：在 create_all 之后执行，为已有表添加新增字段。
"""
from sqlalchemy import text
from app.core.database import engine, DATABASE_URL


def run_migrations():
    """在应用启动时执行增量迁移"""
    is_sqlite = "sqlite" in DATABASE_URL

    if is_sqlite:
        _run_sqlite_migrations()
        _run_sqlite_nullable_migration()
    else:
        _run_pg_migrations()
        _run_pg_nullable_migration()
        _run_attendance_precision_migration()
        _run_salary_nullable_migration()
    _run_salary_export_migrations()
    _run_attendance_lock_migrations()
    _run_salary_split_migrations()
    _run_salary_additional_fields_migration()
    _run_permission_split_migration()
    _run_dashboard_leader_permission_migration()
    _run_dashboard_work_view_permission_migration()
    _run_salary_calculate_permission_split_migration()
    _run_remove_salary_create_permission_migration()
    _run_remove_invalid_permissions_migration()
    _run_permission_action_length_migration()
    _add_contract_warning_permissions_to_presets()
    _remove_duplicate_contract_warning_schedule()
    _init_default_schedules()


def _run_pg_migrations():
    """PostgreSQL: 使用 IF NOT EXISTS 安全添加新列"""
    new_columns = [
        "employee_social_insurance_no VARCHAR(50)",
        "pension_personal_base DECIMAL(10, 2) DEFAULT 0",
        "pension_company_base DECIMAL(10, 2) DEFAULT 0",
        "unemployment_personal_base DECIMAL(10, 2) DEFAULT 0",
        "unemployment_company_base DECIMAL(10, 2) DEFAULT 0",
        "medical_personal_base DECIMAL(10, 2) DEFAULT 0",
        "medical_company_base DECIMAL(10, 2) DEFAULT 0",
        "injury_company_base DECIMAL(10, 2) DEFAULT 0",
        "injury_company DECIMAL(10, 2) DEFAULT 0",
        "pension_personal_rate DECIMAL(6, 4) DEFAULT 0",
        "pension_company_rate DECIMAL(6, 4) DEFAULT 0",
        "unemployment_personal_rate DECIMAL(6, 4) DEFAULT 0",
        "unemployment_company_rate DECIMAL(6, 4) DEFAULT 0",
        "medical_personal_rate DECIMAL(6, 4) DEFAULT 0",
        "medical_company_rate DECIMAL(6, 4) DEFAULT 0",
        "injury_company_rate DECIMAL(6, 4) DEFAULT 0",
        "pension_total DECIMAL(10, 2) DEFAULT 0",
        "unemployment_total DECIMAL(10, 2) DEFAULT 0",
        "medical_total DECIMAL(10, 2) DEFAULT 0",
        "injury_total DECIMAL(10, 2) DEFAULT 0",
        "si_grand_total DECIMAL(10, 2) DEFAULT 0",
        "hf_personal_rate DECIMAL(6, 4) DEFAULT 0",
        "hf_company_rate DECIMAL(6, 4) DEFAULT 0",
        "hf_total DECIMAL(10, 2) DEFAULT 0",
        "grand_total DECIMAL(10, 2) DEFAULT 0",
    ]
    with engine.begin() as conn:
        for col_def in new_columns:
            conn.execute(text(
                f"ALTER TABLE social_insurance ADD COLUMN IF NOT EXISTS {col_def}"
            ))
        # 社保导入模板表：添加默认缴纳比例配置列
        conn.execute(text(
            "ALTER TABLE si_import_templates ADD COLUMN IF NOT EXISTS default_rates JSON"
        ))
        # 添加文件关键词列（用于关键词匹配，替代正则）
        conn.execute(text(
            "ALTER TABLE si_import_templates ADD COLUMN IF NOT EXISTS file_keywords JSON"
        ))


def _run_sqlite_migrations():
    """SQLite: 检查列是否存在，不存在则添加"""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(social_insurance)"))
        existing_cols = {row[1] for row in result.fetchall()}

        new_columns = [
            ("employee_social_insurance_no", "VARCHAR(50)"),
            ("pension_personal_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("pension_company_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("unemployment_personal_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("unemployment_company_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("medical_personal_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("medical_company_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("injury_company_base", "DECIMAL(10, 2) DEFAULT 0"),
            ("injury_company", "DECIMAL(10, 2) DEFAULT 0"),
            ("pension_personal_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("pension_company_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("unemployment_personal_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("unemployment_company_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("medical_personal_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("medical_company_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("injury_company_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("pension_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("unemployment_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("medical_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("injury_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("si_grand_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("hf_personal_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("hf_company_rate", "DECIMAL(6, 4) DEFAULT 0"),
            ("hf_total", "DECIMAL(10, 2) DEFAULT 0"),
            ("grand_total", "DECIMAL(10, 2) DEFAULT 0"),
        ]
        for col_name, col_def in new_columns:
            if col_name not in existing_cols:
                conn.execute(text(
                    f"ALTER TABLE social_insurance ADD COLUMN {col_name} {col_def}"
                ))

        # 社保导入模板表迁移
        result_tpl = conn.execute(text("PRAGMA table_info(si_import_templates)"))
        existing_tpl_cols = {row[1] for row in result_tpl.fetchall()}
        tpl_new_columns = [
            ("default_rates", "TEXT"),
            ("file_keywords", "TEXT"),
        ]
        for col_name, col_def in tpl_new_columns:
            if col_name not in existing_tpl_cols:
                conn.execute(text(
                    f"ALTER TABLE si_import_templates ADD COLUMN {col_name} {col_def}"
                ))

        conn.commit()


def _run_attendance_precision_migration():
    """将考勤表中 DECIMAL(X,1) 字段升级为 DECIMAL(X,2)，保留钉钉源数据精度"""
    pg_columns = [
        ("attendance_records", "total_work_days", "DECIMAL(4, 2)"),
        ("attendance_records", "actual_work_days", "DECIMAL(4, 2)"),
        ("attendance_records", "rest_days", "DECIMAL(4, 2)"),
        ("attendance_records", "work_hours", "DECIMAL(7, 2)"),
        ("attendance_records", "absenteeism_late_days", "DECIMAL(4, 2)"),
        ("attendance_records", "business_travel_duration", "DECIMAL(5, 2)"),
        ("attendance_records", "out_duration", "DECIMAL(5, 2)"),
        ("attendance_records", "overtime_approval_count", "DECIMAL(4, 2)"),
        ("attendance_records", "workday_overtime", "DECIMAL(5, 2)"),
        ("attendance_records", "weekend_overtime", "DECIMAL(5, 2)"),
        ("attendance_records", "holiday_overtime", "DECIMAL(5, 2)"),
        ("attendance_records", "total_overtime", "DECIMAL(5, 2)"),
        ("attendance_records", "workday_overtime_pay", "DECIMAL(5, 2)"),
        ("attendance_records", "weekend_overtime_pay", "DECIMAL(5, 2)"),
        ("attendance_records", "holiday_overtime_pay", "DECIMAL(5, 2)"),
        ("attendance_records", "workday_overtime_leave", "DECIMAL(5, 2)"),
        ("attendance_records", "weekend_overtime_leave", "DECIMAL(5, 2)"),
        ("attendance_records", "holiday_overtime_leave", "DECIMAL(5, 2)"),
        ("salary_calculations", "total_work_days", "DECIMAL(4, 2)"),
        ("salary_calculations", "actual_work_days", "DECIMAL(4, 2)"),
    ]

    with engine.begin() as conn:
        for table, column, new_type in pg_columns:
            conn.execute(text(
                f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type}"
            ))


# 需要修改为允许NULL的社保字段列表
SI_NULLABLE_FIELDS = [
    "pension_personal_base", "pension_company_base",
    "unemployment_personal_base", "unemployment_company_base",
    "medical_personal_base", "medical_company_base",
    "injury_company_base",
    "pension_personal", "unemployment_personal", "medical_personal",
    "si_personal",
    "pension_company", "unemployment_company", "medical_company", "injury_company",
    "si_company",
    "pension_personal_rate", "pension_company_rate",
    "unemployment_personal_rate", "unemployment_company_rate",
    "medical_personal_rate", "medical_company_rate", "injury_company_rate",
    "pension_total", "unemployment_total", "medical_total", "injury_total",
    "si_grand_total",
    "hf_base", "hf_personal", "hf_company",
    "hf_personal_rate", "hf_company_rate", "hf_total",
    "grand_total",
]


def _run_pg_nullable_migration():
    """PostgreSQL: 将社保表所有数值字段改为允许NULL，移除NOT NULL约束"""
    with engine.begin() as conn:
        for col in SI_NULLABLE_FIELDS:
            conn.execute(text(
                f"ALTER TABLE social_insurance ALTER COLUMN {col} DROP NOT NULL"
            ))
            conn.execute(text(
                f"ALTER TABLE social_insurance ALTER COLUMN {col} DROP DEFAULT"
            ))


def _run_sqlite_nullable_migration():
    """SQLite: 重建表以允许所有社保字段为NULL
    
    SQLite不支持直接修改列约束，需要通过重建表实现：
    1. 创建符合新结构的临时表
    2. 复制数据（保留现有数据中的0值，不自动转为NULL）
    3. 删除旧表
    4. 重命名临时表为原表名
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "social_insurance" not in tables:
        return

    with engine.begin() as conn:
        # 检查是否已经迁移过（通过检查hf_base列是否有NOT NULL约束来判断）
        result = conn.execute(text("PRAGMA table_info(social_insurance)"))
        cols_info = {row[1]: row for row in result.fetchall()}
        hf_base_notnull = cols_info.get("hf_base", (None, None, None, None))[3]
        if hf_base_notnull == 0:
            return

        # 创建新表（所有数值字段允许NULL，无DEFAULT值）
        conn.execute(text("""
            CREATE TABLE social_insurance_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period VARCHAR(7) NOT NULL,
                employee_id INTEGER NOT NULL,
                employee_social_insurance_no VARCHAR(50),
                pension_personal_base DECIMAL(10, 2),
                pension_company_base DECIMAL(10, 2),
                unemployment_personal_base DECIMAL(10, 2),
                unemployment_company_base DECIMAL(10, 2),
                medical_personal_base DECIMAL(10, 2),
                medical_company_base DECIMAL(10, 2),
                injury_company_base DECIMAL(10, 2),
                pension_personal DECIMAL(10, 2),
                unemployment_personal DECIMAL(10, 2),
                medical_personal DECIMAL(10, 2),
                si_personal DECIMAL(10, 2),
                pension_company DECIMAL(10, 2),
                unemployment_company DECIMAL(10, 2),
                medical_company DECIMAL(10, 2),
                injury_company DECIMAL(10, 2),
                si_company DECIMAL(10, 2),
                pension_personal_rate DECIMAL(6, 4),
                pension_company_rate DECIMAL(6, 4),
                unemployment_personal_rate DECIMAL(6, 4),
                unemployment_company_rate DECIMAL(6, 4),
                medical_personal_rate DECIMAL(6, 4),
                medical_company_rate DECIMAL(6, 4),
                injury_company_rate DECIMAL(6, 4),
                pension_total DECIMAL(10, 2),
                unemployment_total DECIMAL(10, 2),
                medical_total DECIMAL(10, 2),
                injury_total DECIMAL(10, 2),
                si_grand_total DECIMAL(10, 2),
                hf_base DECIMAL(10, 2),
                hf_personal DECIMAL(10, 2),
                hf_company DECIMAL(10, 2),
                hf_personal_rate DECIMAL(6, 4),
                hf_company_rate DECIMAL(6, 4),
                hf_total DECIMAL(10, 2),
                grand_total DECIMAL(10, 2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            )
        """))

        # 获取旧表所有列名
        old_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(social_insurance)")).fetchall()]
        common_cols = [c for c in old_cols if c in [
            "id", "period", "employee_id", "employee_social_insurance_no",
            "pension_personal_base", "pension_company_base",
            "unemployment_personal_base", "unemployment_company_base",
            "medical_personal_base", "medical_company_base", "injury_company_base",
            "pension_personal", "unemployment_personal", "medical_personal", "si_personal",
            "pension_company", "unemployment_company", "medical_company", "injury_company", "si_company",
            "pension_personal_rate", "pension_company_rate",
            "unemployment_personal_rate", "unemployment_company_rate",
            "medical_personal_rate", "medical_company_rate", "injury_company_rate",
            "pension_total", "unemployment_total", "medical_total", "injury_total", "si_grand_total",
            "hf_base", "hf_personal", "hf_company",
            "hf_personal_rate", "hf_company_rate", "hf_total", "grand_total",
            "created_at"
        ]]
        cols_str = ", ".join(common_cols)

        # 复制数据
        conn.execute(text(f"INSERT INTO social_insurance_new ({cols_str}) SELECT {cols_str} FROM social_insurance"))

        # 删除旧表，重命名新表
        conn.execute(text("DROP TABLE social_insurance"))
        conn.execute(text("ALTER TABLE social_insurance_new RENAME TO social_insurance"))


def _run_salary_export_migrations():
    """为薪资核算表添加导出所需的缺失字段（兼容SQLite和PostgreSQL）"""
    is_sqlite = "sqlite" in DATABASE_URL
    salary_new_columns = [
        ("pretax_adjustment_reason", "VARCHAR(200)"),
        ("severance_pay", "DECIMAL(10, 2) DEFAULT 0"),
        ("year_end_bonus_untaxed", "DECIMAL(10, 2) DEFAULT 0"),
        ("year_end_bonus_net", "DECIMAL(10, 2)"),
        ("salary_after_si_hf", "DECIMAL(10, 2) DEFAULT 0"),
        ("remark", "VARCHAR(500)"),
    ]
    
    with engine.begin() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(salary_calculations)"))
            existing_cols = {row[1] for row in result.fetchall()}
            for col_name, col_def in salary_new_columns:
                if col_name not in existing_cols:
                    conn.execute(text(
                        f"ALTER TABLE salary_calculations ADD COLUMN {col_name} {col_def}"
                    ))
        else:
            for col_name, col_def in salary_new_columns:
                conn.execute(text(
                    f"ALTER TABLE salary_calculations ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                ))


def _run_salary_nullable_migration():
    """PostgreSQL: 将薪资表的个税字段改为允许NULL（未报税时留空）"""
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE salary_calculations ALTER COLUMN tax_deduction DROP NOT NULL"
        ))
        conn.execute(text(
            "ALTER TABLE salary_calculations ALTER COLUMN tax_deduction DROP DEFAULT"
        ))


def _run_attendance_lock_migrations():
    """为考勤表添加数据锁定相关字段"""
    is_sqlite = "sqlite" in DATABASE_URL
    attendance_new_columns = [
        ("is_row_locked", "BOOLEAN DEFAULT FALSE"),
        ("locked_fields", "JSON"),
        ("special_apply_ids", "JSON"),
        ("remark", "VARCHAR(500)"),
    ]
    
    with engine.begin() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(attendance_records)"))
            existing_cols = {row[1] for row in result.fetchall()}
            for col_name, col_def in attendance_new_columns:
                if col_name not in existing_cols:
                    conn.execute(text(
                        f"ALTER TABLE attendance_records ADD COLUMN {col_name} {col_def}"
                    ))
        else:
            for col_name, col_def in attendance_new_columns:
                conn.execute(text(
                    f"ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                ))


def _run_salary_split_migrations():
    """为薪资表添加工资拆分相关字段：pay_company_id, pay_company_name, record_type"""
    is_sqlite = "sqlite" in DATABASE_URL
    salary_split_columns = [
        ("pay_company_id", "INTEGER"),
        ("pay_company_name", "VARCHAR(100) DEFAULT ''"),
        ("record_type", "VARCHAR(20) DEFAULT 'single'"),
    ]

    with engine.begin() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(salary_calculations)"))
            existing_cols = {row[1] for row in result.fetchall()}
            for col_name, col_def in salary_split_columns:
                if col_name not in existing_cols:
                    conn.execute(text(
                        f"ALTER TABLE salary_calculations ADD COLUMN {col_name} {col_def}"
                    ))
        else:
            for col_name, col_def in salary_split_columns:
                conn.execute(text(
                    f"ALTER TABLE salary_calculations ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                ))
            conn.execute(text("COMMENT ON COLUMN salary_calculations.pay_company_id IS '发放公司ID'"))
            conn.execute(text("COMMENT ON COLUMN salary_calculations.pay_company_name IS '发放公司名称'"))
            conn.execute(text("COMMENT ON COLUMN salary_calculations.record_type IS '记录类型: single=单条不拆分, contract=合同公司记录, payroll=实际发放公司记录'"))

            try:
                conn.execute(text("ALTER TABLE salary_calculations DROP CONSTRAINT IF EXISTS uix_period_emp"))
            except Exception:
                pass
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_salary_period_emp_company ON salary_calculations (period, employee_id, pay_company_id)"))
            except Exception:
                pass


def _run_salary_additional_fields_migration():
    """为薪资表添加补充字段：compensation_tax, posttax_adjustment_reason, holiday_red_packet_untaxed, data_completeness, missing_fields, social_insurance_personal"""
    is_sqlite = "sqlite" in DATABASE_URL
    additional_columns = [
        ("posttax_adjustment_reason", "VARCHAR(200)"),
        ("compensation_tax", "DECIMAL(10, 2)"),
        ("holiday_red_packet_untaxed", "DECIMAL(10, 2)"),
        ("data_completeness", "VARCHAR(20) DEFAULT '待完善'"),
        ("missing_fields", "JSON"),
        ("social_insurance_personal", "DECIMAL(10, 2)"),
    ]

    with engine.begin() as conn:
        if is_sqlite:
            result = conn.execute(text("PRAGMA table_info(salary_calculations)"))
            existing_cols = {row[1] for row in result.fetchall()}
            for col_name, col_def in additional_columns:
                if col_name not in existing_cols:
                    conn.execute(text(
                        f"ALTER TABLE salary_calculations ADD COLUMN {col_name} {col_def}"
                    ))
        else:
            for col_name, col_def in additional_columns:
                conn.execute(text(
                    f"ALTER TABLE salary_calculations ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                ))


def _init_default_roles_and_permissions():
    """初始化预置角色和默认权限"""
    from app.core.database import SessionLocal
    from app.models.models import SysRole, SysPermission, SysUser, SysUserRole

    db = SessionLocal()
    try:
        default_roles = [
            {
                "name": "超级管理员",
                "description": "系统最高权限，拥有所有功能访问权",
                "is_preset": True,
                "data_scope": "all",
                "permissions": []
            },
            {
                "name": "人事专员",
                "description": "负责人事信息、考勤、绩效、社保数据录入与维护",
                "is_preset": True,
                "data_scope": "all",
                "permissions": [
                    "dashboard:view", "dashboard:work_view",
                    "employee:view", "employee:create", "employee:edit", "employee:export", "employee:import", "employee:sync",
                    "attendance:view", "attendance:create", "attendance:edit", "attendance:export", "attendance:import", "attendance:sync", "attendance:writeoff",
                    "performance:view", "performance:create", "performance:edit", "performance:export", "performance:import",
                    "insurance:view", "insurance:create", "insurance:edit", "insurance:export", "insurance:import", "insurance:template",
                    "report:view", "report:export", "report:contract_warning_view", "report:contract_warning_export",
                ]
            },
            {
                "name": "人事主管",
                "description": "负责人事管理、薪资审核、审批流程处理",
                "is_preset": True,
                "data_scope": "all",
                "permissions": [
                    "dashboard:view", "dashboard:work_view", "dashboard:leader_view",
                    "employee:view", "employee:create", "employee:edit", "employee:delete", "employee:export", "employee:import", "employee:sync",
                    "attendance:view", "attendance:create", "attendance:edit", "attendance:delete", "attendance:export", "attendance:import", "attendance:sync", "attendance:writeoff",
                    "performance:view", "performance:create", "performance:edit", "performance:export", "performance:import",
                    "insurance:view", "insurance:create", "insurance:edit", "insurance:delete", "insurance:export", "insurance:import", "insurance:template",
                    "salary:view", "salary:edit", "salary:delete", "salary:check", "salary:step_confirm", "salary:export",
                    "approval:view", "approval:approve",
                    "report:view", "report:export", "report:contract_warning_view", "report:contract_warning_export",
                ]
            },
            {
                "name": "会计",
                "description": "负责薪资核算、报税、工资发放相关操作",
                "is_preset": True,
                "data_scope": "all",
                "permissions": [
                    "dashboard:view", "dashboard:work_view", "dashboard:leader_view",
                    "employee:view", "employee:export",
                    "attendance:view", "attendance:export",
                    "performance:view",
                    "insurance:view",
                    "salary:view", "salary:edit", "salary:delete", "salary:check", "salary:step_confirm", "salary:tax_export", "salary:tax_import", "salary:travel_import", "salary:export",
                    "approval:view",
                    "report:view", "report:export", "report:contract_warning_view", "report:contract_warning_export",
                ]
            },
            {
                "name": "普通员工",
                "description": "仅可查看个人相关信息",
                "is_preset": True,
                "data_scope": "self",
                "permissions": [
                    "dashboard:view", "dashboard:work_view",
                ]
            },
            {
                "name": "访客",
                "description": "新注册用户默认角色，仅可查看工作台",
                "is_preset": True,
                "data_scope": "self",
                "permissions": [
                    "dashboard:view", "dashboard:work_view",
                ]
            }
        ]

        for role_data in default_roles:
            role = db.query(SysRole).filter(SysRole.name == role_data["name"]).first()
            if not role:
                role = SysRole(
                    name=role_data["name"],
                    description=role_data["description"],
                    is_preset=role_data["is_preset"],
                    data_scope=role_data["data_scope"]
                )
                db.add(role)
                db.flush()

                if role_data["name"] != "超级管理员":
                    for perm_code in role_data["permissions"]:
                        module, action = perm_code.split(":", 1)
                        perm = SysPermission(role_id=role.id, module=module, action=action)
                        db.add(perm)

        admin_user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if admin_user and admin_user.is_admin:
            super_role = db.query(SysRole).filter(SysRole.name == "超级管理员").first()
            if super_role:
                existing = db.query(SysUserRole).filter(
                    SysUserRole.user_id == admin_user.id,
                    SysUserRole.role_id == super_role.id
                ).first()
                if not existing:
                    db.add(SysUserRole(user_id=admin_user.id, role_id=super_role.id))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _run_permission_split_migration():
    """将旧的 salary:tax 权限拆分为三个细粒度权限：tax_export, tax_import, travel_import"""
    from app.core.database import SessionLocal
    from app.models.models import SysPermission

    db = SessionLocal()
    try:
        old_perms = db.query(SysPermission).filter(
            SysPermission.module == "salary",
            SysPermission.action == "tax"
        ).all()

        new_actions = ["tax_export", "tax_import", "travel_import"]

        for old_perm in old_perms:
            for action in new_actions:
                existing = db.query(SysPermission).filter(
                    SysPermission.role_id == old_perm.role_id,
                    SysPermission.module == "salary",
                    SysPermission.action == action
                ).first()
                if not existing:
                    new_perm = SysPermission(
                        role_id=old_perm.role_id,
                        module="salary",
                        action=action
                    )
                    db.add(new_perm)

            db.delete(old_perm)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_dashboard_leader_permission_migration():
    """为已存在的人事主管和会计角色添加 dashboard:leader_view 权限"""
    from app.core.database import SessionLocal
    from app.models.models import SysRole, SysPermission

    db = SessionLocal()
    try:
        leader_roles = ["人事主管", "会计"]
        for role_name in leader_roles:
            role = db.query(SysRole).filter(SysRole.name == role_name).first()
            if not role:
                continue
            existing = db.query(SysPermission).filter(
                SysPermission.role_id == role.id,
                SysPermission.module == "dashboard",
                SysPermission.action == "leader_view"
            ).first()
            if not existing:
                perm = SysPermission(
                    role_id=role.id,
                    module="dashboard",
                    action="leader_view"
                )
                db.add(perm)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _init_default_schedules():
    """初始化默认算薪日程配置"""
    from app.core.database import SessionLocal
    from app.models.models import SysSchedule

    db = SessionLocal()
    try:
        existing_count = db.query(SysSchedule).count()
        if existing_count > 0:
            return

        default_schedules = [
            {
                "name": "员工档案确认",
                "day_of_month": 1,
                "step_key": "employee",
                "route": "/employees",
                "icon": "User",
                "color": "indigo",
                "description": "确认当月在职员工信息",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 1
            },
            {
                "name": "考勤数据同步",
                "day_of_month": 2,
                "step_key": "attendance",
                "route": "/attendance",
                "icon": "Calendar",
                "color": "green",
                "description": "同步并确认上月考勤数据",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 2
            },
            {
                "name": "绩效评分录入",
                "day_of_month": 3,
                "step_key": "performance",
                "route": "/performance",
                "icon": "TrendCharts",
                "color": "purple",
                "description": "录入上月员工绩效系数",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 3
            },
            {
                "name": "社保公积金导入",
                "day_of_month": 4,
                "step_key": "insurance",
                "route": "/insurance",
                "icon": "CreditCard",
                "color": "orange",
                "description": "导入并确认社保公积金数据",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 4
            },
            {
                "name": "个税申报",
                "day_of_month": 6,
                "step_key": "tax",
                "route": "/salary",
                "icon": "Document",
                "color": "amber",
                "description": "导出报税模板并导入申报结果",
                "is_warning": False,
                "warning_days": 3,
                "sort_order": 5
            },
            {
                "name": "薪资计算",
                "day_of_month": 8,
                "step_key": "salary",
                "route": "/salary",
                "icon": "Money",
                "color": "blue",
                "description": "核算应发与实发工资",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 6
            },
            {
                "name": "两级审批",
                "day_of_month": 10,
                "step_key": "approval",
                "route": "/approval",
                "icon": "Checked",
                "color": "cyan",
                "description": "主管和经理两级审批",
                "is_warning": False,
                "warning_days": 2,
                "sort_order": 7
            },
            {
                "name": "工资发放",
                "day_of_month": 15,
                "step_key": "payment",
                "route": "/reports",
                "icon": "Wallet",
                "color": "red",
                "description": "导出报表完成工资发放",
                "is_warning": False,
                "warning_days": 3,
                "sort_order": 8
            }
        ]

        for sched_data in default_schedules:
            sched = SysSchedule(**sched_data, is_enabled=True)
            db.add(sched)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_dashboard_work_view_permission_migration():
    """为已存在的所有预设角色添加 dashboard:work_view 权限"""
    from app.core.database import SessionLocal
    from app.models.models import SysRole, SysPermission

    db = SessionLocal()
    try:
        work_view_roles = ["人事专员", "人事主管", "会计", "普通员工", "访客"]
        for role_name in work_view_roles:
            role = db.query(SysRole).filter(SysRole.name == role_name).first()
            if not role:
                continue
            existing = db.query(SysPermission).filter(
                SysPermission.role_id == role.id,
                SysPermission.module == "dashboard",
                SysPermission.action == "work_view"
            ).first()
            if not existing:
                perm = SysPermission(
                    role_id=role.id,
                    module="dashboard",
                    action="work_view"
                )
                db.add(perm)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _remove_duplicate_contract_warning_schedule():
    """清理日程表：删除合同到期预警日程项，将所有日程的is_warning重置为False（预警为系统内置功能，日程只管理定期待办）"""
    from app.core.database import SessionLocal
    from app.models.models import SysSchedule

    db = SessionLocal()
    try:
        scheds = db.query(SysSchedule).filter(SysSchedule.name == "合同到期预警").all()
        for sched in scheds:
            db.delete(sched)

        updated = db.query(SysSchedule).filter(SysSchedule.is_warning == True).update({"is_warning": False})

        if scheds or updated > 0:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_salary_calculate_permission_split_migration():
    """将旧的 salary:calculate 权限拆分为 salary:check（数据检查）和 salary:step_confirm（步骤确认），
    同时为会计角色补充 salary:delete 权限"""
    from app.core.database import SessionLocal
    from app.models.models import SysPermission, SysRole

    db = SessionLocal()
    try:
        old_perms = db.query(SysPermission).filter(
            SysPermission.module == "salary",
            SysPermission.action == "calculate"
        ).all()

        new_actions = ["check", "step_confirm"]

        for old_perm in old_perms:
            for action in new_actions:
                existing = db.query(SysPermission).filter(
                    SysPermission.role_id == old_perm.role_id,
                    SysPermission.module == "salary",
                    SysPermission.action == action
                ).first()
                if not existing:
                    new_perm = SysPermission(
                        role_id=old_perm.role_id,
                        module="salary",
                        action=action
                    )
                    db.add(new_perm)
            db.delete(old_perm)

        accountant_role = db.query(SysRole).filter(SysRole.name == "会计").first()
        if accountant_role:
            existing = db.query(SysPermission).filter(
                SysPermission.role_id == accountant_role.id,
                SysPermission.module == "salary",
                SysPermission.action == "delete"
            ).first()
            if not existing:
                db.add(SysPermission(
                    role_id=accountant_role.id,
                    module="salary",
                    action="delete"
                ))

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_remove_salary_create_permission_migration():
    """移除不再使用的 salary:create 权限（薪资记录由系统自动批量创建，无手动新增入口）"""
    from app.core.database import SessionLocal
    from app.models.models import SysPermission

    db = SessionLocal()
    try:
        deleted = db.query(SysPermission).filter(
            SysPermission.module == "salary",
            SysPermission.action == "create"
        ).delete(synchronize_session=False)
        if deleted > 0:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_remove_invalid_permissions_migration():
    """移除不再使用的无效权限：report:view_my_slip, system:view, profile:view, profile:edit"""
    from app.core.database import SessionLocal
    from app.models.models import SysPermission

    db = SessionLocal()
    try:
        invalid_perms = [
            ("report", "view_my_slip"),
            ("system", "view"),
            ("profile", "view"),
            ("profile", "edit"),
        ]
        total_deleted = 0
        for module, action in invalid_perms:
            deleted = db.query(SysPermission).filter(
                SysPermission.module == module,
                SysPermission.action == action
            ).delete(synchronize_session=False)
            total_deleted += deleted
        if total_deleted > 0:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_permission_action_length_migration():
    """扩展 sys_permissions.action 字段长度从 20 到 50，支持更长的权限标识"""
    is_sqlite = "sqlite" in DATABASE_URL
    with engine.begin() as conn:
        if is_sqlite:
            pass
        else:
            conn.execute(text(
                "ALTER TABLE sys_permissions ALTER COLUMN action TYPE VARCHAR(50)"
            ))


def _add_contract_warning_permissions_to_presets():
    """为人事主管和会计角色补充合同到期预警相关权限"""
    from app.core.database import SessionLocal
    from app.models.models import SysRole, SysPermission

    db = SessionLocal()
    try:
        preset_roles = ["人事专员", "人事主管", "会计"]
        new_perms = [
            ("report", "contract_warning_view"),
            ("report", "contract_warning_export"),
        ]
        for role_name in preset_roles:
            role = db.query(SysRole).filter(SysRole.name == role_name).first()
            if not role:
                continue
            for module, action in new_perms:
                existing = db.query(SysPermission).filter(
                    SysPermission.role_id == role.id,
                    SysPermission.module == module,
                    SysPermission.action == action
                ).first()
                if not existing:
                    perm = SysPermission(
                        role_id=role.id,
                        module=module,
                        action=action
                    )
                    db.add(perm)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
