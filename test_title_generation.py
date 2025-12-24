"""
测试视频标题生成功能

使用方法：
    python test_title_generation.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.schedule.models import GameInfo
from src.vide_publish import VideoPublisher
from loguru import logger


def test_title_generation():
    """测试标题生成功能"""
    logger.info("=" * 60)
    logger.info("开始测试视频标题生成功能")
    logger.info("=" * 60)

    # 创建测试用的比赛信息
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

    logger.info(f"测试比赛信息: {game_info}")
    logger.info(f"比赛: {game_info.away_team_name} vs {game_info.home_team_name}")

    # 创建视频发布器
    publisher = VideoPublisher()

    try:
        # 生成标题
        logger.info("\n开始生成视频标题...")
        title = publisher._generate_video_title(game_info)

        logger.info("\n" + "=" * 60)
        logger.info("生成的标题:")
        logger.info(f"  {title}")
        logger.info("=" * 60)

        # 验证标题格式
        if title and len(title) > 0:
            logger.info("✓ 标题生成成功")
            logger.info(f"  标题长度: {len(title)} 字符")
        else:
            logger.error("✗ 标题生成失败：标题为空")

        return title

    except Exception as e:
        logger.error(f"✗ 测试失败: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # 运行测试
    result = test_title_generation()

    if result:
        logger.info("\n✓ 测试完成")
        sys.exit(0)
    else:
        logger.error("\n✗ 测试失败")
        sys.exit(1)
