from app.core.database import SessionLocal, engine, Base
from app.models.models import *
from app.core.security import get_password_hash
from datetime import date, datetime


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(SysUser).count() > 0:
            return

        print("开始初始化种子数据...")

        companies = [
            SysDictBase(category="contract_company", code="BJYJ", name="北京易玖", sort_order=1),
            SysDictBase(category="contract_company", code="GZ", name="广州分公司", sort_order=2),
            SysDictBase(category="contract_company", code="HD", name="邯郸分公司", sort_order=3),
            SysDictBase(category="contract_company", code="SHRF", name="上海瑞方", sort_order=4),
        ]
        db.add_all(companies)

        departments = [
            SysDictBase(category="department", code="DEPT_HR", name="人力资源部", sort_order=1),
            SysDictBase(category="department", code="DEPT_FIN", name="财务部", sort_order=2),
            SysDictBase(category="department", code="DEPT_TECH", name="技术部", sort_order=3),
            SysDictBase(category="department", code="DEPT_SALES", name="销售部", sort_order=4),
            SysDictBase(category="department", code="DEPT_OPS", name="运营部", sort_order=5),
        ]
        db.add_all(departments)

        positions = [
            SysDictBase(category="position", code="POS_MGR", name="经理", sort_order=1),
            SysDictBase(category="position", code="POS_SUPERVISOR", name="主管", sort_order=2),
            SysDictBase(category="position", code="POS_STAFF", name="专员", sort_order=3),
            SysDictBase(category="position", code="POS_ENGINEER", name="工程师", sort_order=4),
            SysDictBase(category="position", code="POS_SALES", name="销售", sort_order=5),
        ]
        db.add_all(positions)

        statuses = [
            SysDictBase(category="employee_status", code="INTERN", name="实习", sort_order=1),
            SysDictBase(category="employee_status", code="PROBATION", name="试用期", sort_order=2),
            SysDictBase(category="employee_status", code="REGULAR", name="正式", sort_order=3),
            SysDictBase(category="employee_status", code="OUTSOURCE", name="外包", sort_order=4),
            SysDictBase(category="employee_status", code="RESIGNED", name="离职", sort_order=5),
        ]
        db.add_all(statuses)

        leave_types = [
            SysDictBase(category="leave_type", code="SICK", name="病假", extra={"deduct_pay": False, "affect_attendance": True}),
            SysDictBase(category="leave_type", code="PERSONAL", name="事假", extra={"deduct_pay": True, "affect_attendance": True}),
            SysDictBase(category="leave_type", code="ANNUAL", name="年假", extra={"deduct_pay": False, "affect_attendance": False}),
            SysDictBase(category="leave_type", code="MARRIAGE", name="婚假", extra={"deduct_pay": False, "affect_attendance": False}),
            SysDictBase(category="leave_type", code="MATERNITY", name="产假", extra={"deduct_pay": False, "affect_attendance": False}),
            SysDictBase(category="leave_type", code="FUNERAL", name="丧假", extra={"deduct_pay": False, "affect_attendance": False}),
        ]
        db.add_all(leave_types)

        salary_items = [
            SysDictBase(category="salary_item", code="BASE_SALARY", name="基本工资", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="PERFORMANCE_STD", name="绩效奖金标准", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="MEAL", name="餐补", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="TRANSPORT", name="交通补", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="COMMUNICATION", name="通讯补", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="COMPUTER", name="电脑补", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="HOUSING", name="住房补", extra={"type": "fixed", "taxable": True}),
            SysDictBase(category="salary_item", code="ACTUAL_PERFORMANCE", name="实际绩效奖金", extra={"type": "variable", "taxable": True}),
            SysDictBase(category="salary_item", code="COMMISSION", name="提成/项目奖金/补发", extra={"type": "variable", "taxable": True}),
            SysDictBase(category="salary_item", code="PRETAX_ADJUST", name="税前调整金额", extra={"type": "variable", "taxable": True}),
            SysDictBase(category="salary_item", code="POSTTAX_ADJUST", name="税后调整金额", extra={"type": "variable", "taxable": False}),
            SysDictBase(category="salary_item", code="LABOR_COMPENSATION", name="劳动补偿金", extra={"type": "variable", "taxable": True, "tax_separate": True}),
            SysDictBase(category="salary_item", code="TRAVEL_REIMBURSEMENT", name="临时差旅报销", extra={"type": "variable", "taxable": True, "untaxed_note": "需本月一并报税"}),
            SysDictBase(category="salary_item", code="OTHER_REIMBURSEMENT", name="其他报销", extra={"type": "variable", "taxable": False}),
        ]
        db.add_all(salary_items)

        db.flush()

        company_map = {c.code: c.id for c in companies}
        dept_map = {d.code: d.id for d in departments}
        pos_map = {p.code: p.id for p in positions}
        status_map = {s.code: s.id for s in statuses}

        admin_role = SysRole(name="admin", description="系统管理员", is_preset=True, data_scope="all")
        hr_role = SysRole(name="人事专员", description="人事专员", is_preset=True, data_scope="all")
        hr_supervisor_role = SysRole(name="人事主管", description="人事主管", is_preset=True, data_scope="all")
        hr_manager_role = SysRole(name="人事经理", description="人事经理", is_preset=True, data_scope="all")
        accountant_role = SysRole(name="会计", description="会计", is_preset=True, data_scope="all")
        employee_role = SysRole(name="普通员工", description="普通员工", is_preset=True, data_scope="self")
        db.add_all([admin_role, hr_role, hr_supervisor_role, hr_manager_role, accountant_role, employee_role])
        db.flush()

        admin_user = SysUser(
            username="admin", password_hash=get_password_hash("admin123"),
            display_name="系统管理员", is_admin=True
        )
        hr_user = SysUser(
            username="hr001", password_hash=get_password_hash("123456"),
            display_name="张人事"
        )
        db.add_all([admin_user, hr_user])
        db.flush()

        db.add(SysUserRole(user_id=admin_user.id, role_id=admin_role.id))
        db.add(SysUserRole(user_id=hr_user.id, role_id=hr_role.id))

        all_modules = ["employee", "attendance", "salary", "approval", "report", "system", "ai_assistant"]
        all_actions = ["view", "create", "edit", "delete", "export", "use"]
        for module in all_modules:
            for action in all_actions:
                db.add(SysPermission(role_id=admin_role.id, module=module, action=action))

        hr_permissions = [
            ("employee", "view"), ("employee", "create"), ("employee", "edit"), ("employee", "delete"), ("employee", "export"),
            ("attendance", "view"), ("attendance", "create"), ("attendance", "edit"), ("attendance", "export"),
            ("salary", "view"), ("salary", "create"), ("salary", "edit"), ("salary", "export"),
            ("report", "view"), ("report", "export"),
        ]
        for module, action in hr_permissions:
            db.add(SysPermission(role_id=hr_role.id, module=module, action=action))

        mock_employees = [
            {"no": "E001", "name": "张三", "gender": "男", "id_card": "110101199001011234", "phone": "13800001001",
             "company": "BJYJ", "dept": "DEPT_TECH", "pos": "POS_ENGINEER", "status": "REGULAR",
             "entry": date(2020, 3, 1), "regular": date(2020, 6, 1),
             "base": 15000, "perf_std": 3000, "meal": 300, "transport": 200, "comm": 100, "computer": 200, "housing": 500},
            {"no": "E002", "name": "李四", "gender": "女", "id_card": "110101199102022345", "phone": "13800001002",
             "company": "BJYJ", "dept": "DEPT_HR", "pos": "POS_STAFF", "status": "REGULAR",
             "entry": date(2021, 5, 10), "regular": date(2021, 8, 10),
             "base": 8000, "perf_std": 1500, "meal": 300, "transport": 200, "comm": 100, "computer": 200, "housing": 300},
            {"no": "E003", "name": "王五", "gender": "男", "id_card": "110101199203033456", "phone": "13800001003",
             "company": "GZ", "dept": "DEPT_SALES", "pos": "POS_SALES", "status": "REGULAR",
             "entry": date(2022, 1, 15), "regular": date(2022, 4, 15),
             "base": 6000, "perf_std": 5000, "meal": 300, "transport": 300, "comm": 100, "computer": 200, "housing": 0},
            {"no": "E004", "name": "赵六", "gender": "女", "id_card": "110101199304044567", "phone": "13800001004",
             "company": "HD", "dept": "DEPT_OPS", "pos": "POS_SUPERVISOR", "status": "REGULAR",
             "entry": date(2021, 8, 1), "regular": date(2021, 11, 1),
             "base": 10000, "perf_std": 2000, "meal": 300, "transport": 200, "comm": 100, "computer": 200, "housing": 400},
            {"no": "E005", "name": "钱七", "gender": "男", "id_card": "110101199405055678", "phone": "13800001005",
             "company": "SHRF", "dept": "DEPT_FIN", "pos": "POS_MGR", "status": "REGULAR",
             "entry": date(2019, 6, 1), "regular": date(2019, 9, 1),
             "base": 18000, "perf_std": 4000, "meal": 300, "transport": 200, "comm": 100, "computer": 200, "housing": 600},
            {"no": "E006", "name": "孙八", "gender": "女", "id_card": "110101199506066789", "phone": "13800001006",
             "company": "BJYJ", "dept": "DEPT_TECH", "pos": "POS_ENGINEER", "status": "PROBATION",
             "entry": date(2026, 4, 1), "regular": None,
             "base": 12000, "perf_std": 2000, "meal": 300, "transport": 200, "comm": 100, "computer": 200, "housing": 400},
        ]

        for emp in mock_employees:
            e = Employee(
                employee_no=emp["no"], name=emp["name"], gender=emp["gender"],
                id_card=emp["id_card"], phone=emp["phone"],
                contract_company_id=company_map[emp["company"]],
                department_id=dept_map[emp["dept"]],
                position_id=pos_map[emp["pos"]],
                status_id=status_map[emp["status"]],
                entry_date=emp["entry"], regular_date=emp["regular"]
            )
            db.add(e)
            db.flush()

            es = EmployeeSalary(
                employee_id=e.id,
                base_salary=emp["base"], performance_standard=emp["perf_std"],
                meal_allowance=emp["meal"], transport_allowance=emp["transport"],
                communication_allowance=emp["comm"], computer_allowance=emp["computer"],
                housing_allowance=emp["housing"],
                effective_date=emp["entry"], change_reason="入职"
            )
            db.add(es)

        period = "202604"
        for emp_data in mock_employees:
            emp_obj = db.query(Employee).filter(Employee.employee_no == emp_data["no"]).first()
            if not emp_obj:
                continue

            ar = AttendanceRecord(
                period=period, employee_id=emp_obj.id,
                total_work_days=22, actual_work_days=22, attendance_rate=1.0000,
                late_count=0, early_count=0, missed_punch_count=0,
                sick_leave_days=0, personal_leave_days=0,
                annual_leave_days=0, other_leave_days=0,
                is_home_checkin=False, need_verify=False, verify_status="已核实"
            )
            db.add(ar)

            ps = PerformanceScore(
                period=period, employee_id=emp_obj.id,
                initial_score=95, final_score=95, coefficient=1.00,
                reviewer_id=admin_user.id
            )
            db.add(ps)

            si = SocialInsurance(
                period=period, employee_id=emp_obj.id,
                si_base=emp_data["base"], si_personal=round(emp_data["base"] * 0.105, 2),
                si_company=round(emp_data["base"] * 0.275, 2),
                hf_base=emp_data["base"], hf_personal=round(emp_data["base"] * 0.12, 2),
                hf_company=round(emp_data["base"] * 0.12, 2)
            )
            db.add(si)

        db.flush()

        company_name_map = {c.code: c.name for c in companies}
        dept_name_map = {d.code: d.name for d in departments}
        pos_name_map = {p.code: p.name for p in positions}
        status_name_map = {s.code: s.name for s in statuses}

        print("生成薪酬核算结果...")
        for emp_data in mock_employees:
            emp_obj = db.query(Employee).filter(Employee.employee_no == emp_data["no"]).first()
            if not emp_obj:
                continue

            base = emp_data["base"]
            perf_std = emp_data["perf_std"]
            meal = emp_data["meal"]
            transport = emp_data["transport"]
            comm = emp_data["comm"]
            computer = emp_data["computer"]
            housing = emp_data["housing"]
            allowance_total = meal + transport + comm + computer + housing
            perf_coef = 1.00
            actual_perf = perf_std * perf_coef
            att_rate = 1.0
            total_work_days = 22.0
            actual_work_days = 22.0

            gross_salary = round((base + allowance_total + actual_perf) * att_rate, 2)

            si_personal = round(base * 0.105, 2)
            hf_personal = round(base * 0.12, 2)
            si_hf_total = si_personal + hf_personal

            net_salary = round(gross_salary - si_hf_total, 2)

            calc = SalaryCalculation(
                period=period,
                employee_id=emp_obj.id,
                contract_company=company_name_map.get(emp_data["company"], emp_data["company"]),
                department=dept_name_map.get(emp_data["dept"], emp_data["dept"]),
                position=pos_name_map.get(emp_data["pos"], emp_data["pos"]),
                status=status_name_map.get(emp_data["status"], emp_data["status"]),
                entry_date=emp_data["entry"],
                base_salary=base,
                monthly_standard=base + perf_std + allowance_total,
                performance_standard=perf_std,
                performance_coefficient=perf_coef,
                actual_performance=actual_perf,
                meal_allowance=meal,
                transport_allowance=transport,
                communication_allowance=comm,
                computer_allowance=computer,
                housing_allowance=housing,
                allowance_total=allowance_total,
                total_work_days=total_work_days,
                actual_work_days=actual_work_days,
                attendance_rate=att_rate,
                gross_salary=gross_salary,
                social_insurance_personal=si_personal,
                housing_fund_personal=hf_personal,
                si_hf_total=si_hf_total,
                net_salary=net_salary,
                calculation_status="应发已核算"
            )
            db.add(calc)

        db.commit()
        print("种子数据初始化完成！")
        print("  管理员账号: admin / admin123")
        print("  人事专员账号: hr001 / 123456")
        print(f"  模拟员工: {len(mock_employees)} 人")
        print(f"  模拟考勤/绩效/社保/核算周期: {period}")

    except Exception as e:
        db.rollback()
        print(f"种子数据初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()