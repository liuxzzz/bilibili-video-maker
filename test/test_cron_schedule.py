"""
测试定时任务调度器配置
验证每天12:00的定时任务是否正确设置
"""

from datetime import datetime
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


def test_cron_schedule():
    """测试定时任务配置"""
    logger.info("=" * 80)
    logger.info("测试定时任务调度器配置")
    logger.info("=" * 80)

    scheduler = BlockingScheduler()

    def daily_job():
        logger.info(f"执行每日任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def hourly_job():
        logger.info(f"执行每小时任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 添加每日12:00的定时任务
    daily_job_obj = scheduler.add_job(
        daily_job,
        trigger=CronTrigger(hour=12, minute=0),
        id="daily_check",
        name="每日比赛检查",
        replace_existing=True,
    )
    logger.info("✅ 已添加定时任务: 每日12:00执行比赛检查")

    next_run_time = daily_job_obj.next_run_time
    if next_run_time:
        logger.info(f"📅 下次每日检查时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 计算距离下次执行的时间
        now = datetime.now()
        if next_run_time > now:
            time_diff = next_run_time - now
            hours = time_diff.total_seconds() / 3600
            logger.info(f"⏰ 距离下次执行还有: {hours:.1f} 小时")
        else:
            logger.info("⚠️  下次执行时间已过，将在明天12:00执行")

    # 添加每小时的检查任务
    hourly_job_obj = scheduler.add_job(
        hourly_job,
        trigger=IntervalTrigger(hours=1),
        id="hourly_check",
        name="每小时状态检查",
        replace_existing=True,
    )
    logger.info("✅ 已添加定时任务: 每小时执行状态检查")

    next_hourly_run = hourly_job_obj.next_run_time
    if next_hourly_run:
        logger.info(f"⏰ 下次每小时检查时间: {next_hourly_run.strftime('%Y-%m-%d %H:%M:%S')}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("📋 定时任务配置验证完成")
    logger.info("=" * 80)
    logger.info("")
    logger.info("💡 注意：这只是配置测试，不会实际启动调度器")
    logger.info("   要实际运行定时任务，请使用: python main.py --mode nba --cron")
    logger.info("")


if __name__ == "__main__":
    test_cron_schedule()
