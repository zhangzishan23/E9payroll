from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
from openpyxl import Workbook
from app.core.database import get_db
from app.core.query_utils import filter_active_employees
from app.models.models import Employee, EmployeeSalary, SalaryCalculation, AttendanceRecord, SysDictBase
from app.api.auth import get_current_user, UserInfo
from sqlalchemy import func

router = APIRouter()


@router.get("/stats")
def get_stats(
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    active_employees_query = filter_active_employees(query, db)
    total_employees = active_employees_query.count()

    status_count = {}
    for emp in active_employees_query.with_entities(Employee.status_id, func.count(Employee.id)).group_by(Employee.status_id).all():
        dict_item = db.query(SysDictBase).filter(SysDictBase.id == emp[0]).first()
        status_count[dict_item.name if dict_item else "未知"] = emp[1]

    latest_period = period or db.query(SalaryCalculation.period).order_by(SalaryCalculation.period.desc()).first()
    latest_period = latest_period[0] if latest_period else None

    salary_stats = {}
    if latest_period:
        calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == latest_period).all()
        completed = sum(1 for c in calcs if c.calculation_status == "核算完成")
        salary_stats = {
            "period": latest_period,
            "total": len(calcs),
            "completed": completed,
            "pending": len(calcs) - completed,
            "review_passed": sum(1 for c in calcs if c.review_status == "审核通过"),
            "review_rejected": sum(1 for c in calcs if c.review_status == "审核驳回"),
            "avg_gross_salary": round(float(sum(c.gross_salary for c in calcs)) / len(calcs), 2) if calcs else 0,
            "avg_net_salary": round(float(sum(c.net_salary for c in calcs)) / len(calcs), 2) if calcs else 0,
        }

    att_stats = {}
    if latest_period:
        atts = db.query(AttendanceRecord).filter(AttendanceRecord.period == latest_period).all()
        if atts:
            att_stats = {
                "period": latest_period,
                "total": len(atts),
                "avg_rate": round(float(sum(a.attendance_rate for a in atts)) / len(atts) * 100, 1) if atts else 0,
                "total_late": sum(a.late_count or 0 for a in atts),
                "total_leave": sum((a.sick_leave_days or 0) + (a.personal_leave_days or 0) for a in atts),
            }

    return {
        "total_employees": total_employees,
        "status_breakdown": status_count,
        "salary_stats": salary_stats,
        "attendance_stats": att_stats
    }


@router.get("/roster")
def export_roster(db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    query = db.query(Employee)
    employees = filter_active_employees(query, db).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "花名册"

    headers = [
        "员工编号", "姓名", "性别", "身份证号", "联系方式",
        "合同公司", "部门", "职务", "用工状态", "成本归属",
        "入职时间", "转正时间", "离职日期",
        "银行卡号", "开户行", "家庭地址",
        "基本工资", "绩效标准", "餐补", "交通补贴", "通讯补贴", "电脑补贴", "住房补贴", "薪资生效日期"
    ]
    ws.append(headers)

    for emp in employees:
        salary = db.query(EmployeeSalary).filter(
            EmployeeSalary.employee_id == emp.id
        ).order_by(EmployeeSalary.effective_date.desc()).first()

        dict_ids = [emp.contract_company_id, emp.department_id, emp.position_id, emp.status_id]
        dict_items = db.query(SysDictBase).filter(SysDictBase.id.in_(dict_ids)).all()
        name_map = {d.id: d.name for d in dict_items}

        ws.append([
            emp.employee_no, emp.name, emp.gender, emp.id_card,
            emp.phone or "",
            name_map.get(emp.contract_company_id, ""),
            name_map.get(emp.department_id, ""),
            name_map.get(emp.position_id, ""),
            name_map.get(emp.status_id, ""),
            emp.cost_owner or "",
            str(emp.entry_date) if emp.entry_date else "",
            str(emp.regular_date) if emp.regular_date else "",
            str(emp.resign_date) if emp.resign_date else "",
            emp.bank_card or "", emp.bank_branch or "", emp.home_address or "",
            float(salary.base_salary) if salary else "",
            float(salary.performance_standard) if salary else "",
            float(salary.meal_allowance) if salary else "",
            float(salary.transport_allowance) if salary else "",
            float(salary.communication_allowance) if salary else "",
            float(salary.computer_allowance) if salary else "",
            float(salary.housing_allowance) if salary else "",
            str(salary.effective_date) if salary and salary.effective_date else ""
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=roster.xlsx"}
    )


@router.get("/salary/{period}")
def export_salary(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    # 获取活跃员工ID列表
    query = db.query(Employee)
    active_employees = filter_active_employees(query, db).all()
    active_employee_ids = [emp.id for emp in active_employees]

    calcs = db.query(SalaryCalculation).filter(
        SalaryCalculation.period == period,
        SalaryCalculation.employee_id.in_(active_employee_ids)
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"薪资核算表_{period}"

    headers = [
        "员工ID", "姓名", "合同公司", "部门", "职务", "成本归属", "状态",
        "基本工资", "绩效标准", "绩效系数", "实际绩效",
        "餐补", "交通补", "通讯补", "电脑补", "住房补", "补贴合计",
        "提成/奖金", "税前调整", "税后调整",
        "总计薪天数", "实际计薪天数", "出勤率",
        "总应发工资", "社保个人", "公积金个人", "社保公积金合计",
        "上月未报税", "差旅未报税", "补偿金计税", "实际应纳税额", "专项附加扣除",
        "本月应扣个税", "实发工资",
        "核算状态", "数据完整性", "审核状态"
    ]
    ws.append(headers)

    for c in calcs:
        emp = db.query(Employee).filter(Employee.id == c.employee_id).first()
        ws.append([
            c.employee_id, emp.name if emp else "",
            c.contract_company, c.department, c.position, c.cost_owner or "", c.status,
            float(c.base_salary), float(c.performance_standard),
            float(c.performance_coefficient), float(c.actual_performance),
            float(c.meal_allowance), float(c.transport_allowance),
            float(c.communication_allowance), float(c.computer_allowance),
            float(c.housing_allowance), float(c.allowance_total),
            float(c.commission_bonus), float(c.pretax_adjustment),
            float(c.posttax_adjustment),
            float(c.total_work_days), float(c.actual_work_days),
            float(c.attendance_rate),
            float(c.gross_salary), float(c.social_insurance_personal),
            float(c.housing_fund_personal), float(c.si_hf_total),
            float(c.last_month_untaxed or 0), float(c.travel_untaxed or 0),
            float(c.compensation_tax or 0), float(c.actual_taxable or 0),
            float(c.special_deduction or 0),
            float(c.tax_deduction), float(c.net_salary),
            c.calculation_status, c.data_completeness, c.review_status
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=salary_{period}.xlsx"}
    )


@router.get("/attendance/{period}")
def export_attendance(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    # 先获取活跃员工ID列表
    query = db.query(Employee)
    active_employees = filter_active_employees(query, db).all()
    active_employee_ids = [emp.id for emp in active_employees]

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.period == period,
        AttendanceRecord.employee_id.in_(active_employee_ids)
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"考勤表_{period}"

    headers = [
        "员工ID", "姓名", "总计薪天数", "实际计薪天数", "出勤率",
        "迟到次数", "早退次数", "缺卡次数",
        "病假天数", "事假天数", "年假天数", "其他假天数",
        "是否在家打卡", "需核实", "核实状态", "备注"
    ]
    ws.append(headers)

    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        ws.append([
            r.employee_id, emp.name if emp else "",
            float(r.total_work_days), float(r.actual_work_days),
            float(r.attendance_rate),
            r.late_count, r.early_count, r.missed_punch_count,
            float(r.sick_leave_days), float(r.personal_leave_days),
            float(r.annual_leave_days), float(r.other_leave_days),
            "是" if r.is_home_checkin else "否",
            "是" if r.need_verify else "否",
            r.verify_status or "", r.remark or ""
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=attendance_{period}.xlsx"}
    )