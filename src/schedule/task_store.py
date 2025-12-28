"""
任务持久化存储模块
使用JSON文件存储任务状态，支持任务的创建、更新、查询
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .models import Task, TaskStatus, GameInfo


class TaskStore:
    """任务存储管理器"""

    def __init__(self, store_path: str = "data/tasks.json"):
        """
        初始化任务存储

        Args:
            store_path: 存储文件路径
        """
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果文件不存在，创建空的存储文件
        if not self.store_path.exists():
            self._save_data({"tasks": {}})
            logger.info(f"创建新的任务存储文件: {self.store_path}")
        else:
            logger.info(f"使用现有任务存储文件: {self.store_path}")

    def _load_data(self) -> dict:
        """加载存储数据"""
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载任务数据失败: {e}")
            return {"tasks": {}}

    def _save_data(self, data: dict):
        """保存存储数据"""
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务数据失败: {e}")

    def save_task(self, task: Task):
        """
        保存任务

        Args:
            task: 任务对象
        """
        data = self._load_data()
        data["tasks"][task.task_id] = task.to_dict()
        self._save_data(data)
        logger.debug(f"任务已保存: {task.task_id}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务

        Args:
            task_id: 任务ID

        Returns:
            Optional[Task]: 任务对象，不存在返回None
        """
        data = self._load_data()
        task_data = data["tasks"].get(task_id)

        if not task_data:
            return None

        return self._dict_to_task(task_data)

    def get_all_tasks(self) -> List[Task]:
        """
        获取所有任务

        Returns:
            List[Task]: 任务列表
        """
        data = self._load_data()
        tasks = []

        for task_data in data["tasks"].values():
            task = self._dict_to_task(task_data)
            if task:
                tasks.append(task)

        return tasks

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态获取任务

        Args:
            status: 任务状态

        Returns:
            List[Task]: 任务列表
        """
        tasks = self.get_all_tasks()
        return [task for task in tasks if task.status == status]

    def get_tasks_by_match_id(self, match_id: str) -> List[Task]:
        """
        根据比赛match_id获取任务

        Args:
            match_id: 比赛match_id

        Returns:
            List[Task]: 任务列表
        """
        tasks = self.get_all_tasks()
        return [task for task in tasks if task.game_info.match_id == match_id]

    def get_pending_retry_tasks(self) -> List[Task]:
        """
        获取所有待重试的任务（状态为WAITING_GAME_END）

        Returns:
            List[Task]: 待重试任务列表
        """
        return self.get_tasks_by_status(TaskStatus.WAITING_GAME_END)

    def delete_task(self, task_id: str):
        """
        删除任务

        Args:
            task_id: 任务ID
        """
        data = self._load_data()
        if task_id in data["tasks"]:
            del data["tasks"][task_id]
            self._save_data(data)
            logger.info(f"任务已删除: {task_id}")

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
            error_msg: 错误信息
            next_check_time: 下次检查时间
        """
        task = self.get_task(task_id)
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

        # 保存下次检查时间
        if next_check_time:
            task.config["next_check_time"] = next_check_time.isoformat()

        self.save_task(task)
        logger.info(f"任务状态已更新: {task_id}, {old_status.value} -> {status.value}")

    def _dict_to_task(self, task_data: dict) -> Optional[Task]:
        """
        将字典转换为Task对象

        Args:
            task_data: 任务数据字典

        Returns:
            Optional[Task]: 任务对象
        """
        try:
            game_info_data = task_data.get("game_info", {})
            game_info = GameInfo(
                game_id=game_info_data.get("game_id", ""),
                home_team_name=game_info_data.get("home_team_name", ""),
                away_team_name=game_info_data.get("away_team_name", ""),
                home_score=game_info_data.get("home_score", ""),
                away_score=game_info_data.get("away_score", ""),
                competition_stage_desc=game_info_data.get("competition_stage_desc", ""),
                match_status=game_info_data.get("match_status", ""),
                match_id=game_info_data.get("match_id", ""),
            )

            task = Task(
                task_id=task_data.get("task_id", ""),
                game_info=game_info,
                status=TaskStatus(task_data.get("status", TaskStatus.PENDING.value)),
                create_time=(
                    datetime.fromisoformat(task_data["create_time"])
                    if task_data.get("create_time")
                    else None
                ),
                start_time=(
                    datetime.fromisoformat(task_data["start_time"])
                    if task_data.get("start_time")
                    else None
                ),
                end_time=(
                    datetime.fromisoformat(task_data["end_time"])
                    if task_data.get("end_time")
                    else None
                ),
                config=task_data.get("config", {}),
                result=task_data.get("result", {}),
                error_msg=task_data.get("error_msg"),
            )

            return task
        except Exception as e:
            logger.error(f"转换任务数据失败: {e}")
            return None
