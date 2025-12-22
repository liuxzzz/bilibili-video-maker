"""
任务数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COLLECTING = "collecting"  # 采集中
    GENERATING = "generating"  # 生成中
    PUBLISHING = "publishing"  # 发布中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class GameInfo:
    """比赛信息数据模型"""

    def __init__(
        self,
        game_id: str,  # 比赛ID
        home_team_name: str,  # 主队名称
        away_team_name: str,  # 客队名称
        home_score: str,  # 主队得分
        away_score: str,  # 客队得分
        competition_stage_desc: str,  # 比赛阶段描述
        match_status: str,  # 比赛状态：未开始/进行中/已结束
    ):
        self.game_id = game_id
        self.home_team_name = home_team_name
        self.away_team_name = away_team_name
        self.home_score = home_score
        self.away_score = away_score
        self.competition_stage_desc = competition_stage_desc
        self.match_status = match_status  # 比赛状态：未开始/进行中/已结束

    def __repr__(self):
        return (
            f"GameInfo(game_id={self.game_id}, "
            f"{self.away_team_name} vs {self.home_team_name}, "
            f"status={self.match_status})"
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "game_id": self.game_id,
            "home_team_name": self.home_team_name,
            "away_team_name": self.away_team_name,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "competition_stage_desc": self.competition_stage_desc,
            "match_status": self.match_status,
        }


class Task:
    """任务数据模型"""

    def __init__(
        self,
        task_id: str,
        game_info: GameInfo,
        status: TaskStatus = TaskStatus.PENDING,
        create_time: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[dict] = None,
        result: Optional[dict] = None,
        error_msg: Optional[str] = None,
    ):
        self.task_id = task_id
        self.game_info = game_info
        self.status = status
        self.create_time = create_time or datetime.now()
        self.start_time = start_time
        self.end_time = end_time
        self.config = config or {}
        self.result = result or {}
        self.error_msg = error_msg

    def __repr__(self):
        return (
            f"Task(task_id={self.task_id}, "
            f"game_id={self.game_info.game_id}, "
            f"status={self.status.value})"
        )

    def to_dict(self):
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "game_info": self.game_info.to_dict(),
            "status": self.status.value,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "config": self.config,
            "result": self.result,
            "error_msg": self.error_msg,
        }
