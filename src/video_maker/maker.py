"""
视频生成器

负责将采集到的内容生成完整的视频内容。
包括视频预处理（帧数转换、格式转换等）、视频合成等功能。
"""

import ffmpeg
import json
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger
from src.utils.video_processor import VideoProcessor


class VideoMaker:
    """视频生成器"""

    def __init__(self):
        """初始化视频生成器"""
        logger.info("视频生成器初始化完成")

    def generate_video(self, content: Dict[str, Any]) -> Optional[str]:
        """
        生成视频

        Args:
            content: 内容字典，包含采集到的数据
                - video_path: 原始视频路径
                - modified_api_data: API数据
                - success: 是否成功

        Returns:
            Optional[str]: 处理后的视频路径，如果失败返回None
        """
        video_path = content.get("video_path")
        if not video_path:
            logger.error("内容中未找到视频路径")
            return None

        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"视频文件不存在: {video_path}")
            return None

        logger.info(f"开始处理视频: {video_path}")

        # 用于存储中间文件路径，处理成功后删除
        intermediate_files = []

        try:
            # 1. 裁剪视频前6秒
            trimmed_video_path = VideoProcessor.trim_video(video_path, start_time=6)
            if not trimmed_video_path:
                logger.error("视频裁剪失败")
                return None
            intermediate_files.append(trimmed_video_path)

            # 2. 裁切视频，将头部120px的区域裁切掉
            cropped_video_path = VideoProcessor.crop_video(trimmed_video_path, crop_top=120)
            if not cropped_video_path:
                logger.error("视频裁切失败")
                return None
            intermediate_files.append(cropped_video_path)

            # 3. 将视频转换为60帧
            processed_video_path = VideoProcessor.convert_to_60fps(cropped_video_path)
            if not processed_video_path:
                logger.error("视频帧数转换失败")
                return None
            intermediate_files.append(processed_video_path)

            # 4. 将音频添加到视频中
            audio_path = content.get("audio_path") or Path("materials/audio/bgm.mp3")
            final_video_path = VideoProcessor.add_audio_to_video(processed_video_path, audio_path)
            if not final_video_path:
                logger.error("音频合并失败")
                return None

            # 处理成功，删除中间文件
            VideoProcessor.cleanup_intermediate_files(intermediate_files)

            logger.info(f"视频处理完成: {final_video_path}")
            return str(final_video_path)

        except Exception as e:
            logger.error(f"视频生成失败: {e}", exc_info=True)
            return None
