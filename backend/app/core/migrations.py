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
    else:
        _run_pg_migrations()
        _run_attendance_precision_migration()


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
