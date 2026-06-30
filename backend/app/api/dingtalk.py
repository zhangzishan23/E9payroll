"""
钉钉数据同步 API
- 花名册同步：将钉钉员工信息同步到系统 Employee 表
- 考勤同步：将钉钉考勤数据同步到系统 AttendanceRecord 表
- 同步日志：查询同步历史记录
"""
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from openpyxl import Workbook

from app.core.database import get_db
from app.core.log_helper import write_log
from app.api.auth import get_current_user, UserInfo
from app.services.dingtalk_service import (
    sync_roster_to_db,
    sync_attendance_to_db,
    get_all_user_ids,
    get_attendance_columns,
    get_sync_logs,
    cleanup_old_daily_records,
    _get_access_token,
    get_root_departments,
    sync_root_depts_to_db,
    get_raw_attendance_by_employee,
    ATTENDANCE_COLUMN_MAP,
)

router = APIRouter()


class SyncResult(BaseModel):
    success: bool
    message: str
    created: int = 0
    updated: int = 0
    synced: int = 0
    errors: list[str] = []


class SyncLogItem(BaseModel):
    id: int
    sync_type: str
    status: str
    period: Optional[str] = None
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    error_detail: Optional[list] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


@router.post("/sync/roster", response_model=SyncResult)
def api_sync_roster(
    mode: str = Query("full", description="同步模式：full 全量 / incremental 增量"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """从钉钉同步花名册到系统员工档案"""
    try:
        stats = sync_roster_to_db(db, mode=mode)
        write_log(
            db, "sync", current_user.id, current_user.username,
            "dingtalk", "sync_roster",
            f"花名册同步完成({mode})：新增{stats['created']}，更新{stats['updated']}"
        )
        return SyncResult(
            success=len(stats["errors"]) == 0,
            message=f"花名册同步完成({mode})：新增 {stats['created']} 人，更新 {stats['updated']} 人",
            created=stats["created"],
            updated=stats["updated"],
            errors=stats["errors"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/sync/attendance", response_model=SyncResult)
def api_sync_attendance(
    period: str = Query(..., description="考勤月份，格式 YYYYMM，如 202406"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """从钉钉同步指定月份的考勤数据（月度汇总）"""
    try:
        stats = sync_attendance_to_db(db, period)
        write_log(
            db, "sync", current_user.id, current_user.username,
            "dingtalk", "sync_attendance",
            f"考勤同步完成({period})：同步{stats['synced']}人"
        )
        return SyncResult(
            success=len(stats["errors"]) == 0,
            message=f"考勤同步完成({period})：同步 {stats['synced']} 人",
            synced=stats["synced"],
            errors=stats["errors"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/sync/logs", response_model=list[SyncLogItem])
def api_sync_logs(
    sync_type: Optional[str] = Query(None, description="同步类型筛选"),
    limit: int = Query(20, description="返回条数"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """查询同步日志"""
    logs = get_sync_logs(db, sync_type=sync_type, limit=limit)
    return [
        SyncLogItem(
            id=log.id,
            sync_type=log.sync_type,
            status=log.status,
            period=log.period,
            total_count=log.total_count,
            success_count=log.success_count,
            failed_count=log.failed_count,
            created_count=log.created_count,
            updated_count=log.updated_count,
            error_detail=log.error_detail,
            started_at=log.started_at.isoformat() if log.started_at else None,
            finished_at=log.finished_at.isoformat() if log.finished_at else None,
            duration_seconds=float(log.duration_seconds) if log.duration_seconds else None,
        )
        for log in logs
    ]


@router.post("/sync/cleanup-daily")
def api_cleanup_daily(
    keep_days: int = Query(60, description="保留天数，默认60天"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """清理过期的每日考勤记录"""
    try:
        count = cleanup_old_daily_records(db, keep_days=keep_days)
        write_log(
            db, "sync", current_user.id, current_user.username,
            "dingtalk", "cleanup_daily",
            f"清理了 {count} 条超过 {keep_days} 天的每日考勤记录"
        )
        return {"success": True, "message": f"清理了 {count} 条记录", "deleted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/status")
def api_dingtalk_status(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """检查钉钉连接状态与所需权限"""
    result = {
        "configured": False,
        "token_ok": False,
        "user_count": 0,
        "attendance_columns": 0,
        "roster_ok": False,
        "warnings": [],
    }
    try:
        token = _get_access_token()
        result["configured"] = True
        result["token_ok"] = True
    except Exception as e:
        result["error"] = f"获取access_token失败: {str(e)}"
        return result

    # 检查通讯录权限
    try:
        user_ids = get_all_user_ids(db)
        result["user_count"] = len(user_ids)
    except Exception as e:
        result["warnings"].append(f"获取员工列表失败（需开通「通讯录管理-成员信息读权限」）: {str(e)}")

    # 检查考勤权限
    try:
        columns = get_attendance_columns()
        result["attendance_columns"] = len(columns)
    except Exception as e:
        result["warnings"].append(f"获取考勤列定义失败: {str(e)}")

    return result


@router.post("/sync/root-depts")
def api_sync_root_depts(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """从钉钉获取一级部门，同步到数据字典"""
    try:
        stats = sync_root_depts_to_db(db)
        write_log(
            db, "sync", current_user.id, current_user.username,
            "dingtalk", "sync_root_depts",
            f"同步根部门：新增{stats['created']}，跳过{stats['skipped']}"
        )
        return {"success": True, "message": f"同步完成：新增 {stats['created']} 个部门，跳过 {stats['skipped']} 个", **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/raw-attendance/columns")
def api_raw_attendance_columns(
    current_user: UserInfo = Depends(get_current_user),
):
    """查看钉钉考勤报表所有原始列定义（不做映射筛选）"""
    try:
        columns = get_attendance_columns()
        return {
            "success": True,
            "total": len(columns),
            "columns": columns,
            "mapped_columns": list(ATTENDANCE_COLUMN_MAP.keys()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取考勤列定义失败: {str(e)}")


@router.get("/raw-attendance/export")
def api_raw_attendance_export(
    period: str = Query(..., description="考勤月份，格式 YYYYMM，如 202406"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """导出钉钉原始考勤数据（所有列，不做映射筛选）为 Excel"""
    raw = get_raw_attendance_by_employee(db, period)
    columns = raw["columns"]
    employees = raw["employees"]

    # 收集所有原始列名（按钉钉返回顺序）
    all_col_names = [c["name"] for c in columns]

    wb = Workbook()
    ws = wb.active
    ws.title = "钉钉原始考勤数据"

    # 表头
    headers = ["员工编号", "员工姓名", "钉钉UserId"] + all_col_names + ["出错信息"]
    ws.append(headers)

    # 数据行
    for emp in employees:
        row = [
            emp.get("employee_no", ""),
            emp.get("employee_name", ""),
            emp.get("dingtalk_user_id", ""),
        ]
        values = emp.get("values", {})
        for col_name in all_col_names:
            row.append(values.get(col_name, ""))
        row.append(emp.get("error", ""))
        ws.append(row)

    # 标注哪些列是系统已映射的
    ws2 = wb.create_sheet("列映射说明")
    ws2.append(["钉钉原始列名", "是否被系统映射", "映射系统字段"])
    for col in columns:
        cn = col["name"]
        mapped_field = ATTENDANCE_COLUMN_MAP.get(cn, "")
        ws2.append([cn, "是" if mapped_field else "否", mapped_field])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=dingtalk_raw_attendance_{period}.xlsx"},
    )