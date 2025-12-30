"""
新模式运行器

负责执行新模式的视频制作流程。
此模式只支持一次性运行，不支持定时任务。
"""

from loguru import logger
from .content_fetcher import NewContentFetcher
from .video_maker import NewVideoMaker
from .publish_video import publish_video
from src.vide_publish import VideoPublisher
import json


class NewModeRunner:
    """新模式运行器"""

    def __init__(self, headless: bool = False):
        """
        初始化新模式运行器

        Args:
            headless: 是否使用无头浏览器模式，默认为True
        """
        logger.info("新模式运行器初始化开始")

        # 在初始化前获取B站登录凭证（从Chrome cookies）
        logger.info("正在从Chrome cookies获取B站登录凭证...")
        from src.utils import get_bilibili_credentials_from_chrome

        sessdata, bili_jct = get_bilibili_credentials_from_chrome()
        if sessdata and bili_jct:
            logger.info("成功从Chrome cookies获取B站登录凭证")
        else:
            logger.warning("未能从Chrome cookies获取完整凭证，将使用环境变量或默认值")

        # 初始化内容获取模块
        self.content_fetcher = NewContentFetcher(headless=headless)
        # 初始化视频生成模块
        self.video_maker = NewVideoMaker(headless=headless)
        # 初始化视频发布模块（传入从Chrome获取的凭证）
        self.video_publisher = VideoPublisher(sessdata=sessdata, bili_jct=bili_jct)
        logger.info("新模式运行器初始化完成")

    def run(self):
        """
        执行新模式的一次性运行流程

        工作流程：
        1. 获取内容数据
        2. 生成视频
        3. 发布视频
        """
        logger.info("=" * 80)
        logger.info("开始执行新模式视频制作流程")
        logger.info("=" * 80)

        try:
            # 1. 获取内容
            logger.info("步骤 1: 开始获取内容数据")
            content = self.content_fetcher.fetch_content()

            if not content.get("success", False):
                logger.error("内容获取失败，终止流程")
                return

            json_data = content.get("json_data", [])
            if not json_data:
                logger.error("内容中未找到JSON数据，终止流程")
                return

            # 提取所有需要处理的视频链接
            video_items = []
            for item in json_data:
                handle_json_data = item.get("handle_json_data")
                if handle_json_data and handle_json_data.get("url"):
                    video_items.append(handle_json_data)

            if not video_items:
                logger.warning("未找到需要处理的视频链接，终止流程")
                return

            logger.info(f"找到 {len(video_items)} 个需要处理的视频")

            # 2. 逐个生成视频并立即上传
            success_count = 0
            for idx, handle_json_data in enumerate(video_items, 1):
                logger.info("=" * 80)
                logger.info(
                    f"处理视频 {idx}/{len(video_items)}: {handle_json_data.get('title', '未知标题')}"
                )
                logger.info("=" * 80)

                # 2.1 生成视频
                logger.info(f"步骤 2.1: 开始生成视频 {idx}")
                video_result = self.video_maker.generate_single_video(handle_json_data)

                if not video_result:
                    logger.error(f"视频 {idx} 生成失败，跳过")
                    continue

                video_path = video_result.get("video_path")
                if not video_path:
                    logger.error(f"视频 {idx} 生成失败（无视频路径），跳过")
                    continue

                logger.info(f"视频 {idx} 生成成功: {video_path}")

                # 2.2 立即发布视频
                logger.info(f"步骤 2.2: 开始发布视频 {idx}")
                publish_success = publish_video(
                    video_path, self.video_publisher, handle_json_data=handle_json_data
                )

                if publish_success:
                    logger.info(f"视频 {idx} 发布成功")
                    success_count += 1
                else:
                    logger.warning(f"视频 {idx} 发布失败")

            logger.info("=" * 80)
            logger.info(
                f"新模式执行完成，共处理 {len(video_items)} 个视频，成功 {success_count} 个"
            )
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"新模式执行失败: {e}", exc_info=True)
            raise
