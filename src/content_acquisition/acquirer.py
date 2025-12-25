"""
内容采集器

负责使用无头浏览器访问虎扑网站，获取比赛信息内容。
"""

import time
import os
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

            # 生成视频文件名（使用比赛ID和时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"{game_info.match_id}_{timestamp}.webm"
            final_video_path: Optional[Path] = None

            # 配置为 iPhone SE 移动端设备
            # iPhone SE 规格: 375x667 分辨率, 2x 设备像素比
            context = browser.new_context(
                viewport={
                    "width": 430,
                    "height": 932,
                },
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                device_scale_factor=3,  # Retina 屏幕
                is_mobile=True,
                has_touch=True,
                # 开启视频录制
                record_video_dir=str(video_dir),
                # 录制分辨率（约等于 viewport * device_scale_factor）
                record_video_size={"width": 860, "height": 1864},
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

                    except Exception as e:
                        logger.error(f"请求修改后的 API 失败: {e}", exc_info=True)
            else:
                logger.warning("未捕获到目标 API URL")

            # 3. 视频生成前的准备工作：保证评论内容完整显示
            logger.info("开始修改页面元素样式，使评论内容完整显示...")
            try:
                page.evaluate(
                    """
                    () => {
                        // 将所有 score-group-comment 的 p 元素高度设为 auto
                        const commentParagraphs = document.querySelectorAll('p.score-group-comment');
                        commentParagraphs.forEach(p => {
                            p.style.height = 'auto';

                            // 将子 span 的 white-space 设为 normal，允许正常换行
                            const spans = p.querySelectorAll('span');
                            spans.forEach(span => {
                                span.style.whiteSpace = 'normal';
                            });
                        });
                    }
                """
                )
                logger.info("页面元素样式修改完成")
                time.sleep(0.5)  # 等待样式应用
            except Exception as e:
                logger.error(f"修改页面元素样式失败: {e}", exc_info=True)

            # 4. 视频录制过程中的平滑向下滚动
            logger.info("开始执行鼠标滚轮平滑滑动（60fps，50秒）...")
            try:
                # 获取页面尺寸，方便后续若需扩展为基于高度的滚动
                viewport_size = page.viewport_size
                page_width = viewport_size["width"]
                page_height = viewport_size["height"]
                center_x = page_width // 2
                center_y = page_height // 2
                page.mouse.move(center_x, center_y)
                logger.info(
                    f"页面尺寸: {page_width}x{page_height}, 中心点: ({center_x}, {center_y})"
                )

                # 平滑滚动配置：60fps，50秒
                total_duration = 50  # 总时长（秒）
                fps = 60  # 帧率
                total_frames = total_duration * fps  # 3000 帧

                # 单帧滚动幅度保持与之前类似（约 0.98 像素），时间拉长，总距离更多
                base_total_distance_30s = 1770.0
                base_frames_30s = 30 * 60
                delta_per_frame = base_total_distance_30s / base_frames_30s  # ≈ 0.98

                total_scroll_distance = delta_per_frame * total_frames
                logger.info(
                    f"平滑滚动配置: 时长={total_duration}s, 帧率={fps}, "
                    f"总帧数={total_frames}, 每帧滚动={delta_per_frame:.3f}px, "
                    f"预期总滚动距离≈{total_scroll_distance:.1f}px"
                )

                frame_interval = 1.0 / fps
                start_time = time.time()

                for frame in range(total_frames):
                    # 执行一次小幅度滚动（正值向下）
                    page.mouse.wheel(0, delta_per_frame)

                    # 按理想帧时间对齐，保证整体接近 60fps 和 50s
                    target_time = start_time + (frame + 1) * frame_interval
                    now = time.time()
                    sleep_time = target_time - now
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    # 每 2 秒输出一次进度日志（约每 120 帧）
                    if frame % (fps * 2) == 0:
                        progress = (frame / total_frames) * 100
                        logger.info(
                            f"滚动进度: {progress:.1f}% "
                            f"({frame}/{total_frames} 帧，累计滚动约 {delta_per_frame * frame:.1f} 像素)"
                        )

                logger.info("鼠标滚轮平滑滑动完成（约50秒，60fps）")
                time.sleep(1.0)  # 滚动结束后稍等，确保内容稳定
            except Exception as e:
                logger.error(f"平滑滚动过程出错: {e}", exc_info=True)

            # 5. 关闭页面和上下文，保存视频
            logger.info("开始关闭页面和浏览器上下文，并保存视频文件...")
            try:
                page.close()
            except Exception as e:
                logger.warning(f"关闭页面时出现问题: {e}")

            try:
                context.close()
            except Exception as e:
                logger.warning(f"关闭浏览器上下文时出现问题: {e}")

            # 等待视频文件写入完成
            time.sleep(2)

            try:
                video_files = list(video_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"检测到录制视频文件: {latest_video}")

                    final_video_path = video_dir / video_filename
                    if latest_video != final_video_path:
                        latest_video.rename(final_video_path)
                        logger.info(f"视频文件已重命名为: {final_video_path}")
                    else:
                        logger.info(f"视频文件已使用目标文件名保存: {final_video_path}")
                else:
                    logger.warning("未在视频目录中找到任何 .webm 文件")
            except Exception as e:
                logger.error(f"处理录制视频文件时出错: {e}", exc_info=True)

            try:
                browser.close()
            except Exception as e:
                logger.warning(f"关闭浏览器实例时出错: {e}")

            return {
                "modified_api_data": modified_api_data,
                "success": len(modified_api_data) > 0,
                "video_path": str(final_video_path) if final_video_path else None,
            }
