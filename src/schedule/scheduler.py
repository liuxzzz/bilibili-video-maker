"""
任务调度器
"""

import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .game_fetcher import GameFetcher
from .models import GameInfo, Task, TaskStatus
from src.content_acquisition.acquirer import ContentAcquirer
from src.video_maker import VideoMaker
from src.vide_publish import VideoPublisher


class TaskScheduler:
    """任务调度器 - 系统的核心管家"""

    def __init__(self):
        self.game_fetcher = GameFetcher()
        self.content_acquirer = ContentAcquirer(headless=False)
        self.video_maker = VideoMaker()
        self.video_publisher = VideoPublisher()
        self.tasks: Dict[str, Task] = {}  # 任务字典，key为task_id
        logger.info("任务调度器初始化完成")

    def start_daily_tasks(self) -> List[Task]:
        """
        启动每日任务流程
        获取当天NBA比赛，为每场比赛创建任务

        Returns:
            List[Task]: 创建的任务列表
        """
        logger.info("开始执行每日任务流程")

        # 1. 获取当天NBA比赛
        games_data = self.game_fetcher.get_today_nba_games()
        if not games_data:
            logger.warning("当日没有比赛，任务流程结束")
            return []

        # 2. 为每场比赛创建任务
        tasks = []
        for game_data in games_data:
            try:

                task = self.create_task_from_game(game_data)
                tasks.append(task)
                logger.info(f"为比赛创建任务: {task}")
            except Exception as e:
                logger.error(f"创建任务失败: {e}, 比赛信息: {game_data}")

        logger.info(f"共创建 {len(tasks)} 个任务")
        return tasks

    def create_task_from_game(self, game_data: dict) -> Task:
        """
        从比赛信息创建任务

        Args:
            game_data: 比赛信息字典

        Returns:
            Task: 任务对象
        """
        # 创建比赛信息对象
        # 这里的字段名与 `GameInfo` 中的定义保持一致
        game_info = GameInfo(
            game_id=game_data.get("game_id", ""),
            # 来自虎扑 JSON 的字段为驼峰式，这里做一次兼容映射
            home_team_name=game_data.get("home_team_name") or game_data.get("homeTeamName", ""),
            away_team_name=game_data.get("away_team_name") or game_data.get("awayTeamName", ""),
            home_score=str(game_data.get("home_score") or game_data.get("homeScore", "") or ""),
            away_score=str(game_data.get("away_score") or game_data.get("awayScore", "") or ""),
            competition_stage_desc=game_data.get("competition_stage_desc")
            or game_data.get("competitionStageDesc", ""),
            match_status=game_data.get("match_status") or game_data.get("matchStatus", ""),
            match_id=game_data.get("match_id") or game_data.get("matchId", ""),
        )

        # 生成任务ID（使用比赛ID作为基础）
        task_id = self._generate_task_id(game_info.game_id)

        # 创建任务
        task = Task(
            task_id=task_id,
            game_info=game_info,
            status=TaskStatus.PENDING,
            create_time=datetime.now(),
        )

        # 保存任务
        self.tasks[task_id] = task

        logger.info(f"创建任务成功: task_id={task_id}, game_id={game_info.game_id}")
        return task

    def _generate_task_id(self, game_id: str) -> str:
        """
        生成任务唯一ID

        Args:
            game_id: 比赛ID

        Returns:
            str: 任务ID
        """
        # 任务ID格式: task_{game_id}_{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        task_id = f"task_{game_id}_{timestamp}"
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务

        Args:
            task_id: 任务ID

        Returns:
            Optional[Task]: 任务对象，如果不存在返回None
        """
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus, error_msg: Optional[str] = None):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error_msg: 错误信息（如果有）
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return

        old_status = task.status
        task.status = status

        if status == TaskStatus.RUNNING and not task.start_time:
            task.start_time = datetime.now()

        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.end_time = datetime.now()

        if error_msg:
            task.error_msg = error_msg

        logger.info(f"任务状态更新: task_id={task_id}, " f"{old_status.value} -> {status.value}")

    def get_all_tasks(self) -> List[Task]:
        """
        获取所有任务

        Returns:
            List[Task]: 任务列表
        """
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态获取任务

        Args:
            status: 任务状态

        Returns:
            List[Task]: 任务列表
        """
        return [task for task in self.tasks.values() if task.status == status]

    def get_task_by_game_id(self, game_id: str) -> Optional[Task]:
        """
        根据比赛ID获取任务

        Args:
            game_id: 比赛ID

        Returns:
            Optional[Task]: 任务对象，如果不存在返回None
        """
        for task in self.tasks.values():
            if task.game_info.game_id == game_id:
                return task
        return None

    def execute_task(self, task_id: str):
        """
        执行单个任务（单线程顺序执行）

        Args:
            task_id: 任务ID
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在，无法执行: {task_id}")
            return

        # 检查任务状态，避免重复执行
        if task.status != TaskStatus.PENDING:
            logger.warning(
                f"任务状态不是PENDING，跳过执行: {task_id}, 当前状态: {task.status.value}"
            )
            return

        try:
            # 更新任务状态为运行中
            self.update_task_status(task_id, TaskStatus.RUNNING)
            logger.info(
                f"开始执行任务: {task_id}, 比赛: {task.game_info.away_team_name} vs {task.game_info.home_team_name}"
            )

            # 1. 内容采集阶段
            self.update_task_status(task_id, TaskStatus.COLLECTING)
            logger.info(f"任务 {task_id} 进入内容采集阶段")

            # 调用内容采集逻辑
            content = self.content_acquirer.acquire_content(task.game_info)

            # 2. 视频处理阶段
            self.update_task_status(task_id, TaskStatus.GENERATING)
            logger.info(f"任务 {task_id} 进入视频生成阶段")
            # 根据采集来的json来生成视频
            video_path = self.video_maker.generate_video(content)

            # 3. 视频发布阶段
            if not video_path:
                logger.error(f"任务 {task_id} 视频路径为空，跳过发布")
            else:
                self.update_task_status(task_id, TaskStatus.PUBLISHING)
                logger.info(f"任务 {task_id} 进入视频发布阶段")
                # 调用视频发布逻辑，传递视频路径和比赛信息
                publish_success = self.video_publisher.publish_video(video_path, task.game_info)
                if not publish_success:
                    logger.warning(f"任务 {task_id} 视频发布失败")

            # 任务完成
            self.update_task_status(task_id, TaskStatus.COMPLETED)
            logger.info(f"任务执行完成: {task_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"任务执行失败: {task_id}, 错误: {error_msg}", exc_info=True)
            self.update_task_status(task_id, TaskStatus.FAILED, error_msg=error_msg)
        finally:
            logger.info(f"任务执行结束: {task_id}")

    def start_task(self, task_id: str) -> bool:
        """
        执行指定任务（单线程顺序执行）

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功开始执行任务
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在，无法执行: {task_id}")
            return False

        # 检查任务状态
        if task.status != TaskStatus.PENDING:
            logger.warning(
                f"任务状态不是PENDING，无法执行: {task_id}, 当前状态: {task.status.value}"
            )
            return False

        # 直接执行任务（单线程顺序执行）
        logger.info(f"开始执行任务: {task_id}")
        self.execute_task(task_id)
        return True

    def start_all_tasks(self, task_ids: Optional[List[str]] = None) -> int:
        """
        顺序执行所有待执行的任务（单线程）
        如果指定了task_ids，则只为这些任务执行

        Args:
            task_ids: 可选的任务ID列表，如果为None则执行所有PENDING状态的任务

        Returns:
            int: 成功执行的任务数量
        """
        if task_ids is None:
            # 获取所有PENDING状态的任务
            pending_tasks = self.get_tasks_by_status(TaskStatus.PENDING)
            task_ids = [task.task_id for task in pending_tasks]

        executed_count = 0
        for task_id in task_ids:
            logger.info(f"准备执行任务: {task_id} ({executed_count + 1}/{len(task_ids)})")
            if self.start_task(task_id):
                executed_count += 1
            logger.info(f"任务 {task_id} 执行完成，继续下一个任务...")
        return executed_count
