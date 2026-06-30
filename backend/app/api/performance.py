from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.query_utils import filter_active_employees
from app.models.models import PerformanceScore, Employee
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class PerformanceOut(BaseModel):
    id: Optional[int] = None
    period: str
    employee_id: int
    employee_no: str = ""
    employee_name: str = ""
    initial_score: Optional[float] = None
    final_score: Optional[float] = None
    coefficient: float = 1.00
    reviewer_id: Optional[int] = None

    class Config:
        from_attributes = True


class PerformanceCreate(BaseModel):
    period: str
    employee_id: int
    initial_score: Optional[float] = None
    final_score: Optional[float] = None
    coefficient: float = 1.00


class PerformanceUpdate(BaseModel):
    initial_score: Optional[float] = None
    final_score: Optional[float] = None
    coefficient: Optional[float] = None


class PerformanceImportItem(BaseModel):
    employee_no: str
    initial_score: Optional[float] = None
    final_score: Optional[float] = None
    coefficient: float = 1.00


@router.get("/", response_model=List[PerformanceOut])
def get_performances(
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if period:
        query = db.query(Employee)
        employees = filter_active_employees(query, db).order_by(Employee.employee_no).all()
        perf_map = {}
        records = db.query(PerformanceScore).filter(PerformanceScore.period == period).all()
        for r in records:
            perf_map[r.employee_id] = r

        result = []
        for emp in employees:
            p = perf_map.get(emp.id)
            result.append(PerformanceOut(
                id=p.id if p else None,
                period=period,
                employee_id=emp.id,
                employee_no=emp.employee_no,
                employee_name=emp.name,
                initial_score=float(p.initial_score) if p and p.initial_score else None,
                final_score=float(p.final_score) if p and p.final_score else None,
                coefficient=float(p.coefficient) if p else 1.00,
                reviewer_id=p.reviewer_id if p else None,
            ))
        return result

    records = db.query(PerformanceScore).order_by(
        PerformanceScore.period.desc(), PerformanceScore.employee_id
    ).all()
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        result.append(PerformanceOut(
            id=r.id, period=r.period, employee_id=r.employee_id,
            employee_no=emp.employee_no if emp else "",
            employee_name=emp.name if emp else "",
            initial_score=float(r.initial_score) if r.initial_score else None,
            final_score=float(r.final_score) if r.final_score else None,
            coefficient=float(r.coefficient),
            reviewer_id=r.reviewer_id,
        ))
    return result


@router.post("/", response_model=PerformanceOut)
def create_performance(
    data: PerformanceCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    existing = db.query(PerformanceScore).filter(
        PerformanceScore.period == data.period,
        PerformanceScore.employee_id == data.employee_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"员工 [{data.employee_id}] 在周期 [{data.period}] 的绩效数据已存在")

    perf = PerformanceScore(
        period=data.period,
        employee_id=data.employee_id,
        initial_score=data.initial_score,
        final_score=data.final_score,
        coefficient=data.coefficient,
        reviewer_id=current_user.id
    )
    db.add(perf)
    db.commit()
    db.refresh(perf)
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "create", f"新增绩效数据 (employee_id={data.employee_id}, period={data.period})")

    emp = db.query(Employee).filter(Employee.id == perf.employee_id).first()
    return PerformanceOut(
        id=perf.id, period=perf.period, employee_id=perf.employee_id,
        employee_no=emp.employee_no if emp else "",
        employee_name=emp.name if emp else "",
        initial_score=float(perf.initial_score) if perf.initial_score else None,
        final_score=float(perf.final_score) if perf.final_score else None,
        coefficient=float(perf.coefficient),
        reviewer_id=perf.reviewer_id,
    )


@router.put("/{perf_id}", response_model=PerformanceOut)
def update_performance(
    perf_id: int,
    data: PerformanceUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    perf = db.query(PerformanceScore).filter(PerformanceScore.id == perf_id).first()
    if not perf:
        raise HTTPException(status_code=404, detail="绩效记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(perf, key, value)
    perf.reviewer_id = current_user.id

    db.commit()
    db.refresh(perf)
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "edit", f"编辑绩效数据 (id={perf_id})")

    emp = db.query(Employee).filter(Employee.id == perf.employee_id).first()
    return PerformanceOut(
        id=perf.id, period=perf.period, employee_id=perf.employee_id,
        employee_no=emp.employee_no if emp else "",
        employee_name=emp.name if emp else "",
        initial_score=float(perf.initial_score) if perf.initial_score else None,
        final_score=float(perf.final_score) if perf.final_score else None,
        coefficient=float(perf.coefficient),
        reviewer_id=perf.reviewer_id,
    )


@router.delete("/{perf_id}")
def delete_performance(
    perf_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    perf = db.query(PerformanceScore).filter(PerformanceScore.id == perf_id).first()
    if not perf:
        raise HTTPException(status_code=404, detail="绩效记录不存在")
    db.delete(perf)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "delete", f"删除绩效记录 (id={perf_id})")
    return {"message": "删除成功"}


@router.post("/import/{period}")
def import_performances(
    period: str,
    items: List[PerformanceImportItem],
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    emp_map = {e.employee_no: e for e in db.query(Employee).all()}
    created = 0
    updated = 0
    errors = []

    for item in items:
        emp = emp_map.get(item.employee_no)
        if not emp:
            errors.append(f"员工编号 [{item.employee_no}] 不存在")
            continue

        existing = db.query(PerformanceScore).filter(
            PerformanceScore.period == period,
            PerformanceScore.employee_id == emp.id
        ).first()

        if existing:
            existing.initial_score = item.initial_score
            existing.final_score = item.final_score
            existing.coefficient = item.coefficient
            existing.reviewer_id = current_user.id
            updated += 1
        else:
            perf = PerformanceScore(
                period=period,
                employee_id=emp.id,
                initial_score=item.initial_score,
                final_score=item.final_score,
                coefficient=item.coefficient,
                reviewer_id=current_user.id
            )
            db.add(perf)
            created += 1

    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "import", f"批量导入绩效：新增{created}条，更新{updated}条 (period={period})")
    return {
        "message": f"导入完成：新增 {created} 条，更新 {updated} 条",
        "created": created,
        "updated": updated,
        "errors": errors
    }


@router.get("/export/{period}")
def export_performances(
    period: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    employees = filter_active_employees(query, db).order_by(Employee.employee_no).all()
    perf_map = {}
    records = db.query(PerformanceScore).filter(PerformanceScore.period == period).all()
    for r in records:
        perf_map[r.employee_id] = r

    wb = Workbook()
    ws = wb.active
    ws.title = f"绩效数据_{period}"
    headers = ["员工编号", "员工姓名", "初评分数", "复评分数", "绩效系数"]
    ws.append(headers)

    for emp in employees:
        p = perf_map.get(emp.id)
        ws.append([
            emp.employee_no,
            emp.name,
            float(p.initial_score) if p and p.initial_score else "",
            float(p.final_score) if p and p.final_score else "",
            float(p.coefficient) if p else 1.00
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=performance_{period}.xlsx"}
    )


@router.post("/batch-delete")
def batch_delete_performances(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的绩效记录ID列表")
    records = db.query(PerformanceScore).filter(PerformanceScore.id.in_(ids)).all()
    if not records:
        raise HTTPException(status_code=404, detail="未找到指定的绩效记录")
    for r in records:
        db.delete(r)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "delete", f"批量删除 {len(records)} 条绩效记录")
    return {"message": f"成功删除 {len(records)} 条绩效记录", "deleted_count": len(records)}


@router.post("/import-excel")
async def import_performances_excel(
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
        elif "初评" in h:
            header_map["initial_score"] = i
        elif "复评" in h:
            header_map["final_score"] = i
        elif "系数" in h or "绩效" in h:
            header_map["coefficient"] = i

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

            def get_float(key):
                if key in header_map and row[header_map[key]] is not None:
                    try:
                        return float(row[header_map[key]])
                    except (ValueError, TypeError):
                        return None
                return None

            initial = get_float("initial_score")
            final = get_float("final_score")
            coef = get_float("coefficient") or 1.00

            existing = db.query(PerformanceScore).filter(
                PerformanceScore.period == period,
                PerformanceScore.employee_id == emp.id
            ).first()

            if existing:
                existing.initial_score = initial
                existing.final_score = final
                existing.coefficient = coef
                existing.reviewer_id = current_user.id
                updated += 1
            else:
                perf = PerformanceScore(
                    period=period, employee_id=emp.id,
                    initial_score=initial, final_score=final,
                    coefficient=coef, reviewer_id=current_user.id
                )
                db.add(perf)
                created += 1
        except Exception as e:
            errors.append(f"第{row_idx}行：处理失败 - {str(e)}")

    db.commit()
    wb.close()
    write_log(db, "data_change", current_user.id, current_user.username, "performance", "import", f"Excel批量导入绩效：新增{created}条，更新{updated}条 (period={period})")

    return {
        "message": f"导入完成：新增 {created} 条，更新 {updated} 条",
        "created": created,
        "updated": updated,
        "errors": errors
    }