"""
大模型客户端

封装阿里云百炼API调用，提供简单易用的接口。
"""

import os
from typing import Optional

from loguru import logger
from openai import OpenAI


class LLMClient:
    """大模型客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus",
    ):
        """
        初始化大模型客户端

        Args:
            api_key: API密钥，如果不提供则从环境变量 DASHSCOPE_API_KEY 读取
            base_url: API基础URL，默认为阿里云百炼
            model: 模型名称，默认为 qwen-plus
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY，大模型调用可能失败")

        self.base_url = base_url
        self.model = model

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(f"大模型客户端初始化完成: model={model}")

    def call(
        self,
        user_content: str,
        system_content: Optional[str] = None,
        enable_search: bool = True,
        **kwargs,
    ) -> str:
        """
        调用大模型

        Args:
            user_content: 用户输入内容
            system_content: 系统提示词，默认为 None
            enable_search: 是否启用搜索，默认为 True
            **kwargs: 其他参数，会传递给 extra_body

        Returns:
            str: 模型返回的内容
        """
        try:
            messages = []
            if system_content:
                messages.append({"role": "system", "content": system_content})
            messages.append({"role": "user", "content": user_content})

            extra_body = {"enable_search": enable_search}
            extra_body.update(kwargs)

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_body=extra_body,
            )

            response_content = completion.choices[0].message.content
            logger.debug(f"大模型调用成功，返回内容长度: {len(response_content)}")
            return response_content

        except Exception as e:
            logger.error(f"大模型调用失败: {e}", exc_info=True)
            raise


# 全局客户端实例
_default_client: Optional[LLMClient] = None


def get_default_client() -> LLMClient:
    """获取默认的大模型客户端实例"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def call_llm(
    user_content: str,
    system_content: Optional[str] = None,
    enable_search: bool = True,
    model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    快速调用大模型的便捷函数

    Args:
        user_content: 用户输入内容
        system_content: 系统提示词，默认为 None
        enable_search: 是否启用搜索，默认为 True
        model: 模型名称，如果不提供则使用默认模型
        **kwargs: 其他参数

    Returns:
        str: 模型返回的内容
    """
    if model:
        # 如果指定了模型，创建临时客户端
        client = LLMClient(model=model)
        return client.call(user_content, system_content, enable_search, **kwargs)
    else:
        # 使用默认客户端
        client = get_default_client()
        return client.call(user_content, system_content, enable_search, **kwargs)
