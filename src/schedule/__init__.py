"""
任务调度模块

作为系统的核心管家，负责统领全局，协调和管理整个视频生成任务的工作流程。
包括任务生命周期管理、工作流编排、状态监控、异常处理等功能。
"""

from .models import GameInfo, Task, TaskStatus
from .scheduler import TaskScheduler
from .game_fetcher import GameFetcher
from .task_store import TaskStore
from .cron_scheduler import CronScheduler

__version__ = "0.1.0"
__all__ = [
    "TaskScheduler",
    "Task",
    "GameInfo",
    "TaskStatus",
    "GameFetcher",
    "TaskStore",
    "CronScheduler",
]
