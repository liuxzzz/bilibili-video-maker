"""
测试评分数量筛选功能
"""

from loguru import logger
from src.schedule.game_fetcher import GameFetcher


def test_parse_rating_count():
    """测试评分数量解析功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试评分数量解析功能")
    logger.info("=" * 60)

    fetcher = GameFetcher()

    # 测试用例
    test_cases = [
        ("4.4万评分", 44000),
        ("10.2万评分", 102000),
        ("1.5万评分", 15000),
        ("15万评分", 150000),
        ("1234评分", 1234),
        ("500评分", 500),
        ("0.5万评分", 5000),
    ]

    for rating_text, expected in test_cases:
        result = fetcher._parse_rating_count(rating_text)
        status = "✓" if result == expected else "✗"
        logger.info(f"{status} '{rating_text}' -> {result} (期望: {expected})")

        if result != expected:
            logger.error(f"解析失败！'{rating_text}' 应该解析为 {expected}，实际得到 {result}")


def test_get_game_status_with_rating():
    """测试获取比赛状态和评分数量"""
    logger.info("\n" + "=" * 60)
    logger.info("测试获取比赛状态和评分数量")
    logger.info("=" * 60)

    fetcher = GameFetcher()

    # 先获取今天的比赛列表
    games = fetcher.get_today_nba_games()

    if not games:
        logger.warning("今天没有比赛，无法测试")
        return

    logger.info(f"找到 {len(games)} 场比赛")

    # 测试前3场比赛（如果有的话）
    for i, game in enumerate(games[:3], 1):
        match_id = game.get("matchId", "")
        home = game.get("homeTeamName", "未知")
        away = game.get("awayTeamName", "未知")

        if not match_id:
            logger.warning(f"比赛 {i} 缺少match_id，跳过")
            continue

        logger.info(f"\n比赛 {i}: {away} vs {home}")
        logger.info(f"Match ID: {match_id}")

        # 获取状态和评分信息
        status_info = fetcher.get_game_status(match_id)

        if status_info:
            status = status_info.get("status", "未知")
            rating_count = status_info.get("rating_count", 0)

            logger.info(f"状态: {status}")
            logger.info(f"评分数量: {rating_count}")

            # 判断是否满足筛选条件
            if status == "已结束" and rating_count >= 30000:
                logger.info("✓ 满足生成视频条件（已结束且评分>=3万）")
            elif status == "已结束":
                logger.info(f"✗ 比赛已结束但评分数量不足（{rating_count} < 30000）")
            else:
                logger.info(f"⏳ 比赛尚未结束（状态: {status}）")
        else:
            logger.warning("无法获取比赛状态信息")


def test_rating_filter_integration():
    """测试评分筛选的完整流程"""
    logger.info("\n" + "=" * 60)
    logger.info("测试评分筛选完整流程")
    logger.info("=" * 60)

    from src.schedule.scheduler import TaskScheduler

    scheduler = TaskScheduler()

    # 创建每日任务（会自动应用评分筛选）
    tasks = scheduler.start_daily_tasks()

    logger.info(f"\n创建了 {len(tasks)} 个任务")

    if not tasks:
        logger.warning("没有创建任何任务，可能是因为：")
        logger.warning("1. 今天没有比赛")
        logger.warning("2. 所有比赛都不满足评分条件（已结束但评分<3万）")
        return

    # 统计各状态的任务数量
    from collections import Counter
    from src.schedule.models import TaskStatus

    status_counts = Counter(task.status for task in tasks)

    logger.info("\n任务状态统计:")
    for status in TaskStatus:
        count = status_counts.get(status, 0)
        if count > 0:
            logger.info(f"  {status.value}: {count}")

    # 显示每个任务的详细信息
    logger.info("\n任务详情:")
    for i, task in enumerate(tasks, 1):
        game = task.game_info
        logger.info(f"\n任务 {i}:")
        logger.info(f"  比赛: {game.away_team_name} vs {game.home_team_name}")
        logger.info(f"  状态: {task.status.value}")
        logger.info(f"  比赛状态: {game.match_status}")
        logger.info(f"  评分数量: {game.rating_count}")

        if task.status == TaskStatus.PENDING:
            logger.info("  ✓ 可以立即执行")
        elif task.status == TaskStatus.WAITING_GAME_END:
            next_check = task.config.get("next_check_time", "未设置")
            logger.info(f"  ⏳ 等待中，下次检查: {next_check}")


def main():
    """主函数"""
    logger.info("开始测试评分数量筛选功能")

    # 测试1: 评分数量解析
    test_parse_rating_count()

    # 测试2: 获取比赛状态和评分
    test_get_game_status_with_rating()

    # 测试3: 完整流程测试
    test_rating_filter_integration()

    logger.info("\n" + "=" * 60)
    logger.info("所有测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
