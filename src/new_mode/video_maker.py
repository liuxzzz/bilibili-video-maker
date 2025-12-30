"""
新模式视频生成器

负责录制视频并生成完整的视频内容。
包括视频录制、视频预处理（帧数转换、格式转换等）、视频合成等功能。
"""

import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.utils.video_processor import VideoProcessor

# 设置环境变量，禁用 Playwright 的 asyncio 事件循环检查
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "0"


class NewVideoMaker:
    """新模式视频生成器"""

    def __init__(self, headless: bool = False):
        """
        初始化视频生成器

        Args:
            headless: 是否使用无头浏览器模式，默认为True
        """
        self.headless = headless
        logger.info(f"新模式视频生成器初始化完成 (headless={headless})")

    def generate_video(self, content: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        生成视频

        Args:
            content: 内容字典，包含采集到的数据
                - json_data: 过滤后的JSON数据列表
                - success: 是否成功

        Returns:
            Optional[List[Dict[str, Any]]]: 处理后的视频信息列表，每个元素包含：
                - video_path: 视频文件路径
                - handle_json_data: 对应的原始数据信息
            如果失败返回None
        """
        if not content.get("success", False):
            logger.error("内容获取失败，无法生成视频")
            return None

        json_data = content.get("json_data", [])
        if not json_data:
            logger.error("内容中未找到JSON数据")
            return None

        # 提取所有需要录制的链接
        video_urls = []
        for item in json_data:
            handle_json_data = item.get("handle_json_data")
            if handle_json_data and handle_json_data.get("url"):
                video_urls.append(handle_json_data)

        if not video_urls:
            logger.warning("未找到需要录制的视频链接")
            return None

        logger.info(f"找到 {len(video_urls)} 个需要录制的视频链接")

        # 确保视频保存目录存在
        video_dir = Path("materials/videos")
        video_dir.mkdir(parents=True, exist_ok=True)

        video_results = []

        # 为每个链接录制视频并处理
        for idx, handle_data in enumerate(video_urls, 1):
            url = handle_data.get("url")
            title = handle_data.get("title", f"video_{idx}")
            item_id = handle_data.get("itemId", f"item_{idx}")

            logger.info(f"开始处理视频 {idx}/{len(video_urls)}: {title}")
            logger.info(f"录制URL: {url}")

            # 1. 录制视频
            raw_video_path = self._record_video(url, item_id, video_dir)
            if not raw_video_path:
                logger.error(f"视频录制失败: {title}")
                continue

            logger.info(f"视频录制成功: {raw_video_path}")

            # 2. 处理视频（裁切头部区域 + 添加背景音乐）
            logger.info(f"开始处理视频 {idx}/{len(video_urls)}: 裁切和添加音频")
            processed_video_path = self.process_video(raw_video_path, crop_top=200)

            if processed_video_path:
                # 保存视频路径和对应的 handle_json_data
                video_results.append(
                    {"video_path": processed_video_path, "handle_json_data": handle_data}
                )
                logger.info(f"视频处理完成: {processed_video_path}")

                # 删除原始录制的视频文件（已经处理完成）
                try:
                    Path(raw_video_path).unlink()
                    logger.info(f"已删除原始录制文件: {raw_video_path}")
                except Exception as e:
                    logger.warning(f"删除原始录制文件失败: {e}")
            else:
                logger.error(f"视频处理失败: {title}")
                # 处理失败，但至少保留原始录制的视频
                video_results.append(
                    {"video_path": raw_video_path, "handle_json_data": handle_data}
                )

        if not video_results:
            logger.error("所有视频录制和处理都失败了")
            return None

        logger.info(f"共成功处理 {len(video_results)} 个视频")
        return video_results

    def generate_single_video(self, handle_json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成单个视频

        Args:
            handle_json_data: 单个视频的原始数据信息，包含：
                - url: 要录制的页面URL
                - title: 视频标题
                - itemId: 项目ID

        Returns:
            Optional[Dict[str, Any]]: 处理后的视频信息，包含：
                - video_path: 视频文件路径
                - handle_json_data: 对应的原始数据信息
            如果失败返回None
        """
        if not handle_json_data:
            logger.error("handle_json_data 为空，无法生成视频")
            return None

        url = handle_json_data.get("url")
        title = handle_json_data.get("title", "video")
        item_id = handle_json_data.get("itemId", "item")

        if not url:
            logger.error("未找到视频URL，无法生成视频")
            return None

        logger.info(f"开始生成单个视频: {title}")
        logger.info(f"录制URL: {url}")

        # 确保视频保存目录存在
        video_dir = Path("materials/videos")
        video_dir.mkdir(parents=True, exist_ok=True)

        # 1. 录制视频
        raw_video_path = self._record_video(url, item_id, video_dir)
        if not raw_video_path:
            logger.error(f"视频录制失败: {title}")
            return None

        logger.info(f"视频录制成功: {raw_video_path}")

        # 2. 处理视频（裁切头部区域 + 添加背景音乐）
        logger.info(f"开始处理视频: 裁切和添加音频")
        processed_video_path = self.process_video(raw_video_path, crop_top=200)

        if processed_video_path:
            logger.info(f"视频处理完成: {processed_video_path}")

            # 删除原始录制的视频文件（已经处理完成）
            try:
                Path(raw_video_path).unlink()
                logger.info(f"已删除原始录制文件: {raw_video_path}")
            except Exception as e:
                logger.warning(f"删除原始录制文件失败: {e}")

            return {"video_path": processed_video_path, "handle_json_data": handle_json_data}
        else:
            logger.error(f"视频处理失败: {title}")
            # 处理失败，但至少保留原始录制的视频
            return {"video_path": raw_video_path, "handle_json_data": handle_json_data}

    def _record_video(self, url: str, item_id: str, video_dir: Path) -> Optional[str]:
        """
        录制单个视频

        Args:
            url: 要录制的页面URL
            item_id: 项目ID，用于生成文件名
            video_dir: 视频保存目录

        Returns:
            Optional[str]: 录制成功的视频路径，如果失败返回None
        """
        try:
            with sync_playwright() as playwright:
                # 1. 启动浏览器
                browser = playwright.chromium.launch(headless=self.headless)
                logger.info("浏览器启动成功")

                # 生成视频文件名（使用项目ID和时间戳）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_filename = f"{item_id}_{timestamp}.webm"
                final_video_path: Optional[Path] = None

                # 配置为 iPhone SE 移动端设备（与NBA模块保持一致）
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

                # 2. 打开目标链接
                logger.info(f"正在打开目标链接: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                logger.info(f"页面加载完成: {page.url}")

                # 等待页面完全加载
                time.sleep(2)

                # 3. 视频生成前的准备工作：保证评论内容完整显示
                logger.info("开始修改页面元素样式，使评论内容完整显示...")
                try:
                    page.evaluate(
                        """
                        () => {
                            // 将所有 score-group-comment 的 p 元素高度设为 auto
                            const commentParagraphs = document.querySelectorAll('p.score-group_score-group-comment__0jLQY');
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
                    logger.warning(f"修改页面元素样式失败（可能页面结构不同）: {e}")

                # 4. 视频录制过程中的平滑向下滚动
                logger.info("开始执行鼠标滚轮平滑滑动（60fps，40秒）...")
                try:
                    # 获取页面尺寸
                    viewport_size = page.viewport_size
                    page_width = viewport_size["width"]
                    page_height = viewport_size["height"]
                    center_x = page_width // 2
                    center_y = page_height // 2
                    page.mouse.move(center_x, center_y)
                    logger.info(
                        f"页面尺寸: {page_width}x{page_height}, 中心点: ({center_x}, {center_y})"
                    )

                    # 获取 body 的总高度
                    body_height = page.evaluate("() => document.body.scrollHeight")
                    viewport_height = page_height
                    total_scrollable_distance = body_height - viewport_height
                    logger.info(
                        f"Body总高度: {body_height}px, 视口高度: {viewport_height}px, "
                        f"可滚动距离: {total_scrollable_distance}px"
                    )

                    # 平滑滚动配置：60fps，40秒
                    total_duration = 40  # 总时长（秒）
                    fps = 60  # 帧率
                    total_frames = total_duration * fps  # 2400 帧

                    # 计算每一帧需要滚动的距离
                    delta_per_frame = total_scrollable_distance / total_frames
                    logger.info(
                        f"平滑滚动配置: 时长={total_duration}s, 帧率={fps}, "
                        f"总帧数={total_frames}, 每帧滚动={delta_per_frame:.3f}px, "
                        f"总滚动距离={total_scrollable_distance:.1f}px"
                    )

                    frame_interval = 1.0 / fps
                    start_time = time.time()

                    for frame in range(total_frames):
                        # 执行一次小幅度滚动（正值向下）
                        page.mouse.wheel(0, delta_per_frame)

                        # 按理想帧时间对齐，保证整体接近 60fps 和 40s
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

                    logger.info("鼠标滚轮平滑滑动完成（约40秒，60fps）")
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
                        return None
                except Exception as e:
                    logger.error(f"处理录制视频文件时出错: {e}", exc_info=True)
                    return None

                try:
                    browser.close()
                except Exception as e:
                    logger.warning(f"关闭浏览器实例时出错: {e}")

                return str(final_video_path) if final_video_path else None

        except Exception as e:
            logger.error(f"录制视频时发生错误: {e}", exc_info=True)
            return None

    def process_video(self, video_path: str, crop_top: int = 200) -> Optional[str]:
        """
        处理视频

        Args:
            video_path: 视频路径
            crop_top: 裁切顶部像素数，默认200px

        handle:
            1. 裁剪视频头部指定px的区域
            2. 将音频添加到视频中

        Returns:
            Optional[str]: 处理后的视频路径，如果失败返回None
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"视频文件不存在: {video_path}")
            return None

        logger.info(f"开始处理视频: {video_path}")

        # 用于存储中间文件路径，处理成功后删除
        intermediate_files = []

        try:
            # 1. 裁切视频，将头部指定px的区域裁切掉
            cropped_video_path = VideoProcessor.crop_video(video_path, crop_top=crop_top)
            if not cropped_video_path:
                logger.error("视频裁切失败")
                return None
            intermediate_files.append(cropped_video_path)

            # 2. 将音频添加到视频中
            audio_path = Path("materials/audio/bgm.mp3")
            final_video_path = VideoProcessor.add_audio_to_video(cropped_video_path, audio_path)
            if not final_video_path:
                logger.error("音频合并失败")
                return None

            # 处理成功，删除中间文件
            VideoProcessor.cleanup_intermediate_files(intermediate_files)

            logger.info(f"视频处理完成: {final_video_path}")
            return str(final_video_path)

        except Exception as e:
            logger.error(f"视频处理失败: {e}", exc_info=True)
            return None
