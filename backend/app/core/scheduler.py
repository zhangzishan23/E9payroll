"""
APScheduler 定时任务模块
- 每月1号凌晨2点：自动同步钉钉花名册 + 上月考勤
- 每月15号凌晨2点：自动同步钉钉花名册 + 本月考勤
- 每天凌晨3点：清理60天前的每日考勤记录
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.database import SessionLocal

logger = logging.getLogger("apscheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
_scheduler: BackgroundScheduler = None


def _sync_roster_job():
    """定时任务：同步钉钉花名册"""
    logger.info("【定时任务】开始同步钉钉花名册...")
    db = SessionLocal()
    try:
        from app.services.dingtalk_service import sync_roster_to_db
        stats = sync_roster_to_db(db)
        logger.info(
            "【定时任务】花名册同步完成：新增 %d 人，更新 %d 人，错误 %d 条",
            stats["created"], stats["updated"], len(stats["errors"])
        )
        if stats["errors"]:
            for err in stats["errors"]:
                logger.warning("【定时任务】花名册错误: %s", err)
    except Exception as e:
        logger.error("【定时任务】花名册同步异常: %s", str(e))
    finally:
        db.close()


def _sync_attendance_job():
    """定时任务：同步钉钉考勤"""
    now = datetime.now()
    if now.day == 1:
        if now.month == 1:
            period = f"{now.year - 1}12"
        else:
            period = f"{now.year}{now.month - 1:02d}"
    else:
        period = f"{now.year}{now.month:02d}"

    logger.info("【定时任务】开始同步钉钉考勤 period=%s ...", period)
    db = SessionLocal()
    try:
        from app.services.dingtalk_service import sync_attendance_to_db
        stats = sync_attendance_to_db(db, period)
        logger.info(
            "【定时任务】考勤同步完成(period=%s)：同步 %d 人，错误 %d 条",
            period, stats["synced"], len(stats["errors"])
        )
        if stats["errors"]:
            for err in stats["errors"]:
                logger.warning("【定时任务】考勤错误: %s", err)
    except Exception as e:
        logger.error("【定时任务】考勤同步异常: %s", str(e))
    finally:
        db.close()


def _cleanup_daily_job():
    """定时任务：清理过期每日考勤记录"""
    logger.info("【定时任务】开始清理过期每日考勤记录...")
    db = SessionLocal()
    try:
        from app.services.dingtalk_service import cleanup_old_daily_records
        count = cleanup_old_daily_records(db, keep_days=60)
        logger.info("【定时任务】清理完成：删除 %d 条记录", count)
    except Exception as e:
        logger.error("【定时任务】清理每日考勤异常: %s", str(e))
    finally:
        db.close()


def start_scheduler():
    """启动定时任务调度器"""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # 每月1号凌晨2点：同步花名册 + 上月考勤
    _scheduler.add_job(
        _sync_roster_job,
        CronTrigger(day=1, hour=2, minute=0),
        id="dingtalk_roster_sync_1st",
        name="钉钉花名册同步(每月1号)",
        replace_existing=True,
    )
    _scheduler.add_job(
        _sync_attendance_job,
        CronTrigger(day=1, hour=2, minute=5),
        id="dingtalk_attendance_sync_1st",
        name="钉钉考勤同步(每月1号)",
        replace_existing=True,
    )

    # 每月15号凌晨2点：同步花名册 + 本月考勤
    _scheduler.add_job(
        _sync_roster_job,
        CronTrigger(day=15, hour=2, minute=0),
        id="dingtalk_roster_sync_15th",
        name="钉钉花名册同步(每月15号)",
        replace_existing=True,
    )
    _scheduler.add_job(
        _sync_attendance_job,
        CronTrigger(day=15, hour=2, minute=5),
        id="dingtalk_attendance_sync_15th",
        name="钉钉考勤同步(每月15号)",
        replace_existing=True,
    )

    # 每天凌晨3点：清理过期每日考勤记录
    _scheduler.add_job(
        _cleanup_daily_job,
        CronTrigger(hour=3, minute=0),
        id="dingtalk_daily_cleanup",
        name="清理过期每日考勤记录",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("定时任务调度器已启动（每月1号和15号凌晨2点同步钉钉数据，每天凌晨3点清理过期考勤记录）")


def stop_scheduler():
    """停止定时任务调度器"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时任务调度器已关闭")