"""
检查今天有哪些比赛满足生成视频的条件
"""

from loguru import logger
from src.schedule.game_fetcher import GameFetcher


def check_today_games():
    """检查今天的比赛，看哪些满足生成视频条件"""
    
    logger.info("=" * 80)
    logger.info("🏀 检查今天的NBA比赛")
    logger.info("=" * 80)
    
    fetcher = GameFetcher()
    
    # 获取今天的比赛
    games = fetcher.get_today_nba_games()
    
    if not games:
        logger.warning("❌ 今天没有比赛")
        return
    
    logger.info(f"\n📋 今天共有 {len(games)} 场比赛\n")
    
    # 统计数据
    games_to_generate = []
    games_ended_low_rating = []
    games_not_ended = []
    
    # 检查每场比赛
    for i, game in enumerate(games, 1):
        match_id = game.get("matchId", "")
        home = game.get("homeTeamName", "未知")
        away = game.get("awayTeamName", "未知")
        
        if not match_id:
            logger.warning(f"⚠️  比赛 {i} 缺少match_id，跳过")
            continue
        
        # 获取状态和评分信息
        status_info = fetcher.get_game_status(match_id)
        
        if not status_info:
            logger.warning(f"⚠️  比赛 {i}: {away} vs {home} - 无法获取状态信息")
            continue
        
        status = status_info.get("status", "未知")
        rating_count = status_info.get("rating_count", 0)
        
        game_info = {
            "index": i,
            "home": home,
            "away": away,
            "status": status,
            "rating_count": rating_count,
            "match_id": match_id,
        }
        
        # 分类
        if status == "已结束":
            if rating_count >= 100000:
                games_to_generate.append(game_info)
            else:
                games_ended_low_rating.append(game_info)
        else:
            games_not_ended.append(game_info)
    
    # 输出结果
    logger.info("\n" + "=" * 80)
    logger.info(f"✅ 满足生成视频条件的比赛: {len(games_to_generate)} 场")
    logger.info("=" * 80)
    
    if games_to_generate:
        for game in games_to_generate:
            logger.info(
                f"  {game['index']}. {game['away']} vs {game['home']} "
                f"(评分: {game['rating_count']:,})"
            )
    else:
        logger.info("  无")
    
    logger.info("\n" + "=" * 80)
    logger.info(f"⏸️  已结束但评分不足10万的比赛: {len(games_ended_low_rating)} 场")
    logger.info("=" * 80)
    
    if games_ended_low_rating:
        for game in games_ended_low_rating:
            rating_text = f"{game['rating_count']:,}".replace(",", "")
            shortage = 100000 - game['rating_count']
            logger.info(
                f"  {game['index']}. {game['away']} vs {game['home']} "
                f"(评分: {rating_text}, 还差: {shortage:,})"
            )
    else:
        logger.info("  无")
    
    logger.info("\n" + "=" * 80)
    logger.info(f"⏳ 尚未结束的比赛: {len(games_not_ended)} 场")
    logger.info("=" * 80)
    
    if games_not_ended:
        for game in games_not_ended:
            logger.info(
                f"  {game['index']}. {game['away']} vs {game['home']} "
                f"(状态: {game['status']}, 评分: {game['rating_count']:,})"
            )
    else:
        logger.info("  无")
    
    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 总结")
    logger.info("=" * 80)
    logger.info(f"  总比赛数: {len(games)}")
    logger.info(f"  ✅ 可生成视频: {len(games_to_generate)} 场")
    logger.info(f"  ⏸️  已结束但评分不足: {len(games_ended_low_rating)} 场")
    logger.info(f"  ⏳ 尚未结束: {len(games_not_ended)} 场")
    logger.info("=" * 80)
    
    # 如果有可生成视频的比赛，输出下一步操作提示
    if games_to_generate:
        logger.info("\n💡 下一步操作:")
        logger.info("  可以运行调度器来为这些比赛生成视频")
        logger.info("  命令: uv run python -m test.example_usage")


if __name__ == "__main__":
    check_today_games()

