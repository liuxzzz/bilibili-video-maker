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
        logger.info(f"\n成功创建 {len(tasks)} 个任务:")
        for task in tasks:
            logger.info(f"  - {task}")
            logger.info(
                f"    比赛: {task.game_info.away_team_name} vs {task.game_info.home_team_name}"
            )
            logger.info(f"    状态: {task.status.value}")
    else:
        logger.warning("未创建任何任务")

    logger.info("=" * 60)
    logger.info("任务调度完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
