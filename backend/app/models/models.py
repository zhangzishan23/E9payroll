from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, DECIMAL, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SysUser(Base):
    __tablename__ = "sys_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    display_name = Column(String(50), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    login_fail_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SysRole(Base):
    __tablename__ = "sys_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    is_preset = Column(Boolean, default=False)
    data_scope = Column(String(20), default="all")
    created_at = Column(DateTime, server_default=func.now())


class SysUserRole(Base):
    __tablename__ = "sys_user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("sys_roles.id"), nullable=False)


class SysPermission(Base):
    __tablename__ = "sys_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("sys_roles.id"), nullable=False)
    module = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)


class SysDictBase(Base):
    __tablename__ = "sys_dict_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SysLog(Base):
    __tablename__ = "sys_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    module = Column(String(50), nullable=True)
    action = Column(String(20), nullable=True)
    target = Column(String(200), nullable=True)
    detail = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    result = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_no = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=False)
    id_card = Column(String(18), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    contract_company_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    cost_owner = Column(String(50), nullable=True)
    entry_date = Column(Date, nullable=False)
    regular_date = Column(Date, nullable=True)
    resign_date = Column(Date, nullable=True)
    bank_card = Column(String(30), nullable=True)
    bank_branch = Column(String(100), nullable=True)
    home_address = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EmployeeSalary(Base):
    __tablename__ = "employee_salaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    base_salary = Column(DECIMAL(10, 2), nullable=False)
    monthly_standard = Column(DECIMAL(10, 2), default=0)
    entry_date = Column(Date, nullable=True)
    performance_standard = Column(DECIMAL(10, 2), nullable=False)
    meal_allowance = Column(DECIMAL(10, 2), default=0)
    transport_allowance = Column(DECIMAL(10, 2), default=0)
    communication_allowance = Column(DECIMAL(10, 2), default=0)
    computer_allowance = Column(DECIMAL(10, 2), default=0)
    housing_allowance = Column(DECIMAL(10, 2), default=0)
    effective_date = Column(Date, nullable=False)
    change_reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    total_work_days = Column(DECIMAL(4, 1), nullable=False)
    actual_work_days = Column(DECIMAL(4, 1), nullable=False)
    attendance_rate = Column(DECIMAL(5, 4), nullable=False)
    late_count = Column(Integer, default=0)
    early_count = Column(Integer, default=0)
    missed_punch_count = Column(Integer, default=0)
    sick_leave_days = Column(DECIMAL(4, 1), default=0)
    personal_leave_days = Column(DECIMAL(4, 1), default=0)
    annual_leave_days = Column(DECIMAL(4, 1), default=0)
    other_leave_days = Column(DECIMAL(4, 1), default=0)
    is_home_checkin = Column(Boolean, default=False)
    need_verify = Column(Boolean, default=False)
    verify_status = Column(String(20), nullable=True)
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PerformanceScore(Base):
    __tablename__ = "performance_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    initial_score = Column(DECIMAL(5, 2), nullable=True)
    final_score = Column(DECIMAL(5, 2), nullable=True)
    coefficient = Column(DECIMAL(4, 2), nullable=False, default=1.00)
    reviewer_id = Column(Integer, ForeignKey("sys_users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SocialInsurance(Base):
    __tablename__ = "social_insurance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    si_base = Column(DECIMAL(10, 2), nullable=False)
    pension_personal = Column(DECIMAL(10, 2), default=0)
    unemployment_personal = Column(DECIMAL(10, 2), default=0)
    medical_personal = Column(DECIMAL(10, 2), default=0)
    si_personal = Column(DECIMAL(10, 2), nullable=False)
    pension_company = Column(DECIMAL(10, 2), default=0)
    unemployment_company = Column(DECIMAL(10, 2), default=0)
    medical_company = Column(DECIMAL(10, 2), default=0)
    si_company = Column(DECIMAL(10, 2), nullable=False)
    hf_base = Column(DECIMAL(10, 2), nullable=False)
    hf_personal = Column(DECIMAL(10, 2), nullable=False)
    hf_company = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class LegacyAdjustment(Base):
    __tablename__ = "legacy_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    adjustment_type = Column(String(30), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    is_pretax = Column(Boolean, nullable=False)
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class TravelReimbursement(Base):
    __tablename__ = "travel_reimbursements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class LaborCompensation(Base):
    __tablename__ = "labor_compensations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SalaryCalculation(Base):
    __tablename__ = "salary_calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    contract_company = Column(String(50), nullable=False)
    department = Column(String(50), nullable=False)
    position = Column(String(50), nullable=False)
    cost_owner = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False)
    entry_date = Column(Date, nullable=True)
    base_salary = Column(DECIMAL(10, 2), nullable=False)
    monthly_standard = Column(DECIMAL(10, 2), default=0)
    performance_standard = Column(DECIMAL(10, 2), nullable=False)
    performance_coefficient = Column(DECIMAL(4, 2), default=1.00)
    actual_performance = Column(DECIMAL(10, 2), default=0)
    effective_performance = Column(DECIMAL(10, 2), default=0)
    meal_allowance = Column(DECIMAL(10, 2), default=0)
    transport_allowance = Column(DECIMAL(10, 2), default=0)
    communication_allowance = Column(DECIMAL(10, 2), default=0)
    computer_allowance = Column(DECIMAL(10, 2), default=0)
    housing_allowance = Column(DECIMAL(10, 2), default=0)
    allowance_total = Column(DECIMAL(10, 2), default=0)
    commission_bonus = Column(DECIMAL(10, 2), default=0)
    pretax_adjustment = Column(DECIMAL(10, 2), default=0)
    posttax_adjustment = Column(DECIMAL(10, 2), default=0)
    posttax_adjustment_reason = Column(String(200), nullable=True)
    total_work_days = Column(DECIMAL(4, 1), nullable=False)
    actual_work_days = Column(DECIMAL(4, 1), nullable=False)
    attendance_rate = Column(DECIMAL(5, 4), nullable=False)
    gross_salary = Column(DECIMAL(10, 2), nullable=False)
    pension_personal = Column(DECIMAL(10, 2), default=0)
    unemployment_personal = Column(DECIMAL(10, 2), default=0)
    medical_personal = Column(DECIMAL(10, 2), default=0)
    social_insurance_personal = Column(DECIMAL(10, 2), default=0)
    housing_fund_personal = Column(DECIMAL(10, 2), default=0)
    si_hf_total = Column(DECIMAL(10, 2), default=0)
    tax_deduction = Column(DECIMAL(10, 2), default=0)
    net_salary = Column(DECIMAL(10, 2), nullable=False)
    last_month_untaxed = Column(DECIMAL(10, 2), default=0)
    travel_untaxed = Column(DECIMAL(10, 2), default=0)
    compensation_tax = Column(DECIMAL(10, 2), default=0)
    actual_taxable = Column(DECIMAL(10, 2), default=0)
    special_deduction = Column(DECIMAL(10, 2), default=0)
    review_status = Column(String(20), default="待审核")
    calculation_status = Column(String(20), default="草稿")
    data_completeness = Column(String(20), default="完整")
    missing_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CalculationLog(Base):
    __tablename__ = "calculation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(32), unique=True, nullable=False)
    period = Column(String(7), nullable=False)
    calculation_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(DECIMAL(10, 2), nullable=True)
    total_employees = Column(Integer, nullable=False)
    success_count = Column(Integer, nullable=False)
    failed_count = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    calculation_id = Column(Integer, ForeignKey("salary_calculations.id"), nullable=False)
    slip_status = Column(String(20), default="待审核")
    sent_status = Column(String(20), default="未发送")
    created_at = Column(DateTime, server_default=func.now())


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    approval_no = Column(String(32), nullable=False)
    period = Column(String(7), nullable=False)
    submitter_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    submitter_name = Column(String(50), nullable=False)
    submit_time = Column(DateTime, nullable=False)
    approval_level = Column(String(20), nullable=False)
    approver_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    approver_name = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    opinion = Column(String(500), nullable=True)
    approval_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())