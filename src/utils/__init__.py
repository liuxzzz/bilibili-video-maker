"""
工具模块

提供各种通用工具函数。
"""

__version__ = "0.1.0"

from .llm_client import call_llm, LLMClient

__all__ = ["call_llm", "LLMClient"]
