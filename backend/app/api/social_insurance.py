from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.query_utils import filter_active_employees
from app.models.models import SocialInsurance, Employee
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class SocialInsuranceOut(BaseModel):
    id: Optional[int] = None
    period: str
    employee_id: int
    employee_no: str = ""
    employee_name: str = ""
    si_base: Optional[float] = None
    pension_personal: Optional[float] = None
    unemployment_personal: Optional[float] = None
    medical_personal: Optional[float] = None
    si_personal: Optional[float] = None
    pension_company: Optional[float] = None
    unemployment_company: Optional[float] = None
    medical_company: Optional[float] = None
    si_company: Optional[float] = None
    hf_base: Optional[float] = None
    hf_personal: Optional[float] = None
    hf_company: Optional[float] = None

    class Config:
        from_attributes = True


class SocialInsuranceCreate(BaseModel):
    period: str
    employee_id: int
    si_base: float = 0
    pension_personal: float = 0
    unemployment_personal: float = 0
    medical_personal: float = 0
    si_personal: float = 0
    pension_company: float = 0
    unemployment_company: float = 0
    medical_company: float = 0
    si_company: float = 0
    hf_base: float = 0
    hf_personal: float = 0
    hf_company: float = 0


class SocialInsuranceUpdate(BaseModel):
    si_base: Optional[float] = None
    pension_personal: Optional[float] = None
    unemployment_personal: Optional[float] = None
    medical_personal: Optional[float] = None
    si_personal: Optional[float] = None
    pension_company: Optional[float] = None
    unemployment_company: Optional[float] = None
    medical_company: Optional[float] = None
    si_company: Optional[float] = None
    hf_base: Optional[float] = None
    hf_personal: Optional[float] = None
    hf_company: Optional[float] = None


@router.get("/", response_model=List[SocialInsuranceOut])
def get_social_insurance(
    period: Optional[str] = Query(None),
    hide_status_id: Optional[int] = Query(None, description="要隐藏的员工状态ID"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        query = db.query(Employee)
        employees = filter_active_employees(query, db, hide_status_id=hide_status_id).order_by(Employee.employee_no).all()
        si_map = {}
        records = db.query(SocialInsurance).filter(SocialInsurance.period == period).all()
        for r in records:
            si_map[r.employee_id] = r

        result = []
        for emp in employees:
            si = si_map.get(emp.id)
            result.append(SocialInsuranceOut(
                id=si.id if si else None,
                period=period,
                employee_id=emp.id,
                employee_no=emp.employee_no,
                employee_name=emp.name,
                si_base=float(si.si_base) if si else None,
                pension_personal=float(si.pension_personal or 0) if si else None,
                unemployment_personal=float(si.unemployment_personal or 0) if si else None,
                medical_personal=float(si.medical_personal or 0) if si else None,
                si_personal=float(si.si_personal) if si else None,
                pension_company=float(si.pension_company or 0) if si else None,
                unemployment_company=float(si.unemployment_company or 0) if si else None,
                medical_company=float(si.medical_company or 0) if si else None,
                si_company=float(si.si_company) if si else None,
                hf_base=float(si.hf_base) if si else None,
                hf_personal=float(si.hf_personal) if si else None,
                hf_company=float(si.hf_company) if si else None,
            ))
        return result

    records = db.query(SocialInsurance).order_by(SocialInsurance.period.desc()).all()
    return [
        SocialInsuranceOut(
            id=r.id,
            period=r.period,
            employee_id=r.employee_id,
            employee_no="",
            employee_name="",
            si_base=float(r.si_base),
            pension_personal=float(r.pension_personal or 0),
            unemployment_personal=float(r.unemployment_personal or 0),
            medical_personal=float(r.medical_personal or 0),
            si_personal=float(r.si_personal),
            pension_company=float(r.pension_company or 0),
            unemployment_company=float(r.unemployment_company or 0),
            medical_company=float(r.medical_company or 0),
            si_company=float(r.si_company),
            hf_base=float(r.hf_base),
            hf_personal=float(r.hf_personal),
            hf_company=float(r.hf_company),
        ) for r in records
    ]


@router.post("/", response_model=SocialInsuranceOut)
def create_social_insurance(
    data: SocialInsuranceCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    existing = db.query(SocialInsurance).filter(
        SocialInsurance.period == data.period,
        SocialInsurance.employee_id == data.employee_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该员工本月社保公积金记录已存在，请使用编辑功能")

    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    si = SocialInsurance(
        period=data.period,
        employee_id=data.employee_id,
        si_base=data.si_base,
        pension_personal=data.pension_personal,
        unemployment_personal=data.unemployment_personal,
        medical_personal=data.medical_personal,
        si_personal=data.si_personal,
        pension_company=data.pension_company,
        unemployment_company=data.unemployment_company,
        medical_company=data.medical_company,
        si_company=data.si_company,
        hf_base=data.hf_base,
        hf_personal=data.hf_personal,
        hf_company=data.hf_company,
    )
    db.add(si)
    db.commit()
    db.refresh(si)
    write_log(db, "data_change", current_user.id, current_user.username, "social_insurance", "create", f"新增社保公积金记录 (period={data.period}, employee={emp.name})")
    return SocialInsuranceOut(
        id=si.id, period=si.period, employee_id=si.employee_id,
        employee_no=emp.employee_no, employee_name=emp.name,
        si_base=float(si.si_base),
        pension_personal=float(si.pension_personal or 0),
        unemployment_personal=float(si.unemployment_personal or 0),
        medical_personal=float(si.medical_personal or 0),
        si_personal=float(si.si_personal),
        pension_company=float(si.pension_company or 0),
        unemployment_company=float(si.unemployment_company or 0),
        medical_company=float(si.medical_company or 0),
        si_company=float(si.si_company),
        hf_base=float(si.hf_base),
        hf_personal=float(si.hf_personal),
        hf_company=float(si.hf_company),
    )


@router.put("/{record_id}", response_model=SocialInsuranceOut)
def update_social_insurance(
    record_id: int,
    data: SocialInsuranceUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    si = db.query(SocialInsurance).filter(SocialInsurance.id == record_id).first()
    if not si:
        raise HTTPException(status_code=404, detail="社保公积金记录不存在")

    emp = db.query(Employee).filter(Employee.id == si.employee_id).first()
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(si, key, value)

    db.commit()
    db.refresh(si)
    write_log(db, "data_change", current_user.id, current_user.username, "social_insurance", "edit", f"编辑社保公积金记录 (id={record_id})")
    return SocialInsuranceOut(
        id=si.id, period=si.period, employee_id=si.employee_id,
        employee_no=emp.employee_no if emp else "",
        employee_name=emp.name if emp else "",
        si_base=float(si.si_base),
        pension_personal=float(si.pension_personal or 0),
        unemployment_personal=float(si.unemployment_personal or 0),
        medical_personal=float(si.medical_personal or 0),
        si_personal=float(si.si_personal),
        pension_company=float(si.pension_company or 0),
        unemployment_company=float(si.unemployment_company or 0),
        medical_company=float(si.medical_company or 0),
        si_company=float(si.si_company),
        hf_base=float(si.hf_base),
        hf_personal=float(si.hf_personal),
        hf_company=float(si.hf_company),
    )


@router.delete("/{record_id}")
def delete_social_insurance(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    si = db.query(SocialInsurance).filter(SocialInsurance.id == record_id).first()
    if not si:
        raise HTTPException(status_code=404, detail="社保公积金记录不存在")
    db.delete(si)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "social_insurance", "delete", f"删除社保公积金记录 (id={record_id})")
    return {"message": "删除成功"}


@router.post("/import/{period}")
def import_social_insurance(
    period: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file.file)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析Excel文件，请确认格式正确")

    created = 0
    updated = 0
    emp_map = {e.employee_no: e for e in db.query(Employee).all()}

    for row in rows:
        if not row or not row[0]:
            continue
        emp_no = str(row[0]).strip()
        emp = emp_map.get(emp_no)
        if not emp:
            continue

        existing = db.query(SocialInsurance).filter(
            SocialInsurance.period == period,
            SocialInsurance.employee_id == emp.id
        ).first()

        si_data = {
            "si_base": float(row[1]) if len(row) > 1 and row[1] else 0,
            "pension_personal": float(row[2]) if len(row) > 2 and row[2] else 0,
            "unemployment_personal": float(row[3]) if len(row) > 3 and row[3] else 0,
            "medical_personal": float(row[4]) if len(row) > 4 and row[4] else 0,
            "si_personal": float(row[5]) if len(row) > 5 and row[5] else 0,
            "pension_company": float(row[6]) if len(row) > 6 and row[6] else 0,
            "unemployment_company": float(row[7]) if len(row) > 7 and row[7] else 0,
            "medical_company": float(row[8]) if len(row) > 8 and row[8] else 0,
            "si_company": float(row[9]) if len(row) > 9 and row[9] else 0,
            "hf_base": float(row[10]) if len(row) > 10 and row[10] else 0,
            "hf_personal": float(row[11]) if len(row) > 11 and row[11] else 0,
            "hf_company": float(row[12]) if len(row) > 12 and row[12] else 0,
        }

        if existing:
            for key, value in si_data.items():
                setattr(existing, key, value)
            updated += 1
        else:
            si = SocialInsurance(period=period, employee_id=emp.id, **si_data)
            db.add(si)
            created += 1

    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "social_insurance", "import", f"批量导入社保公积金 (period={period}, 新增{created}条, 更新{updated}条)")
    return {"message": f"导入完成：新增 {created} 条，更新 {updated} 条", "created": created, "updated": updated}


@router.get("/export/{period}")
def export_social_insurance(
    period: str,
    hide_status_id: Optional[int] = Query(None, description="要隐藏的员工状态ID"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    employees = filter_active_employees(query, db, hide_status_id=hide_status_id).order_by(Employee.employee_no).all()
    si_map = {}
    records = db.query(SocialInsurance).filter(SocialInsurance.period == period).all()
    for r in records:
        si_map[r.employee_id] = r

    wb = Workbook()
    ws = wb.active
    ws.title = f"社保公积金_{period}"
    headers = ["员工编号", "姓名", "社保基数", "养老保险个人", "失业保险个人", "医疗保险个人", "社保个人合计", "养老保险公司", "失业保险公司", "医疗保险公司", "社保公司合计", "公积金基数", "公积金个人", "公积金公司"]
    ws.append(headers)

    for emp in employees:
        si = si_map.get(emp.id)
        ws.append([
            emp.employee_no, emp.name,
            float(si.si_base) if si else "",
            float(si.pension_personal or 0) if si else "",
            float(si.unemployment_personal or 0) if si else "",
            float(si.medical_personal or 0) if si else "",
            float(si.si_personal) if si else "",
            float(si.pension_company or 0) if si else "",
            float(si.unemployment_company or 0) if si else "",
            float(si.medical_company or 0) if si else "",
            float(si.si_company) if si else "",
            float(si.hf_base) if si else "",
            float(si.hf_personal) if si else "",
            float(si.hf_company) if si else "",
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=社保公积金_{period}.xlsx"}
    )