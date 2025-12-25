"""
主程序入口
"""

from pathlib import Path

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

    # 兜底逻辑：如果当日没有比赛，则不运行接下来的逻辑
    if not tasks:
        logger.warning("当日没有比赛，程序退出")
        return

    # 打印任务信息并顺序执行所有任务
    executed_count = scheduler.start_all_tasks()
    logger.info(f"成功执行 {executed_count} 个任务")

    # 清理 videos 目录中的所有文件
    videos_dir = Path("materials/videos")
    if videos_dir.exists():
        deleted_count = 0
        for file_path in videos_dir.iterdir():
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"已删除文件: {file_path.name}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path.name}: {e}")
        logger.info(f"已清理 videos 目录，共删除 {deleted_count} 个文件")
    else:
        logger.warning(f"videos 目录不存在: {videos_dir}")


if __name__ == "__main__":
    main()
