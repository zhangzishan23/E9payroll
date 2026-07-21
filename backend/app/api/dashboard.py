from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.core.database import get_db
from app.core.log_helper import write_log
from app.core.query_utils import filter_active_employees, get_pending_resign_status_id
from app.models.models import (
    SysUser, SysSchedule, SysUserFavorite, SysUserPreference,
    Employee, SalaryCalculation, PerformanceScore, SocialInsurance,
    AttendanceRecord, SysDictBase, SalaryPeriodStep
)
from app.api.auth import get_current_user, UserInfo, require_permission
from sqlalchemy import func, and_

router = APIRouter()


class FavoriteCreate(BaseModel):
    module_key: str
    name: str
    route: str
    icon: Optional[str] = None
    color: Optional[str] = None


class FavoriteUpdate(BaseModel):
    sort_order: Optional[int] = None


class PreferenceUpdate(BaseModel):
    dashboard_view: Optional[str] = None
    extra: Optional[dict] = None


class ScheduleCreate(BaseModel):
    name: str
    day_of_month: int
    step_key: Optional[str] = None
    route: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = "blue"
    description: Optional[str] = None
    is_warning: Optional[bool] = False
    warning_days: Optional[int] = 3
    sort_order: Optional[int] = 0
    is_enabled: Optional[bool] = True


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    day_of_month: Optional[int] = None
    step_key: Optional[str] = None
    route: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    is_warning: Optional[bool] = None
    warning_days: Optional[int] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None


def _get_user_role_type(user: SysUser, db: Session) -> str:
    """判断用户角色类型: leader/employee"""
    from app.models.models import SysUserRole, SysRole
    roles = db.query(SysRole).join(SysUserRole).filter(
        SysUserRole.user_id == user.id
    ).all()
    role_names = [r.name for r in roles]
    if "超级管理员" in role_names or "人事主管" in role_names:
        return "leader"
    return "employee"


def _get_active_employees(db: Session):
    """获取活跃员工列表（排除待离职）"""
    query = db.query(Employee)
    query = filter_active_employees(query, db)
    pending_resign_ids = get_pending_resign_status_id(db)
    if pending_resign_ids:
        query = query.filter(Employee.status_id.notin_(pending_resign_ids))
    return query.all()


def _get_root_dept_id(dept_id: int, db: Session) -> int:
    """获取部门的根部门ID（向上追溯到parent_id为None的部门）"""
    if dept_id is None:
        return None
    current_id = dept_id
    visited = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        dept = db.query(SysDictBase).filter(SysDictBase.id == current_id).first()
        if dept is None:
            return current_id
        if dept.parent_id is None:
            return current_id
        current_id = dept.parent_id
    return current_id


@router.get("/overview", dependencies=[Depends(require_permission("dashboard:view"))])
def get_dashboard_overview(
    period: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取工作台概览数据"""
    user = db.query(SysUser).filter(SysUser.id == current_user.id).first()
    role_type = _get_user_role_type(user, db)
    can_access_leader = current_user.has_permission("dashboard:leader_view")
    can_access_work = current_user.has_permission("dashboard:work_view")
    can_switch_view = can_access_leader and can_access_work

    if current_user.is_admin:
        can_access_leader = True
        can_access_work = True
        can_switch_view = True

    pref = db.query(SysUserPreference).filter(SysUserPreference.user_id == user.id).first()
    if not pref:
        pref = SysUserPreference(user_id=user.id, dashboard_view="auto", extra={})
        db.add(pref)
        db.commit()
        db.refresh(pref)
    view_mode = pref.dashboard_view if pref else "auto"
    if view_mode == "auto":
        if can_access_work:
            view_mode = "employee"
        elif can_access_leader:
            view_mode = "leader"
        else:
            view_mode = "employee"
    if view_mode == "leader" and not can_access_leader:
        view_mode = "employee"
        pref.dashboard_view = "employee"
        db.commit()
    if view_mode == "employee" and not can_access_work:
        view_mode = "leader"
        pref.dashboard_view = "leader"
        db.commit()
    if not pref.extra:
        pref.extra = {}

    today = date.today()
    current_day = today.day
    if not period:
        period = today.strftime("%Y%m")

    schedules = db.query(SysSchedule).filter(SysSchedule.is_enabled == True).order_by(SysSchedule.sort_order).all()
    step_records = {}
    period_steps = db.query(SalaryPeriodStep).filter(SalaryPeriodStep.period == period).all()
    for ps in period_steps:
        step_records[ps.step_key] = ps

    todos = []
    warnings = []
    for sched in schedules:
        target_day = sched.day_of_month
        days_until = target_day - current_day
        is_completed = False
        if sched.step_key and sched.step_key in step_records:
            is_completed = step_records[sched.step_key].is_confirmed

        status = "completed" if is_completed else ("upcoming" if days_until > 0 else ("today" if days_until == 0 else "overdue"))
        
        todo_item = {
            "id": sched.id,
            "name": sched.name,
            "day_of_month": sched.day_of_month,
            "route": sched.route,
            "icon": sched.icon,
            "color": sched.color,
            "description": sched.description,
            "days_until": days_until,
            "status": status,
            "is_warning": False,
            "step_key": sched.step_key,
            "is_completed": is_completed
        }

        if not is_completed:
            todos.append(todo_item)

    active_employees = _get_active_employees(db)
    from datetime import timedelta

    warning_30d = today + timedelta(days=30)

    def _add_months(dt, months):
        """简单的月份加法，不依赖dateutil"""
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        import calendar
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    # 1. 合同到期预警
    expiring_emps = []
    for emp in active_employees:
        if emp.contract_end_date and emp.contract_end_date <= warning_30d:
            expiring_emps.append(emp)
    contract_warning = len(expiring_emps)
    if expiring_emps:
        expired_count = len([e for e in expiring_emps if e.contract_end_date < today])
        warnings.append({
            "id": -1,
            "name": "合同到期预警",
            "description": f"{len(expiring_emps)}人合同即将到期，{expired_count}人已过期",
            "route": "/employees",
            "icon": "Warning",
            "color": "red"
        })

    # 2. 生日提醒（本月过生日）
    birthday_emps = []
    for emp in active_employees:
        if emp.birth_date and emp.birth_date.month == today.month:
            birthday_emps.append(emp)
    if birthday_emps:
        warnings.append({
            "id": -2,
            "name": "员工生日提醒",
            "description": f"本月有{len(birthday_emps)}名员工过生日",
            "route": "/employees",
            "icon": "Calendar",
            "color": "pink"
        })

    # 3. 转正提醒（入职3个月内即将转正，或试用期已过未转正）
    probation_emps = []
    for emp in active_employees:
        if emp.entry_date:
            should_regular_date = _add_months(emp.entry_date, 3)
            if today <= should_regular_date <= warning_30d:
                probation_emps.append(emp)
            elif should_regular_date < today and not emp.regular_date:
                probation_emps.append(emp)
    if probation_emps:
        overdue_count = len([e for e in probation_emps if _add_months(e.entry_date, 3) < today and not e.regular_date])
        desc = f"{len(probation_emps)}人试用期即将到期"
        if overdue_count > 0:
            desc += f"，{overdue_count}人已逾期未转正"
        warnings.append({
            "id": -3,
            "name": "转正提醒",
            "description": desc,
            "route": "/employees",
            "icon": "User",
            "color": "orange"
        })

    # 4. 离职预警（已有离职日期，30天内即将离职）
    resign_emps = []
    for emp in active_employees:
        if emp.resign_date and emp.resign_date <= warning_30d and emp.resign_date >= today:
            resign_emps.append(emp)
    if resign_emps:
        warnings.append({
            "id": -4,
            "name": "离职预警",
            "description": f"{len(resign_emps)}人即将在30天内离职",
            "route": "/employees",
            "icon": "UserFilled",
            "color": "gray"
        })

    favorites = db.query(SysUserFavorite).filter(
        SysUserFavorite.user_id == user.id
    ).order_by(SysUserFavorite.sort_order, SysUserFavorite.click_count.desc()).all()

    favorites_initialized = pref.extra.get("favorites_initialized", False)
    if not favorites_initialized and len(favorites) > 0:
        pref.extra["favorites_initialized"] = True
        favorites_initialized = True
        db.commit()

    if len(favorites) == 0 and not favorites_initialized:
        default_favs = [
            {"module_key": "salary", "name": "薪资计算", "route": "/salary", "icon": "Money", "color": "blue"},
            {"module_key": "attendance", "name": "考勤管理", "route": "/attendance", "icon": "Calendar", "color": "green"},
            {"module_key": "insurance", "name": "社保公积金", "route": "/insurance", "icon": "CreditCard", "color": "orange"},
            {"module_key": "performance", "name": "绩效评分", "route": "/performance", "icon": "TrendCharts", "color": "purple"},
        ]
        for i, f in enumerate(default_favs):
            fav = SysUserFavorite(
                user_id=user.id,
                sort_order=i,
                click_count=0,
                is_auto=True,
                **f
            )
            db.add(fav)
            favorites.append(fav)
        pref.extra["favorites_initialized"] = True
        db.commit()

    return {
        "view_mode": view_mode,
        "role_type": role_type,
        "can_access_leader_view": can_access_leader,
        "can_access_work_view": can_access_work,
        "can_switch_view": can_switch_view,
        "period": period,
        "today": today.strftime("%Y-%m-%d"),
        "todos": todos,
        "warnings": warnings,
        "favorites": [
            {
                "id": f.id,
                "module_key": f.module_key,
                "name": f.name,
                "route": f.route,
                "icon": f.icon,
                "color": f.color,
                "click_count": f.click_count
            } for f in favorites
        ],
        "contract_warning": contract_warning
    }


@router.get("/charts", dependencies=[Depends(require_permission("dashboard:leader_view"))])
def get_dashboard_charts(
    period: Optional[str] = None,
    months: int = 6,
    dept_id: Optional[int] = None,
    employee_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取数据看板图表数据"""
    today = date.today()
    if not period:
        period = today.strftime("%Y%m")

    def _get_periods(n):
        periods = []
        y, m = int(period[:4]), int(period[4:])
        for i in range(n):
            periods.append(f"{y:04d}{m:02d}")
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        return list(reversed(periods))

    periods = _get_periods(months)

    root_depts = db.query(SysDictBase).filter(
        SysDictBase.category == "department",
        SysDictBase.parent_id.is_(None),
        SysDictBase.is_enabled == True
    ).all()
    root_dept_ids = {d.id for d in root_depts}

    def _get_all_sub_dept_ids(parent_dept_id: int) -> set:
        """递归获取部门及其所有子部门ID"""
        result = {parent_dept_id}
        children = db.query(SysDictBase).filter(
            SysDictBase.category == "department",
            SysDictBase.parent_id == parent_dept_id,
            SysDictBase.is_enabled == True
        ).all()
        for child in children:
            result.update(_get_all_sub_dept_ids(child.id))
        return result

    active_employees = _get_active_employees(db)

    emp_root_dept_map = {}
    for emp in active_employees:
        emp_root_dept_map[emp.id] = _get_root_dept_id(emp.department_id, db)

    if dept_id:
        target_dept_ids = _get_all_sub_dept_ids(dept_id)
        active_employees = [e for e in active_employees if e.department_id in target_dept_ids or emp_root_dept_map.get(e.id) in target_dept_ids]
    
    if employee_name:
        keyword = employee_name.strip()
        active_employees = [e for e in active_employees if keyword in (e.name or "")]
    
    active_employee_ids = [e.id for e in active_employees]
    
    dept_costs = []
    if not dept_id:
        for dept in root_depts:
            emp_ids = [e.id for e in active_employees if emp_root_dept_map.get(e.id) == dept.id]
            if not emp_ids:
                continue
            total_gross = db.query(func.coalesce(func.sum(SalaryCalculation.gross_salary), 0)).filter(
                SalaryCalculation.period == period,
                SalaryCalculation.employee_id.in_(emp_ids),
                SalaryCalculation.record_type.in_(["single", "contract", "payroll"])
            ).scalar() or 0
            if float(total_gross) > 0:
                dept_costs.append({
                    "name": dept.name,
                    "value": float(total_gross)
                })
    else:
        selected_dept = db.query(SysDictBase).filter(SysDictBase.id == dept_id).first()
        if selected_dept and active_employee_ids:
            total_gross = db.query(func.coalesce(func.sum(SalaryCalculation.gross_salary), 0)).filter(
                SalaryCalculation.period == period,
                SalaryCalculation.employee_id.in_(active_employee_ids),
                SalaryCalculation.record_type.in_(["single", "contract", "payroll"])
            ).scalar() or 0
            dept_costs.append({
                "name": selected_dept.name,
                "value": float(total_gross)
            })

    monthly_costs = []
    for p in periods:
        query = db.query(func.coalesce(func.sum(SalaryCalculation.gross_salary), 0)).filter(
            SalaryCalculation.period == p,
            SalaryCalculation.record_type.in_(["single", "contract", "payroll"])
        )
        if active_employee_ids:
            query = query.filter(SalaryCalculation.employee_id.in_(active_employee_ids))
        total = query.scalar() or 0
        monthly_costs.append({
            "period": p,
            "label": f"{p[:4]}-{p[4:6]}",
            "value": float(total)
        })

    dept_perf = []
    if not dept_id:
        for dept in root_depts:
            emp_ids = [e.id for e in active_employees if emp_root_dept_map.get(e.id) == dept.id]
            if not emp_ids:
                continue
            scores = db.query(PerformanceScore.final_score).filter(
                PerformanceScore.period == period,
                PerformanceScore.employee_id.in_(emp_ids),
                PerformanceScore.final_score.isnot(None)
            ).all()
            if scores:
                avg_score = sum(float(s[0]) for s in scores) / len(scores)
                dept_perf.append({
                    "name": dept.name,
                    "value": round(avg_score, 2)
                })
    else:
        selected_dept = db.query(SysDictBase).filter(SysDictBase.id == dept_id).first()
        if selected_dept and active_employee_ids:
            scores = db.query(PerformanceScore.final_score).filter(
                PerformanceScore.period == period,
                PerformanceScore.employee_id.in_(active_employee_ids),
                PerformanceScore.final_score.isnot(None)
            ).all()
            if scores:
                avg_score = sum(float(s[0]) for s in scores) / len(scores)
                dept_perf.append({
                    "name": selected_dept.name,
                    "value": round(avg_score, 2)
                })

    perf_trend = []
    for p in periods:
        query = db.query(PerformanceScore.final_score).filter(
            PerformanceScore.period == p,
            PerformanceScore.final_score.isnot(None)
        )
        if active_employee_ids:
            query = query.filter(PerformanceScore.employee_id.in_(active_employee_ids))
        scores = query.all()
        avg = sum(float(s[0]) for s in scores) / len(scores) if scores else None
        perf_trend.append({
            "period": p,
            "label": f"{p[:4]}-{p[4:6]}",
            "value": round(avg, 2) if avg is not None else None
        })

    total_employees = len(active_employees)
    total_cost = sum(d["value"] for d in dept_costs)
    avg_cost = total_cost / total_employees if total_employees > 0 else 0

    atts_query = db.query(AttendanceRecord.attendance_rate).filter(
        AttendanceRecord.period == period,
        AttendanceRecord.attendance_rate.isnot(None)
    )
    if active_employee_ids:
        atts_query = atts_query.filter(AttendanceRecord.employee_id.in_(active_employee_ids))
    atts = atts_query.all()
    avg_attend = sum(float(a[0]) for a in atts) / len(atts) * 100 if atts else 0

    departments = [{"id": 0, "name": "全部部门"}]
    for d in root_depts:
        departments.append({"id": d.id, "name": d.name})

    return {
        "summary": {
            "total_employees": total_employees,
            "total_cost": round(total_cost, 2),
            "avg_cost": round(avg_cost, 2),
            "avg_attend_rate": round(avg_attend, 1)
        },
        "charts": {
            "dept_costs": dept_costs,
            "monthly_costs": monthly_costs,
            "dept_perf": dept_perf,
            "perf_trend": perf_trend
        },
        "departments": departments
    }


@router.get("/favorites", dependencies=[Depends(require_permission("dashboard:view"))])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取用户常用功能"""
    favorites = db.query(SysUserFavorite).filter(
        SysUserFavorite.user_id == current_user.id
    ).order_by(SysUserFavorite.sort_order, SysUserFavorite.click_count.desc()).all()
    return [
        {
            "id": f.id,
            "module_key": f.module_key,
            "name": f.name,
            "route": f.route,
            "icon": f.icon,
            "color": f.color,
            "click_count": f.click_count,
            "is_auto": f.is_auto
        } for f in favorites
    ]


@router.post("/favorites", dependencies=[Depends(require_permission("dashboard:view"))])
def add_favorite(
    data: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """添加常用功能"""
    existing = db.query(SysUserFavorite).filter(
        SysUserFavorite.user_id == current_user.id,
        SysUserFavorite.route == data.route
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该功能已在常用列表中")

    max_order = db.query(func.max(SysUserFavorite.sort_order)).filter(
        SysUserFavorite.user_id == current_user.id
    ).scalar() or 0

    fav = SysUserFavorite(
        user_id=current_user.id,
        module_key=data.module_key,
        name=data.name,
        route=data.route,
        icon=data.icon,
        color=data.color or "blue",
        sort_order=max_order + 1,
        click_count=0,
        is_auto=False
    )
    db.add(fav)

    pref = db.query(SysUserPreference).filter(SysUserPreference.user_id == current_user.id).first()
    if not pref:
        pref = SysUserPreference(user_id=current_user.id, dashboard_view="auto", extra={})
        db.add(pref)
    if not pref.extra:
        pref.extra = {}
    if not pref.extra.get("favorites_initialized"):
        pref.extra["favorites_initialized"] = True

    db.commit()
    db.refresh(fav)
    write_log(db, "operation", current_user.id, current_user.username, "dashboard", "favorite_add", data.route, {"name": data.name})
    return {"id": fav.id, "message": "添加成功"}


@router.delete("/favorites/{fav_id}", dependencies=[Depends(require_permission("dashboard:view"))])
def delete_favorite(
    fav_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """删除常用功能"""
    fav = db.query(SysUserFavorite).filter(
        SysUserFavorite.id == fav_id,
        SysUserFavorite.user_id == current_user.id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="常用功能不存在")
    db.delete(fav)
    db.commit()
    write_log(db, "operation", current_user.id, current_user.username, "dashboard", "favorite_remove", str(fav_id), {"name": fav.name})
    return {"message": "删除成功"}


@router.post("/favorites/{fav_id}/click", dependencies=[Depends(require_permission("dashboard:view"))])
def record_favorite_click(
    fav_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """记录常用功能点击（用于自动推荐）"""
    fav = db.query(SysUserFavorite).filter(
        SysUserFavorite.id == fav_id,
        SysUserFavorite.user_id == current_user.id
    ).first()
    if fav:
        fav.click_count = (fav.click_count or 0) + 1
        db.commit()
    return {"ok": True}


@router.get("/preferences", dependencies=[Depends(require_permission("dashboard:view"))])
def get_preferences(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取用户偏好"""
    pref = db.query(SysUserPreference).filter(
        SysUserPreference.user_id == current_user.id
    ).first()
    if not pref:
        pref = SysUserPreference(user_id=current_user.id, dashboard_view="auto")
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return {
        "dashboard_view": pref.dashboard_view,
        "extra": pref.extra or {}
    }


@router.put("/preferences", dependencies=[Depends(require_permission("dashboard:view"))])
def update_preferences(
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """更新用户偏好"""
    can_access_leader = current_user.has_permission("dashboard:leader_view") or current_user.is_admin
    can_access_work = current_user.has_permission("dashboard:work_view") or current_user.is_admin
    can_switch = can_access_leader and can_access_work

    if data.dashboard_view == "leader" and not can_access_leader:
        raise HTTPException(status_code=403, detail="您没有该操作权限，请联系管理员")
    if data.dashboard_view == "employee" and not can_access_work:
        raise HTTPException(status_code=403, detail="您没有该操作权限，请联系管理员")
    if not can_switch and data.dashboard_view is not None:
        if (can_access_work and data.dashboard_view != "employee") or (can_access_leader and data.dashboard_view != "leader"):
            raise HTTPException(status_code=403, detail="您没有该操作权限，请联系管理员")
    pref = db.query(SysUserPreference).filter(
        SysUserPreference.user_id == current_user.id
    ).first()
    if not pref:
        pref = SysUserPreference(user_id=current_user.id)
        db.add(pref)
    
    if data.dashboard_view is not None:
        pref.dashboard_view = data.dashboard_view
    if data.extra is not None:
        pref.extra = data.extra
    
    db.commit()
    db.refresh(pref)
    write_log(db, "operation", current_user.id, current_user.username, "dashboard", "preference_update", None, data.model_dump())
    return {
        "dashboard_view": pref.dashboard_view,
        "extra": pref.extra or {}
    }


@router.get("/schedules", dependencies=[Depends(require_permission("system:dict"))])
def get_schedules(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """获取日程配置列表（系统管理用）"""
    schedules = db.query(SysSchedule).order_by(SysSchedule.sort_order).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "day_of_month": s.day_of_month,
            "step_key": s.step_key,
            "route": s.route,
            "icon": s.icon,
            "color": s.color,
            "description": s.description,
            "is_warning": s.is_warning,
            "warning_days": s.warning_days,
            "sort_order": s.sort_order,
            "is_enabled": s.is_enabled
        } for s in schedules
    ]


@router.post("/schedules", dependencies=[Depends(require_permission("system:dict"))])
def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """创建日程配置"""
    sched = SysSchedule(**data.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    write_log(db, "operation", current_user.id, current_user.username, "system", "schedule_create", str(sched.id), data.model_dump())
    return {"id": sched.id, "message": "创建成功"}


@router.put("/schedules/{sched_id}", dependencies=[Depends(require_permission("system:dict"))])
def update_schedule(
    sched_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """更新日程配置"""
    sched = db.query(SysSchedule).filter(SysSchedule.id == sched_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="日程不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sched, key, value)
    
    db.commit()
    db.refresh(sched)
    write_log(db, "operation", current_user.id, current_user.username, "system", "schedule_update", str(sched_id), update_data)
    return {"message": "更新成功"}


@router.delete("/schedules/{sched_id}", dependencies=[Depends(require_permission("system:dict"))])
def delete_schedule(
    sched_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user)
):
    """删除日程配置"""
    sched = db.query(SysSchedule).filter(SysSchedule.id == sched_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="日程不存在")
    db.delete(sched)
    db.commit()
    write_log(db, "operation", current_user.id, current_user.username, "system", "schedule_delete", str(sched_id), {"name": sched.name})
    return {"message": "删除成功"}
