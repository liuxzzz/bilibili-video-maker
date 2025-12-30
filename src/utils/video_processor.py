"""
视频处理工具模块

提供视频处理的通用功能，可在多个模块中复用。
"""

import ffmpeg
from pathlib import Path
from typing import Optional

from loguru import logger


class VideoProcessor:
    """视频处理工具类"""

    @staticmethod
    def trim_video(input_path: Path, start_time: float = 6.0) -> Optional[Path]:
        """
        裁剪视频，移除开头的指定秒数

        Args:
            input_path: 输入视频路径
            start_time: 开始时间（秒），默认为6秒，即移除前6秒

        Returns:
            Optional[Path]: 裁剪后的视频路径，如果失败返回None
        """
        try:
            logger.info(f"开始裁剪视频前 {start_time} 秒: {input_path}")

            # 获取视频信息以确定时长
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe.get("format", {}).get("duration", 0))

            if duration == 0:
                logger.error("无法获取视频时长")
                return None

            if start_time >= duration:
                logger.error(f"开始时间 {start_time} 秒大于等于视频时长 {duration} 秒")
                return None

            logger.info(f"视频时长: {duration} 秒, 裁剪后: {duration - start_time} 秒")

            # 生成输出文件路径（添加 _trimmed 后缀）
            output_path = input_path.parent / f"{input_path.stem}_trimmed{input_path.suffix}"

            # 使用 ffmpeg 的 ss 参数从指定时间开始
            stream = ffmpeg.input(str(input_path), ss=start_time)
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vcodec="copy",  # 使用 copy 编码，避免重新编码，速度更快
                acodec="copy",  # 音频也使用 copy
            )

            # 执行裁剪，覆盖已存在的输出文件
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"视频已成功裁剪: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg 裁剪失败: {e}")
            if e.stderr:
                logger.error(f"FFmpeg 错误信息: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"视频裁剪失败: {e}", exc_info=True)
            return None

    @staticmethod
    def crop_video(input_path: Path, crop_top: int = 50) -> Optional[Path]:
        """
        裁切视频，移除头部指定像素区域

        Args:
            input_path: 输入视频路径
            crop_top: 要裁切的顶部像素数，默认为50

        Returns:
            Optional[Path]: 裁切后的视频路径，如果失败返回None
        """
        try:
            logger.info(f"开始裁切视频头部 {crop_top}px: {input_path}")

            # 获取视频信息以确定尺寸
            probe = ffmpeg.probe(str(input_path))
            video_stream = next(
                (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
            )

            if not video_stream:
                logger.error("未找到视频流")
                return None

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            if width == 0 or height == 0:
                logger.error(f"无法获取视频尺寸: {width}x{height}")
                return None

            if crop_top >= height:
                logger.error(f"裁切高度 {crop_top}px 大于等于视频高度 {height}px")
                return None

            # 计算裁切后的高度
            new_height = height - crop_top

            logger.info(f"视频尺寸: {width}x{height}, 裁切后: {width}x{new_height}")

            # 生成输出文件路径（转换为 MP4 格式，添加 _cropped 后缀）
            output_path = input_path.parent / f"{input_path.stem}_cropped.mp4"

            # 使用 ffmpeg 的 crop 滤镜裁切视频
            # crop=width:height:x:y
            stream = ffmpeg.input(str(input_path))
            stream = ffmpeg.filter(stream, "crop", width, new_height, 0, crop_top)
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vcodec="libx264",  # 使用 H.264 编码（必须重新编码，因为使用了滤镜）
                preset="medium",  # 编码速度和质量平衡
                crf=23,  # 质量控制（18-28，值越小质量越高）
                pix_fmt="yuv420p",  # 像素格式，确保兼容性
            )

            # 执行裁切，覆盖已存在的输出文件
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"视频已成功裁切: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg 裁切失败: {e}")
            if e.stderr:
                logger.error(f"FFmpeg 错误信息: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"视频裁切失败: {e}", exc_info=True)
            return None

    @staticmethod
    def convert_to_60fps(input_path: Path) -> Optional[Path]:
        """
        将视频转换为60帧

        Args:
            input_path: 输入视频路径

        Returns:
            Optional[Path]: 输出视频路径，如果失败返回None
        """
        try:
            logger.info(f"开始将视频转换为60帧: {input_path}")

            # 生成输出文件路径（转换为 MP4 格式，添加 _60fps 后缀）
            output_path = input_path.parent / f"{input_path.stem}_60fps.mp4"

            # 使用 ffmpeg 将视频转换为60帧
            stream = ffmpeg.input(str(input_path))
            stream = ffmpeg.filter(stream, "fps", fps=60)
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vcodec="libx264",  # 使用 H.264 编码
                preset="medium",  # 编码速度和质量平衡
                crf=23,  # 质量控制
                pix_fmt="yuv420p",  # 像素格式，确保兼容性
            )

            # 执行转换，覆盖已存在的输出文件
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"视频已成功转换为60帧: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg 处理失败: {e}")
            if e.stderr:
                logger.error(f"FFmpeg 错误信息: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"视频帧数转换失败: {e}", exc_info=True)
            return None

    @staticmethod
    def add_audio_to_video(video_path: Path, audio_path: str | Path) -> Optional[Path]:
        """
        将音频添加到视频中

        Args:
            video_path: 输入视频路径
            audio_path: 音频文件路径（可以是字符串或 Path 对象）

        Returns:
            Optional[Path]: 合并后的视频路径，如果失败返回None
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                logger.warning(f"音频文件不存在: {audio_path}，跳过音频合并")
                return video_path

            logger.info(f"开始将音频添加到视频: 视频={video_path}, 音频={audio_path}")

            # 获取视频时长，用于截取音频
            video_probe = ffmpeg.probe(str(video_path))
            video_duration = float(video_probe.get("format", {}).get("duration", 0))

            if video_duration == 0:
                logger.error("无法获取视频时长")
                return None

            logger.info(f"视频时长: {video_duration} 秒")

            # 生成输出文件路径（移除 _60fps 后缀，添加 _final 后缀）
            output_path = video_path.parent / f"{video_path.stem.replace('_60fps', '')}_final.mp4"

            # 输入视频和音频
            video_input = ffmpeg.input(str(video_path))
            audio_input = ffmpeg.input(str(audio_path), t=video_duration)  # 截取音频到视频时长

            # 合并视频和音频
            stream = ffmpeg.output(
                video_input,
                audio_input,
                str(output_path),
                vcodec="copy",  # 视频流直接复制，不重新编码
                acodec="aac",  # 音频编码为 AAC
                shortest=None,  # 以最短的流为准
            )

            # 执行合并，覆盖已存在的输出文件
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"音频已成功添加到视频: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg 音频合并失败: {e}")
            if e.stderr:
                logger.error(f"FFmpeg 错误信息: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"音频合并失败: {e}", exc_info=True)
            return None

    @staticmethod
    def cleanup_intermediate_files(file_paths: list[Path]) -> None:
        """
        删除中间处理过程中生成的临时文件

        Args:
            file_paths: 要删除的文件路径列表
        """
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"已删除中间文件: {file_path}")
                else:
                    logger.debug(f"中间文件不存在，跳过删除: {file_path}")
            except Exception as e:
                logger.warning(f"删除中间文件失败: {file_path}, 错误: {e}")
