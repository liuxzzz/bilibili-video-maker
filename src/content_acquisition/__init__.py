"""
信息内容采集模块

负责操作无头浏览器访问虎扑网站，获取当前赛事的信息内容并保存起来。
包括无头浏览器管理、页面导航、内容提取、素材保存等功能。
"""

from .acquirer import ContentAcquirer

__all__ = ["ContentAcquirer"]
__version__ = "0.1.0"
