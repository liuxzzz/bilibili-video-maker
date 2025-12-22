"""
内容采集器

负责使用无头浏览器访问虎扑网站，获取比赛信息内容。
"""

import time
import os
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from src.schedule.models import GameInfo

# 设置环境变量，禁用 Playwright 的 asyncio 事件循环检查
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "0"


class ContentAcquirer:
    """内容采集器 - 负责访问网页并采集内容"""

    def __init__(self, headless: bool = True):
        """
        初始化内容采集器

        Args:
            headless: 是否使用无头模式，默认为True
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._lock = threading.Lock()
        self._playwright_thread: Optional[threading.Thread] = None
        self._use_thread = False  # 标记是否使用线程模式
        logger.info(f"内容采集器初始化完成 (headless={headless})")

    def acquire_content(
        self,
        game_info: GameInfo,
    ) -> dict:

        print(game_info, "game_info.game_id")

        with sync_playwright() as playwright:

            # 1. 启动浏览器打开页面
            browser = playwright.chromium.launch(headless=self.headless)

            maker_sort = 0

            # 确保视频保存目录存在
            video_dir = Path("materials/videos")
            video_dir.mkdir(parents=True, exist_ok=True)

            # 配置为 iPhone SE 移动端设备
            # iPhone SE 规格: 375x667 分辨率, 2x 设备像素比
            context = browser.new_context(
                viewport={
                    "width": 375,
                    "height": 667,
                },
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                device_scale_factor=2,  # Retina 屏幕
                is_mobile=True,
                has_touch=True,
            )

            page = context.new_page()

            # 用于存储捕获的 API URL
            captured_api_urls = []

            # 监听网络请求，只捕获特定 API 的 URL
            def handle_request(request):
                # 只处理包含 getCurAndSubNodeByBizKey 的请求
                if "getCurAndSubNodeByBizKey" in request.url:
                    logger.info(f"捕获到目标 API URL: {request.url}")
                    captured_api_urls.append(request.url)

            page.on("request", handle_request)

            page.goto("https://m.hupu.com/nba/schedule")
            page.wait_for_load_state("networkidle")

            # 2. 点击比赛id来跳转新页面
            # HTML 结构：<div data-match="1405864802949005312" class="match-item">...</div>
            logger.info(f"开始查找比赛 ID: {game_info.match_id}")

            # 等待页面完全加载
            time.sleep(2)

            # 根据 data-match 属性定位比赛元素
            match_selector = f'div.match-item[data-match="{game_info.match_id}"]'
            match_element = page.locator(match_selector)

            # 检查元素是否存在
            count = match_element.count()
            logger.info(f"找到匹配的比赛元素数量: {count}")

            if count > 0:
                # 滚动到元素位置，确保可见
                match_element.first.scroll_into_view_if_needed()
                time.sleep(0.5)

                logger.info(
                    f"正在点击比赛: {game_info.away_team_name} vs {game_info.home_team_name}"
                )

                # 点击比赛元素，等待导航到新页面
                with page.expect_navigation(timeout=30000):
                    match_element.first.click()

                # 等待新页面加载完成
                page.wait_for_load_state("networkidle")
                logger.info(f"已跳转到比赛详情页: {page.url}")

                # 等待内容加载
                time.sleep(2)

            # 检查是否捕获到目标 API URL
            logger.info(f"共捕获到 {len(captured_api_urls)} 个 API URL")

            modified_api_data = []

            if captured_api_urls:
                import requests
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

                for original_url in captured_api_urls:
                    try:
                        logger.info(f"原始 URL: {original_url}")

                        # 解析 URL
                        parsed = urlparse(original_url)
                        params = parse_qs(parsed.query)

                        # 修改 pageSize 参数
                        params["pageSize"] = ["50"]  # parse_qs 返回列表，所以用列表赋值

                        # 重新构建 URL
                        new_query = urlencode(params, doseq=True)
                        modified_url = urlunparse(
                            (
                                parsed.scheme,
                                parsed.netloc,
                                parsed.path,
                                parsed.params,
                                new_query,
                                parsed.fragment,
                            )
                        )

                        logger.info(f"修改后 URL: {modified_url}")

                        # 请求修改后的 API
                        logger.info("正在请求修改后的 API...")
                        response = requests.get(modified_url, timeout=30)
                        response.raise_for_status()

                        # 获取 JSON 数据
                        data = response.json()

                        modified_api_data.append(
                            {
                                "original_url": original_url,
                                "modified_url": modified_url,
                                "status_code": response.status_code,
                                "data": data,
                            }
                        )

                        logger.info(f"成功获取 API 数据，状态码: {response.status_code}")
                        logger.info(f"返回数据: {data}")

                    except Exception as e:
                        logger.error(f"请求修改后的 API 失败: {e}", exc_info=True)
            else:
                logger.warning("未捕获到目标 API URL")

            time.sleep(300)

            return {
                "content": page.content(),
                "modified_api_data": modified_api_data,
                "success": len(modified_api_data) > 0,
            }
