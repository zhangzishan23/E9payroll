from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.models.models import AttendanceRecord, Employee
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class AttendanceOut(BaseModel):
    id: Optional[int] = None
    period: str
    employee_id: int
    employee_no: str = ""
    employee_name: str = ""
    total_work_days: Optional[float] = None
    actual_work_days: Optional[float] = None
    attendance_rate: Optional[float] = None
    late_count: Optional[int] = None
    early_count: Optional[int] = None
    missed_punch_count: Optional[int] = None
    sick_leave_days: Optional[float] = None
    personal_leave_days: Optional[float] = None
    annual_leave_days: Optional[float] = None
    other_leave_days: Optional[float] = None
    is_home_checkin: Optional[bool] = None
    need_verify: Optional[bool] = None
    verify_status: Optional[str] = None
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    period: str
    employee_id: int
    total_work_days: float
    actual_work_days: float
    late_count: int = 0
    early_count: int = 0
    missed_punch_count: int = 0
    sick_leave_days: float = 0
    personal_leave_days: float = 0
    annual_leave_days: float = 0
    other_leave_days: float = 0
    is_home_checkin: bool = False
    need_verify: bool = False
    verify_status: Optional[str] = None
    remark: Optional[str] = None


class AttendanceUpdate(BaseModel):
    total_work_days: Optional[float] = None
    actual_work_days: Optional[float] = None
    late_count: Optional[int] = None
    early_count: Optional[int] = None
    missed_punch_count: Optional[int] = None
    sick_leave_days: Optional[float] = None
    personal_leave_days: Optional[float] = None
    annual_leave_days: Optional[float] = None
    other_leave_days: Optional[float] = None
    is_home_checkin: Optional[bool] = None
    need_verify: Optional[bool] = None
    verify_status: Optional[str] = None
    remark: Optional[str] = None


@router.get("/", response_model=List[AttendanceOut])
def get_attendance(
    period: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        employees = db.query(Employee).order_by(Employee.employee_no).all()
        attendance_map = {}
        records = db.query(AttendanceRecord).filter(AttendanceRecord.period == period).all()
        for r in records:
            attendance_map[r.employee_id] = r

        result = []
        for emp in employees:
            att = attendance_map.get(emp.id)
            result.append(AttendanceOut(
                id=att.id if att else None,
                period=period,
                employee_id=emp.id,
                employee_no=emp.employee_no,
                employee_name=emp.name,
                total_work_days=att.total_work_days if att else None,
                actual_work_days=att.actual_work_days if att else None,
                attendance_rate=att.attendance_rate if att else None,
                late_count=att.late_count if att else None,
                early_count=att.early_count if att else None,
                missed_punch_count=att.missed_punch_count if att else None,
                sick_leave_days=att.sick_leave_days if att else None,
                personal_leave_days=att.personal_leave_days if att else None,
                annual_leave_days=att.annual_leave_days if att else None,
                other_leave_days=att.other_leave_days if att else None,
                is_home_checkin=att.is_home_checkin if att else None,
                need_verify=att.need_verify if att else None,
                verify_status=att.verify_status if att else None,
                remark=att.remark if att else None,
            ))
        return result

    query = db.query(AttendanceRecord)
    if employee_id:
        query = query.filter(AttendanceRecord.employee_id == employee_id)
    records = query.order_by(AttendanceRecord.period.desc(), AttendanceRecord.employee_id).all()
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        result.append(AttendanceOut(
            id=r.id, period=r.period, employee_id=r.employee_id,
            employee_no=emp.employee_no if emp else "",
            employee_name=emp.name if emp else "",
            total_work_days=r.total_work_days, actual_work_days=r.actual_work_days,
            attendance_rate=r.attendance_rate, late_count=r.late_count,
            early_count=r.early_count, missed_punch_count=r.missed_punch_count,
            sick_leave_days=r.sick_leave_days, personal_leave_days=r.personal_leave_days,
            annual_leave_days=r.annual_leave_days, other_leave_days=r.other_leave_days,
            is_home_checkin=r.is_home_checkin, need_verify=r.need_verify,
            verify_status=r.verify_status, remark=r.remark,
        ))
    return result


@router.get("/export")
def export_attendance(
    period: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        employees = db.query(Employee).order_by(Employee.employee_no).all()
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
    headers = ["核算周期", "员工编号", "员工姓名", "总计薪天数", "实际计薪天数", "出勤率", "迟到次数", "早退次数", "缺卡次数", "病假天数", "事假天数", "年假天数", "其他假天数", "在家打卡", "需核实", "核实状态", "备注"]
    ws.append(headers)
    for emp, r in data:
        if r:
            ws.append([
                r.period, emp.employee_no if emp else "", emp.name if emp else "",
                float(r.total_work_days), float(r.actual_work_days),
                float(r.attendance_rate), r.late_count, r.early_count, r.missed_punch_count,
                float(r.sick_leave_days), float(r.personal_leave_days), float(r.annual_leave_days),
                float(r.other_leave_days), "是" if r.is_home_checkin else "否",
                "是" if r.need_verify else "否", r.verify_status or "", r.remark or ""
            ])
        else:
            ws.append([
                period, emp.employee_no, emp.name,
                "", "", "", "", "", "", "", "", "", "", "", "", "", ""
            ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=attendance_export.xlsx"}
    )


@router.post("/", response_model=AttendanceOut)
def create_attendance(att: AttendanceCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.period == att.period,
        AttendanceRecord.employee_id == att.employee_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"员工 [{att.employee_id}] 在周期 [{att.period}] 的考勤记录已存在")

    attendance_rate = att.actual_work_days / att.total_work_days if att.total_work_days > 0 else 0
    db_att = AttendanceRecord(
        attendance_rate=attendance_rate,
        **{k: v for k, v in att.model_dump().items() if k != "attendance_rate"}
    )
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "create", f"新增考勤记录 (employee_id={att.employee_id}, period={att.period})")
    return db_att


@router.put("/{record_id}", response_model=AttendanceOut)
def update_attendance(record_id: int, data: AttendanceUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    att = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="考勤记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(att, key, value)

    if "total_work_days" in update_data or "actual_work_days" in update_data:
        att.attendance_rate = float(att.actual_work_days) / float(att.total_work_days) if float(att.total_work_days) > 0 else 0

    db.commit()
    db.refresh(att)
    write_log(db, "data_change", current_user.id, current_user.username, "attendance", "edit", f"编辑考勤记录 (id={record_id})")

    emp = db.query(Employee).filter(Employee.id == att.employee_id).first()
    return AttendanceOut(
        id=att.id, period=att.period, employee_id=att.employee_id,
        employee_no=emp.employee_no if emp else "",
        employee_name=emp.name if emp else "",
        total_work_days=att.total_work_days, actual_work_days=att.actual_work_days,
        attendance_rate=att.attendance_rate, late_count=att.late_count,
        early_count=att.early_count, missed_punch_count=att.missed_punch_count,
        sick_leave_days=att.sick_leave_days, personal_leave_days=att.personal_leave_days,
        annual_leave_days=att.annual_leave_days, other_leave_days=att.other_leave_days,
        is_home_checkin=att.is_home_checkin, need_verify=att.need_verify,
        verify_status=att.verify_status, remark=att.remark,
    )


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
        elif "实际计薪" in h or "实际出勤" in h:
            header_map["actual_work_days"] = i
        elif "迟到" in h:
            header_map["late_count"] = i
        elif "早退" in h:
            header_map["early_count"] = i
        elif "缺卡" in h:
            header_map["missed_punch_count"] = i
        elif "病假" in h:
            header_map["sick_leave_days"] = i
        elif "事假" in h:
            header_map["personal_leave_days"] = i
        elif "年假" in h:
            header_map["annual_leave_days"] = i
        elif "其他假" in h:
            header_map["other_leave_days"] = i
        elif "核实" in h:
            header_map["verify_status"] = i
        elif "备注" in h:
            header_map["remark"] = i

    if "employee_no" not in header_map:
        raise HTTPException(status_code=400, detail="Excel 表头缺少「员工编号」列")

    emp_map = {e.employee_no: e for e in db.query(Employee).all()}

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
            actual_work = get_float("actual_work_days", 0)
            att_rate = actual_work / total_work if total_work > 0 else 0

            existing = db.query(AttendanceRecord).filter(
                AttendanceRecord.period == period,
                AttendanceRecord.employee_id == emp.id
            ).first()

            if existing:
                existing.total_work_days = total_work
                existing.actual_work_days = actual_work
                existing.attendance_rate = att_rate
                existing.late_count = get_int("late_count")
                existing.early_count = get_int("early_count")
                existing.missed_punch_count = get_int("missed_punch_count")
                existing.sick_leave_days = get_float("sick_leave_days")
                existing.personal_leave_days = get_float("personal_leave_days")
                existing.annual_leave_days = get_float("annual_leave_days")
                existing.other_leave_days = get_float("other_leave_days")
                existing.verify_status = get_str("verify_status") or "已核实"
                existing.remark = get_str("remark")
                updated += 1
            else:
                new_att = AttendanceRecord(
                    period=period, employee_id=emp.id,
                    total_work_days=total_work, actual_work_days=actual_work,
                    attendance_rate=att_rate,
                    late_count=get_int("late_count"),
                    early_count=get_int("early_count"),
                    missed_punch_count=get_int("missed_punch_count"),
                    sick_leave_days=get_float("sick_leave_days"),
                    personal_leave_days=get_float("personal_leave_days"),
                    annual_leave_days=get_float("annual_leave_days"),
                    other_leave_days=get_float("other_leave_days"),
                    verify_status=get_str("verify_status") or "已核实",
                    remark=get_str("remark")
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


