"""
主程序入口
"""

from loguru import logger

from src.schedule import TaskScheduler


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("B站视频制作发布系统启动")
    logger.info("=" * 60)

    # 创建任务调度器
    scheduler = TaskScheduler()

    # 启动每日任务流程
    tasks = scheduler.start_daily_tasks()

    # 打印任务信息
    if tasks:
        started_count = scheduler.start_all_tasks()
        logger.info(f"成功启动 {started_count} 个任务线程")

    else:
        logger.warning("未创建任何任务")


if __name__ == "__main__":
    main()
