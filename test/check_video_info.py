"""
检查视频文件信息
用于诊断B站上传失败问题
"""

import sys
import json
from pathlib import Path
import ffmpeg
from loguru import logger


def check_video_info(video_path: Path):
    """检查视频文件的详细信息"""
    logger.info(f"检查视频文件: {video_path}")
    logger.info("=" * 60)

    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return

    # 文件基本信息
    file_size = video_path.stat().st_size
    logger.info(f"文件大小: {file_size / (1024 * 1024):.2f} MB")

    try:
        # 使用 ffprobe 获取视频信息
        probe = ffmpeg.probe(str(video_path))

        # 格式信息
        format_info = probe.get("format", {})
        logger.info("\n格式信息:")
        logger.info(f"  格式名称: {format_info.get('format_name', 'N/A')}")
        logger.info(f"  格式长名称: {format_info.get('format_long_name', 'N/A')}")
        logger.info(f"  时长: {float(format_info.get('duration', 0)):.2f} 秒")
        logger.info(f"  比特率: {int(format_info.get('bit_rate', 0)) / 1000:.0f} kbps")

        # 视频流信息
        video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
        if video_streams:
            video = video_streams[0]
            logger.info("\n视频流信息:")
            logger.info(f"  编码格式: {video.get('codec_name', 'N/A')}")
            logger.info(f"  编码长名称: {video.get('codec_long_name', 'N/A')}")
            logger.info(f"  分辨率: {video.get('width', 0)}x{video.get('height', 0)}")
            logger.info(f"  帧率: {video.get('r_frame_rate', 'N/A')}")
            logger.info(f"  像素格式: {video.get('pix_fmt', 'N/A')}")
            logger.info(
                f"  比特率: {int(video.get('bit_rate', 0)) / 1000:.0f} kbps"
                if "bit_rate" in video
                else "  比特率: N/A"
            )

            # B站视频要求检查
            logger.info("\nB站视频要求检查:")
            width = video.get("width", 0)
            height = video.get("height", 0)
            duration = float(format_info.get("duration", 0))

            # 检查分辨率
            if width >= 640 and height >= 360:
                logger.info(f"  ✓ 分辨率符合要求 ({width}x{height} >= 640x360)")
            else:
                logger.warning(f"  ✗ 分辨率过小 ({width}x{height} < 640x360)")

            # 检查时长
            if 1 <= duration <= 7200:  # 1秒到2小时
                logger.info(f"  ✓ 时长符合要求 ({duration:.1f}秒)")
            else:
                logger.warning(f"  ✗ 时长不符合要求 ({duration:.1f}秒，应在1-7200秒之间)")

            # 检查文件大小
            max_size = 8 * 1024 * 1024 * 1024  # 8GB
            if file_size <= max_size:
                logger.info(f"  ✓ 文件大小符合要求 ({file_size / (1024 * 1024):.2f}MB <= 8GB)")
            else:
                logger.warning(f"  ✗ 文件过大 ({file_size / (1024 * 1024):.2f}MB > 8GB)")

            # 检查编码格式
            codec = video.get("codec_name", "")
            if codec in ["h264", "h265", "hevc"]:
                logger.info(f"  ✓ 编码格式符合要求 ({codec})")
            else:
                logger.warning(f"  ⚠ 编码格式可能不支持 ({codec})，推荐使用 h264 或 h265")

        # 音频流信息
        audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
        if audio_streams:
            audio = audio_streams[0]
            logger.info("\n音频流信息:")
            logger.info(f"  编码格式: {audio.get('codec_name', 'N/A')}")
            logger.info(f"  采样率: {audio.get('sample_rate', 'N/A')} Hz")
            logger.info(f"  声道数: {audio.get('channels', 'N/A')}")
            logger.info(
                f"  比特率: {int(audio.get('bit_rate', 0)) / 1000:.0f} kbps"
                if "bit_rate" in audio
                else "  比特率: N/A"
            )
        else:
            logger.warning("\n⚠ 未找到音频流")

        logger.info("\n" + "=" * 60)

    except ffmpeg.Error as e:
        logger.error(f"FFmpeg 错误: {e}")
        if e.stderr:
            logger.error(f"详细信息: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"检查视频信息失败: {e}", exc_info=True)


def check_credentials():
    """检查B站凭证配置"""
    import os

    logger.info("\n检查B站登录凭证:")
    logger.info("=" * 60)

    sessdata = os.getenv("BILIBILI_SESSDATA")
    bili_jct = os.getenv("BILIBILI_BILI_JCT")
    buvid3 = os.getenv("BILIBILI_BUVID3")

    if sessdata:
        logger.info(f"✓ SESSDATA: {sessdata[:20]}...{sessdata[-10:] if len(sessdata) > 30 else ''}")
    else:
        logger.warning("✗ SESSDATA: 未设置")

    if bili_jct:
        logger.info(f"✓ bili_jct: {bili_jct[:20]}...{bili_jct[-10:] if len(bili_jct) > 30 else ''}")
    else:
        logger.warning("✗ bili_jct: 未设置")

    if buvid3:
        logger.info(f"✓ buvid3: {buvid3[:20]}...{buvid3[-10:] if len(buvid3) > 30 else ''}")
    else:
        logger.warning("⚠ buvid3: 未设置（可选，但推荐设置）")

    logger.info("=" * 60)

    if not sessdata or not bili_jct:
        logger.error("\n请设置必需的环境变量：")
        logger.error("  export BILIBILI_SESSDATA='your_sessdata'")
        logger.error("  export BILIBILI_BILI_JCT='your_bili_jct'")
        logger.error("  export BILIBILI_BUVID3='your_buvid3'  # 推荐")
        logger.error("\n获取方法：")
        logger.error("  1. 在浏览器中登录 B站")
        logger.error("  2. 打开开发者工具 (F12)")
        logger.error("  3. Application/存储 → Cookies → https://www.bilibili.com")
        logger.error("  4. 复制 SESSDATA、bili_jct 和 buvid3 的值")


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    # 检查凭证
    check_credentials()

    # 查找视频文件
    videos_dir = Path("materials/videos")

    if not videos_dir.exists():
        logger.error(f"\n视频目录不存在: {videos_dir}")
        return

    # 查找所有视频文件
    video_files = list(videos_dir.glob("*.mp4")) + list(videos_dir.glob("*.webm"))

    if not video_files:
        logger.error(f"\n在 {videos_dir} 中未找到视频文件")
        return

    logger.info(f"\n找到 {len(video_files)} 个视频文件")

    # 检查每个视频
    for video_file in video_files:
        logger.info("\n")
        check_video_info(video_file)


if __name__ == "__main__":
    main()
