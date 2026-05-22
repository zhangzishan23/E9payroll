# Skill: 数据完整性校验（data-completeness）

## 描述
在薪资核算前，校验所有员工的数据源是否齐全。检查每个员工是否具备：薪资档案、考勤数据、绩效评分、社保公积金等必须数据。缺什么、缺谁的，一目了然。

## 代码（Python）
```python
from typing import List, Dict, Optional, Set
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.models import (
    Employee, EmployeeSalary, AttendanceRecord,
    PerformanceScore, SocialInsurance
)


def _get_period_end(period: str) -> date:
    """将核算周期（如 2026-05）转换为月末日期"""
    if '-' in period:
        year, month = map(int, period.split('-'))
    else:
        year = int(period[:4])
        month = int(period[4:6])
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def check_completeness(db: Session, period: str) -> dict:
    """
    校验指定核算周期内所有员工的数据完整性。

    返回格式：
    {
        "period": "2026-05",
        "total": 61,
        "complete": 55,
        "incomplete": 6,
        "issues": [
            {
                "employee_id": 1,
                "employee_name": "张三",
                "employee_no": "E001",
                "missing": ["考勤数据", "绩效评分"]
            },
            ...
        ]
    }
    """
    all_employees = db.query(Employee).order_by(Employee.employee_no).all()
    period_end = _get_period_end(period)

    emp_ids = [e.id for e in all_employees]

    salaries = db.query(EmployeeSalary).filter(
        EmployeeSalary.employee_id.in_(emp_ids),
        EmployeeSalary.effective_date <= period_end
    ).order_by(
        EmployeeSalary.effective_date.desc(),
        EmployeeSalary.id.desc()
    ).all()
    salary_ids = {s.employee_id for s in {s.employee_id: s for s in salaries}.keys()}

    attendances = db.query(AttendanceRecord).filter(
        AttendanceRecord.period == period,
        AttendanceRecord.employee_id.in_(emp_ids)
    ).all()
    att_ids = {a.employee_id for a in attendances}

    performances = db.query(PerformanceScore).filter(
        PerformanceScore.period == period,
        PerformanceScore.employee_id.in_(emp_ids)
    ).all()
    perf_ids = {p.employee_id for p in performances}

    social_ins = db.query(SocialInsurance).filter(
        SocialInsurance.period == period,
        SocialInsurance.employee_id.in_(emp_ids)
    ).all()
    si_ids = {s.employee_id for s in social_ins}

    issues = []
    for emp in all_employees:
        missing = []
        if emp.id not in salary_ids:
            missing.append("薪资档案")
        if emp.id not in att_ids:
            missing.append("考勤数据")
        if emp.id not in perf_ids:
            missing.append("绩效评分")
        if emp.id not in si_ids:
            missing.append("社保公积金")

        if missing:
            issues.append({
                "employee_id": emp.id,
                "employee_name": emp.name,
                "employee_no": emp.employee_no,
                "missing": missing,
            })

    return {
        "period": period,
        "total": len(all_employees),
        "complete": len(all_employees) - len(issues),
        "incomplete": len(issues),
        "issues": issues,
    }


REQUIRED_DATA_SOURCES = {
    "salary": "薪资档案",
    "attendance": "考勤数据",
    "performance": "绩效评分",
    "social_insurance": "社保公积金",
}

OPTIONAL_DATA_SOURCES = {
    "travel_reimbursement": "临时差旅报销",
    "labor_compensation": "劳动补偿金",
    "legacy_adjustment": "遗留金额调整",
}
```

## 外部依赖与错误处理
- 依赖：SQLAlchemy Session、Employee、EmployeeSalary、AttendanceRecord、PerformanceScore、SocialInsurance 模型
- 自动处理多种周期格式（2026-05 / 202605）
- 薪资档案校验使用 `effective_date <= 月末`，确保取到最新的有效薪资
- 性能注意：员工数 > 100 时建议对查询添加分页

## 调用示例
```python
result = check_completeness(db, "2026-05")
if result["incomplete"] > 0:
    print(f"警告：{result['incomplete']} 名员工数据不完整")
    for issue in result["issues"]:
        print(f"  {issue['employee_name']}: 缺少 {', '.join(issue['missing'])}")
```

## 使用场景
- [salary.py](file:///d:/devtool/cm/backend/app/api/salary.py) - `check_data_completeness` 端点
- 薪资核算前的自动化前置检查
- 报表统计中心的数据就绪度展示