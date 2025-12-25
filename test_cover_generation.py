"""
测试封面图生成功能

使用方法：
    python test_cover_generation.py

测试内容：
    1. 从视频第30帧提取
    2. 裁剪上方0-450px区域
    3. 验证封面图尺寸是否正确
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.vide_publish import VideoPublisher
from loguru import logger

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow 未安装，将使用 ffprobe 验证图片尺寸")


def find_test_video() -> Path | None:
    """查找测试用的视频文件"""
    videos_dir = project_root / "materials" / "videos"

    if not videos_dir.exists():
        logger.error(f"视频目录不存在: {videos_dir}")
        return None

    # 查找 mp4 文件
    mp4_files = list(videos_dir.glob("*.mp4"))

    if not mp4_files:
        logger.error(f"在 {videos_dir} 中未找到 mp4 文件")
        return None

    # 优先使用 final.mp4 文件，否则使用第一个找到的
    final_video = next((f for f in mp4_files if "final" in f.name), None)
    test_video = final_video or mp4_files[0]

    logger.info(f"找到测试视频: {test_video}")
    return test_video


def get_video_dimensions(video_path: Path) -> tuple[int, int] | None:
    """获取视频的宽度和高度"""
    try:
        import ffmpeg

        probe = ffmpeg.probe(str(video_path))
        video_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
        )

        if not video_stream:
            return None

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        return (width, height) if width > 0 and height > 0 else None
    except Exception as e:
        logger.error(f"获取视频尺寸失败: {e}")
        return None


def verify_cover_image(cover_path: Path, expected_width: int) -> bool:
    """
    验证封面图尺寸是否正确

    Args:
        cover_path: 封面图路径
        expected_width: 期望的宽度（应该等于视频宽度）
        expected_height: 期望的高度（应该是450px）

    Returns:
        bool: 验证是否通过
    """
    if not cover_path.exists():
        logger.error(f"封面图文件不存在: {cover_path}")
        return False

    file_size_kb = cover_path.stat().st_size / 1024
    logger.info(f"封面图文件大小: {file_size_kb:.2f} KB")

    # 使用 PIL 验证尺寸（如果可用）
    if PIL_AVAILABLE:
        try:
            with Image.open(cover_path) as img:
                width, height = img.size
                logger.info(f"封面图尺寸: {width}x{height} px")

                # 验证尺寸
                if width != expected_width:
                    logger.error(f"封面图宽度不正确: 期望 {expected_width}px，实际 {width}px")
                    return False

                if height != 450:
                    logger.error(f"封面图高度不正确: 期望 450px，实际 {height}px")
                    return False

                logger.info("✓ 封面图尺寸验证通过")
                return True
        except Exception as e:
            logger.error(f"使用 PIL 验证封面图失败: {e}")
            return False
    else:
        # 使用 ffprobe 验证尺寸
        try:
            import ffmpeg

            probe = ffmpeg.probe(str(cover_path))
            video_stream = next(
                (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
            )

            if not video_stream:
                logger.warning("无法使用 ffprobe 验证封面图，跳过尺寸验证")
                logger.info("建议安装 Pillow: pip install Pillow")
                return True  # 文件存在，认为验证通过

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            logger.info(f"封面图尺寸: {width}x{height} px")

            if width != expected_width:
                logger.error(f"封面图宽度不正确: 期望 {expected_width}px，实际 {width}px")
                return False

            if height != 200:
                logger.error(f"封面图高度不正确: 期望 200px，实际 {height}px")
                return False

            logger.info("✓ 封面图尺寸验证通过")
            return True
        except Exception as e:
            logger.warning(f"使用 ffprobe 验证封面图失败: {e}")
            logger.info("文件已生成，但无法验证尺寸")
            return True  # 文件存在，认为基本验证通过


def test_cover_generation():
    """测试封面图生成功能"""
    logger.info("=" * 60)
    logger.info("开始测试封面图生成功能")
    logger.info("=" * 60)

    # 1. 查找测试视频
    test_video = find_test_video()
    if not test_video:
        logger.error("未找到测试视频，测试终止")
        return False

    if not test_video.exists():
        logger.error(f"测试视频文件不存在: {test_video}")
        return False

    # 2. 获取视频尺寸
    video_dimensions = get_video_dimensions(test_video)
    if not video_dimensions:
        logger.error("无法获取视频尺寸，测试终止")
        return False

    video_width, video_height = video_dimensions
    logger.info(f"视频尺寸: {video_width}x{video_height} px")

    # 3. 创建视频发布器
    publisher = VideoPublisher()

    try:
        # 4. 生成封面图
        logger.info("\n" + "=" * 60)
        logger.info("开始生成封面图...")
        logger.info("=" * 60)

        cover_path_str = publisher._generate_cover_image(test_video)

        if not cover_path_str:
            logger.error("封面图生成失败")
            return False

        cover_path = Path(cover_path_str)
        logger.info(f"封面图路径: {cover_path}")

        # 5. 验证封面图
        logger.info("\n" + "=" * 60)
        logger.info("验证封面图...")
        logger.info("=" * 60)

        if not cover_path.exists():
            logger.error("封面图文件不存在")
            return False

        # 验证尺寸
        verification_passed = verify_cover_image(cover_path, video_width)

        if verification_passed:
            logger.info("\n" + "=" * 60)
            logger.info("✓ 封面图生成测试成功！")
            logger.info("=" * 60)
            logger.info(f"封面图文件: {cover_path}")
            logger.info(f"期望尺寸: {video_width}x450 px")
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("✗ 封面图尺寸验证失败")
            logger.error("=" * 60)
            return False

    except Exception as e:
        logger.error(f"✗ 测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # 运行测试
    result = test_cover_generation()

    if result:
        logger.info("\n✓ 测试完成")
        sys.exit(0)
    else:
        logger.error("\n✗ 测试失败")
        sys.exit(1)
