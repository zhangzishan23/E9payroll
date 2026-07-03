from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from io import BytesIO
from openpyxl import Workbook
from datetime import date
import calendar
from app.core.database import get_db
from app.core.log_helper import write_log
from app.models.models import AttendanceRecord, Employee, SysDictBase, SalaryCalendarOverride
from app.api.auth import get_current_user, UserInfo
from app.core.query_utils import filter_active_employees

router = APIRouter()

DAILY_WORK_HOURS = 7  # 每日工作时长（小时）


def _get_dict_name(db: Session, dict_id: Optional[int]) -> str:
    """从数据字典获取名称"""
    if not dict_id:
        return ""
    item = db.query(SysDictBase).filter(SysDictBase.id == dict_id).first()
    return item.name if item else ""


def _calc_salary_dates(period: str) -> tuple:
    """根据核算周期计算计薪起止日期"""
    year = int(period[:4])
    month = int(period[4:6])
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def _calc_adjusted_salary_days(db: Session, period: str, total_work_days: float) -> float:
    """计算应计薪天数：含调休补班、节假日排除和用户覆盖"""
    year = int(period[:4])
    month = int(period[4:6])
    _, last_day = _calc_salary_dates(period)

    overrides = db.query(SalaryCalendarOverride).filter(
        SalaryCalendarOverride.period == period
    ).all()
    override_map = {o.override_date.isoformat(): o.is_salary_day for o in overrides}
    preset_holidays = set(_get_preset_holidays(db, year, month))

    salary_days = 0
    for d in range(1, last_day.day + 1):
        day_date = date(year, month, d)
        date_str = day_date.isoformat()
        is_weekday = day_date.weekday() < 5

        if date_str in override_map:
            if override_map[date_str]:
                salary_days += 1
        elif is_weekday and date_str not in preset_holidays:
            salary_days += 1

    return float(salary_days)


def _calc_late_to_personal_leave(late_count: int, late_duration: int) -> float:
    """迟到转事假：当月迟到次数>3次时，累计迟到时长换算为事假天数"""
    if late_count <= 3 or late_duration <= 0:
        return 0.0
    return round(late_duration / 60 / DAILY_WORK_HOURS, 2)


def _calc_actual_salary_days(adjusted_days: float, leave_total: float) -> float:
    """计薪天数 = 应计薪天数 - 请假合计"""
    return max(round(adjusted_days - leave_total, 2), 0)


def _calc_leave_total(
    late_to_personal: float,
    personal_leave: float, full_pay_sick: float, reduced_pay_sick: float,
    statutory_sick: float, compensatory: float, annual: float,
    prenatal: float, maternity: float, paternity: float,
    marriage: float, funeral: float, engineering: float
) -> float:
    """请假合计（天）"""
    return round(
        late_to_personal + personal_leave + full_pay_sick + reduced_pay_sick +
        statutory_sick + compensatory + annual + prenatal + maternity +
        paternity + marriage + funeral + engineering, 2
    )


# ==================== Schemas ====================

class AttendanceOut(BaseModel):
    id: Optional[int] = None
    period: str
    employee_id: int
    employee_no: str = ""
    employee_name: str = ""
    contract_company: str = ""   # 合同主体
    department: str = ""         # 部门
    # 计薪日期
    salary_start_date: Optional[str] = None
    salary_end_date: Optional[str] = None
    # 计薪天数
    total_work_days: Optional[float] = None      # 当月总计薪天数
    adjusted_salary_days: Optional[float] = None  # 应计薪天数
    actual_salary_days: Optional[float] = None    # 计薪天数
    attendance_rate: Optional[float] = None       # 出勤率
    # 缺卡
    half_day_missed_punch: Optional[int] = None   # 半天缺卡(次数)
    absenteeism_days: Optional[float] = None       # 全天缺卡(天数)
    # 迟到
    late_count: Optional[int] = None
    late_duration: Optional[int] = None
    severe_late_count: Optional[int] = None
    severe_late_duration: Optional[int] = None
    # 早退
    early_count: Optional[int] = None
    early_duration: Optional[int] = None
    # 加班
    total_overtime: Optional[float] = None
    # 迟到转事假
    late_to_personal_leave_days: Optional[float] = None
    # 请假明细
    personal_leave_days: Optional[float] = None
    full_pay_sick_days: Optional[float] = None
    reduced_pay_sick_days: Optional[float] = None
    statutory_sick_days: Optional[float] = None
    compensatory_leave_days: Optional[float] = None
    annual_leave_days: Optional[float] = None
    prenatal_checkup_days: Optional[float] = None
    maternity_leave_days: Optional[float] = None
    paternity_leave_days: Optional[float] = None
    marriage_leave_days: Optional[float] = None
    funeral_leave_days: Optional[float] = None
    engineering_compensatory_days: Optional[float] = None
    # 合计
    leave_total_days: Optional[float] = None
    # 备注
    remark: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_record(cls, att, emp, db: Session = None, fallback_period: str = "") -> "AttendanceOut":
        if att:
            contract_company = ""
            department = ""
            if emp and db:
                contract_company = _get_dict_name(db, emp.contract_company_id)
                department = _get_dict_name(db, emp.department_id)

            start_date = att.salary_start_date.isoformat() if att.salary_start_date else None
            end_date = att.salary_end_date.isoformat() if att.salary_end_date else None

            return cls(
                id=att.id, period=att.period, employee_id=att.employee_id,
                employee_no=emp.employee_no if emp else "",
                employee_name=emp.name if emp else "",
                contract_company=contract_company,
                department=department,
                salary_start_date=start_date,
                salary_end_date=end_date,
                total_work_days=float(att.total_work_days),
                adjusted_salary_days=float(att.adjusted_salary_days) if att.adjusted_salary_days else float(att.total_work_days),
                actual_salary_days=float(att.actual_salary_days) if att.actual_salary_days else None,
                attendance_rate=float(att.attendance_rate),
                half_day_missed_punch=att.half_day_missed_punch,
                absenteeism_days=float(att.absenteeism_days),
                late_count=att.late_count,
                late_duration=att.late_duration,
                severe_late_count=att.severe_late_count,
                severe_late_duration=att.severe_late_duration,
                early_count=att.early_count,
                early_duration=att.early_duration,
                total_overtime=float(att.total_overtime),
                late_to_personal_leave_days=float(att.late_to_personal_leave_days) if att.late_to_personal_leave_days else 0,
                personal_leave_days=float(att.personal_leave_days),
                full_pay_sick_days=float(att.full_pay_sick_days),
                reduced_pay_sick_days=float(att.reduced_pay_sick_days),
                statutory_sick_days=float(att.statutory_sick_days),
                compensatory_leave_days=float(att.compensatory_leave_days),
                annual_leave_days=float(att.annual_leave_days),
                prenatal_checkup_days=float(att.prenatal_checkup_days),
                maternity_leave_days=float(att.maternity_leave_days),
                paternity_leave_days=float(att.paternity_leave_days),
                marriage_leave_days=float(att.marriage_leave_days),
                funeral_leave_days=float(att.funeral_leave_days),
                engineering_compensatory_days=float(att.engineering_compensatory_days),
                leave_total_days=float(att.leave_total_days) if att.leave_total_days else 0,
                remark=att.remark,
            )
        else:
            return cls(
                period=fallback_period,
                employee_id=emp.id if emp else 0,
                employee_no=emp.employee_no if emp else "",
                employee_name=emp.name if emp else "",
            )


class AttendanceCreate(BaseModel):
    period: str
    employee_id: int
    total_work_days: float
    adjusted_salary_days: float = 0
    actual_salary_days: float = 0
    late_count: int = 0
    late_duration: int = 0
    severe_late_count: int = 0
    severe_late_duration: int = 0
    early_count: int = 0
    early_duration: int = 0
    half_day_missed_punch: int = 0
    absenteeism_days: float = 0
    total_overtime: float = 0
    late_to_personal_leave_days: float = 0
    personal_leave_days: float = 0
    full_pay_sick_days: float = 0
    reduced_pay_sick_days: float = 0
    statutory_sick_days: float = 0
    compensatory_leave_days: float = 0
    annual_leave_days: float = 0
    prenatal_checkup_days: float = 0
    maternity_leave_days: float = 0
    paternity_leave_days: float = 0
    marriage_leave_days: float = 0
    funeral_leave_days: float = 0
    engineering_compensatory_days: float = 0
    leave_total_days: float = 0
    remark: Optional[str] = None


class AttendanceUpdate(BaseModel):
    total_work_days: Optional[float] = None
    adjusted_salary_days: Optional[float] = None
    actual_salary_days: Optional[float] = None
    late_count: Optional[int] = None
    late_duration: Optional[int] = None
    severe_late_count: Optional[int] = None
    severe_late_duration: Optional[int] = None
    early_count: Optional[int] = None
    early_duration: Optional[int] = None
    half_day_missed_punch: Optional[int] = None
    absenteeism_days: Optional[float] = None
    total_overtime: Optional[float] = None
    late_to_personal_leave_days: Optional[float] = None
    personal_leave_days: Optional[float] = None
    full_pay_sick_days: Optional[float] = None
    reduced_pay_sick_days: Optional[float] = None
    statutory_sick_days: Optional[float] = None
    compensatory_leave_days: Optional[float] = None
    annual_leave_days: Optional[float] = None
    prenatal_checkup_days: Optional[float] = None
    maternity_leave_days: Optional[float] = None
    paternity_leave_days: Optional[float] = None
    marriage_leave_days: Optional[float] = None
    funeral_leave_days: Optional[float] = None
    engineering_compensatory_days: Optional[float] = None
    leave_total_days: Optional[float] = None
    remark: Optional[str] = None


# ==================== 考勤查询 ====================

@router.get("/", response_model=List[AttendanceOut])
def get_attendance(
    period: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    filter_field: Optional[str] = Query(None),
    filter_value: Optional[str] = Query(None),
    hide_status_id: Optional[int] = Query(None, description="要隐藏的员工状态ID"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        employee_query = filter_active_employees(db.query(Employee), db, hide_status_id=hide_status_id)
        if filter_field and filter_value:
            if filter_field == 'employee_no':
                employee_query = employee_query.filter(Employee.employee_no.ilike(f'%{filter_value}%'))
            elif filter_field == 'employee_name':
                employee_query = employee_query.filter(Employee.name.ilike(f'%{filter_value}%'))
        employees = employee_query.order_by(Employee.employee_no).all()

        attendance_map = {}
        records = db.query(AttendanceRecord).filter(AttendanceRecord.period == period).all()
        for r in records:
            attendance_map[r.employee_id] = r

        result = []
        for emp in employees:
            att = attendance_map.get(emp.id)
            result.append(AttendanceOut.from_record(att, emp, db=db, fallback_period=period))
        return result

    query = db.query(AttendanceRecord)
    if employee_id:
        query = query.filter(AttendanceRecord.employee_id == employee_id)
    records = query.order_by(AttendanceRecord.period.desc(), AttendanceRecord.employee_id).all()
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        result.append(AttendanceOut.from_record(r, emp, db=db))
    return result


# ==================== 导出 ====================

@router.get("/export")
def export_attendance(
    period: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    hide_status_id: Optional[int] = Query(None, description="要隐藏的员工状态ID"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        employee_query = filter_active_employees(db.query(Employee), db, hide_status_id=hide_status_id)
        employees = employee_query.order_by(Employee.employee_no).all()

        attendance_map = {}
        records = db.query(AttendanceRecord).filter(AttendanceRecord.period == period).all()
        for r in records:
            attendance_map[r.employee_id] = r
        data = []
        for emp in employees:
            att = attendance_map.get(emp.id)
            data.append((emp, att))
    else:
        query = db.query(AttendanceRecord)
        if employee_id:
            query = query.filter(AttendanceRecord.employee_id == employee_id)
        records = query.order_by(AttendanceRecord.period.desc(), AttendanceRecord.employee_id).all()
        data = []
        for r in records:
            emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
            data.append((emp, r))

    wb = Workbook()
    ws = wb.active
    ws.title = "考勤数据"
    headers = [
        "核算周期", "员工编号", "员工姓名", "合同主体", "部门",
        "计薪开始日期", "计薪截至日期",
        "当月总计薪天数", "应计薪天数", "计薪天数", "出勤率",
        "半天缺卡(次数)", "全天缺卡(天数)",
        "迟到次数", "迟到时长(分钟)", "严重迟到次数", "严重迟到时长(分钟)",
        "早退次数", "早退时长(分钟)", "加班(小时)", "迟到转事假",
        "事假", "全薪病假", "减薪病假", "法定病假",
        "调休", "年假", "产检假", "产假", "陪产假", "婚假", "丧假",
        "调休-工程交付(天)", "合计", "备注",
    ]
    ws.append(headers)
    for emp, r in data:
        if r:
            contract_company = _get_dict_name(db, emp.contract_company_id) if emp else ""
            department = _get_dict_name(db, emp.department_id) if emp else ""
            ws.append([
                r.period, emp.employee_no if emp else "", emp.name if emp else "",
                contract_company, department,
                r.salary_start_date.isoformat() if r.salary_start_date else "",
                r.salary_end_date.isoformat() if r.salary_end_date else "",
                float(r.total_work_days),
                float(r.adjusted_salary_days) if r.adjusted_salary_days else float(r.total_work_days),
                float(r.actual_salary_days) if r.actual_salary_days else "",
                float(r.attendance_rate),
                r.half_day_missed_punch, float(r.absenteeism_days),
                r.late_count, r.late_duration, r.severe_late_count, r.severe_late_duration,
                r.early_count, r.early_duration, float(r.total_overtime),
                float(r.late_to_personal_leave_days) if r.late_to_personal_leave_days else 0,
                float(r.personal_leave_days), float(r.full_pay_sick_days),
                float(r.reduced_pay_sick_days), float(r.statutory_sick_days),
                float(r.compensatory_leave_days), float(r.annual_leave_days),
                float(r.prenatal_checkup_days), float(r.maternity_leave_days),
                float(r.paternity_leave_days), float(r.marriage_leave_days),
                float(r.funeral_leave_days), float(r.engineering_compensatory_days),
                float(r.leave_total_days) if r.leave_total_days else 0,
                r.remark or "",
            ])
        else:
            empty_count = len(headers) - 3
            ws.append([period, emp.employee_no, emp.name] + [""] * empty_count)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance_export.xlsx"}
    )


# ==================== 新增 ====================

@router.post("/", response_model=AttendanceOut)
def create_attendance(att: AttendanceCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.period == att.period,
        AttendanceRecord.employee_id == att.employee_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"员工 [{att.employee_id}] 在周期 [{att.period}] 的考勤记录已存在")

    # 计算计薪日期
    start_date, end_date = _calc_salary_dates(att.period)

    # 计算应计薪天数（如果未指定）
    adjusted = att.adjusted_salary_days if att.adjusted_salary_days > 0 else _calc_adjusted_salary_days(db, att.period, att.total_work_days)

    # 计算迟到转事假
    late_leave = att.late_to_personal_leave_days if att.late_to_personal_leave_days > 0 else _calc_late_to_personal_leave(att.late_count, att.late_duration)

    # 计算请假合计
    leave_total = att.leave_total_days if att.leave_total_days > 0 else _calc_leave_total(
        late_leave, att.personal_leave_days, att.full_pay_sick_days,
        att.reduced_pay_sick_days, att.statutory_sick_days,
        att.compensatory_leave_days, att.annual_leave_days,
        att.prenatal_checkup_days, att.maternity_leave_days,
        att.paternity_leave_days, att.marriage_leave_days,
        att.funeral_leave_days, att.engineering_compensatory_days
    )

    # 计算计薪天数
    actual_salary = att.actual_salary_days if att.actual_salary_days > 0 else _calc_actual_salary_days(adjusted, leave_total)

    # 出勤率 = 计薪天数 / 应计薪天数 × 100%
    attendance_rate = round(actual_salary / adjusted, 4) if adjusted > 0 else 0

    db_att = AttendanceRecord(
        period=att.period, employee_id=att.employee_id,
        total_work_days=att.total_work_days,
        actual_work_days=actual_salary,  # 兼容旧字段
        attendance_rate=attendance_rate,
        salary_start_date=start_date, salary_end_date=end_date,
        adjusted_salary_days=adjusted,
        actual_salary_days=actual_salary,
        late_to_personal_leave_days=late_leave,
        leave_total_days=leave_total,
        late_count=att.late_count, late_duration=att.late_duration,
        severe_late_count=att.severe_late_count, severe_late_duration=att.severe_late_duration,
        early_count=att.early_count, early_duration=att.early_duration,
        half_day_missed_punch=att.half_day_missed_punch,
        absenteeism_days=att.absenteeism_days,
        total_overtime=att.total_overtime,
        personal_leave_days=att.personal_leave_days,
        full_pay_sick_days=att.full_pay_sick_days,
        reduced_pay_sick_days=att.reduced_pay_sick_days,
        statutory_sick_days=att.statutory_sick_days,
        compensatory_leave_days=att.compensatory_leave_days,
        annual_leave_days=att.annual_leave_days,
        prenatal_checkup_days=att.prenatal_checkup_days,
        maternity_leave_days=att.maternity_leave_days,
        paternity_leave_days=att.paternity_leave_days,
        marriage_leave_days=att.marriage_leave_days,
        funeral_leave_days=att.funeral_leave_days,
        engineering_compensatory_days=att.engineering_compensatory_days,
        remark=att.remark,
    )
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "create", f"新增考勤记录 (employee_id={att.employee_id}, period={att.period})")
    emp = db.query(Employee).filter(Employee.id == att.employee_id).first()
    return AttendanceOut.from_record(db_att, emp, db=db)


# ==================== 编辑 ====================

@router.put("/{record_id}", response_model=AttendanceOut)
def update_attendance(record_id: int, data: AttendanceUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    att = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="考勤记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(att, key, value)

    # 重新计算派生字段
    total_work = float(att.total_work_days)
    adjusted = float(att.adjusted_salary_days) if att.adjusted_salary_days else total_work
    late_leave = float(att.late_to_personal_leave_days) if att.late_to_personal_leave_days else _calc_late_to_personal_leave(att.late_count or 0, att.late_duration or 0)

    leave_total = _calc_leave_total(
        late_leave,
        float(att.personal_leave_days), float(att.full_pay_sick_days),
        float(att.reduced_pay_sick_days), float(att.statutory_sick_days),
        float(att.compensatory_leave_days), float(att.annual_leave_days),
        float(att.prenatal_checkup_days), float(att.maternity_leave_days),
        float(att.paternity_leave_days), float(att.marriage_leave_days),
        float(att.funeral_leave_days), float(att.engineering_compensatory_days)
    )
    actual_salary = _calc_actual_salary_days(adjusted, leave_total)
    att_rate = round(actual_salary / adjusted, 4) if adjusted > 0 else 0

    att.adjusted_salary_days = adjusted
    att.actual_salary_days = actual_salary
    att.late_to_personal_leave_days = late_leave
    att.leave_total_days = leave_total
    att.attendance_rate = att_rate
    att.actual_work_days = actual_salary  # 兼容旧字段

    db.commit()
    db.refresh(att)
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "edit", f"编辑考勤记录 (id={record_id})")

    emp = db.query(Employee).filter(Employee.id == att.employee_id).first()
    return AttendanceOut.from_record(att, emp, db=db)


# ==================== 批量删除 ====================

@router.post("/batch-delete")
def batch_delete_attendance(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的考勤记录ID列表")
    records = db.query(AttendanceRecord).filter(AttendanceRecord.id.in_(ids)).all()
    if not records:
        raise HTTPException(status_code=404, detail="未找到指定的考勤记录")
    for r in records:
        db.delete(r)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "delete", f"批量删除 {len(records)} 条考勤记录")
    return {"message": f"成功删除 {len(records)} 条考勤记录", "deleted_count": len(records)}


# ==================== 导入 ====================

@router.post("/import")
async def import_attendance(
    file: UploadFile = File(...),
    period: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

    try:
        contents = await file.read()
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(contents), read_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法读取 Excel 文件：{str(e)}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel 文件为空或只有表头，没有数据行")

    headers = [str(h).strip() if h else "" for h in rows[0]]
    header_map = {}
    for i, h in enumerate(headers):
        if "员工编号" in h or "编号" in h:
            header_map["employee_no"] = i
        elif "总计薪" in h or "应出勤" in h:
            header_map["total_work_days"] = i
        elif "应计薪" in h:
            header_map["adjusted_salary_days"] = i
        elif "实际计薪" in h or "计薪天数" in h:
            header_map["actual_salary_days"] = i
        elif "迟到" in h and "转事假" in h:
            header_map["late_to_personal_leave"] = i
        elif "迟到" in h:
            header_map["late_count"] = i
        elif "早退" in h:
            header_map["early_count"] = i
        elif "半天缺卡" in h or "缺卡" in h:
            header_map["half_day_missed_punch"] = i
        elif "全天缺卡" in h:
            header_map["absenteeism_days"] = i
        elif "加班" in h:
            header_map["total_overtime"] = i
        elif "事假" in h:
            header_map["personal_leave_days"] = i
        elif "全薪病假" in h:
            header_map["full_pay_sick_days"] = i
        elif "减薪病假" in h:
            header_map["reduced_pay_sick_days"] = i
        elif "法定病假" in h:
            header_map["statutory_sick_days"] = i
        elif "调休" in h and "工程" in h:
            header_map["engineering_compensatory_days"] = i
        elif "调休" in h:
            header_map["compensatory_leave_days"] = i
        elif "年假" in h:
            header_map["annual_leave_days"] = i
        elif "产检假" in h:
            header_map["prenatal_checkup_days"] = i
        elif "产假" in h:
            header_map["maternity_leave_days"] = i
        elif "陪产假" in h:
            header_map["paternity_leave_days"] = i
        elif "婚假" in h:
            header_map["marriage_leave_days"] = i
        elif "丧假" in h:
            header_map["funeral_leave_days"] = i
        elif "合计" in h:
            header_map["leave_total_days"] = i
        elif "备注" in h:
            header_map["remark"] = i

    if "employee_no" not in header_map:
        raise HTTPException(status_code=400, detail="Excel 表头缺少「员工编号」列")

    emp_map = {e.employee_no: e for e in db.query(Employee).all()}
    start_date, end_date = _calc_salary_dates(period)
    exclusions_count = db.query(SalaryCalendarOverride).filter(SalaryCalendarOverride.period == period).count()

    created = 0
    updated = 0
    errors = []

    for row_idx, row in enumerate(rows[1:], start=2):
        try:
            emp_no = str(row[header_map["employee_no"]]).strip() if row[header_map["employee_no"]] else ""
            emp = emp_map.get(emp_no)
            if not emp:
                errors.append(f"第{row_idx}行：员工编号「{emp_no}」不存在")
                continue

            def get_float(key, default=0):
                if key in header_map and row[header_map[key]] is not None:
                    try:
                        return float(row[header_map[key]])
                    except (ValueError, TypeError):
                        return default
                return default

            def get_int(key, default=0):
                if key in header_map and row[header_map[key]] is not None:
                    try:
                        return int(float(row[header_map[key]]))
                    except (ValueError, TypeError):
                        return default
                return default

            def get_str(key, default=None):
                if key in header_map and row[header_map[key]] is not None:
                    return str(row[header_map[key]]).strip()
                return default

            total_work = get_float("total_work_days", 0)
            late_count_val = get_int("late_count")
            late_duration_val = get_int("late_duration", 0)
            late_leave = get_float("late_to_personal_leave", 0) or _calc_late_to_personal_leave(late_count_val, late_duration_val)

            personal = get_float("personal_leave_days")
            full_sick = get_float("full_pay_sick_days")
            reduced_sick = get_float("reduced_pay_sick_days")
            stat_sick = get_float("statutory_sick_days")
            comp = get_float("compensatory_leave_days")
            annual = get_float("annual_leave_days")
            prenatal = get_float("prenatal_checkup_days")
            maternity = get_float("maternity_leave_days")
            paternity = get_float("paternity_leave_days")
            marriage = get_float("marriage_leave_days")
            funeral = get_float("funeral_leave_days")
            eng = get_float("engineering_compensatory_days")

            leave_total = get_float("leave_total_days", 0) or _calc_leave_total(
                late_leave, personal, full_sick, reduced_sick, stat_sick,
                comp, annual, prenatal, maternity, paternity, marriage, funeral, eng
            )
            adjusted = get_float("adjusted_salary_days", 0) or max(total_work - exclusions_count, 0)
            actual_salary = get_float("actual_salary_days", 0) or _calc_actual_salary_days(adjusted, leave_total)
            att_rate = round(actual_salary / adjusted, 4) if adjusted > 0 else 0

            existing = db.query(AttendanceRecord).filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp.id
            ).first()

            if existing:
                existing.total_work_days = total_work
                existing.adjusted_salary_days = adjusted
                existing.actual_salary_days = actual_salary
                existing.attendance_rate = att_rate
                existing.actual_work_days = actual_salary
                existing.late_count = late_count_val
                existing.late_duration = late_duration_val
                existing.severe_late_count = get_int("severe_late_count")
                existing.severe_late_duration = get_int("severe_late_duration")
                existing.early_count = get_int("early_count")
                existing.early_duration = get_int("early_duration")
                existing.half_day_missed_punch = get_int("half_day_missed_punch")
                existing.absenteeism_days = get_float("absenteeism_days")
                existing.total_overtime = get_float("total_overtime")
                existing.late_to_personal_leave_days = late_leave
                existing.personal_leave_days = personal
                existing.full_pay_sick_days = full_sick
                existing.reduced_pay_sick_days = reduced_sick
                existing.statutory_sick_days = stat_sick
                existing.compensatory_leave_days = comp
                existing.annual_leave_days = annual
                existing.prenatal_checkup_days = prenatal
                existing.maternity_leave_days = maternity
                existing.paternity_leave_days = paternity
                existing.marriage_leave_days = marriage
                existing.funeral_leave_days = funeral
                existing.engineering_compensatory_days = eng
                existing.leave_total_days = leave_total
                existing.remark = get_str("remark")
                existing.salary_start_date = start_date
                existing.salary_end_date = end_date
                updated += 1
            else:
                new_att = AttendanceRecord(
                    period=period, employee_id=emp.id,
                    total_work_days=total_work,
                    actual_work_days=actual_salary,
                    attendance_rate=att_rate,
                    salary_start_date=start_date, salary_end_date=end_date,
                    adjusted_salary_days=adjusted,
                    actual_salary_days=actual_salary,
                    late_to_personal_leave_days=late_leave,
                    leave_total_days=leave_total,
                    late_count=late_count_val,
                    late_duration=late_duration_val,
                    severe_late_count=get_int("severe_late_count"),
                    severe_late_duration=get_int("severe_late_duration"),
                    early_count=get_int("early_count"),
                    early_duration=get_int("early_duration"),
                    half_day_missed_punch=get_int("half_day_missed_punch"),
                    absenteeism_days=get_float("absenteeism_days"),
                    total_overtime=get_float("total_overtime"),
                    personal_leave_days=personal,
                    full_pay_sick_days=full_sick,
                    reduced_pay_sick_days=reduced_sick,
                    statutory_sick_days=stat_sick,
                    compensatory_leave_days=comp,
                    annual_leave_days=annual,
                    prenatal_checkup_days=prenatal,
                    maternity_leave_days=maternity,
                    paternity_leave_days=paternity,
                    marriage_leave_days=marriage,
                    funeral_leave_days=funeral,
                    engineering_compensatory_days=eng,
                    remark=get_str("remark"),
                )
                db.add(new_att)
                created += 1
        except Exception as e:
            errors.append(f"第{row_idx}行：处理失败 - {str(e)}")

    db.commit()
    wb.close()
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "import", f"批量导入考勤：新增{created}条，更新{updated}条 (period={period})")

    return {
        "message": f"导入完成：新增 {created} 条，更新 {updated} 条",
        "created": created,
        "updated": updated,
        "errors": errors
    }


def _get_preset_holidays(db: Session, year: int, month: int) -> list:
    """从数据字典读取法定节假日（仅返回周一至周五的日期）"""
    from app.models.models import SysDictBase
    from datetime import date as dt_date
    items = db.query(SysDictBase).filter(
        SysDictBase.category == "holiday",
        SysDictBase.is_enabled == True
    ).all()
    result = []
    for item in items:
        d_str = item.code
        try:
            d = dt_date.fromisoformat(d_str)
        except ValueError:
            continue
        if d.year == year and d.month == month and d.weekday() < 5:
            result.append(d_str)
    return result


# ==================== 计薪日历 API ====================

@router.get("/salary-calendar")
def get_salary_calendar(
    period: str = Query(..., description="核算周期 YYYYMM"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取指定月份的计薪日历数据（支持调休补班和节假日排除）"""
    year = int(period[:4])
    month = int(period[4:6])
    _, last_day = _calc_salary_dates(period)

    # 读取用户覆盖记录
    overrides = db.query(SalaryCalendarOverride).filter(
        SalaryCalendarOverride.period == period
    ).all()
    override_map = {o.override_date.isoformat(): o.is_salary_day for o in overrides}

    # 从数据字典读取法定节假日
    preset_holidays = set(_get_preset_holidays(db, year, month))

    days = []
    for d in range(1, last_day.day + 1):
        day_date = date(year, month, d)
        date_str = day_date.isoformat()
        is_weekday = day_date.weekday() < 5

        if date_str in override_map:
            # 用户覆盖优先级最高
            is_salary_day = override_map[date_str]
            is_overridden = True
        elif is_weekday and date_str in preset_holidays:
            # 工作日遇到法定节假日 → 自动排除
            is_salary_day = False
            is_overridden = False
        else:
            # 默认：工作日计薪，周末不计薪
            is_salary_day = is_weekday
            is_overridden = False

        days.append({
            "date": date_str,
            "day": d,
            "weekday": day_date.weekday(),
            "is_workday": is_weekday,
            "is_salary_day": is_salary_day,
            "is_overridden": is_overridden,
        })

    total_salary_days = sum(1 for d in days if d["is_salary_day"])
    override_count = db.query(SalaryCalendarOverride).filter(
        SalaryCalendarOverride.period == period
    ).count()

    return {
        "period": period,
        "days": days,
        "total_salary_days": total_salary_days,
        "override_count": override_count,
    }


@router.post("/salary-calendar/toggle")
def toggle_salary_day(
    period: str = Form(...),
    date_str: str = Form(..., alias="date"),
    action: str = Form("exclude", description="操作类型: exclude排除工作日/include纳入周末/restore恢复默认"),
    reason: str = Form(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """切换计薪日状态：排除工作日 / 纳入休息日 / 恢复默认"""
    from datetime import datetime
    override_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if action == "restore":
        # 恢复默认：删除覆盖记录
        db.query(SalaryCalendarOverride).filter(
            SalaryCalendarOverride.period == period,
            SalaryCalendarOverride.override_date == override_date
        ).delete()
        db.commit()
        return {"message": f"已恢复 {date_str} 为默认状态", "action": "restore"}

    elif action == "include":
        # 纳入休息日为计薪日（调休补班场景）
        existing = db.query(SalaryCalendarOverride).filter(
            SalaryCalendarOverride.period == period,
            SalaryCalendarOverride.override_date == override_date
        ).first()
        if existing:
            existing.is_salary_day = True
            existing.reason = reason or "调休补班"
        else:
            db.add(SalaryCalendarOverride(
                period=period,
                override_date=override_date,
                is_salary_day=True,
                reason=reason or "调休补班"
            ))
        db.commit()
        return {"message": f"已将 {date_str} 纳入计薪日", "action": "include"}

    else:
        # exclude: 排除工作日（节假日/请假场景）
        existing = db.query(SalaryCalendarOverride).filter(
            SalaryCalendarOverride.period == period,
            SalaryCalendarOverride.override_date == override_date
        ).first()
        if existing:
            existing.is_salary_day = False
            existing.reason = reason or "用户手动排除"
        else:
            db.add(SalaryCalendarOverride(
                period=period,
                override_date=override_date,
                is_salary_day=False,
                reason=reason or "用户手动排除"
            ))
        db.commit()
        return {"message": f"已排除 {date_str}", "action": "exclude"}
