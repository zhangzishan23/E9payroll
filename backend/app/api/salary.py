from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
from io import BytesIO
from openpyxl import Workbook
import uuid
from app.core.database import get_db
from app.core.log_helper import write_log
from app.models.models import (
    Employee, EmployeeSalary, EmployeeSalaryAdjustment, AttendanceRecord, PerformanceScore,
    SocialInsurance, LegacyAdjustment, TravelReimbursement, LaborCompensation,
    SalaryCalculation, CalculationLog, SysDictBase
)
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


def _get_period_end(period: str) -> date:
    if '-' in period:
        year, month = map(int, period.split('-'))
    else:
        year = int(period[:4])
        month = int(period[4:6])
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


class DataSourceStatus(BaseModel):
    source_name: str
    source_key: str
    status: str
    count: int
    missing_employees: List[str] = []


class DataCompletenessOut(BaseModel):
    period: str
    total_employees: int
    complete_count: int
    missing_count: int
    optional_missing_count: int
    sources: List[DataSourceStatus] = []


class SalaryCalcOut(BaseModel):
    id: Optional[int] = None
    period: str
    employee_id: int
    employee_no: str = ""
    employee_name: str = ""
    contract_company: str = ""
    department: str = ""
    position: str = ""
    status: str = ""
    entry_date: Optional[str] = None
    base_salary: Optional[float] = None
    base_salary_prorated: Optional[float] = None
    performance_standard_prorated: Optional[float] = None
    adjustment_id: Optional[int] = None
    monthly_standard: Optional[float] = None
    performance_standard: Optional[float] = None
    performance_coefficient: Optional[float] = None
    actual_performance: Optional[float] = None
    effective_performance: Optional[float] = None
    meal_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    communication_allowance: Optional[float] = None
    computer_allowance: Optional[float] = None
    housing_allowance: Optional[float] = None
    allowance_total: Optional[float] = None
    commission_bonus: Optional[float] = None
    pretax_adjustment: Optional[float] = None
    posttax_adjustment: Optional[float] = None
    posttax_adjustment_reason: Optional[str] = None
    total_work_days: Optional[float] = None
    actual_work_days: Optional[float] = None
    attendance_rate: Optional[float] = None
    gross_salary: Optional[float] = None
    pension_personal: Optional[float] = None
    unemployment_personal: Optional[float] = None
    medical_personal: Optional[float] = None
    social_insurance_personal: Optional[float] = None
    housing_fund_personal: Optional[float] = None
    si_hf_total: Optional[float] = None
    tax_deduction: Optional[float] = None
    net_salary: Optional[float] = None
    last_month_untaxed: Optional[float] = None
    travel_untaxed: Optional[float] = None
    compensation_tax: Optional[float] = None
    actual_taxable: Optional[float] = None
    special_deduction: Optional[float] = None
    review_status: str = ""
    calculation_status: str = ""
    data_completeness: str = ""

    class Config:
        from_attributes = True


class SalaryCalcUpdate(BaseModel):
    commission_bonus: Optional[float] = None
    pretax_adjustment: Optional[float] = None
    posttax_adjustment: Optional[float] = None
    posttax_adjustment_reason: Optional[str] = None
    performance_coefficient: Optional[float] = None
    tax_deduction: Optional[float] = None
    special_deduction: Optional[float] = None
    last_month_untaxed: Optional[float] = None
    travel_untaxed: Optional[float] = None
    compensation_tax: Optional[float] = None
    review_status: Optional[str] = None


class CalculationSummary(BaseModel):
    period: str
    total_employees: int
    success_count: int
    failed_count: int
    total_gross_salary: float
    avg_gross_salary: float
    total_net_salary: float
    avg_net_salary: float
    batch_no: str


@router.get("/periods")
def get_available_periods(db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    periods = db.query(SalaryCalculation.period).distinct().order_by(SalaryCalculation.period.desc()).all()
    return [p[0] for p in periods]


@router.get("/check-completeness/{period}", response_model=DataCompletenessOut)
def check_data_completeness(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    active_employees = db.query(Employee).order_by(Employee.employee_no).all()

    sources = []
    missing_map = {}

    period_end = _get_period_end(period)
    salaries = {s.employee_id: s for s in db.query(EmployeeSalary).filter(
        EmployeeSalary.employee_id.in_([e.id for e in active_employees]),
        EmployeeSalary.effective_date <= period_end
    ).order_by(EmployeeSalary.effective_date.desc(), EmployeeSalary.id.desc()).all()}

    attendance = {a.employee_id: a for a in db.query(AttendanceRecord).filter(
        AttendanceRecord.period == period,
        AttendanceRecord.employee_id.in_([e.id for e in active_employees])
    ).all()}

    performances = {p.employee_id: p for p in db.query(PerformanceScore).filter(
        PerformanceScore.period == period,
        PerformanceScore.employee_id.in_([e.id for e in active_employees])
    ).all()}

    social_ins = {s.employee_id: s for s in db.query(SocialInsurance).filter(
        SocialInsurance.period == period,
        SocialInsurance.employee_id.in_([e.id for e in active_employees])
    ).all()}

    for emp in active_employees:
        missing = []
        if emp.id not in salaries:
            missing.append("薪资档案")
        if emp.id not in attendance:
            missing.append("考勤数据")
        if emp.id not in social_ins:
            missing.append("社保公积金")
        if missing:
            missing_map[emp.id] = missing

    sources.append(DataSourceStatus(
        source_name="员工档案", source_key="employee",
        status="完整", count=len(active_employees)
    ))
    sources.append(DataSourceStatus(
        source_name="薪资档案", source_key="salary",
        status="完整" if len(salaries) == len(active_employees) else "部分缺失",
        count=len(salaries),
        missing_employees=[e.name for e in active_employees if e.id not in salaries]
    ))
    sources.append(DataSourceStatus(
        source_name="考勤数据", source_key="attendance",
        status="完整" if len(attendance) == len(active_employees) else "部分缺失",
        count=len(attendance),
        missing_employees=[e.name for e in active_employees if e.id not in attendance]
    ))
    sources.append(DataSourceStatus(
        source_name="绩效系数", source_key="performance",
        status="完整" if len(performances) == len(active_employees) else "部分缺失",
        count=len(performances),
        missing_employees=[e.name for e in active_employees if e.id not in performances]
    ))
    sources.append(DataSourceStatus(
        source_name="社保公积金", source_key="social_insurance",
        status="完整" if len(social_ins) == len(active_employees) else "部分缺失",
        count=len(social_ins),
        missing_employees=[e.name for e in active_employees if e.id not in social_ins]
    ))

    travel_reimbs = {t.employee_id: t for t in db.query(TravelReimbursement).filter(
        TravelReimbursement.period == period
    ).all()}
    sources.append(DataSourceStatus(
        source_name="临时差旅报销", source_key="travel_reimbursement",
        status="可选数据",
        count=len(travel_reimbs),
        missing_employees=[]
    ))

    labor_comps = {l.employee_id: l for l in db.query(LaborCompensation).filter(
        LaborCompensation.period == period
    ).all()}
    sources.append(DataSourceStatus(
        source_name="劳动补偿金", source_key="labor_compensation",
        status="可选数据",
        count=len(labor_comps),
        missing_employees=[]
    ))

    legacy_adjs = {l.employee_id: l for l in db.query(LegacyAdjustment).filter(
        LegacyAdjustment.period == period
    ).all()}
    sources.append(DataSourceStatus(
        source_name="遗留金额调整", source_key="legacy_adjustment",
        status="可选数据",
        count=len(legacy_adjs),
        missing_employees=[]
    ))

    complete_count = sum(1 for e in active_employees if e.id not in missing_map)
    missing_count = len(missing_map)

    return DataCompletenessOut(
        period=period,
        total_employees=len(active_employees),
        complete_count=complete_count,
        missing_count=missing_count,
        optional_missing_count=0,
        sources=sources
    )


@router.post("/calculate/{period}", response_model=CalculationSummary)
def calculate_salary(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    existing = db.query(SalaryCalculation).filter(SalaryCalculation.period == period).first()
    if existing:
        db.query(SalaryCalculation).filter(SalaryCalculation.period == period).delete()
        db.commit()

    batch_no = f"CALC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    start_time = datetime.now()

    active_employees = db.query(Employee).order_by(Employee.employee_no).all()

    period_end = _get_period_end(period)
    salaries = {}
    for s in db.query(EmployeeSalary).filter(
        EmployeeSalary.effective_date <= period_end
    ).order_by(EmployeeSalary.effective_date.desc(), EmployeeSalary.id.desc()).all():
        if s.employee_id not in salaries:
            salaries[s.employee_id] = s

    attendance = {a.employee_id: a for a in db.query(AttendanceRecord).filter(
        AttendanceRecord.period == period
    ).all()}

    performances = {p.employee_id: p for p in db.query(PerformanceScore).filter(
        PerformanceScore.period == period
    ).all()}

    social_ins = {s.employee_id: s for s in db.query(SocialInsurance).filter(
        SocialInsurance.period == period
    ).all()}

    travel_reimbs = {}
    for tr in db.query(TravelReimbursement).filter(TravelReimbursement.period == period).all():
        travel_reimbs[tr.employee_id] = travel_reimbs.get(tr.employee_id, 0) + float(tr.amount)

    labor_comps = {}
    for lc in db.query(LaborCompensation).filter(LaborCompensation.period == period).all():
        labor_comps[lc.employee_id] = labor_comps.get(lc.employee_id, 0) + float(lc.amount)

    legacy_adjs = {}
    for la in db.query(LegacyAdjustment).filter(LegacyAdjustment.period == period).all():
        if la.employee_id not in legacy_adjs:
            legacy_adjs[la.employee_id] = {"pretax": 0, "posttax": 0}
        if la.is_pretax:
            legacy_adjs[la.employee_id]["pretax"] += float(la.amount)
        else:
            legacy_adjs[la.employee_id]["posttax"] += float(la.amount)

    # 加载月中调薪记录
    adjustments = {a.employee_id: a for a in db.query(EmployeeSalaryAdjustment).filter(
        EmployeeSalaryAdjustment.period == period
    ).all()}

    success_count = 0
    failed_count = 0
    total_gross = 0
    total_net = 0

    dict_items = db.query(SysDictBase).all()
    name_map = {d.id: d.name for d in dict_items}

    for emp in active_employees:
        try:
            sal = salaries.get(emp.id)
            att = attendance.get(emp.id)
            perf = performances.get(emp.id)
            si = social_ins.get(emp.id)

            if not sal or not att:
                failed_count += 1
                continue

            base_salary = float(sal.base_salary)
            perf_std = float(sal.performance_standard)
            base_salary_ratio = float(sal.base_salary_ratio) if sal.base_salary_ratio else 1.00
            meal = float(sal.meal_allowance or 0)
            transport = float(sal.transport_allowance or 0)
            comm = float(sal.communication_allowance or 0)
            computer = float(sal.computer_allowance or 0)
            housing = float(sal.housing_allowance or 0)
            allowance_total = meal + transport + comm + computer + housing

            att_rate = float(att.attendance_rate)
            total_work_days = float(att.total_work_days)
            actual_work_days = float(att.actual_work_days)

            # 月中调薪：使用折算后工资
            adj = adjustments.get(emp.id)
            if adj:
                base_salary_prorated = float(adj.base_salary_prorated or 0)
                perf_std_prorated = float(adj.performance_standard_prorated or 0)
                commission_prorated = float(adj.commission_prorated or 0)
                total_prorated = float(adj.total_prorated or 0)
                adjustment_id = adj.id
                # 折算后月薪标准 = 折算后基本工资 + 折算后绩效标准 + 补贴
                monthly_standard = round(base_salary_prorated + perf_std_prorated + allowance_total, 2)
            else:
                base_salary_prorated = base_salary
                perf_std_prorated = perf_std
                commission_prorated = 0
                total_prorated = base_salary + perf_std
                adjustment_id = None
                monthly_standard = round(base_salary + perf_std + allowance_total, 2)

            perf_coef = float(perf.coefficient) if perf else 1.00
            actual_perf = round(perf_std_prorated * perf_coef, 2)
            effective_performance = round(actual_perf * att_rate, 2)

            travel_untaxed = travel_reimbs.get(emp.id, 0)
            compensation_tax = labor_comps.get(emp.id, 0)
            legacy = legacy_adjs.get(emp.id, {"pretax": 0, "posttax": 0})
            pretax_adj = legacy["pretax"]
            posttax_adj = legacy["posttax"]

            # 总应发工资 = (折算后基本工资 + 补贴 + 提成/补发) * 出勤率 + 实际绩效 * 出勤率
            gross_salary = round((base_salary_prorated + allowance_total + commission_prorated) * att_rate + effective_performance, 2)

            pension_personal = float(si.pension_personal or 0) if si else 0
            unemployment_personal = float(si.unemployment_personal or 0) if si else 0
            medical_personal = float(si.medical_personal or 0) if si else 0
            si_personal = pension_personal + unemployment_personal + medical_personal
            hf_personal = float(si.hf_personal) if si else 0
            si_hf_total = si_personal + hf_personal

            net_salary = round(gross_salary - si_hf_total + posttax_adj, 2)

            calc = SalaryCalculation(
                period=period,
                employee_id=emp.id,
                contract_company=name_map.get(emp.contract_company_id, ''),
                department=name_map.get(emp.department_id, ''),
                position=name_map.get(emp.position_id, ''),
                cost_owner=emp.cost_owner or '',
                status=name_map.get(emp.status_id, ''),
                entry_date=emp.entry_date,
                base_salary=base_salary,
                base_salary_prorated=base_salary_prorated,
                performance_standard_prorated=perf_std_prorated,
                adjustment_id=adjustment_id,
                monthly_standard=monthly_standard,
                performance_standard=perf_std,
                performance_coefficient=perf_coef,
                actual_performance=actual_perf,
                effective_performance=effective_performance,
                meal_allowance=meal,
                transport_allowance=transport,
                communication_allowance=comm,
                computer_allowance=computer,
                housing_allowance=housing,
                allowance_total=allowance_total,
                commission_bonus=commission_prorated,
                pretax_adjustment=pretax_adj,
                posttax_adjustment=posttax_adj,
                travel_untaxed=travel_untaxed,
                compensation_tax=compensation_tax,
                total_work_days=total_work_days,
                actual_work_days=actual_work_days,
                attendance_rate=att_rate,
                gross_salary=gross_salary,
                pension_personal=pension_personal,
                unemployment_personal=unemployment_personal,
                medical_personal=medical_personal,
                social_insurance_personal=si_personal,
                housing_fund_personal=hf_personal,
                si_hf_total=si_hf_total,
                net_salary=net_salary,
                calculation_status="应发已核算"
            )
            db.add(calc)
            total_gross += gross_salary
            total_net += net_salary
            success_count += 1

        except Exception:
            failed_count += 1

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    log = CalculationLog(
        batch_no=batch_no,
        period=period,
        calculation_type="应发工资核算",
        status="成功" if failed_count == 0 else "部分成功",
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        total_employees=len(active_employees),
        success_count=success_count,
        failed_count=failed_count,
        operator_id=current_user.id
    )
    db.add(log)
    db.commit()
    write_log(db, "operation", current_user.id, current_user.username, "salary", "calculate", f"应发工资核算 (period={period}, batch={batch_no})", {"success": success_count, "failed": failed_count})

    return CalculationSummary(
        period=period,
        total_employees=len(active_employees),
        success_count=success_count,
        failed_count=failed_count,
        total_gross_salary=round(total_gross, 2),
        avg_gross_salary=round(total_gross / success_count, 2) if success_count > 0 else 0,
        total_net_salary=round(total_net, 2),
        avg_net_salary=round(total_net / success_count, 2) if success_count > 0 else 0,
        batch_no=batch_no
    )


@router.get("/results/{period}", response_model=List[SalaryCalcOut])
def get_calculation_results(
    period: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == period).all()
    calc_map = {c.employee_id: c for c in calcs}
    employees = db.query(Employee).order_by(Employee.employee_no).all()

    period_end = _get_period_end(period)
    salary_map = {}
    for s in db.query(EmployeeSalary).filter(
        EmployeeSalary.effective_date <= period_end
    ).order_by(EmployeeSalary.effective_date.desc(), EmployeeSalary.id.desc()).all():
        if s.employee_id not in salary_map:
            salary_map[s.employee_id] = s

    perf_map = {p.employee_id: p for p in db.query(PerformanceScore).filter(
        PerformanceScore.period == period
    ).all()}

    results = []
    for emp in employees:
        c = calc_map.get(emp.id)
        if c:
            results.append(SalaryCalcOut(
                id=c.id, period=c.period, employee_id=c.employee_id,
                employee_no=emp.employee_no, employee_name=emp.name,
                contract_company=c.contract_company, department=c.department,
                position=c.position, status=c.status,
                entry_date=c.entry_date.isoformat() if c.entry_date else None,
                base_salary=c.base_salary,
                base_salary_prorated=c.base_salary_prorated,
                performance_standard_prorated=c.performance_standard_prorated,
                adjustment_id=c.adjustment_id,
                monthly_standard=c.monthly_standard,
                performance_standard=c.performance_standard,
                performance_coefficient=c.performance_coefficient,
                actual_performance=c.actual_performance,
                effective_performance=c.effective_performance,
                meal_allowance=c.meal_allowance, transport_allowance=c.transport_allowance,
                communication_allowance=c.communication_allowance,
                computer_allowance=c.computer_allowance,
                housing_allowance=c.housing_allowance,
                allowance_total=c.allowance_total,
                commission_bonus=c.commission_bonus,
                pretax_adjustment=c.pretax_adjustment,
                posttax_adjustment=c.posttax_adjustment,
                posttax_adjustment_reason=c.posttax_adjustment_reason,
                total_work_days=c.total_work_days,
                actual_work_days=c.actual_work_days,
                attendance_rate=c.attendance_rate,
                gross_salary=c.gross_salary,
                pension_personal=c.pension_personal,
                unemployment_personal=c.unemployment_personal,
                medical_personal=c.medical_personal,
                social_insurance_personal=c.social_insurance_personal,
                housing_fund_personal=c.housing_fund_personal,
                si_hf_total=c.si_hf_total,
                tax_deduction=c.tax_deduction,
                net_salary=c.net_salary,
                last_month_untaxed=c.last_month_untaxed,
                travel_untaxed=c.travel_untaxed,
                compensation_tax=c.compensation_tax,
                actual_taxable=c.actual_taxable,
                special_deduction=c.special_deduction,
                review_status=c.review_status or "",
                calculation_status=c.calculation_status or "",
                data_completeness=c.data_completeness or "",
            ))
        else:
            sal = salary_map.get(emp.id)
            perf = perf_map.get(emp.id)
            base_salary = float(sal.base_salary) if sal else None
            perf_std = float(sal.performance_standard) if sal else None
            meal = float(sal.meal_allowance or 0) if sal else None
            transport = float(sal.transport_allowance or 0) if sal else None
            comm = float(sal.communication_allowance or 0) if sal else None
            computer = float(sal.computer_allowance or 0) if sal else None
            housing = float(sal.housing_allowance or 0) if sal else None
            allowance_total = round((meal or 0) + (transport or 0) + (comm or 0) + (computer or 0) + (housing or 0), 2) if sal else None
            monthly_standard = round((base_salary or 0) + (perf_std or 0) + (allowance_total or 0), 2) if sal else None
            perf_coef = float(perf.coefficient) if perf else None
            actual_perf = round((perf_std or 0) * (perf_coef or 0), 2) if sal and perf else None

            results.append(SalaryCalcOut(
                period=period, employee_id=emp.id,
                employee_no=emp.employee_no, employee_name=emp.name,
                entry_date=emp.entry_date.isoformat() if emp.entry_date else None,
                base_salary=base_salary,
                monthly_standard=monthly_standard,
                performance_standard=perf_std,
                performance_coefficient=perf_coef,
                actual_performance=actual_perf,
                meal_allowance=meal,
                transport_allowance=transport,
                communication_allowance=comm,
                computer_allowance=computer,
                housing_allowance=housing,
                allowance_total=allowance_total,
            ))
    return results


@router.put("/results/{calc_id}", response_model=SalaryCalcOut)
def update_calculation_result(
    calc_id: int,
    data: SalaryCalcUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    calc = db.query(SalaryCalculation).filter(SalaryCalculation.id == calc_id).first()
    if not calc:
        raise HTTPException(status_code=404, detail="核算记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(calc, key, value)

    if "performance_coefficient" in update_data:
        calc.actual_performance = float(calc.performance_standard) * float(calc.performance_coefficient)

    # 使用折算后工资（如有月中调薪），否则用原始工资
    base = float(calc.base_salary_prorated or calc.base_salary)
    allowance = float(calc.allowance_total)
    actual_perf = float(calc.actual_performance)
    commission = float(calc.commission_bonus or 0)
    att_rate = float(calc.attendance_rate)

    calc.effective_performance = round(actual_perf * att_rate, 2)
    calc.monthly_standard = round(base + float(calc.performance_standard or 0) + allowance, 2)
    calc.gross_salary = round((base + allowance + commission) * att_rate + calc.effective_performance, 2)

    si_hf = float(calc.pension_personal or 0) + float(calc.unemployment_personal or 0) + float(calc.medical_personal or 0) + float(calc.housing_fund_personal or 0)
    calc.si_hf_total = si_hf
    tax = float(calc.tax_deduction or 0)
    posttax = float(calc.posttax_adjustment or 0)
    calc.net_salary = round(float(calc.gross_salary) - si_hf - tax + posttax, 2)

    calc.actual_taxable = round(
        float(calc.gross_salary) + float(calc.last_month_untaxed or 0) + float(calc.travel_untaxed or 0), 2
    )

    if calc.net_salary < 0:
        raise HTTPException(status_code=400, detail="实发工资不能为负数，请检查各项数据是否正确")
    if si_hf > float(calc.gross_salary):
        raise HTTPException(status_code=400, detail="社保公积金个人合计不能超过总应发工资，请检查社保公积金数据")
    if calc.actual_taxable < float(calc.gross_salary) and not calc.posttax_adjustment_reason:
        raise HTTPException(status_code=400, detail="本月实际报税金额小于总应发工资时，必须填写税后调整原因")

    db.commit()
    db.refresh(calc)
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "edit", f"编辑核算结果 (id={calc_id}, employee_id={calc.employee_id})")

    emp = db.query(Employee).filter(Employee.id == calc.employee_id).first()
    return SalaryCalcOut(
        id=calc.id, period=calc.period, employee_id=calc.employee_id,
        employee_no=emp.employee_no if emp else "", employee_name=emp.name if emp else "",
        contract_company=calc.contract_company, department=calc.department,
        position=calc.position, status=calc.status,
        entry_date=calc.entry_date.isoformat() if calc.entry_date else None,
        base_salary=calc.base_salary,
        base_salary_prorated=calc.base_salary_prorated,
        performance_standard_prorated=calc.performance_standard_prorated,
        adjustment_id=calc.adjustment_id,
        monthly_standard=calc.monthly_standard,
        performance_standard=calc.performance_standard,
        performance_coefficient=calc.performance_coefficient,
        actual_performance=calc.actual_performance,
        effective_performance=calc.effective_performance,
        meal_allowance=calc.meal_allowance, transport_allowance=calc.transport_allowance,
        communication_allowance=calc.communication_allowance,
        computer_allowance=calc.computer_allowance,
        housing_allowance=calc.housing_allowance,
        allowance_total=calc.allowance_total,
        commission_bonus=calc.commission_bonus,
        pretax_adjustment=calc.pretax_adjustment,
        posttax_adjustment=calc.posttax_adjustment,
        posttax_adjustment_reason=calc.posttax_adjustment_reason,
        total_work_days=calc.total_work_days,
        actual_work_days=calc.actual_work_days,
        attendance_rate=calc.attendance_rate,
        gross_salary=calc.gross_salary,
        pension_personal=calc.pension_personal,
        unemployment_personal=calc.unemployment_personal,
        medical_personal=calc.medical_personal,
        social_insurance_personal=calc.social_insurance_personal,
        housing_fund_personal=calc.housing_fund_personal,
        si_hf_total=calc.si_hf_total,
        tax_deduction=calc.tax_deduction,
        net_salary=calc.net_salary,
        last_month_untaxed=calc.last_month_untaxed,
        travel_untaxed=calc.travel_untaxed,
        compensation_tax=calc.compensation_tax,
        actual_taxable=calc.actual_taxable,
        special_deduction=calc.special_deduction,
        review_status=calc.review_status or "",
        calculation_status=calc.calculation_status or "",
        data_completeness=calc.data_completeness or "",
    )


@router.post("/calculate-net/{period}", response_model=CalculationSummary)
def calculate_net_salary(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == period).all()
    if not calcs:
        raise HTTPException(status_code=404, detail=f"周期 [{period}] 没有核算记录，请先进行应发工资核算")

    batch_no = f"CALC-NET-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    start_time = datetime.now()

    total_gross = 0
    total_net = 0
    for calc in calcs:
        base = float(calc.base_salary_prorated or calc.base_salary)
        allowance = float(calc.allowance_total)
        calc.monthly_standard = round(base + float(calc.performance_standard) + allowance, 2)
        calc.effective_performance = round(float(calc.actual_performance or 0) * float(calc.attendance_rate or 1), 2)

        si_hf = float(calc.pension_personal or 0) + float(calc.unemployment_personal or 0) + float(calc.medical_personal or 0) + float(calc.housing_fund_personal or 0)
        calc.si_hf_total = si_hf
        tax = float(calc.tax_deduction or 0)
        posttax = float(calc.posttax_adjustment or 0)
        calc.net_salary = round(float(calc.gross_salary) - si_hf - tax + posttax, 2)
        calc.actual_taxable = round(
            float(calc.gross_salary) + float(calc.last_month_untaxed or 0) + float(calc.travel_untaxed or 0), 2
        )
        calc.calculation_status = "实发已核算"
        total_gross += float(calc.gross_salary)
        total_net += float(calc.net_salary)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    log = CalculationLog(
        batch_no=batch_no,
        period=period,
        calculation_type="实发工资核算",
        status="成功",
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        total_employees=len(calcs),
        success_count=len(calcs),
        failed_count=0,
        operator_id=current_user.id
    )
    db.add(log)
    db.commit()
    write_log(db, "operation", current_user.id, current_user.username, "salary", "calculate", f"实发工资核算 (period={period}, batch={batch_no})")

    return CalculationSummary(
        period=period,
        total_employees=len(calcs),
        success_count=len(calcs),
        failed_count=0,
        total_gross_salary=round(total_gross, 2),
        avg_gross_salary=round(total_gross / len(calcs), 2) if calcs else 0,
        total_net_salary=round(total_net, 2),
        avg_net_salary=round(total_net / len(calcs), 2) if calcs else 0,
        batch_no=batch_no
    )


@router.get("/logs/{period}")
def get_calculation_logs(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    logs = db.query(CalculationLog).filter(CalculationLog.period == period).order_by(CalculationLog.start_time.desc()).all()
    return [
        {
            "batch_no": l.batch_no,
            "calculation_type": l.calculation_type,
            "status": l.status,
            "start_time": str(l.start_time),
            "end_time": str(l.end_time) if l.end_time else None,
            "duration_seconds": float(l.duration_seconds) if l.duration_seconds else 0,
            "total_employees": l.total_employees,
            "success_count": l.success_count,
            "failed_count": l.failed_count
        }
        for l in logs
    ]


@router.get("/export/{period}")
def export_salary_results(
    period: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == period).all()
    calc_map = {c.employee_id: c for c in calcs}
    employees = db.query(Employee).order_by(Employee.employee_no).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"薪酬核算_{period}"
    headers = [
        "员工编号", "员工姓名", "部门", "入职时间", "合同公司", "实发工资",
        "当月总计薪天数", "实际计薪天数", "出勤率",
        "基本工资", "提成/项目奖金/补发",
        "餐补", "交通补", "通讯补", "电脑补贴（非固定收入）", "住房补（非固定收入）", "补贴合计",
        "绩效奖金标准", "实发绩效奖金系数", "实发绩效奖金标准", "实发绩效奖金",
        "月薪标准", "总应发工资",
        "养老保险（个人）", "失业保险（个人）", "医疗保险（个人）", "公积金（个人）",
        "社保、公积金（个人）合计",
        "本月应扣个税额", "税后调整金额", "税后调整原因",
        "临时性差旅补贴未报税费用", "本月实际报税金额",
        "岗位", "用工状态", "上月未报税", "补偿金报税", "专项附加扣除", "核算状态", "审核状态"
    ]
    ws.append(headers)

    for emp in employees:
        c = calc_map.get(emp.id)
        if c:
            ws.append([
                emp.employee_no, emp.name,
                c.department, c.entry_date.isoformat() if c.entry_date else "", c.contract_company,
                float(c.net_salary or 0),
                float(c.total_work_days), float(c.actual_work_days),
                float(c.attendance_rate),
                float(c.base_salary),
                float(c.commission_bonus or 0),
                float(c.meal_allowance), float(c.transport_allowance),
                float(c.communication_allowance), float(c.computer_allowance),
                float(c.housing_allowance), float(c.allowance_total),
                float(c.performance_standard),
                float(c.performance_coefficient), float(c.actual_performance),
                float(c.effective_performance or 0),
                float(c.monthly_standard or 0),
                float(c.gross_salary),
                float(c.pension_personal or 0), float(c.unemployment_personal or 0),
                float(c.medical_personal or 0), float(c.housing_fund_personal or 0),
                float(c.si_hf_total or 0),
                float(c.tax_deduction or 0), float(c.posttax_adjustment or 0),
                c.posttax_adjustment_reason or "",
                float(c.travel_untaxed or 0), float(c.actual_taxable or 0),
                c.position, c.status,
                float(c.last_month_untaxed or 0), float(c.compensation_tax or 0),
                float(c.special_deduction or 0),
                c.calculation_status, c.review_status
            ])
        else:
            ws.append([
                emp.employee_no, emp.name,
                "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "",
                "", ""
            ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=salary_{period}.xlsx"}
    )


class TaxImportItem(BaseModel):
    employee_no: str
    last_month_untaxed: Optional[float] = 0
    travel_untaxed: Optional[float] = 0
    compensation_tax: Optional[float] = 0
    special_deduction: Optional[float] = 0


@router.post("/import-tax/{period}")
def import_tax_data(
    period: str,
    items: List[TaxImportItem],
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    updated = 0
    for item in items:
        emp = db.query(Employee).filter(Employee.employee_no == item.employee_no).first()
        if not emp:
            continue
        calc = db.query(SalaryCalculation).filter(
            SalaryCalculation.period == period,
            SalaryCalculation.employee_id == emp.id
        ).first()
        if not calc:
            continue
        if item.last_month_untaxed is not None:
            calc.last_month_untaxed = item.last_month_untaxed
        if item.travel_untaxed is not None:
            calc.travel_untaxed = item.travel_untaxed
        if item.compensation_tax is not None:
            calc.compensation_tax = item.compensation_tax
        if item.special_deduction is not None:
            calc.special_deduction = item.special_deduction
        updated += 1
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "import", f"导入报税数据 (period={period}, updated={updated})")
    return {"message": f"成功导入 {updated} 条报税数据", "updated": updated}


@router.post("/batch-delete")
def batch_delete_salary_calculations(ids: List[int], db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的核算记录ID列表")
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.id.in_(ids)).all()
    if not calcs:
        raise HTTPException(status_code=404, detail="未找到指定的核算记录")
    for c in calcs:
        db.delete(c)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "delete", f"批量删除 {len(calcs)} 条核算记录")
    return {"message": f"成功删除 {len(calcs)} 条核算记录", "deleted_count": len(calcs)}


# ============================================================
# 月中调薪（EmployeeSalaryAdjustment）API
# ============================================================

class SalaryAdjustmentIn(BaseModel):
    period: str
    employee_id: int
    base_salary_before: float
    bonus_before: float = 0
    performance_standard_before: float = 0
    base_salary_after: float
    bonus_after: float = 0
    performance_standard_after: float = 0
    month_start: date
    adjustment_date: date
    month_end: date
    total_days: float
    days_before: float = 0
    days_after: float = 0
    base_salary_ratio: float = 1.00
    adjustment_type: str = "转正调薪"


class SalaryAdjustmentOut(BaseModel):
    id: int
    period: str
    employee_id: int
    employee_name: str = ""
    base_salary_before: float
    bonus_before: float
    performance_standard_before: float
    total_before: float
    base_salary_after: float
    bonus_after: float
    performance_standard_after: float
    total_after: float
    base_salary_prorated: float
    commission_prorated: float
    performance_standard_prorated: float
    total_prorated: float
    month_start: str
    adjustment_date: str
    month_end: str
    days_before: float
    days_after: float
    total_days: float
    base_salary_ratio: float
    adjustment_type: str

    class Config:
        from_attributes = True


def _calc_prorated(adj: EmployeeSalaryAdjustment):
    """按 Excel 公式计算折算后工资"""
    total_days = float(adj.total_days)
    days_before = float(adj.days_before)
    days_after = float(adj.days_after)

    if total_days == 0:
        return

    base_before = float(adj.base_salary_before)
    base_after = float(adj.base_salary_after)
    perf_before = float(adj.performance_standard_before)
    perf_after = float(adj.performance_standard_after)

    # 折算后基本工资 = ROUND(调前天数 * 调前基本工资 / 总计薪天数 + 调后基本工资 * 调后天数 / 总计薪天数, 2)
    adj.base_salary_prorated = round(days_before * base_before / total_days + base_after * days_after / total_days, 2)
    # 折算后绩效奖金标准 = ROUND(调前天数 * 调前绩效标准 / 总计薪天数 + 调后绩效标准 * 调后天数 / 总计薪天数, 2)
    adj.performance_standard_prorated = round(days_before * perf_before / total_days + perf_after * days_after / total_days, 2)
    # 折算后工资标准合计 = ROUND(折算后基本工资 + 提成 + 折算后绩效标准, 0)
    adj.total_prorated = round(float(adj.base_salary_prorated) + float(adj.commission_prorated or 0) + float(adj.performance_standard_prorated), 0)

    # 调前/调后合计
    adj.total_before = round(base_before + float(adj.bonus_before or 0) + perf_before, 2)
    adj.total_after = round(base_after + float(adj.bonus_after or 0) + perf_after, 2)


@router.get("/adjustments/{period}", response_model=List[SalaryAdjustmentOut])
def get_adjustments(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """获取指定月份的月中调薪记录"""
    adjs = db.query(EmployeeSalaryAdjustment).filter(
        EmployeeSalaryAdjustment.period == period
    ).order_by(EmployeeSalaryAdjustment.id).all()

    emp_map = {e.id: e.name for e in db.query(Employee).all()}
    return [
        SalaryAdjustmentOut(
            id=a.id, period=a.period, employee_id=a.employee_id,
            employee_name=emp_map.get(a.employee_id, ""),
            base_salary_before=float(a.base_salary_before),
            bonus_before=float(a.bonus_before or 0),
            performance_standard_before=float(a.performance_standard_before),
            total_before=float(a.total_before),
            base_salary_after=float(a.base_salary_after),
            bonus_after=float(a.bonus_after or 0),
            performance_standard_after=float(a.performance_standard_after),
            total_after=float(a.total_after),
            base_salary_prorated=float(a.base_salary_prorated or 0),
            commission_prorated=float(a.commission_prorated or 0),
            performance_standard_prorated=float(a.performance_standard_prorated or 0),
            total_prorated=float(a.total_prorated or 0),
            month_start=a.month_start.isoformat(),
            adjustment_date=a.adjustment_date.isoformat(),
            month_end=a.month_end.isoformat(),
            days_before=float(a.days_before),
            days_after=float(a.days_after),
            total_days=float(a.total_days),
            base_salary_ratio=float(a.base_salary_ratio),
            adjustment_type=a.adjustment_type,
        ) for a in adjs
    ]


@router.post("/adjustments", response_model=SalaryAdjustmentOut)
def create_adjustment(data: SalaryAdjustmentIn, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """创建月中调薪记录（自动计算折算后工资）"""
    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    adj = EmployeeSalaryAdjustment(
        period=data.period,
        employee_id=data.employee_id,
        base_salary_before=data.base_salary_before,
        bonus_before=data.bonus_before,
        performance_standard_before=data.performance_standard_before,
        base_salary_after=data.base_salary_after,
        bonus_after=data.bonus_after,
        performance_standard_after=data.performance_standard_after,
        month_start=data.month_start,
        adjustment_date=data.adjustment_date,
        month_end=data.month_end,
        total_days=data.total_days,
        days_before=data.days_before,
        days_after=data.days_after,
        base_salary_ratio=data.base_salary_ratio,
        adjustment_type=data.adjustment_type,
    )
    _calc_prorated(adj)
    db.add(adj)
    db.commit()
    db.refresh(adj)
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "create", f"创建月中调薪记录 (period={data.period}, employee_id={data.employee_id})")

    return SalaryAdjustmentOut(
        id=adj.id, period=adj.period, employee_id=adj.employee_id,
        employee_name=emp.name,
        base_salary_before=float(adj.base_salary_before),
        bonus_before=float(adj.bonus_before or 0),
        performance_standard_before=float(adj.performance_standard_before),
        total_before=float(adj.total_before),
        base_salary_after=float(adj.base_salary_after),
        bonus_after=float(adj.bonus_after or 0),
        performance_standard_after=float(adj.performance_standard_after),
        total_after=float(adj.total_after),
        base_salary_prorated=float(adj.base_salary_prorated or 0),
        commission_prorated=float(adj.commission_prorated or 0),
        performance_standard_prorated=float(adj.performance_standard_prorated or 0),
        total_prorated=float(adj.total_prorated or 0),
        month_start=adj.month_start.isoformat(),
        adjustment_date=adj.adjustment_date.isoformat(),
        month_end=adj.month_end.isoformat(),
        days_before=float(adj.days_before),
        days_after=float(adj.days_after),
        total_days=float(adj.total_days),
        base_salary_ratio=float(adj.base_salary_ratio),
        adjustment_type=adj.adjustment_type,
    )


@router.put("/adjustments/{adj_id}", response_model=SalaryAdjustmentOut)
def update_adjustment(adj_id: int, data: SalaryAdjustmentIn, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """更新月中调薪记录（重新计算折算后工资）"""
    adj = db.query(EmployeeSalaryAdjustment).filter(EmployeeSalaryAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调薪记录不存在")

    adj.period = data.period
    adj.employee_id = data.employee_id
    adj.base_salary_before = data.base_salary_before
    adj.bonus_before = data.bonus_before
    adj.performance_standard_before = data.performance_standard_before
    adj.base_salary_after = data.base_salary_after
    adj.bonus_after = data.bonus_after
    adj.performance_standard_after = data.performance_standard_after
    adj.month_start = data.month_start
    adj.adjustment_date = data.adjustment_date
    adj.month_end = data.month_end
    adj.total_days = data.total_days
    adj.days_before = data.days_before
    adj.days_after = data.days_after
    adj.base_salary_ratio = data.base_salary_ratio
    adj.adjustment_type = data.adjustment_type
    _calc_prorated(adj)

    db.commit()
    db.refresh(adj)
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "edit", f"更新月中调薪记录 (id={adj_id})")

    emp = db.query(Employee).filter(Employee.id == adj.employee_id).first()
    return SalaryAdjustmentOut(
        id=adj.id, period=adj.period, employee_id=adj.employee_id,
        employee_name=emp.name if emp else "",
        base_salary_before=float(adj.base_salary_before),
        bonus_before=float(adj.bonus_before or 0),
        performance_standard_before=float(adj.performance_standard_before),
        total_before=float(adj.total_before),
        base_salary_after=float(adj.base_salary_after),
        bonus_after=float(adj.bonus_after or 0),
        performance_standard_after=float(adj.performance_standard_after),
        total_after=float(adj.total_after),
        base_salary_prorated=float(adj.base_salary_prorated or 0),
        commission_prorated=float(adj.commission_prorated or 0),
        performance_standard_prorated=float(adj.performance_standard_prorated or 0),
        total_prorated=float(adj.total_prorated or 0),
        month_start=adj.month_start.isoformat(),
        adjustment_date=adj.adjustment_date.isoformat(),
        month_end=adj.month_end.isoformat(),
        days_before=float(adj.days_before),
        days_after=float(adj.days_after),
        total_days=float(adj.total_days),
        base_salary_ratio=float(adj.base_salary_ratio),
        adjustment_type=adj.adjustment_type,
    )


@router.delete("/adjustments/{adj_id}")
def delete_adjustment(adj_id: int, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    """删除月中调薪记录"""
    adj = db.query(EmployeeSalaryAdjustment).filter(EmployeeSalaryAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调薪记录不存在")
    db.delete(adj)
    db.commit()
    write_log(db, "data_change", current_user.id, current_user.username, "salary", "delete", f"删除月中调薪记录 (id={adj_id})")
    return {"message": "调薪记录已删除"}