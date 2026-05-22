from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date
from io import BytesIO
from openpyxl import Workbook
from app.core.database import get_db
from app.core.log_helper import write_log
from app.models.models import Employee, EmployeeSalary, SysDictBase
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class EmployeeOut(BaseModel):
    id: int
    employee_no: str
    name: str
    gender: str
    id_card: str
    phone: Optional[str] = None
    contract_company_id: int
    contract_company_name: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    position_id: int
    position_name: Optional[str] = None
    status_id: int
    status_name: Optional[str] = None
    cost_owner: Optional[str] = None
    entry_date: date
    regular_date: Optional[date] = None
    resign_date: Optional[date] = None
    bank_card: Optional[str] = None
    bank_branch: Optional[str] = None
    home_address: Optional[str] = None
    base_salary: Optional[float] = None
    performance_standard: Optional[float] = None
    meal_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    communication_allowance: Optional[float] = None
    computer_allowance: Optional[float] = None
    housing_allowance: Optional[float] = None
    salary_effective_date: Optional[str] = None

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    gender: str
    id_card: str
    phone: Optional[str] = None
    contract_company_id: int
    department_id: int
    position_id: int
    status_id: int
    cost_owner: Optional[str] = None
    entry_date: date
    regular_date: Optional[date] = None
    bank_card: Optional[str] = None
    bank_branch: Optional[str] = None
    home_address: Optional[str] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    contract_company_id: Optional[int] = None
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    status_id: Optional[int] = None
    cost_owner: Optional[str] = None
    entry_date: Optional[date] = None
    regular_date: Optional[date] = None
    resign_date: Optional[date] = None
    bank_card: Optional[str] = None
    bank_branch: Optional[str] = None
    home_address: Optional[str] = None


class SalaryOut(BaseModel):
    id: int
    employee_id: int
    base_salary: float
    performance_standard: float
    meal_allowance: float
    transport_allowance: float
    communication_allowance: float
    computer_allowance: float
    housing_allowance: float
    effective_date: str
    change_reason: Optional[str] = None

    @field_validator('effective_date', mode='before')
    @classmethod
    def convert_effective_date(cls, v):
        if isinstance(v, date):
            return v.isoformat()
        return str(v) if v else ''

    class Config:
        from_attributes = True


class SalaryCreate(BaseModel):
    employee_id: int
    base_salary: float
    performance_standard: float
    meal_allowance: float = 0
    transport_allowance: float = 0
    communication_allowance: float = 0
    computer_allowance: float = 0
    housing_allowance: float = 0
    effective_date: date
    change_reason: Optional[str] = None


def _enrich_employee(emp: Employee, db: Session) -> dict:
    dict_ids = [emp.contract_company_id, emp.department_id, emp.position_id, emp.status_id]
    dict_items = db.query(SysDictBase).filter(SysDictBase.id.in_(dict_ids)).all()
    name_map = {d.id: d.name for d in dict_items}

    latest_salary = db.query(EmployeeSalary).filter(
        EmployeeSalary.employee_id == emp.id
    ).order_by(EmployeeSalary.effective_date.desc()).first()

    result = {
        "id": emp.id, "employee_no": emp.employee_no, "name": emp.name,
        "gender": emp.gender, "id_card": emp.id_card, "phone": emp.phone,
        "contract_company_id": emp.contract_company_id,
        "contract_company_name": name_map.get(emp.contract_company_id),
        "department_id": emp.department_id,
        "department_name": name_map.get(emp.department_id),
        "position_id": emp.position_id,
        "position_name": name_map.get(emp.position_id),
        "status_id": emp.status_id,
        "status_name": name_map.get(emp.status_id),
        "cost_owner": emp.cost_owner, "entry_date": emp.entry_date,
        "regular_date": emp.regular_date, "resign_date": emp.resign_date,
        "bank_card": emp.bank_card, "bank_branch": emp.bank_branch,
        "home_address": emp.home_address,
        "base_salary": float(latest_salary.base_salary) if latest_salary else None,
        "performance_standard": float(latest_salary.performance_standard) if latest_salary else None,
        "meal_allowance": float(latest_salary.meal_allowance) if latest_salary else None,
        "transport_allowance": float(latest_salary.transport_allowance) if latest_salary else None,
        "communication_allowance": float(latest_salary.communication_allowance) if latest_salary else None,
        "computer_allowance": float(latest_salary.computer_allowance) if latest_salary else None,
        "housing_allowance": float(latest_salary.housing_allowance) if latest_salary else None,
        "salary_effective_date": str(latest_salary.effective_date) if latest_salary and latest_salary.effective_date else None,
    }
    return result


@router.get("/", response_model=List[EmployeeOut])
def get_employees(
    status_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    filter_field: Optional[str] = Query(None),
    filter_value: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    if status_id:
        query = query.filter(Employee.status_id == status_id)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if filter_field and filter_value:
        if filter_field == 'name':
            query = query.filter(Employee.name.contains(filter_value))
        elif filter_field == 'no':
            query = query.filter(Employee.employee_no.contains(filter_value))
        elif filter_field == 'department':
            dept_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'department',
                SysDictBase.name.contains(filter_value)
            ).all()
            if dept_ids:
                query = query.filter(Employee.department_id.in_([d[0] for d in dept_ids]))
        elif filter_field == 'company':
            company_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'contract_company',
                SysDictBase.name.contains(filter_value)
            ).all()
            if company_ids:
                query = query.filter(Employee.contract_company_id.in_([c[0] for c in company_ids]))
        elif filter_field == 'status':
            status_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'employee_status',
                SysDictBase.name.contains(filter_value)
            ).all()
            if status_ids:
                query = query.filter(Employee.status_id.in_([s[0] for s in status_ids]))
    elif keyword:
        query = query.filter(
            Employee.name.contains(keyword) | Employee.employee_no.contains(keyword)
        )
    employees = query.order_by(Employee.employee_no).all()
    return [_enrich_employee(e, db) for e in employees]


@router.get("/export")
def export_employees(
    filter_field: Optional[str] = Query(None),
    filter_value: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    query = db.query(Employee)
    if filter_field and filter_value:
        if filter_field == 'name':
            query = query.filter(Employee.name.contains(filter_value))
        elif filter_field == 'no':
            query = query.filter(Employee.employee_no.contains(filter_value))
        elif filter_field == 'department':
            dept_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'department',
                SysDictBase.name.contains(filter_value)
            ).all()
            if dept_ids:
                query = query.filter(Employee.department_id.in_([d[0] for d in dept_ids]))
        elif filter_field == 'company':
            company_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'contract_company',
                SysDictBase.name.contains(filter_value)
            ).all()
            if company_ids:
                query = query.filter(Employee.contract_company_id.in_([c[0] for c in company_ids]))
        elif filter_field == 'status':
            status_ids = db.query(SysDictBase.id).filter(
                SysDictBase.category == 'employee_status',
                SysDictBase.name.contains(filter_value)
            ).all()
            if status_ids:
                query = query.filter(Employee.status_id.in_([s[0] for s in status_ids]))
    employees = query.order_by(Employee.employee_no).all()
    enriched = [_enrich_employee(e, db) for e in employees]

    wb = Workbook()
    ws = wb.active
    ws.title = "员工数据"
    headers = ["编号", "姓名", "性别", "身份证号", "手机号", "合同公司", "部门", "岗位", "状态", "成本归属", "入职日期", "转正日期", "离职日期", "银行卡号", "开户行", "家庭地址", "基本工资", "绩效标准", "餐补", "交通补贴", "通讯补贴", "电脑补贴", "住房补贴", "薪资生效日期"]
    ws.append(headers)
    for e in enriched:
        ws.append([
            e["employee_no"], e["name"], e["gender"], e["id_card"], e.get("phone") or "",
            e.get("contract_company_name") or "", e.get("department_name") or "",
            e.get("position_name") or "", e.get("status_name") or "",
            e.get("cost_owner") or "", str(e["entry_date"]),
            str(e.get("regular_date") or ""), str(e.get("resign_date") or ""),
            e.get("bank_card") or "", e.get("bank_branch") or "", e.get("home_address") or "",
            e.get("base_salary") or "", e.get("performance_standard") or "",
            e.get("meal_allowance") or "", e.get("transport_allowance") or "",
            e.get("communication_allowance") or "", e.get("computer_allowance") or "",
            e.get("housing_allowance") or "", e.get("salary_effective_date") or ""
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employees_export.xlsx"}
    )


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")
    return _enrich_employee(emp, db)


@router.post("/", response_model=EmployeeOut)
def create_employee(emp: EmployeeCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    existing = db.query(Employee).filter(Employee.id_card == emp.id_card).first()
    if existing:
        raise HTTPException(status_code=400, detail="该身份证号已存在")
    count = db.query(Employee).count()
    employee_no = f"E{count + 1:04d}"
    db_emp = Employee(employee_no=employee_no, **emp.model_dump())
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    write_log(db, "data_change", current_user.id, current_user.username, "employee", "create", f"新增员工 {db_emp.name}({db_emp.employee_no})")
    return _enrich_employee(db_emp, db)


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, emp: EmployeeUpdate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    db_emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="员工不存在")
    update_data = emp.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_emp, key, value)
    db.commit()
    db.refresh(db_emp)
    write_log(db, "data_change", current_user.id, current_user.username, "employee", "edit", f"编辑员工 {db_emp.name}({db_emp.employee_no})")
    return _enrich_employee(db_emp, db)


@router.delete("/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    db_emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="员工不存在")
    db.delete(db_emp)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "employee", "delete", f"删除员工 {db_emp.name}({db_emp.employee_no})")
    return {"message": "删除成功"}


@router.get("/{employee_id}/salaries", response_model=List[SalaryOut])
def get_employee_salaries(employee_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    salaries = db.query(EmployeeSalary).filter(
        EmployeeSalary.employee_id == employee_id
    ).order_by(EmployeeSalary.effective_date.desc()).all()
    return salaries


@router.post("/salaries", response_model=SalaryOut)
def create_employee_salary(salary: SalaryCreate, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    employee = db.query(Employee).filter(Employee.id == salary.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在，无法创建薪资记录")
    try:
        db_salary = EmployeeSalary(**salary.model_dump())
        db.add(db_salary)
        db.commit()
        db.refresh(db_salary)
        write_log(db, "data_change", current_user.id, current_user.username, "employee", "edit", f"更新员工薪资记录 (employee_id={salary.employee_id})")
        return db_salary
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"薪资记录创建失败：{str(e)}")


@router.post("/batch-delete")
def batch_delete_employees(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的员工ID列表")
    employees = db.query(Employee).filter(Employee.id.in_(ids)).all()
    if not employees:
        raise HTTPException(status_code=404, detail="未找到指定的员工")
    for emp in employees:
        db.query(EmployeeSalary).filter(EmployeeSalary.employee_id == emp.id).delete()
        db.delete(emp)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "employee", "delete", f"批量删除 {len(employees)} 名员工")
    return {"message": f"成功删除 {len(employees)} 名员工", "deleted_count": len(employees)}


@router.post("/export-selected")
def export_selected_employees(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要导出的员工ID列表")
    employees = db.query(Employee).filter(Employee.id.in_(ids)).order_by(Employee.employee_no).all()
    enriched = [_enrich_employee(e, db) for e in employees]

    wb = Workbook()
    ws = wb.active
    ws.title = "员工数据"
    headers = ["编号", "姓名", "性别", "身份证号", "手机号", "合同公司", "部门", "岗位", "状态", "成本归属", "入职日期", "转正日期", "离职日期", "银行卡号", "开户行", "家庭地址", "基本工资", "绩效标准", "餐补", "交通补贴", "通讯补贴", "电脑补贴", "住房补贴", "薪资生效日期"]
    ws.append(headers)
    for e in enriched:
        ws.append([
            e["employee_no"], e["name"], e["gender"], e["id_card"], e.get("phone") or "",
            e.get("contract_company_name") or "", e.get("department_name") or "",
            e.get("position_name") or "", e.get("status_name") or "",
            e.get("cost_owner") or "", str(e["entry_date"]),
            str(e.get("regular_date") or ""), str(e.get("resign_date") or ""),
            e.get("bank_card") or "", e.get("bank_branch") or "", e.get("home_address") or "",
            e.get("base_salary") or "", e.get("performance_standard") or "",
            e.get("meal_allowance") or "", e.get("transport_allowance") or "",
            e.get("communication_allowance") or "", e.get("computer_allowance") or "",
            e.get("housing_allowance") or "", e.get("salary_effective_date") or ""
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employees_selected_export.xlsx"}
    )


@router.post("/import")
async def import_employees(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

    try:
        contents = await file.read()
        wb = Workbook()
        wb.close()
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
        if "姓名" in h:
            header_map["name"] = i
        elif "性别" in h:
            header_map["gender"] = i
        elif "身份证" in h:
            header_map["id_card"] = i
        elif "电话" in h or "手机" in h or "联系" in h:
            header_map["phone"] = i
        elif "合同公司" in h or "公司" in h:
            header_map["company"] = i
        elif "部门" in h:
            header_map["department"] = i
        elif "职务" in h or "岗位" in h or "职位" in h:
            header_map["position"] = i
        elif "状态" in h or "用工" in h:
            header_map["status"] = i
        elif "入职" in h:
            header_map["entry_date"] = i
        elif "转正" in h:
            header_map["regular_date"] = i
        elif "地址" in h or "家庭" in h or "住址" in h:
            header_map["home_address"] = i
        elif "费用负责人" in h or "成本" in h:
            header_map["cost_owner"] = i
        elif "银行卡" in h:
            header_map["bank_card"] = i
        elif "开户行" in h:
            header_map["bank_branch"] = i

    required = ["name", "gender", "id_card", "company", "department", "position", "status", "entry_date"]
    missing = [k for k in required if k not in header_map]
    if missing:
        raise HTTPException(status_code=400, detail=f"Excel 表头缺少必要列：{', '.join(missing)}")

    dict_items = db.query(SysDictBase).all()
    company_map = {d.name: d.id for d in dict_items if d.category == "contract_company"}
    dept_map = {d.name: d.id for d in dict_items if d.category == "department"}
    position_map = {d.name: d.id for d in dict_items if d.category == "position"}
    status_map = {d.name: d.id for d in dict_items if d.category == "employee_status"}

    created = 0
    updated = 0
    errors = []

    for row_idx, row in enumerate(rows[1:], start=2):
        try:
            name = str(row[header_map["name"]]).strip() if row[header_map["name"]] else ""
            gender = str(row[header_map["gender"]]).strip() if row[header_map["gender"]] else ""
            id_card = str(row[header_map["id_card"]]).strip() if row[header_map["id_card"]] else ""
            phone = str(row[header_map["phone"]]).strip() if header_map.get("phone") is not None and row[header_map["phone"]] else None
            company_name = str(row[header_map["company"]]).strip() if row[header_map["company"]] else ""
            dept_name = str(row[header_map["department"]]).strip() if row[header_map["department"]] else ""
            position_name = str(row[header_map["position"]]).strip() if row[header_map["position"]] else ""
            status_name = str(row[header_map["status"]]).strip() if row[header_map["status"]] else ""
            entry_date_str = str(row[header_map["entry_date"]]).strip() if row[header_map["entry_date"]] else ""
            regular_date_str = str(row[header_map["regular_date"]]).strip() if header_map.get("regular_date") is not None and row[header_map["regular_date"]] else None
            home_address = str(row[header_map["home_address"]]).strip() if header_map.get("home_address") is not None and row[header_map["home_address"]] else None
            cost_owner = str(row[header_map["cost_owner"]]).strip() if header_map.get("cost_owner") is not None and row[header_map["cost_owner"]] else None
            bank_card = str(row[header_map["bank_card"]]).strip() if header_map.get("bank_card") is not None and row[header_map["bank_card"]] else None
            bank_branch = str(row[header_map["bank_branch"]]).strip() if header_map.get("bank_branch") is not None and row[header_map["bank_branch"]] else None

            if not name or not gender or not id_card:
                errors.append(f"第{row_idx}行：姓名、性别、身份证号不能为空")
                continue

            company_id = company_map.get(company_name)
            dept_id = dept_map.get(dept_name)
            pos_id = position_map.get(position_name)
            stat_id = status_map.get(status_name)

            if not company_id:
                errors.append(f"第{row_idx}行：合同公司「{company_name}」在数据字典中不存在")
                continue
            if not dept_id:
                errors.append(f"第{row_idx}行：部门「{dept_name}」在数据字典中不存在")
                continue
            if not pos_id:
                errors.append(f"第{row_idx}行：职务「{position_name}」在数据字典中不存在")
                continue
            if not stat_id:
                errors.append(f"第{row_idx}行：用工状态「{status_name}」在数据字典中不存在")
                continue

            try:
                entry_date = date.fromisoformat(entry_date_str[:10]) if entry_date_str else None
            except ValueError:
                errors.append(f"第{row_idx}行：入职时间格式错误「{entry_date_str}」，应为 YYYY-MM-DD")
                continue

            regular_date = None
            if regular_date_str:
                try:
                    regular_date = date.fromisoformat(regular_date_str[:10])
                except ValueError:
                    pass

            existing = db.query(Employee).filter(Employee.id_card == id_card).first()
            if existing:
                existing.name = name
                existing.gender = gender
                existing.phone = phone
                existing.contract_company_id = company_id
                existing.department_id = dept_id
                existing.position_id = pos_id
                existing.status_id = stat_id
                existing.cost_owner = cost_owner
                existing.entry_date = entry_date
                existing.regular_date = regular_date
                existing.home_address = home_address
                existing.bank_card = bank_card
                existing.bank_branch = bank_branch
                updated += 1
            else:
                count = db.query(Employee).count()
                employee_no = f"E{count + 1:04d}"
                new_emp = Employee(
                    employee_no=employee_no, name=name, gender=gender, id_card=id_card,
                    phone=phone, contract_company_id=company_id, department_id=dept_id,
                    position_id=pos_id, status_id=stat_id, cost_owner=cost_owner,
                    entry_date=entry_date, regular_date=regular_date,
                    home_address=home_address, bank_card=bank_card, bank_branch=bank_branch
                )
                db.add(new_emp)
                created += 1
        except Exception as e:
            errors.append(f"第{row_idx}行：处理失败 - {str(e)}")

    db.commit()
    wb.close()
    write_log(db, "data_change", current_user.id, current_user.username, "employee", "import", f"批量导入员工：新增{created}人，更新{updated}人")

    return {
        "message": f"导入完成：新增 {created} 人，更新 {updated} 人",
        "created": created,
        "updated": updated,
        "errors": errors
    }