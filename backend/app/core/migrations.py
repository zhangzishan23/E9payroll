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
