"""
新模式视频制作模块

这是一个新的视频制作模式，与NBA模式类似但内容不同。
此模式只支持一次性运行，不支持定时任务。
"""

from .runner import NewModeRunner

__all__ = ["NewModeRunner"]
