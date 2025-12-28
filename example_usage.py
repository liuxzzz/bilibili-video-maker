#!/usr/bin/env python
"""
快速开始示例 - 演示如何使用定时任务系统
"""

from datetime import datetime
from loguru import logger

from src.schedule import TaskScheduler, GameFetcher, TaskStore


def example_1_get_games():
    """示例1: 获取当天的比赛"""
    logger.info("=" * 60)
    logger.info("示例1: 获取当天的NBA比赛")
    logger.info("=" * 60)

    fetcher = GameFetcher()
    games = fetcher.get_today_nba_games()

    logger.info(f"找到 {len(games)} 场比赛：")
    for i, game in enumerate(games, 1):
        home = game.get("homeTeamName", "未知")
        away = game.get("awayTeamName", "未知")
        match_id = game.get("matchId", "")
        status = game.get("matchStatus", "未知")
        logger.info(f"{i}. {away} vs {home} (ID: {match_id}, 状态: {status})")


def example_2_check_game_status():
    """示例2: 检查指定比赛的状态"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 检查比赛状态")
    logger.info("=" * 60)

    # 先获取比赛列表
    fetcher = GameFetcher()
    games = fetcher.get_today_nba_games()

    if not games:
        logger.warning("今天没有比赛")
        return

    # 检查第一场比赛的状态
    first_game = games[0]
    match_id = first_game.get("matchId", "")

    if not match_id:
        logger.warning("无法获取比赛ID")
        return

    home = first_game.get("homeTeamName", "未知")
    away = first_game.get("awayTeamName", "未知")

    logger.info(f"检查比赛: {away} vs {home}")
    logger.info(f"比赛ID: {match_id}")

    status = fetcher.get_game_status(match_id)
    logger.info(f"当前状态: {status}")

    if status == "已结束":
        logger.info("✓ 比赛已结束，可以生成视频")
    elif status in ["未开始", "进行中"]:
        logger.info("⏳ 比赛尚未结束，需要等待")
    else:
        logger.warning("⚠ 无法确定比赛状态")


def example_3_create_tasks():
    """示例3: 创建任务"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 创建任务")
    logger.info("=" * 60)

    scheduler = TaskScheduler()

    # 启动每日任务流程（会自动检查比赛状态）
    tasks = scheduler.start_daily_tasks()

    logger.info(f"创建了 {len(tasks)} 个任务")

    # 显示任务信息
    for task in tasks:
        logger.info(f"\n任务ID: {task.task_id}")
        logger.info(f"比赛: {task.game_info.away_team_name} vs {task.game_info.home_team_name}")
        logger.info(f"状态: {task.status.value}")

        if hasattr(task, "config") and "next_check_time" in task.config:
            logger.info(f"下次检查: {task.config['next_check_time']}")


def example_4_view_stored_tasks():
    """示例4: 查看存储的任务"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 查看存储的任务")
    logger.info("=" * 60)

    store = TaskStore()
    all_tasks = store.get_all_tasks()

    if not all_tasks:
        logger.info("还没有任何任务")
        return

    logger.info(f"共有 {len(all_tasks)} 个任务")

    # 按状态分类
    from collections import defaultdict

    status_groups = defaultdict(list)

    for task in all_tasks:
        status_groups[task.status.value].append(task)

    # 显示各状态的任务数
    logger.info("\n任务状态统计:")
    for status, tasks in status_groups.items():
        logger.info(f"  {status}: {len(tasks)} 个")

    # 显示最近的5个任务
    logger.info("\n最近的任务:")
    recent_tasks = sorted(all_tasks, key=lambda t: t.create_time, reverse=True)[:5]

    for i, task in enumerate(recent_tasks, 1):
        create_time = task.create_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            f"{i}. [{task.status.value}] {task.game_info.away_team_name} vs {task.game_info.home_team_name} ({create_time})"
        )


def example_5_check_waiting_tasks():
    """示例5: 检查等待中的任务"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5: 检查等待中的任务")
    logger.info("=" * 60)

    scheduler = TaskScheduler()

    # 获取等待中的任务
    from src.schedule import TaskStatus

    waiting_tasks = scheduler.task_store.get_tasks_by_status(TaskStatus.WAITING_GAME_END)

    logger.info(f"找到 {len(waiting_tasks)} 个等待中的任务")

    if not waiting_tasks:
        logger.info("没有等待中的任务")
        return

    # 检查哪些任务到了检查时间
    tasks_to_check = scheduler.check_waiting_tasks()
    logger.info(f"其中 {len(tasks_to_check)} 个任务需要重新检查")

    # 重新检查比赛状态
    for task in tasks_to_check:
        logger.info(f"\n检查任务: {task.task_id}")
        logger.info(f"比赛: {task.game_info.away_team_name} vs {task.game_info.home_team_name}")

        is_finished = scheduler.recheck_game_status_and_update(task)

        if is_finished:
            logger.info("✓ 比赛已结束，任务已转为待执行状态")
        else:
            logger.info("⏳ 比赛仍在进行，继续等待")


def main():
    """运行所有示例"""
    logger.info("定时任务系统 - 快速开始示例")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    try:
        # 示例1: 获取比赛
        example_1_get_games()

        # 示例2: 检查比赛状态
        example_2_check_game_status()

        # 示例3: 创建任务
        example_3_create_tasks()

        # 示例4: 查看存储的任务
        example_4_view_stored_tasks()

        # 示例5: 检查等待中的任务
        example_5_check_waiting_tasks()

        logger.info("\n" + "=" * 60)
        logger.info("所有示例运行完成")
        logger.info("=" * 60)

        logger.info("\n接下来你可以:")
        logger.info("1. 运行 'python main.py' 立即执行一次完整流程")
        logger.info("2. 运行 'python main.py --cron' 启动定时任务模式")
        logger.info("3. 查看 SCHEDULER_README.md 了解更多信息")

    except Exception as e:
        logger.error(f"运行示例失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
