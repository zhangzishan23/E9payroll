from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, DECIMAL, ForeignKey, JSON, func
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
    employee_no = Column(String(64), unique=True, nullable=False)
    dingtalk_user_id = Column(String(64), unique=True, nullable=True, comment="钉钉员工userId")
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=True, default="未知")
    id_card = Column(String(18), unique=True, nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(100), nullable=True, comment="邮箱")
    work_place = Column(String(100), nullable=True, comment="办公地点")
    contract_company_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("sys_dict_base.id"), nullable=False)
    position_level = Column(String(50), nullable=True, comment="岗位职级")
    employee_type = Column(String(50), nullable=True, comment="员工类型")
    job_level = Column(String(50), nullable=True, comment="岗位级别")
    cost_owner = Column(String(50), nullable=True)
    report_manager = Column(String(50), nullable=True, comment="直属主管")
    entry_date = Column(Date, nullable=False)
    regular_date = Column(Date, nullable=True)
    resign_date = Column(Date, nullable=True)
    birth_date = Column(Date, nullable=True, comment="出生日期")
    nation = Column(String(50), nullable=True, comment="民族")
    marital_status = Column(String(20), nullable=True, comment="婚姻状况")
    children_status = Column(String(50), nullable=True, comment="子女情况")
    political_status = Column(String(50), nullable=True, comment="政治面貌")
    native_place = Column(String(100), nullable=True, comment="籍贯")
    residence_type = Column(String(50), nullable=True, comment="户籍类型")
    census_address = Column(String(200), nullable=True, comment="户籍地址")
    first_work_date = Column(Date, nullable=True, comment="首次参加工作时间")
    education = Column(String(50), nullable=True, comment="学历")
    graduate_school = Column(String(100), nullable=True, comment="毕业院校")
    graduate_date = Column(Date, nullable=True, comment="毕业时间")
    major = Column(String(100), nullable=True, comment="所学专业")
    cert1 = Column(String(100), nullable=True, comment="资格证/职称证1")
    cert2 = Column(String(100), nullable=True, comment="资格证/职称证2")
    emergency_contact_name = Column(String(100), nullable=True, comment="紧急联系人姓名")
    emergency_contact_relation = Column(String(100), nullable=True, comment="联系人关系")
    emergency_contact_phone = Column(String(50), nullable=True, comment="联系人电话")
    contract_start_date = Column(Date, nullable=True, comment="现合同起始日")
    contract_end_date = Column(Date, nullable=True, comment="现合同到期日")
    contract_type = Column(String(50), nullable=True, comment="合同类型")
    insurance_start_date = Column(Date, nullable=True, comment="五险一金起购日期")
    insurance_location = Column(String(100), nullable=True, comment="社保公积金购买地")
    recruitment_channel = Column(String(100), nullable=True, comment="招聘渠道")
    hobby = Column(String(200), nullable=True, comment="特长爱好")
    commercial_insurance_type = Column(String(50), nullable=True, comment="商业保险类型")
    remark = Column(String(500), nullable=True, comment="备注")
    bank_card = Column(String(30), nullable=True)
    bank_branch = Column(String(100), nullable=True)
    bank_branch_detail = Column(String(100), nullable=True, comment="开户行支行")
    home_address = Column(String(200), nullable=True)
    dept_path = Column(String(500), nullable=True, comment="部门全路径")
    dept_level1 = Column(String(100), nullable=True, comment="1级部门")
    dept_level2 = Column(String(100), nullable=True, comment="2级部门")
    dept_level3 = Column(String(100), nullable=True, comment="3级部门")
    dept_level4 = Column(String(100), nullable=True, comment="4级部门")
    dept_level5 = Column(String(100), nullable=True, comment="5级部门")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EmployeeSalary(Base):
    __tablename__ = "employee_salaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    base_salary = Column(DECIMAL(10, 2), nullable=False)
    base_salary_ratio = Column(DECIMAL(3, 2), default=1.00, nullable=False, comment="基本工资比例，试用期0.8/正式1.0")
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
    operator_id = Column(Integer, ForeignKey("sys_users.id"), nullable=True, comment="操作人ID")
    created_at = Column(DateTime, server_default=func.now())


class EmployeeSalaryAdjustment(Base):
    """月中调薪记录表 — 对应 Excel「转正及月中调薪」Sheet"""
    __tablename__ = "employee_salary_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, comment="调整月份，格式 YYYYMM")
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    # 调整前
    base_salary_before = Column(DECIMAL(10, 2), nullable=False, comment="调整前基本工资")
    bonus_before = Column(DECIMAL(10, 2), default=0, comment="调整前奖金")
    performance_standard_before = Column(DECIMAL(10, 2), default=0, comment="调整前绩效奖金标准")
    actual_performance_before = Column(DECIMAL(10, 2), default=0, comment="调整前实发绩效奖金标准")
    total_before = Column(DECIMAL(10, 2), nullable=False, comment="调整前工资标准合计")
    # 调整后
    base_salary_after = Column(DECIMAL(10, 2), nullable=False, comment="调整后基本工资")
    bonus_after = Column(DECIMAL(10, 2), default=0, comment="调整后奖金")
    performance_standard_after = Column(DECIMAL(10, 2), default=0, comment="调整后绩效奖金标准")
    actual_performance_after = Column(DECIMAL(10, 2), default=0, comment="调整后实发绩效奖金标准")
    total_after = Column(DECIMAL(10, 2), nullable=False, comment="调整后工资标准合计")
    # 折算后
    base_salary_prorated = Column(DECIMAL(10, 2), default=0, comment="折算后基本工资")
    commission_prorated = Column(DECIMAL(10, 2), default=0, comment="折算后提成/项目奖金/补发")
    performance_standard_prorated = Column(DECIMAL(10, 2), default=0, comment="折算后绩效奖金标准")
    actual_performance_prorated = Column(DECIMAL(10, 2), default=0, comment="折算后实发绩效奖金标准")
    total_prorated = Column(DECIMAL(10, 2), default=0, comment="折算后工资标准合计")
    # 调薪日期与天数
    month_start = Column(Date, nullable=False, comment="月初")
    adjustment_date = Column(Date, nullable=False, comment="调薪日期")
    month_end = Column(Date, nullable=False, comment="月末")
    days_before = Column(DECIMAL(4, 1), default=0, comment="调整前计薪天数")
    days_after = Column(DECIMAL(4, 1), default=0, comment="调整后计薪天数")
    total_days = Column(DECIMAL(4, 1), default=0, comment="当月总计薪天数")
    base_salary_ratio = Column(DECIMAL(3, 2), default=1.00, comment="基本工资比例")
    adjustment_type = Column(String(20), default="转正调薪", comment="调整类型：转正调薪/月中调薪")
    created_at = Column(DateTime, server_default=func.now())


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # === 考勤基本信息 ===
    total_work_days = Column(DECIMAL(4, 2), nullable=False, comment="当月总计薪天数(钉钉应出勤天数)")
    actual_work_days = Column(DECIMAL(4, 2), nullable=False, comment="出勤天数")
    attendance_rate = Column(DECIMAL(5, 4), nullable=False, comment="出勤率")
    rest_days = Column(DECIMAL(4, 2), default=0, comment="休息天数")
    work_hours = Column(DECIMAL(7, 2), default=0, comment="工作时长(分钟)")

    # === 计薪相关（加工字段） ===
    salary_start_date = Column(Date, nullable=True, comment="计薪开始日期")
    salary_end_date = Column(Date, nullable=True, comment="计薪截至日期")
    adjusted_salary_days = Column(DECIMAL(5, 2), nullable=False, default=0, comment="应计薪天数(总计薪-扣减)")
    actual_salary_days = Column(DECIMAL(5, 2), nullable=False, default=0, comment="计薪天数(实际计薪)")
    late_to_personal_leave_days = Column(DECIMAL(4, 2), default=0, comment="迟到转事假(天)")
    leave_total_days = Column(DECIMAL(5, 2), default=0, comment="请假合计(天)")

    # === 补卡 ===
    resupplement_count = Column(Integer, default=0, comment="补卡次数")

    # === 迟到相关 ===
    late_count = Column(Integer, default=0, comment="迟到次数")
    late_duration = Column(Integer, default=0, comment="迟到时长(分钟)")
    severe_late_count = Column(Integer, default=0, comment="严重迟到次数")
    severe_late_duration = Column(Integer, default=0, comment="严重迟到时长(分钟)")
    absenteeism_late_count = Column(Integer, default=0, comment="旷工迟到次数")
    absenteeism_late_days = Column(DECIMAL(4, 2), default=0, comment="旷工迟到天数")
    late_over_10min_count = Column(Integer, default=0, comment="迟到10分钟以上次数")
    late_over_30min_count = Column(Integer, default=0, comment="迟到30分钟以上次数")

    # === 早退相关 ===
    early_count = Column(Integer, default=0, comment="早退次数")
    early_duration = Column(Integer, default=0, comment="早退时长(分钟)")

    # === 缺卡相关 ===
    missed_clock_in_count = Column(Integer, default=0, comment="上班缺卡次数")
    missed_clock_out_count = Column(Integer, default=0, comment="下班缺卡次数")
    missed_punch_count = Column(Integer, default=0, comment="缺卡总次数(上下班合计)")
    half_day_missed_punch = Column(Integer, default=0, comment="半天缺卡次数合计")

    # === 旷工 ===
    absenteeism_days = Column(DECIMAL(4, 2), default=0, comment="旷工天数")

    # === 出差/外出 ===
    business_travel_duration = Column(DECIMAL(5, 2), default=0, comment="出差时长(小时)")
    out_duration = Column(DECIMAL(5, 2), default=0, comment="外出时长(小时)")

    # === 加班相关 ===
    overtime_approval_count = Column(DECIMAL(4, 2), default=0, comment="加班-审批单统计")
    workday_overtime = Column(DECIMAL(5, 2), default=0, comment="工作日加班(小时)")
    weekend_overtime = Column(DECIMAL(5, 2), default=0, comment="休息日加班(小时)")
    holiday_overtime = Column(DECIMAL(5, 2), default=0, comment="节假日加班(小时)")
    total_overtime = Column(DECIMAL(5, 2), default=0, comment="加班总时长(小时)")
    workday_overtime_pay = Column(DECIMAL(5, 2), default=0, comment="工作日(转加班费)")
    weekend_overtime_pay = Column(DECIMAL(5, 2), default=0, comment="休息日(转加班费)")
    holiday_overtime_pay = Column(DECIMAL(5, 2), default=0, comment="节假日(转加班费)")
    workday_overtime_leave = Column(DECIMAL(5, 2), default=0, comment="工作日(转调休)")
    weekend_overtime_leave = Column(DECIMAL(5, 2), default=0, comment="休息日(转调休)")
    holiday_overtime_leave = Column(DECIMAL(5, 2), default=0, comment="节假日(转调休)")

    # === 晚下班统计 ===
    clock_out_after_7pm_count = Column(Integer, default=0, comment="下班晚于7点次数")
    clock_out_after_8pm_count = Column(Integer, default=0, comment="下班晚于8点次数")
    clock_out_after_9pm_count = Column(Integer, default=0, comment="下班晚于9点次数")

    # === 打卡次数 ===
    punch_count = Column(Integer, default=0, comment="打卡次数")

    # === 班次信息 ===
    shift_type = Column(String(50), nullable=True, comment="出勤班次")
    shift_name = Column(String(100), nullable=True, comment="班次名称")

    # === 请假分项（从钉钉'考勤结果'列解析） ===
    personal_leave_days = Column(DECIMAL(4, 2), default=0, comment="事假(天)")
    full_pay_sick_days = Column(DECIMAL(4, 2), default=0, comment="全薪病假(天)")
    reduced_pay_sick_days = Column(DECIMAL(4, 2), default=0, comment="减薪病假(天)")
    statutory_sick_days = Column(DECIMAL(4, 2), default=0, comment="法定病假(天)")
    sick_leave_days = Column(DECIMAL(4, 2), default=0, comment="病假合计(天)")
    annual_leave_days = Column(DECIMAL(4, 2), default=0, comment="年假(天)")
    compensatory_leave_days = Column(DECIMAL(4, 2), default=0, comment="调休(天)")
    prenatal_checkup_days = Column(DECIMAL(4, 2), default=0, comment="产检假(天)")
    maternity_leave_days = Column(DECIMAL(4, 2), default=0, comment="产假(天)")
    paternity_leave_days = Column(DECIMAL(4, 2), default=0, comment="陪产假(天)")
    marriage_leave_days = Column(DECIMAL(4, 2), default=0, comment="婚假(天)")
    funeral_leave_days = Column(DECIMAL(4, 2), default=0, comment="丧假(天)")
    engineering_compensatory_days = Column(DECIMAL(4, 2), default=0, comment="调休-工程交付(天)")
    other_leave_days = Column(DECIMAL(4, 2), default=0, comment="其他假合计(天)")

    # === 审核标记 ===
    is_home_checkin = Column(Boolean, default=False)
    need_verify = Column(Boolean, default=False)
    verify_status = Column(String(20), nullable=True)
    remark = Column(String(500), nullable=True)

    # === 数据锁定 ===
    is_row_locked = Column(Boolean, default=False, comment="整行锁定：锁定后同步时不更新该员工任何考勤数据")
    locked_fields = Column(JSON, nullable=True, comment="单元格锁定：JSON格式，如{'late_count': true, 'personal_leave_days': true}，锁定的字段在同步时不更新")
    special_apply_ids = Column(JSON, nullable=True, comment="已应用的特殊申请单ID列表，避免重复应用")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PerformanceScore(Base):
    __tablename__ = "performance_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    initial_score = Column(DECIMAL(5, 2), nullable=True, comment="初评（绩效系数）")
    final_score = Column(DECIMAL(5, 2), nullable=True, comment="复评（绩效系数，工资核算使用此值）")
    performance_category = Column(String(50), nullable=True, comment="绩效类别")
    score_reason = Column(String(500), nullable=True, comment="评分理由")
    review_note = Column(String(500), nullable=True, comment="分管领导审核后调整说明")
    reviewer_id = Column(Integer, ForeignKey("sys_users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SocialInsurance(Base):
    __tablename__ = "social_insurance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, comment="核算月份 YYYYMM")
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_social_insurance_no = Column(String(50), nullable=True, comment="个人社保号")
    # 各险种单独基数（综合表文件使用）
    pension_personal_base = Column(DECIMAL(10, 2), nullable=True, comment="养老保险个人基数")
    pension_company_base = Column(DECIMAL(10, 2), nullable=True, comment="养老保险单位基数")
    unemployment_personal_base = Column(DECIMAL(10, 2), nullable=True, comment="失业保险个人基数")
    unemployment_company_base = Column(DECIMAL(10, 2), nullable=True, comment="失业保险单位基数")
    medical_personal_base = Column(DECIMAL(10, 2), nullable=True, comment="医疗保险个人基数")
    medical_company_base = Column(DECIMAL(10, 2), nullable=True, comment="医疗保险单位基数")
    injury_company_base = Column(DECIMAL(10, 2), nullable=True, comment="工伤保险单位基数")
    # 社保-个人缴纳金额
    pension_personal = Column(DECIMAL(10, 2), nullable=True, comment="养老保险个人金额")
    unemployment_personal = Column(DECIMAL(10, 2), nullable=True, comment="失业保险个人金额")
    medical_personal = Column(DECIMAL(10, 2), nullable=True, comment="医疗保险个人金额")
    si_personal = Column(DECIMAL(10, 2), nullable=True, comment="社保个人合计")
    # 社保-单位缴纳金额
    pension_company = Column(DECIMAL(10, 2), nullable=True, comment="养老保险单位金额")
    unemployment_company = Column(DECIMAL(10, 2), nullable=True, comment="失业保险单位金额")
    medical_company = Column(DECIMAL(10, 2), nullable=True, comment="医疗保险单位金额")
    injury_company = Column(DECIMAL(10, 2), nullable=True, comment="工伤保险单位金额")
    si_company = Column(DECIMAL(10, 2), nullable=True, comment="社保单位合计")
    # 社保-各险种缴纳比例
    pension_personal_rate = Column(DECIMAL(6, 4), nullable=True, comment="养老保险个人比例")
    pension_company_rate = Column(DECIMAL(6, 4), nullable=True, comment="养老保险单位比例")
    unemployment_personal_rate = Column(DECIMAL(6, 4), nullable=True, comment="失业保险个人比例")
    unemployment_company_rate = Column(DECIMAL(6, 4), nullable=True, comment="失业保险单位比例")
    medical_personal_rate = Column(DECIMAL(6, 4), nullable=True, comment="医疗保险个人比例")
    medical_company_rate = Column(DECIMAL(6, 4), nullable=True, comment="医疗保险单位比例")
    injury_company_rate = Column(DECIMAL(6, 4), nullable=True, comment="工伤保险单位比例")
    # 社保-各险种合计（个人+单位）
    pension_total = Column(DECIMAL(10, 2), nullable=True, comment="养老保险合计")
    unemployment_total = Column(DECIMAL(10, 2), nullable=True, comment="失业保险合计")
    medical_total = Column(DECIMAL(10, 2), nullable=True, comment="医疗保险合计")
    injury_total = Column(DECIMAL(10, 2), nullable=True, comment="工伤保险合计")
    si_grand_total = Column(DECIMAL(10, 2), nullable=True, comment="社保总合计(个人+单位)")
    # 公积金
    hf_base = Column(DECIMAL(10, 2), nullable=True, comment="公积金缴存基数")
    hf_personal = Column(DECIMAL(10, 2), nullable=True, comment="公积金个人金额")
    hf_company = Column(DECIMAL(10, 2), nullable=True, comment="公积金单位金额")
    hf_personal_rate = Column(DECIMAL(6, 4), nullable=True, comment="公积金个人比例")
    hf_company_rate = Column(DECIMAL(6, 4), nullable=True, comment="公积金单位比例")
    hf_total = Column(DECIMAL(10, 2), nullable=True, comment="公积金合计")
    # 总合计
    grand_total = Column(DECIMAL(10, 2), nullable=True, comment="社保公积金总合计")
    created_at = Column(DateTime, server_default=func.now())


class SiImportTemplate(Base):
    """社保公积金导入模板配置——适配不同政务平台导出的文件格式"""
    __tablename__ = "si_import_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="模板名称，如「广州公积金」")
    source_category = Column(String(20), nullable=False, comment="数据来源类别: social_insurance / housing_fund")
    file_type = Column(String(10), nullable=False, comment="文件类型: excel / pdf")
    city = Column(String(50), nullable=True, comment="适用城市")
    description = Column(String(500), nullable=True, comment="模板说明")
    # 文件识别
    file_pattern = Column(String(200), nullable=True, comment="文件名匹配正则，用于自动识别模板")
    file_keywords = Column(JSON, nullable=True, comment="文件名关键词列表，正则的通俗替代，如['广州','个人明细表']，只要文件名同时包含所有关键词即匹配")
    sheet_pattern = Column(String(200), nullable=True, comment="工作表名匹配正则")
    # 解析配置
    header_rows = Column(JSON, nullable=False, comment="表头行号列表(0-based)，如[6,7]表示第7-8行为表头")
    data_start_row = Column(Integer, nullable=False, comment="数据起始行号(0-based)")
    skip_footer_rows = Column(Integer, default=0, comment="跳过末尾行数")
    # 字段映射: {"文件中的列名": "数据库字段名"}
    column_mappings = Column(JSON, nullable=False, comment="列名到数据库字段的映射")
    # 行过滤规则: {"列名": "要保留的值"}，如{"缴存状态":"正常"}
    row_filters = Column(JSON, nullable=True, comment="行过滤条件，只保留满足条件的行")
    # 数值解析规则: {"remove_chars":[","], "decimal_separator":"."}
    number_format = Column(JSON, nullable=True, comment="数值解析规则")
    # 默认缴纳比例配置（用于数据源缺少比例或只有总计值时推算）
    # 格式示例:
    # {
    #   "pension": {"personal_rate": 0.08, "company_rate": 0.16},
    #   "unemployment": {"personal_rate": 0.005, "company_rate": 0.005},
    #   "medical": {"personal_rate": 0.02, "company_rate": 0.08},
    #   "injury": {"company_rate": 0.004},
    #   "hf": {"personal_rate": 0.10, "company_rate": 0.10, "split_equal": true}
    # }
    default_rates = Column(JSON, nullable=True, comment="默认缴纳比例配置，用于数据推算")
    # 管理字段
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序序号")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SiImportLog(Base):
    """社保公积金导入异常日志"""
    __tablename__ = "si_import_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, comment="核算月份")
    batch_id = Column(String(36), nullable=False, comment="导入批次UUID，同一次导入共用")
    file_name = Column(Text, nullable=True, comment="来源文件名")
    row_number = Column(Integer, nullable=True, comment="文件中的行号(1-based)")
    employee_name = Column(String(100), nullable=True, comment="涉及的员工姓名")
    error_level = Column(String(20), nullable=False, comment="级别: error(阻断) / warning(预警)")
    error_type = Column(String(50), nullable=False, comment="异常类型: file_error/name_not_found/duplicate_name/empty_name/missing_period/missing_base/amount_mismatch/duplicate_record/unknown_format")
    error_message = Column(Text, nullable=False, comment="异常描述（中文）")
    raw_data = Column(JSON, nullable=True, comment="原始行数据，便于排查")
    resolved = Column(Boolean, default=False, comment="是否已处理")
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
    contract_company = Column(String(50), nullable=False, default='')
    department = Column(String(50), nullable=False, default='')
    position = Column(String(50), nullable=False, default='')
    cost_owner = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default='')
    entry_date = Column(Date, nullable=True)
    base_salary = Column(DECIMAL(10, 2), nullable=True)
    base_salary_prorated = Column(DECIMAL(10, 2), nullable=True, comment="折算后基本工资（月中调薪后）")
    performance_standard_prorated = Column(DECIMAL(10, 2), nullable=True, comment="折算后绩效奖金标准（月中调薪后）")
    adjustment_id = Column(Integer, ForeignKey("employee_salary_adjustments.id"), nullable=True, comment="关联月中调薪记录")
    monthly_standard = Column(DECIMAL(10, 2), nullable=True)
    performance_standard = Column(DECIMAL(10, 2), nullable=True)
    performance_coefficient = Column(DECIMAL(4, 2), nullable=True)
    actual_performance = Column(DECIMAL(10, 2), nullable=True)
    effective_performance = Column(DECIMAL(10, 2), nullable=True)
    meal_allowance = Column(DECIMAL(10, 2), nullable=True)
    transport_allowance = Column(DECIMAL(10, 2), nullable=True)
    communication_allowance = Column(DECIMAL(10, 2), nullable=True)
    computer_allowance = Column(DECIMAL(10, 2), nullable=True)
    housing_allowance = Column(DECIMAL(10, 2), nullable=True)
    allowance_total = Column(DECIMAL(10, 2), nullable=True)
    commission_bonus = Column(DECIMAL(10, 2), nullable=True)
    pretax_adjustment = Column(DECIMAL(10, 2), nullable=True)
    pretax_adjustment_reason = Column(String(200), nullable=True, comment="税前调整原因")
    posttax_adjustment = Column(DECIMAL(10, 2), nullable=True)
    posttax_adjustment_reason = Column(String(200), nullable=True)
    total_work_days = Column(DECIMAL(4, 2), nullable=True)
    actual_work_days = Column(DECIMAL(4, 2), nullable=True)
    attendance_rate = Column(DECIMAL(5, 4), nullable=True)
    gross_salary = Column(DECIMAL(10, 2), nullable=True)
    pension_personal = Column(DECIMAL(10, 2), nullable=True)
    unemployment_personal = Column(DECIMAL(10, 2), nullable=True)
    medical_personal = Column(DECIMAL(10, 2), nullable=True)
    social_insurance_personal = Column(DECIMAL(10, 2), nullable=True)
    housing_fund_personal = Column(DECIMAL(10, 2), nullable=True)
    si_hf_total = Column(DECIMAL(10, 2), nullable=True)
    salary_after_si_hf = Column(DECIMAL(10, 2), nullable=True, comment="扣掉社保公积金工资")
    tax_deduction = Column(DECIMAL(10, 2), nullable=True, comment="本月应扣个税额，导入个税申报结果后才有值")
    net_salary = Column(DECIMAL(10, 2), nullable=True)
    last_month_untaxed = Column(DECIMAL(10, 2), nullable=True)
    travel_untaxed = Column(DECIMAL(10, 2), nullable=True)
    compensation_tax = Column(DECIMAL(10, 2), nullable=True)
    severance_pay = Column(DECIMAL(10, 2), nullable=True, comment="实发离职补偿金")
    year_end_bonus_untaxed = Column(DECIMAL(10, 2), nullable=True, comment="未报税年终奖")
    actual_taxable = Column(DECIMAL(10, 2), nullable=True)
    special_deduction = Column(DECIMAL(10, 2), nullable=True)
    review_status = Column(String(20), default="待审核")
    calculation_status = Column(String(20), default="待核算")
    data_completeness = Column(String(20), default="待完善")
    missing_fields = Column(JSON, nullable=True)
    remark = Column(String(500), nullable=True, comment="备注")
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


class DingtalkSyncLog(Base):
    """钉钉数据同步日志表"""
    __tablename__ = "dingtalk_sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(30), nullable=False, comment="同步类型：roster_full/roster_incremental/attendance_monthly/attendance_daily")
    status = Column(String(20), nullable=False, default="running", comment="状态：running/success/failed/partial")
    period = Column(String(7), nullable=True, comment="考勤月份 YYYYMM")
    total_count = Column(Integer, default=0, comment="总处理数")
    success_count = Column(Integer, default=0, comment="成功数")
    failed_count = Column(Integer, default=0, comment="失败数")
    created_count = Column(Integer, default=0, comment="新增数")
    updated_count = Column(Integer, default=0, comment="更新数")
    error_detail = Column(JSON, nullable=True, comment="错误详情列表")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    duration_seconds = Column(DECIMAL(10, 2), nullable=True, comment="耗时(秒)")
    created_at = Column(DateTime, server_default=func.now())


class AttendanceDaily(Base):
    """每日考勤明细表（保留2个月自动清理）"""
    __tablename__ = "attendance_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    dingtalk_user_id = Column(String(64), nullable=True, comment="钉钉userId")
    record_date = Column(Date, nullable=False, comment="考勤日期")
    check_in_time = Column(String(10), nullable=True, comment="上班打卡时间 HH:MM")
    check_out_time = Column(String(10), nullable=True, comment="下班打卡时间 HH:MM")
    status = Column(String(20), nullable=True, comment="状态：正常/迟到/早退/旷工/缺卡/请假")
    late_minutes = Column(Integer, default=0, comment="迟到分钟数")
    early_minutes = Column(Integer, default=0, comment="早退分钟数")
    is_holiday = Column(Boolean, default=False, comment="是否休息日")
    is_leave = Column(Boolean, default=False, comment="是否请假")
    leave_type = Column(String(30), nullable=True, comment="请假类型")
    remark = Column(String(200), nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        {"comment": "每日考勤明细（保留2个月自动清理）"}
    )


class SalaryCalendarOverride(Base):
    """计薪日历覆盖表（已废弃，保留兼容）— 记录用户手动覆盖的计薪日"""
    __tablename__ = "salary_calendar_override"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, comment="核算周期 YYYYMM")
    override_date = Column(Date, nullable=False, comment="覆盖日期")
    is_salary_day = Column(Boolean, nullable=False, default=False, comment="Ture=纳入计薪日(调休补班), False=排除计薪日(请假)")
    reason = Column(String(200), nullable=True, comment="覆盖原因")
    created_at = Column(DateTime, server_default=func.now())


class WorkCalendar(Base):
    """年度工作日历表 — 存储每一天的计薪状态，用于准确计算应计薪天数"""
    __tablename__ = "work_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cal_date = Column(Date, nullable=False, unique=True, comment="日期")
    year = Column(Integer, nullable=False, index=True, comment="年份")
    month = Column(Integer, nullable=False, comment="月份")
    day = Column(Integer, nullable=False, comment="日")
    weekday = Column(Integer, nullable=False, comment="星期几 0=周一 6=周日")
    day_type = Column(String(20), nullable=False, default="workday", comment="日期类型: workday=工作日 weekend=周末 holiday=法定节假日 makeup_work=调休补班")
    is_salary_day = Column(Boolean, nullable=False, default=True, comment="是否计薪日")
    remark = Column(String(100), nullable=True, comment="备注（如节日名称）")
    is_ai_generated = Column(Boolean, default=False, comment="是否AI生成")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExportTemplate(Base):
    """导出表配置模板"""
    __tablename__ = "export_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    template_type = Column(String(50), nullable=False, comment="模板类型: salary_finance=财务薪资表, salary_slip=工资条, tax=报税表, roster=花名册, attendance=考勤表, custom=自定义")
    description = Column(String(500), nullable=True, comment="模板说明")
    fields = Column(JSON, nullable=False, comment="字段配置列表: [{key:'xxx', label:'xxx', width:100}]")
    is_default = Column(Boolean, default=False, comment="是否为默认模板")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("sys_users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SalaryPeriodStep(Base):
    """月度算薪步骤确认状态表"""
    __tablename__ = "salary_period_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, index=True, comment="核算月份 YYYYMM")
    step_key = Column(String(50), nullable=False, comment="步骤标识: employee/attendance/performance/insurance/salary/approval/payment")
    is_confirmed = Column(Boolean, default=False, comment="是否已确认")
    is_force_confirmed = Column(Boolean, default=False, comment="是否强制确认（数据不全时确认）")
    confirmed_by = Column(Integer, ForeignKey("sys_users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"comment": "月度算薪步骤确认状态"}
    )