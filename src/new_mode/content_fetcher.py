"""
新模式内容获取器

负责使用无头浏览器访问虎扑活动页面，获取内容数据。
"""

import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# 设置环境变量，禁用 Playwright 的 asyncio 事件循环检查
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "0"


class NewContentFetcher:
    """新模式内容获取器 - 负责访问网页并采集内容"""

    def __init__(self, headless: bool = True):
        """
        初始化内容获取器

        Args:
            headless: 是否使用无头模式，默认为True
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        logger.info(f"新模式内容获取器初始化完成 (headless={headless})")

    def fetch_content(self) -> Dict[str, Any]:
        """
        获取内容数据

        首先打开 https://bbsactivity.hupu.com/pc-viewer/index.html 页面，
        然后进行后续的内容采集操作。

        Returns:
            包含采集到的内容数据的字典
        """
        logger.info("开始获取新模式内容数据")

        try:
            with sync_playwright() as playwright:
                # 1. 启动浏览器
                browser = playwright.chromium.launch(headless=self.headless)
                self.browser = browser
                logger.info("浏览器启动成功")

                # 2. 创建浏览器上下文（PC端配置）
                context = browser.new_context(
                    viewport={
                        "width": 1920,
                        "height": 1080,
                    },
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                self.context = context
                logger.info("浏览器上下文创建成功")

                # 3. 创建新页面
                page = context.new_page()
                self.page = page

                # 4. 打开目标链接
                target_url = "https://bbsactivity.hupu.com/pc-viewer/index.html?t=https%3A%2F%2Fm.hupu.com%2Fscore-home"
                logger.info(f"正在打开目标链接: {target_url}")
                page.goto(target_url, wait_until="networkidle", timeout=60000)
                logger.info(f"页面加载完成: {page.url}")

                # 等待页面完全加载
                time.sleep(2)

                # 5. 获取页面基本信息
                page_title = page.title()
                page_url = page.url
                logger.info(f"页面标题: {page_title}")
                logger.info(f"当前URL: {page_url}")

                # 6. 通过 HTTP 获取页面 HTML 内容
                score_home_url = "https://m.hupu.com/score-home"
                logger.info(f"正在通过 HTTP 获取页面内容: {score_home_url}")

                html_content = None
                response = requests.get(score_home_url, timeout=30)
                response.raise_for_status()

                # 设置正确的编码
                response.encoding = response.apparent_encoding or "utf-8"
                html_content = response.text

                logger.info(f"成功获取 HTML 内容，长度: {len(html_content)} 字符")

                # 7. 从 HTML 中提取 JSON 数据
                json_data = self._extract_json_from_html(html_content)

                # 从json中提取有效信息。
                # item - scoreCountNum 从item中提取出评分数量用于筛选
                filtered_json_data = self._filter_json_data(json_data)

                # 8. 采集内容（这里可以根据实际需求扩展）
                content_data = {
                    "url": page_url,
                    "title": page_title,
                    "json_data": filtered_json_data,
                    "score_home_url": score_home_url,
                    "timestamp": time.time(),
                    "success": True,
                }

                logger.info("内容获取完成")

                # 清理资源（在返回前清理，with 块会自动关闭 playwright）
                self._cleanup()

                return content_data

        except Exception as e:
            logger.error(f"获取内容时发生错误: {e}", exc_info=True)
            # 确保在异常时也清理资源
            self._cleanup()
            return {
                "success": False,
                "error": str(e),
                "timestamp": time.time(),
            }

    def _extract_json_from_html(self, html: str) -> Optional[Dict[str, Any]]:
        """
        从 HTML 中提取 JSON 数据（方法同 _parse_hupu_schedule，但不做日期处理）

        Args:
            html: HTML 内容

        Returns:
            Optional[Dict[str, Any]]: 提取的 JSON 数据，提取失败返回 None
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # 从 soup 中获取 script 标签，查找 __NEXT_DATA__
            next_data_script = soup.find("script", id="__NEXT_DATA__", type="application/json")

            if not next_data_script:
                logger.warning("未找到 __NEXT_DATA__ script 标签")
                return None

            # 从 script 标签中提取 JSON 数据
            json_text = next_data_script.get_text()
            json_data = json.loads(json_text)

            output_json_data = json_data.get("props", {}).get("pageProps", {}).get("list", [])

            return output_json_data

        except Exception as e:
            logger.error(f"从 HTML 中提取 JSON 数据失败: {e}", exc_info=True)
            return None

    def _cleanup(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            logger.info("浏览器资源清理完成")
        except Exception as e:
            logger.warning(f"清理浏览器资源时出现问题: {e}")

    def _filter_json_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从json中提取有效信息。
        """
        try:
            if not json_data:
                logger.warning("json_data 为空，无法筛选")
                return []

            # 筛选，只处理scoreCountNum > 1w的数据
            # 需要处理 None 值的情况，避免比较错误
            filtered_json_data = [
                item
                for item in json_data
                if item.get("item")
                and item.get("item").get("scoreCountNum") is not None
                and item.get("item").get("scoreCountNum") > 10000
            ]
            # filtered_json_data中新增一个handle_json_data 空字段，用于后续处理。
            # handle_json_data中包含一下字段：
            # scoreCountNum: 评分数量
            # title: 该内容的标题
            # url: 该内容用于录制的url
            # itemId: 该内容的id
            for item in filtered_json_data:
                # 安全获取数据，避免 None 值错误
                subject = item.get("subject")
                infoObj = item.get("item")

                if not subject or not infoObj:
                    logger.warning(f"跳过无效的 item，缺少 subject 或 item 字段")
                    continue

                bizNo = subject.get("bizNo")
                if not bizNo:
                    logger.warning(f"跳过无效的 item，缺少 bizNo")
                    continue

                handle_json_data = {
                    "scoreCountNum": infoObj.get("scoreCountNum"),
                    "title": infoObj.get("name"),
                    "url": f"https://m.hupu.com/score-list/common_first/{bizNo}",
                    "itemId": infoObj.get("itemId"),
                }
                item["handle_json_data"] = handle_json_data

            return filtered_json_data
        except Exception as e:
            logger.error(f"从json中提取有效信息失败: {e}", exc_info=True)
            return None
