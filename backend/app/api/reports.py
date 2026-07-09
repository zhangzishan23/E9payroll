from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import io
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.query_utils import filter_active_employees, get_pending_resign_status_id
from app.models.models import Employee, EmployeeSalary, SalaryCalculation, AttendanceRecord, SysDictBase, ExportTemplate
from app.api.auth import get_current_user, UserInfo
from sqlalchemy import func

router = APIRouter()


def _filter_active_without_pending_resign(query, db: Session):
    """过滤活跃员工，排除待离职状态"""
    query = filter_active_employees(query, db)
    pending_resign_ids = get_pending_resign_status_id(db)
    if pending_resign_ids:
        query = query.filter(Employee.status_id.notin_(pending_resign_ids))
    return query


@router.get("/stats")
def get_stats(
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    active_employees = _filter_active_without_pending_resign(query, db).all()
    total_employees = len(active_employees)
    active_employee_ids = [emp.id for emp in active_employees]

    status_count = {}
    status_id_counts = {}
    for emp in active_employees:
        status_id_counts[emp.status_id] = status_id_counts.get(emp.status_id, 0) + 1
    for status_id, count in status_id_counts.items():
        dict_item = db.query(SysDictBase).filter(SysDictBase.id == status_id).first()
        status_count[dict_item.name if dict_item else "未知"] = count

    latest_period = period or db.query(SalaryCalculation.period).order_by(SalaryCalculation.period.desc()).first()
    latest_period = latest_period[0] if latest_period else None

    salary_stats = {}
    if latest_period:
        calcs = db.query(SalaryCalculation).filter(
            SalaryCalculation.period == latest_period,
            SalaryCalculation.employee_id.in_(active_employee_ids)
        ).all()
        completed = sum(1 for c in calcs if c.calculation_status == "核算完成")
        salary_stats = {
            "period": latest_period,
            "total": len(active_employees),
            "completed": completed,
            "pending": len(active_employees) - completed,
            "review_passed": sum(1 for c in calcs if c.review_status == "审核通过"),
            "review_rejected": sum(1 for c in calcs if c.review_status == "审核驳回"),
            "avg_gross_salary": round(float(sum(c.gross_salary for c in calcs)) / len(calcs), 2) if calcs else 0,
            "avg_net_salary": round(float(sum(c.net_salary for c in calcs)) / len(calcs), 2) if calcs else 0,
        }

    att_stats = {}
    if latest_period:
        atts = db.query(AttendanceRecord).filter(
            AttendanceRecord.period == latest_period,
            AttendanceRecord.employee_id.in_(active_employee_ids)
        ).all()
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
    employees = _filter_active_without_pending_resign(query, db).all()

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
    active_employees = _filter_active_without_pending_resign(query, db).all()
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
        "应计薪天数", "实际计薪天数", "出勤率",
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
    active_employees = _filter_active_without_pending_resign(query, db).all()
    active_employee_ids = [emp.id for emp in active_employees]

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.period == period,
        AttendanceRecord.employee_id.in_(active_employee_ids)
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"考勤表_{period}"

    headers = [
        "员工ID", "姓名", "应计薪天数", "实际计薪天数", "出勤率",
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


# ============================================================
# 导出表配置相关
# ============================================================

SALARY_FIELDS = [
    {"key": "employee_no", "label": "员工编号", "width": 90},
    {"key": "contract_company", "label": "合同公司", "width": 120},
    {"key": "employee_name", "label": "姓名", "width": 70},
    {"key": "department", "label": "部门", "width": 90},
    {"key": "position", "label": "职务", "width": 90},
    {"key": "cost_owner", "label": "费用负责人", "width": 90},
    {"key": "status", "label": "状态", "width": 80},
    {"key": "entry_date", "label": "入职时间", "width": 100},
    {"key": "total_work_days", "label": "应计薪天数", "width": 100},
    {"key": "actual_work_days", "label": "实际计薪天数", "width": 100},
    {"key": "attendance_rate", "label": "出勤率", "width": 75},
    {"key": "base_salary", "label": "基本工资", "width": 95},
    {"key": "commission_bonus", "label": "提成/项目奖金/补发", "width": 130},
    {"key": "meal_allowance", "label": "餐补", "width": 70},
    {"key": "transport_allowance", "label": "交通补", "width": 75},
    {"key": "communication_allowance", "label": "通讯补", "width": 75},
    {"key": "computer_allowance", "label": "电脑补贴（非固定收入）", "width": 130},
    {"key": "housing_allowance", "label": "住房补（非固定收入）", "width": 120},
    {"key": "allowance_total", "label": "补贴合计", "width": 85},
    {"key": "performance_standard", "label": "绩效奖金标准", "width": 100},
    {"key": "performance_coefficient", "label": "实发绩效奖金系数", "width": 120},
    {"key": "actual_performance", "label": "实发绩效奖金标准", "width": 120},
    {"key": "effective_performance", "label": "实发绩效奖金", "width": 100},
    {"key": "monthly_standard", "label": "月薪标准", "width": 90},
    {"key": "gross_salary", "label": "总应发工资", "width": 100},
    {"key": "pension_personal", "label": "养老保险（个人）", "width": 120},
    {"key": "unemployment_personal", "label": "失业保险（个人）", "width": 120},
    {"key": "medical_personal", "label": "医疗保险（个人）", "width": 120},
    {"key": "housing_fund_personal", "label": "公积金（个人）", "width": 110},
    {"key": "si_hf_total", "label": "社保、公积金（个人）合计", "width": 150},
    {"key": "salary_after_si_hf", "label": "扣掉社保公积金工资", "width": 130},
    {"key": "tax_deduction", "label": "本月应扣个税额", "width": 110},
    {"key": "posttax_adjustment", "label": "税后调整金额", "width": 110},
    {"key": "posttax_adjustment_reason", "label": "税后调整原因", "width": 120},
    {"key": "net_salary", "label": "实发工资", "width": 100},
    {"key": "last_month_untaxed", "label": "上月未报税金额", "width": 120},
    {"key": "travel_untaxed", "label": "临时性差旅补贴未报税费用", "width": 160},
    {"key": "compensation_tax", "label": "未报税补偿金", "width": 110},
    {"key": "actual_taxable", "label": "本月实际报税金额", "width": 130},
    {"key": "special_deduction", "label": "专项附加扣除", "width": 110},
]


class ExportTemplateIn(BaseModel):
    name: str
    template_type: str
    description: Optional[str] = None
    fields: List[dict]
    is_default: bool = False
    is_enabled: bool = True


class ExportTemplateOut(BaseModel):
    id: int
    name: str
    template_type: str
    description: Optional[str] = None
    fields: List[dict]
    is_default: bool
    is_enabled: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("/export/available-fields")
def get_available_fields(current_user: UserInfo = Depends(get_current_user)):
    """获取可配置的导出字段列表"""
    return {
        "salary": SALARY_FIELDS
    }


@router.get("/export/templates", response_model=List[ExportTemplateOut])
def get_export_templates(
    template_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取导出模板列表"""
    query = db.query(ExportTemplate)
    if template_type:
        query = query.filter(ExportTemplate.template_type == template_type)
    templates = query.order_by(ExportTemplate.is_default.desc(), ExportTemplate.created_at.desc()).all()
    return [
        ExportTemplateOut(
            id=t.id, name=t.name, template_type=t.template_type,
            description=t.description, fields=t.fields,
            is_default=t.is_default, is_enabled=t.is_enabled,
            created_at=str(t.created_at)
        ) for t in templates
    ]


@router.post("/export/templates", response_model=ExportTemplateOut)
def create_export_template(
    data: ExportTemplateIn,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """创建导出模板"""
    if data.is_default:
        db.query(ExportTemplate).filter(
            ExportTemplate.template_type == data.template_type,
            ExportTemplate.is_default == True
        ).update({"is_default": False})
    
    template = ExportTemplate(
        name=data.name,
        template_type=data.template_type,
        description=data.description,
        fields=data.fields,
        is_default=data.is_default,
        is_enabled=data.is_enabled,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    write_log(db, "data_change", current_user.id, current_user.username, "report", "create", f"创建导出模板 {data.name}")
    return ExportTemplateOut(
        id=template.id, name=template.name, template_type=template.template_type,
        description=template.description, fields=template.fields,
        is_default=template.is_default, is_enabled=template.is_enabled,
        created_at=str(template.created_at)
    )


@router.put("/export/templates/{tpl_id}", response_model=ExportTemplateOut)
def update_export_template(
    tpl_id: int,
    data: ExportTemplateIn,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """更新导出模板"""
    template = db.query(ExportTemplate).filter(ExportTemplate.id == tpl_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    if data.is_default and not template.is_default:
        db.query(ExportTemplate).filter(
            ExportTemplate.template_type == data.template_type,
            ExportTemplate.is_default == True,
            ExportTemplate.id != tpl_id
        ).update({"is_default": False})
    
    template.name = data.name
    template.template_type = data.template_type
    template.description = data.description
    template.fields = data.fields
    template.is_default = data.is_default
    template.is_enabled = data.is_enabled
    db.commit()
    db.refresh(template)
    write_log(db, "data_change", current_user.id, current_user.username, "report", "edit", f"更新导出模板 {data.name}")
    return ExportTemplateOut(
        id=template.id, name=template.name, template_type=template.template_type,
        description=template.description, fields=template.fields,
        is_default=template.is_default, is_enabled=template.is_enabled,
        created_at=str(template.created_at)
    )


@router.delete("/export/templates/{tpl_id}")
def delete_export_template(
    tpl_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """删除导出模板"""
    template = db.query(ExportTemplate).filter(ExportTemplate.id == tpl_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.is_default:
        raise HTTPException(status_code=400, detail="默认模板不能删除，请先设置其他模板为默认")
    name = template.name
    db.delete(template)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "report", "delete", f"删除导出模板 {name}")
    return {"message": "模板已删除"}


@router.get("/salary-by-template/{period}")
def export_salary_by_template(
    period: str,
    template_id: Optional[int] = Query(None, description="模板ID，不传则使用默认模板"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """按自定义模板导出薪资表"""
    query = db.query(Employee)
    active_employees = _filter_active_without_pending_resign(query, db).all()
    active_employee_ids = [emp.id for emp in active_employees]

    calcs = db.query(SalaryCalculation).filter(
        SalaryCalculation.period == period,
        SalaryCalculation.employee_id.in_(active_employee_ids)
    ).all()
    
    emp_map = {e.id: e for e in active_employees}
    
    if template_id:
        template = db.query(ExportTemplate).filter(ExportTemplate.id == template_id).first()
    else:
        template = db.query(ExportTemplate).filter(
            ExportTemplate.template_type.in_(["salary_finance", "salary_slip", "custom"]),
            ExportTemplate.is_default == True,
            ExportTemplate.is_enabled == True
        ).first()
    
    field_list = SALARY_FIELDS
    if template:
        field_list = template.fields
    
    wb = Workbook()
    ws = wb.active
    ws.title = f"薪资表_{period}"
    
    headers = [f["label"] for f in field_list]
    ws.append(headers)
    
    field_keys = [f["key"] for f in field_list]
    
    for c in calcs:
        emp = emp_map.get(c.employee_id)
        row_data = {}
        row_data["employee_no"] = emp.employee_no if emp else ""
        row_data["contract_company"] = c.contract_company
        row_data["employee_name"] = emp.name if emp else ""
        row_data["department"] = c.department
        row_data["position"] = c.position
        row_data["cost_owner"] = c.cost_owner or ""
        row_data["status"] = c.status
        row_data["entry_date"] = str(c.entry_date) if c.entry_date else ""
        row_data["total_work_days"] = float(c.total_work_days)
        row_data["actual_work_days"] = float(c.actual_work_days)
        row_data["attendance_rate"] = float(c.attendance_rate)
        row_data["base_salary"] = float(c.base_salary)
        row_data["commission_bonus"] = float(c.commission_bonus or 0)
        row_data["meal_allowance"] = float(c.meal_allowance)
        row_data["transport_allowance"] = float(c.transport_allowance)
        row_data["communication_allowance"] = float(c.communication_allowance)
        row_data["computer_allowance"] = float(c.computer_allowance)
        row_data["housing_allowance"] = float(c.housing_allowance)
        row_data["allowance_total"] = float(c.allowance_total)
        row_data["performance_standard"] = float(c.performance_standard)
        row_data["performance_coefficient"] = float(c.performance_coefficient)
        row_data["actual_performance"] = float(c.actual_performance)
        row_data["effective_performance"] = float(c.effective_performance)
        row_data["monthly_standard"] = float(c.monthly_standard)
        row_data["gross_salary"] = float(c.gross_salary)
        row_data["pension_personal"] = float(c.pension_personal)
        row_data["unemployment_personal"] = float(c.unemployment_personal)
        row_data["medical_personal"] = float(c.medical_personal)
        row_data["housing_fund_personal"] = float(c.housing_fund_personal)
        row_data["si_hf_total"] = float(c.si_hf_total)
        row_data["salary_after_si_hf"] = round(float(c.gross_salary) - float(c.si_hf_total), 2)
        row_data["tax_deduction"] = float(c.tax_deduction)
        row_data["posttax_adjustment"] = float(c.posttax_adjustment)
        row_data["posttax_adjustment_reason"] = c.posttax_adjustment_reason or ""
        row_data["net_salary"] = float(c.net_salary)
        row_data["last_month_untaxed"] = float(c.last_month_untaxed or 0)
        row_data["travel_untaxed"] = float(c.travel_untaxed or 0)
        row_data["compensation_tax"] = float(c.compensation_tax or 0)
        row_data["actual_taxable"] = float(c.actual_taxable or 0)
        row_data["special_deduction"] = float(c.special_deduction or 0)
        
        ws.append([row_data.get(k, "") for k in field_keys])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"薪资表_{period}.xlsx"
    if template:
        filename = f"{template.name}_{period}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )