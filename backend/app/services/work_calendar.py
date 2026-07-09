"""
工作日历服务
提供年度日历初始化、应计薪天数计算、AI节假日生成等功能
"""
import calendar
import logging
from datetime import date
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.models import WorkCalendar

logger = logging.getLogger(__name__)


def generate_holidays_by_ai(year: int) -> dict:
    """
    调用AI生成指定年份的国务院法定节假日和调休补班安排
    返回: {"holidays": [{"date": "YYYY-MM-DD", "name": "节日名"}], "workdays": [{"date": "YYYY-MM-DD", "name": "调休补班"}]}
    """
    from app.core import ai_service

    if not ai_service.is_available():
        raise RuntimeError(
            "AI 服务未配置，无法自动生成节假日。\n"
            "请在 .env 中设置 LLM_API_KEY（阿里云百炼 API Key），\n"
            "或手动在年度日历中标记节假日和调休补班。"
        )

    system_prompt = f"""你是一个中国法定节假日专家，熟知国务院每年发布的放假安排通知。
请生成{year}年全年的法定节假日和调休补班日期。

要求：
1. 严格按照国务院办公厅发布的{year}年部分节假日安排的通知来生成，不要猜测或编造
2. 包含所有法定节假日：元旦、春节、清明节、劳动节、端午节、中秋节、国庆节
3. holidays数组列出所有放假日期（包括调休形成的连休日，不只是节日当天）
4. workdays数组列出所有调休补班上班日期（即因放假调休，原本是周末需要上班的日子）
5. 调休补班日期的判断规则：仔细核对通知原文中明确写的"XX月XX日上班"的日期，不要错放工作日到补班列表
6. 正常工作日（周一到周五）如果不是法定节假日，不要标记为holiday
7. 正常周末（周六周日）如果没有被通知列为补班上班日，不要标记为workday
8. 每个日期必须严格对应星期几，避免日期和星期错位
9. 日期格式必须是 YYYY-MM-DD
10. 只返回JSON，不要有其他说明文字

返回格式：
{{
  "holidays": [
    {{"date": "{year}-01-01", "name": "元旦"}},
    ...
  ],
  "workdays": [
    {{"date": "{year}-02-04", "name": "春节调休补班"}},
    ...
  ]
}}"""

    user_message = f"请生成{year}年中国国务院法定节假日及调休补班安排，严格按照官方放假通知，特别注意核对补班日期是否为周末。"

    result = ai_service.chat_json(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.1,
    )

    holidays = result.get("holidays", [])
    workdays = result.get("workdays", [])

    if not holidays:
        raise ValueError(f"AI未能返回{year}年节假日数据，请重试或手动配置")

    return {
        "holidays": holidays,
        "workdays": workdays,
    }


def init_year_calendar(db: Session, year: int) -> int:
    """
    初始化指定年份的日历（如果某日期不存在则创建默认记录）
    返回创建的记录数
    """
    created_count = 0
    for month in range(1, 13):
        _, last_day = calendar.monthrange(year, month)
        for day in range(1, last_day + 1):
            cal_date = date(year, month, day)
            exists = db.query(WorkCalendar).filter(WorkCalendar.cal_date == cal_date).first()
            if not exists:
                weekday = cal_date.weekday()
                is_workday = weekday < 5
                db.add(WorkCalendar(
                    cal_date=cal_date,
                    year=year,
                    month=month,
                    day=day,
                    weekday=weekday,
                    day_type="workday" if is_workday else "weekend",
                    is_salary_day=is_workday,
                    remark=None,
                    is_ai_generated=False,
                ))
                created_count += 1
    if created_count > 0:
        db.commit()
    return created_count


def get_month_salary_days(db: Session, period: str) -> float:
    """
    计算指定月份的应计薪天数
    period: 格式 YYYYMM
    """
    year = int(period[:4])
    month = int(period[4:6])

    init_year_calendar(db, year)

    count = db.query(WorkCalendar).filter(
        WorkCalendar.year == year,
        WorkCalendar.month == month,
        WorkCalendar.is_salary_day == True
    ).count()
    return float(count)


def get_year_calendar(db: Session, year: int) -> List[dict]:
    """
    获取指定年份的完整日历数据
    返回按月份分组的列表，每个月包含该月所有日期
    """
    init_year_calendar(db, year)

    records = db.query(WorkCalendar).filter(
        WorkCalendar.year == year
    ).order_by(WorkCalendar.cal_date).all()

    result = []
    for r in records:
        result.append({
            "date": r.cal_date.isoformat(),
            "year": r.year,
            "month": r.month,
            "day": r.day,
            "weekday": r.weekday,
            "day_type": r.day_type,
            "is_salary_day": r.is_salary_day,
            "remark": r.remark,
            "is_ai_generated": r.is_ai_generated,
        })
    return result


def update_calendar_days(db: Session, updates: List[dict]) -> int:
    """
    批量更新日历日期状态
    updates: [{"date": "2026-05-01", "day_type": "holiday", "is_salary_day": false, "remark": "劳动节"}, ...]
    返回更新的记录数
    """
    updated = 0
    for item in updates:
        date_str = item.get("date")
        if not date_str:
            continue
        try:
            cal_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        record = db.query(WorkCalendar).filter(WorkCalendar.cal_date == cal_date).first()
        if not record:
            init_year_calendar(db, cal_date.year)
            record = db.query(WorkCalendar).filter(WorkCalendar.cal_date == cal_date).first()
            if not record:
                continue

        if "day_type" in item:
            record.day_type = item["day_type"]
        if "is_salary_day" in item:
            record.is_salary_day = item["is_salary_day"]
        if "remark" in item:
            record.remark = item["remark"]
        if "is_ai_generated" in item:
            record.is_ai_generated = item["is_ai_generated"]
        updated += 1

    db.commit()
    return updated


def apply_ai_holidays(db: Session, year: int, holidays: List[dict], workdays: List[dict]) -> Tuple[int, int]:
    """
    应用AI生成的节假日和补班数据
    holidays: [{"date": "2026-05-01", "name": "劳动节"}, ...]
    workdays: [{"date": "2026-04-26", "name": "调休补班"}, ...]
    返回 (更新的节假日数, 更新的补班数)
    """
    init_year_calendar(db, year)

    holiday_count = 0
    for h in holidays:
        date_str = h.get("date")
        name = h.get("name", "")
        if not date_str:
            continue
        try:
            cal_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        if cal_date.year != year:
            continue
        record = db.query(WorkCalendar).filter(WorkCalendar.cal_date == cal_date).first()
        if record:
            record.day_type = "holiday"
            record.is_salary_day = False
            record.remark = name
            record.is_ai_generated = True
            holiday_count += 1

    workday_count = 0
    for w in workdays:
        date_str = w.get("date")
        name = w.get("name", "调休补班")
        if not date_str:
            continue
        try:
            cal_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        if cal_date.year != year:
            continue
        weekday = cal_date.weekday()
        if weekday < 5:
            logger.warning(f"AI生成的补班日期{date_str}是正常工作日(周{weekday+1})，已跳过")
            continue
        record = db.query(WorkCalendar).filter(WorkCalendar.cal_date == cal_date).first()
        if record:
            record.day_type = "makeup_work"
            record.is_salary_day = True
            record.remark = name
            record.is_ai_generated = True
            workday_count += 1

    db.commit()
    return holiday_count, workday_count


def get_calendar_status_summary(db: Session, year: int) -> dict:
    """获取指定年份日历的状态统计"""
    init_year_calendar(db, year)

    workdays = db.query(WorkCalendar).filter(
        WorkCalendar.year == year, WorkCalendar.day_type == "workday", WorkCalendar.is_salary_day == True
    ).count()
    weekends = db.query(WorkCalendar).filter(
        WorkCalendar.year == year, WorkCalendar.day_type == "weekend"
    ).count()
    holidays = db.query(WorkCalendar).filter(
        WorkCalendar.year == year, WorkCalendar.day_type == "holiday"
    ).count()
    makeup = db.query(WorkCalendar).filter(
        WorkCalendar.year == year, WorkCalendar.day_type == "makeup_work"
    ).count()
    total_salary_days = db.query(WorkCalendar).filter(
        WorkCalendar.year == year, WorkCalendar.is_salary_day == True
    ).count()

    return {
        "year": year,
        "workdays": workdays,
        "weekends": weekends,
        "holidays": holidays,
        "makeup_work": makeup,
        "total_salary_days": total_salary_days,
    }
