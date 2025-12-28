"""
定时任务调度器
使用APScheduler实现定时任务
"""

from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from .scheduler import TaskScheduler
from .models import TaskStatus


class CronScheduler:
    """定时任务调度器"""

    def __init__(self):
        """初始化定时任务调度器"""
        self.scheduler = BlockingScheduler()
        self.task_scheduler = TaskScheduler()
        logger.info("定时任务调度器初始化完成")

    def daily_check_job(self):
        """
        每日检查任务（每天12:00执行）
        - 获取当天比赛
        - 为已结束的比赛创建任务并执行
        - 为未结束的比赛创建等待任务
        """
        logger.info("=" * 80)
        logger.info(f"执行每日检查任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 1. 获取当天比赛并创建任务
            tasks = self.task_scheduler.start_daily_tasks()

            if not tasks:
                logger.info("当天没有比赛，任务结束")
                return

            # 2. 统计任务状态
            pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
            waiting_tasks = [t for t in tasks if t.status == TaskStatus.WAITING_GAME_END]

            logger.info(
                f"任务统计 - 待执行: {len(pending_tasks)}, 等待比赛结束: {len(waiting_tasks)}"
            )

            # 3. 执行所有待执行的任务
            if pending_tasks:
                logger.info(f"开始执行 {len(pending_tasks)} 个待执行任务")
                task_ids = [t.task_id for t in pending_tasks]
                executed_count = self.task_scheduler.start_all_tasks(task_ids)
                logger.info(f"成功执行 {executed_count} 个任务")

                # 清理视频文件
                self._cleanup_videos()
            else:
                logger.info("没有待执行的任务")

            logger.info("每日检查任务执行完成")

        except Exception as e:
            logger.error(f"每日检查任务执行失败: {e}", exc_info=True)

    def hourly_check_job(self):
        """
        每小时检查任务
        - 检查所有等待中的任务
        - 重新检查比赛状态
        - 对已结束的比赛执行任务
        """
        logger.info("-" * 80)
        logger.info(f"执行每小时检查任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 80)

        try:
            # 1. 获取需要检查的等待任务
            tasks_to_check = self.task_scheduler.check_waiting_tasks()

            if not tasks_to_check:
                logger.info("没有需要检查的等待任务")
                return

            logger.info(f"找到 {len(tasks_to_check)} 个需要检查的等待任务")

            # 2. 重新检查比赛状态
            ready_tasks = []
            for task in tasks_to_check:
                try:
                    is_finished = self.task_scheduler.recheck_game_status_and_update(task)
                    if is_finished:
                        ready_tasks.append(task)
                except Exception as e:
                    logger.error(f"检查任务 {task.task_id} 失败: {e}", exc_info=True)

            # 3. 执行已结束比赛的任务
            if ready_tasks:
                logger.info(f"找到 {len(ready_tasks)} 个比赛已结束的任务，开始执行")
                task_ids = [t.task_id for t in ready_tasks]
                executed_count = self.task_scheduler.start_all_tasks(task_ids)
                logger.info(f"成功执行 {executed_count} 个任务")

                # 清理视频文件
                self._cleanup_videos()
            else:
                logger.info("没有比赛已结束的任务")

            logger.info("每小时检查任务执行完成")

        except Exception as e:
            logger.error(f"每小时检查任务执行失败: {e}", exc_info=True)

    def _cleanup_videos(self):
        """清理临时视频文件"""
        try:
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
        except Exception as e:
            logger.error(f"清理视频文件失败: {e}")

    def start(self):
        """启动定时任务调度器"""
        logger.info("=" * 80)
        logger.info("B站视频制作发布系统 - 定时任务模式")
        logger.info("=" * 80)

        # 添加每日12:00的定时任务
        self.scheduler.add_job(
            self.daily_check_job,
            trigger=CronTrigger(hour=12, minute=0),
            id="daily_check",
            name="每日比赛检查",
            replace_existing=True,
        )
        logger.info("已添加定时任务: 每日12:00执行比赛检查")

        # 添加每小时的检查任务
        self.scheduler.add_job(
            self.hourly_check_job,
            trigger=IntervalTrigger(hours=1),
            id="hourly_check",
            name="每小时状态检查",
            replace_existing=True,
        )
        logger.info("已添加定时任务: 每小时执行状态检查")

        # 立即执行一次每日检查（用于测试和启动时的初始化）
        logger.info("启动时执行一次每日检查任务...")
        self.daily_check_job()

        logger.info("定时任务调度器启动成功，等待执行定时任务...")
        logger.info("按 Ctrl+C 停止")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("定时任务调度器已停止")
