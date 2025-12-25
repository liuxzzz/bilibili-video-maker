"""
测试视频上传功能

使用方法：
    python test_video_upload.py

测试内容：
    1. 检查B站登录凭证
    2. 创建测试用的比赛信息
    3. 查找测试视频文件
    4. 调用视频发布器上传视频
    5. 验证上传结果

注意：
    - 需要设置环境变量 BILIBILI_SESSDATA 和 BILIBILI_BILI_JCT
    - 需要确保有可用的测试视频文件
    - 此测试会真实上传视频到B站，请谨慎使用
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.schedule.models import GameInfo
from src.vide_publish import VideoPublisher
from loguru import logger


def check_credentials() -> tuple[bool, str]:
    """
    检查B站登录凭证是否配置

    Returns:
        tuple[bool, str]: (是否配置, 错误信息)
    """
    sessdata = os.getenv("BILIBILI_SESSDATA")
    bili_jct = os.getenv("BILIBILI_BILI_JCT")

    if not sessdata:
        return False, "未设置环境变量 BILIBILI_SESSDATA"
    if not bili_jct:
        return False, "未设置环境变量 BILIBILI_BILI_JCT"

    logger.info("✓ B站登录凭证已配置")
    logger.debug(f"  sessdata: {sessdata[:20]}...")
    logger.debug(f"  bili_jct: {bili_jct[:20]}...")
    return True, ""


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

    logger.info(f"✓ 找到测试视频: {test_video}")
    logger.info(f"  文件大小: {test_video.stat().st_size / (1024 * 1024):.2f} MB")
    return test_video


def create_test_game_info() -> GameInfo:
    """创建测试用的比赛信息"""
    game_info = GameInfo(
        game_id="1405864805306204160",
        home_team_name="快船",
        away_team_name="湖人",
        home_score="103",
        away_score="88",
        competition_stage_desc="常规赛",
        match_status="已结束",
        match_id="1405864805306204160",
    )
    logger.info(f"✓ 创建测试比赛信息: {game_info}")
    logger.info(f"  比赛: {game_info.away_team_name} vs {game_info.home_team_name}")
    logger.info(
        f"  比分: {game_info.away_team_name} {game_info.away_score}-{game_info.home_score} {game_info.home_team_name}"
    )
    return game_info


def test_video_upload():
    """测试视频上传功能"""
    logger.info("=" * 60)
    logger.info("开始测试视频上传功能")
    logger.info("=" * 60)
    logger.warning("⚠️  此测试会真实上传视频到B站，请确保：")
    logger.warning("   1. 已正确配置B站登录凭证")
    logger.warning("   2. 视频内容符合B站规范")
    logger.warning("   3. 已准备好测试视频文件")
    logger.info("=" * 60)

    # 1. 检查登录凭证
    logger.info("\n[步骤 1/5] 检查B站登录凭证...")
    credentials_ok, error_msg = check_credentials()
    if not credentials_ok:
        logger.error(f"✗ 凭证检查失败: {error_msg}")
        logger.error("\n请设置环境变量：")
        logger.error("  export BILIBILI_SESSDATA='your_sessdata'")
        logger.error("  export BILIBILI_BILI_JCT='your_bili_jct'")
        logger.error("\n或者通过浏览器开发者工具获取这些值：")
        logger.error("  1. 登录B站后，打开开发者工具 (F12)")
        logger.error("  2. 在 Application/存储 -> Cookies -> https://www.bilibili.com")
        logger.error("  3. 找到 SESSDATA 和 bili_jct 的值")
        return False

    # 2. 查找测试视频
    logger.info("\n[步骤 2/5] 查找测试视频文件...")
    test_video = find_test_video()
    if not test_video:
        logger.error("✗ 未找到测试视频，测试终止")
        return False

    if not test_video.exists():
        logger.error(f"✗ 测试视频文件不存在: {test_video}")
        return False

    # 3. 创建测试比赛信息
    logger.info("\n[步骤 3/5] 创建测试比赛信息...")
    game_info = create_test_game_info()

    # 4. 创建视频发布器
    logger.info("\n[步骤 4/5] 初始化视频发布器...")
    try:
        publisher = VideoPublisher()
        if not publisher.credential:
            logger.error("✗ 视频发布器初始化失败：凭证无效")
            return False
        logger.info("✓ 视频发布器初始化成功")
    except Exception as e:
        logger.error(f"✗ 视频发布器初始化失败: {e}", exc_info=True)
        return False

    # 5. 上传视频
    logger.info("\n[步骤 5/5] 开始上传视频到B站...")
    logger.info("=" * 60)
    logger.info("上传信息:")
    logger.info(f"  视频文件: {test_video}")
    logger.info(f"  比赛信息: {game_info}")
    logger.info("=" * 60)
    logger.warning("\n⚠️  即将开始真实上传，请确认...")
    logger.info("上传过程可能需要较长时间，请耐心等待...\n")

    try:
        # 调用发布方法
        success = publisher.publish_video(video_path=test_video, game_info=game_info)

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✓ 视频上传测试成功！")
            logger.info("=" * 60)
            logger.info("视频已成功上传到B站")
            logger.info("请前往B站个人中心查看上传的视频")
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("✗ 视频上传测试失败")
            logger.error("=" * 60)
            logger.error("请检查：")
            logger.error("  1. 登录凭证是否正确")
            logger.error("  2. 视频文件是否符合B站要求")
            logger.error("  3. 网络连接是否正常")
            logger.error("  4. 查看上方错误日志获取详细信息")
            return False

    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断上传")
        return False
    except Exception as e:
        logger.error(f"\n✗ 上传过程中发生异常: {e}", exc_info=True)
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
    result = test_video_upload()

    if result:
        logger.info("\n" + "=" * 60)
        logger.info("✓ 测试完成")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ 测试失败")
        logger.error("=" * 60)
        sys.exit(1)
