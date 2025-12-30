"""
任务调度器
"""

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .game_fetcher import GameFetcher
from .models import GameInfo, Task, TaskStatus
from .task_store import TaskStore
from src.content_acquisition.acquirer import ContentAcquirer
from src.video_maker import VideoMaker
from src.vide_publish import VideoPublisher


class TaskScheduler:
    """任务调度器 - 系统的核心管家"""

    def __init__(self):
        # 在初始化前获取B站登录凭证（从Chrome cookies）
        logger.info("正在从Chrome cookies获取B站登录凭证...")
        from src.utils import get_bilibili_credentials_from_chrome

        sessdata, bili_jct = get_bilibili_credentials_from_chrome()
        if sessdata and bili_jct:
            logger.info("成功从Chrome cookies获取B站登录凭证")
        else:
            logger.warning("未能从Chrome cookies获取完整凭证，将使用环境变量或默认值")

        self.game_fetcher = GameFetcher()
        self.content_acquirer = ContentAcquirer(headless=False)
        self.video_maker = VideoMaker()
        self.video_publisher = VideoPublisher(sessdata=sessdata, bili_jct=bili_jct)
        self.task_store = TaskStore()  # 使用持久化存储
        logger.info("任务调度器初始化完成")

    def start_daily_tasks(self) -> List[Task]:
        """
        启动每日任务流程
        获取当天NBA比赛，为每场比赛创建任务并检查状态

        Returns:
            List[Task]: 创建的任务列表
        """
        logger.info("开始执行每日任务流程")

        # 1. 获取当天NBA比赛
        games_data = self.game_fetcher.get_today_nba_games()
        if not games_data:
            logger.warning("当日没有比赛，任务流程结束")
            return []

        # 2. 为每场比赛创建任务并检查状态
        tasks = []
        for game_data in games_data:
            try:
                match_id = game_data.get("matchId") or game_data.get("match_id", "")

                # 检查是否已存在该比赛的任务（避免重复创建）
                existing_tasks = self.task_store.get_tasks_by_match_id(match_id)
                if existing_tasks:
                    # 过滤出未完成的任务
                    incomplete_tasks = [
                        t
                        for t in existing_tasks
                        if t.status
                        not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                    ]
                    if incomplete_tasks:
                        logger.info(f"比赛 {match_id} 已存在未完成任务，跳过创建")
                        tasks.extend(incomplete_tasks)
                        continue

                # 创建任务
                task = self.create_task_from_game(game_data)

                # 检查比赛状态和评分数量
                game_status_info = self.game_fetcher.get_game_status(match_id)

                if not game_status_info:
                    # 无法获取状态信息，保守处理：设置为等待状态
                    logger.warning(f"比赛 {match_id} 无法获取状态信息，设置为等待状态")
                    task.status = TaskStatus.WAITING_GAME_END
                    next_check = datetime.now() + timedelta(hours=1)
                    task.config["next_check_time"] = next_check.isoformat()
                    self.task_store.save_task(task)
                    tasks.append(task)
                    continue

                game_status = game_status_info.get("status", "")
                rating_count = game_status_info.get("rating_count", 0)

                # 更新任务中的比赛评分数量
                task.game_info.rating_count = rating_count

                if game_status == "已结束":
                    # 比赛已结束，检查评分数量
                    if rating_count >= 30000:
                        logger.info(
                            f"比赛 {match_id} 已结束且评分数量({rating_count})>=3万，任务可以执行"
                        )
                        task.status = TaskStatus.PENDING
                    else:
                        logger.info(
                            f"比赛 {match_id} 已结束但评分数量({rating_count})<3万，跳过任务创建"
                        )
                        # 不保存任务，直接跳过
                        continue
                elif game_status in ["未开始", "进行中"]:
                    # 比赛未结束，标记为等待状态，并设置1小时后重新检查
                    logger.info(
                        f"比赛 {match_id} 状态为 {game_status}，评分数量: {rating_count}，设置为等待状态"
                    )
                    task.status = TaskStatus.WAITING_GAME_END
                    next_check = datetime.now() + timedelta(hours=1)
                    task.config["next_check_time"] = next_check.isoformat()
                    task.config["game_status"] = game_status
                    task.config["rating_count"] = rating_count
                else:
                    # 无法获取状态，保守处理：设置为等待状态
                    logger.warning(
                        f"比赛 {match_id} 状态未知，评分数量: {rating_count}，设置为等待状态"
                    )
                    task.status = TaskStatus.WAITING_GAME_END
                    next_check = datetime.now() + timedelta(hours=1)
                    task.config["next_check_time"] = next_check.isoformat()
                    task.config["rating_count"] = rating_count

                # 保存任务到持久化存储
                self.task_store.save_task(task)
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
        return self.task_store.get_task(task_id)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_msg: Optional[str] = None,
        next_check_time: Optional[datetime] = None,
    ):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error_msg: 错误信息（如果有）
            next_check_time: 下次检查时间
        """
        self.task_store.update_task_status(task_id, status, error_msg, next_check_time)

    def get_all_tasks(self) -> List[Task]:
        """
        获取所有任务

        Returns:
            List[Task]: 任务列表
        """
        return self.task_store.get_all_tasks()

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态获取任务

        Args:
            status: 任务状态

        Returns:
            List[Task]: 任务列表
        """
        return self.task_store.get_tasks_by_status(status)

    def get_task_by_game_id(self, game_id: str) -> Optional[Task]:
        """
        根据比赛ID获取任务

        Args:
            game_id: 比赛ID

        Returns:
            Optional[Task]: 任务对象，如果不存在返回None
        """
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.game_info.game_id == game_id:
                return task
        return None

    def check_waiting_tasks(self) -> List[Task]:
        """
        检查所有等待中的任务，看是否到了重新检查的时间

        Returns:
            List[Task]: 需要重新检查的任务列表
        """
        logger.info("开始检查等待中的任务")

        waiting_tasks = self.task_store.get_tasks_by_status(TaskStatus.WAITING_GAME_END)
        tasks_to_check = []
        current_time = datetime.now()

        for task in waiting_tasks:
            next_check_time_str = task.config.get("next_check_time")
            if not next_check_time_str:
                logger.warning(f"任务 {task.task_id} 缺少next_check_time，跳过")
                continue

            try:
                next_check_time = datetime.fromisoformat(next_check_time_str)
                if current_time >= next_check_time:
                    logger.info(f"任务 {task.task_id} 到达检查时间")
                    tasks_to_check.append(task)
                else:
                    remaining = (next_check_time - current_time).total_seconds() / 60
                    logger.debug(f"任务 {task.task_id} 还需等待 {remaining:.1f} 分钟")
            except Exception as e:
                logger.error(f"解析任务 {task.task_id} 的检查时间失败: {e}")

        logger.info(f"找到 {len(tasks_to_check)} 个需要检查的任务")
        return tasks_to_check

    def recheck_game_status_and_update(self, task: Task) -> bool:
        """
        重新检查比赛状态并更新任务

        Args:
            task: 任务对象

        Returns:
            bool: 比赛是否已结束且满足评分条件
        """
        match_id = task.game_info.match_id
        logger.info(f"重新检查比赛 {match_id} 的状态")

        game_status_info = self.game_fetcher.get_game_status(match_id)

        if not game_status_info:
            logger.warning(f"比赛 {match_id} 无法获取状态信息，继续等待")
            # 无法获取状态，1小时后再试
            next_check = datetime.now() + timedelta(hours=1)
            task.config["next_check_time"] = next_check.isoformat()
            self.task_store.save_task(task)
            return False

        game_status = game_status_info.get("status", "")
        rating_count = game_status_info.get("rating_count", 0)

        # 更新任务中的评分数量
        task.game_info.rating_count = rating_count
        task.config["rating_count"] = rating_count

        if game_status == "已结束":
            # 比赛已结束，检查评分数量
            if rating_count >= 30000:
                logger.info(
                    f"比赛 {match_id} 已结束且评分数量({rating_count})>=3万，任务转为待执行状态"
                )
                self.task_store.update_task_status(task.task_id, TaskStatus.PENDING)
                return True
            else:
                logger.info(f"比赛 {match_id} 已结束但评分数量({rating_count})<3万，继续等待")
                # 设置下次检查时间（1小时后），继续等待评分数量增长
                next_check = datetime.now() + timedelta(hours=1)
                task.config["game_status"] = game_status
                task.config["next_check_time"] = next_check.isoformat()
                self.task_store.save_task(task)
                return False
        elif game_status in ["未开始", "进行中"]:
            logger.info(
                f"比赛 {match_id} 仍在进行或未开始（状态：{game_status}），评分数量: {rating_count}，继续等待"
            )
            # 设置下次检查时间（1小时后）
            next_check = datetime.now() + timedelta(hours=1)
            task.config["game_status"] = game_status
            task.config["next_check_time"] = next_check.isoformat()
            self.task_store.save_task(task)
            return False
        else:
            logger.warning(f"比赛 {match_id} 状态未知，评分数量: {rating_count}，继续等待")
            # 无法获取状态，1小时后再试
            next_check = datetime.now() + timedelta(hours=1)
            task.config["next_check_time"] = next_check.isoformat()
            self.task_store.save_task(task)
            return False

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
