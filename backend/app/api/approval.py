from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.models.models import SalaryCalculation, ApprovalRecord, SysUser
from app.api.auth import get_current_user, UserInfo

router = APIRouter()


class ApprovalSubmit(BaseModel):
    period: str


class ApprovalAction(BaseModel):
    approval_no: str
    approval_level: str
    action: str
    opinion: Optional[str] = None


class ApprovalRecordOut(BaseModel):
    id: int
    approval_no: str
    period: str
    submitter_id: int
    submitter_name: str
    submit_time: Optional[str] = None
    approval_level: str
    approver_id: int
    approver_name: str
    action: str
    opinion: Optional[str] = None
    approval_time: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalStatusOut(BaseModel):
    period: str
    approval_no: Optional[str] = None
    status: str
    progress: str
    submitter_name: Optional[str] = None
    submit_time: Optional[str] = None
    employee_count: int = 0
    total_gross: float = 0.0
    records: List[ApprovalRecordOut] = []


def generate_approval_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"AP-{today}-"
    last = db.query(func.max(ApprovalRecord.approval_no)).filter(
        ApprovalRecord.approval_no.like(f"{prefix}%")
    ).scalar()
    if last:
        seq = int(last.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


@router.post("/submit", response_model=dict)
def submit_approval(data: ApprovalSubmit, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == data.period).all()
    if not calcs:
        raise HTTPException(status_code=404, detail=f"周期 [{data.period}] 没有核算记录")

    pending = db.query(ApprovalRecord).filter(
        ApprovalRecord.period == data.period,
        ApprovalRecord.action == "通过"
    ).all()

    current_level = "待主管审核"
    for r in pending:
        if r.approval_level == "主管审核":
            current_level = "主管已通过，待经理审核"
            break

    if current_level != "待主管审核":
        has_pending = db.query(ApprovalRecord).filter(
            ApprovalRecord.period == data.period,
            ApprovalRecord.approval_level == "经理审核",
            ApprovalRecord.action.is_(None)
        ).first()
        if has_pending:
            raise HTTPException(status_code=400, detail="该周期已有进行中的审批流程，请等待经理审核完成")

    approval_no = generate_approval_no(db)
    now = datetime.now()

    employee_count = len(calcs)
    total_gross = sum(float(c.gross_salary or 0) for c in calcs)

    db.query(SalaryCalculation).filter(SalaryCalculation.period == data.period).update(
        {"review_status": "审核中"}
    )

    record = ApprovalRecord(
        approval_no=approval_no,
        period=data.period,
        submitter_id=current_user.id,
        submitter_name=current_user.display_name,
        submit_time=now,
        approval_level="主管审核",
        approver_id=current_user.id,
        approver_name=current_user.display_name,
        action="提交",
        opinion=None,
        approval_time=now
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "approval_no": approval_no,
        "period": data.period,
        "submitter_name": current_user.display_name,
        "submit_time": str(now),
        "employee_count": employee_count,
        "total_gross": round(total_gross, 2),
        "progress": "待主管审核"
    }


@router.post("/action", response_model=ApprovalRecordOut)
def do_approval_action(data: ApprovalAction, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    record = db.query(ApprovalRecord).filter(
        ApprovalRecord.approval_no == data.approval_no,
        ApprovalRecord.approval_level == data.approval_level,
        ApprovalRecord.action == "提交"
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="未找到对应的审批记录")

    if data.action == "驳回" and not data.opinion:
        raise HTTPException(status_code=400, detail="驳回时必须填写审核意见")

    now = datetime.now()

    approval_record = ApprovalRecord(
        approval_no=data.approval_no,
        period=record.period,
        submitter_id=record.submitter_id,
        submitter_name=record.submitter_name,
        submit_time=record.submit_time,
        approval_level=data.approval_level,
        approver_id=current_user.id,
        approver_name=current_user.display_name,
        action=data.action,
        opinion=data.opinion,
        approval_time=now
    )
    db.add(approval_record)

    if data.action == "通过":
        if data.approval_level == "主管审核":
            db.query(SalaryCalculation).filter(SalaryCalculation.period == record.period).update(
                {"review_status": "主管已审"}
            )
        elif data.approval_level == "经理审核":
            db.query(SalaryCalculation).filter(SalaryCalculation.period == record.period).update(
                {"review_status": "经理已审"}
            )
    elif data.action == "驳回":
        db.query(SalaryCalculation).filter(SalaryCalculation.period == record.period).update(
            {"review_status": "已驳回"}
        )

    db.commit()
    db.refresh(approval_record)
    return approval_record


@router.get("/status/{period}", response_model=ApprovalStatusOut)
def get_approval_status(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    calcs = db.query(SalaryCalculation).filter(SalaryCalculation.period == period).all()
    if not calcs:
        return ApprovalStatusOut(period=period, status="未核算", progress="未提交")

    records = db.query(ApprovalRecord).filter(
        ApprovalRecord.period == period
    ).order_by(ApprovalRecord.created_at).all()

    if not records:
        return ApprovalStatusOut(
            period=period,
            status="待提交",
            progress="未提交",
            employee_count=len(calcs),
            total_gross=round(sum(float(c.gross_salary or 0) for c in calcs), 2)
        )

    submit_record = records[0]
    approval_no = submit_record.approval_no

    progress = "待主管审核"
    status = "审核中"
    for r in records:
        if r.approval_level == "主管审核" and r.action == "通过":
            progress = "主管已通过，待经理审核"
        elif r.approval_level == "主管审核" and r.action == "驳回":
            progress = "主管已驳回"
            status = "已驳回"
            break
        elif r.approval_level == "经理审核" and r.action == "通过":
            progress = "经理已通过"
            status = "已通过"
        elif r.approval_level == "经理审核" and r.action == "驳回":
            progress = "经理已驳回"
            status = "已驳回"
            break

    employee_count = len(calcs)
    total_gross = round(sum(float(c.gross_salary or 0) for c in calcs), 2)

    return ApprovalStatusOut(
        period=period,
        approval_no=approval_no,
        status=status,
        progress=progress,
        submitter_name=submit_record.submitter_name,
        submit_time=str(submit_record.submit_time),
        employee_count=employee_count,
        total_gross=total_gross,
        records=[
            ApprovalRecordOut(
                id=r.id,
                approval_no=r.approval_no,
                period=r.period,
                submitter_id=r.submitter_id,
                submitter_name=r.submitter_name,
                submit_time=str(r.submit_time),
                approval_level=r.approval_level,
                approver_id=r.approver_id,
                approver_name=r.approver_name,
                action=r.action,
                opinion=r.opinion,
                approval_time=str(r.approval_time),
                created_at=str(r.created_at)
            )
            for r in records
        ]
    )


@router.get("/records/{period}", response_model=List[ApprovalRecordOut])
def get_approval_records(period: str, db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)):
    records = db.query(ApprovalRecord).filter(
        ApprovalRecord.period == period
    ).order_by(ApprovalRecord.created_at.desc()).all()
    return [
        ApprovalRecordOut(
            id=r.id,
            approval_no=r.approval_no,
            period=r.period,
            submitter_id=r.submitter_id,
            submitter_name=r.submitter_name,
            submit_time=str(r.submit_time),
            approval_level=r.approval_level,
            approver_id=r.approver_id,
            approver_name=r.approver_name,
            action=r.action,
            opinion=r.opinion,
            approval_time=str(r.approval_time),
            created_at=str(r.created_at)
        )
        for r in records
    ]
