"""
测试定时任务系统

测试场景：
1. 获取当天比赛并检查状态
2. 测试等待中任务的重试机制
3. 测试任务持久化存储
"""

from datetime import datetime, timedelta
from loguru import logger

from src.schedule import TaskScheduler, CronScheduler, TaskStatus


def test_daily_check():
    """测试每日检查功能"""
    logger.info("=" * 80)
    logger.info("测试1: 每日检查功能")
    logger.info("=" * 80)

    scheduler = TaskScheduler()
    tasks = scheduler.start_daily_tasks()

    logger.info(f"获取到 {len(tasks)} 场比赛")

    for task in tasks:
        logger.info(f"任务ID: {task.task_id}")
        logger.info(f"比赛: {task.game_info.away_team_name} vs {task.game_info.home_team_name}")
        logger.info(f"比赛ID: {task.game_info.match_id}")
        logger.info(f"状态: {task.status.value}")
        logger.info(f"比赛状态: {task.game_info.match_status}")

        if task.status == TaskStatus.WAITING_GAME_END:
            next_check = task.config.get("next_check_time")
            if next_check:
                logger.info(f"下次检查时间: {next_check}")

        logger.info("-" * 40)

    # 统计
    pending_count = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
    waiting_count = sum(1 for t in tasks if t.status == TaskStatus.WAITING_GAME_END)

    logger.info(f"统计: 待执行 {pending_count} 个, 等待比赛结束 {waiting_count} 个")


def test_waiting_check():
    """测试等待任务检查功能"""
    logger.info("=" * 80)
    logger.info("测试2: 等待任务检查功能")
    logger.info("=" * 80)

    scheduler = TaskScheduler()

    # 获取所有等待中的任务
    waiting_tasks = scheduler.task_store.get_tasks_by_status(TaskStatus.WAITING_GAME_END)
    logger.info(f"找到 {len(waiting_tasks)} 个等待中的任务")

    if not waiting_tasks:
        logger.info("没有等待中的任务，测试结束")
        return

    # 检查哪些任务需要重新检查
    tasks_to_check = scheduler.check_waiting_tasks()
    logger.info(f"需要检查 {len(tasks_to_check)} 个任务")

    # 重新检查比赛状态
    for task in tasks_to_check:
        logger.info(f"检查任务: {task.task_id}")
        is_finished = scheduler.recheck_game_status_and_update(task)
        logger.info(f"比赛是否结束: {is_finished}")


def test_task_persistence():
    """测试任务持久化"""
    logger.info("=" * 80)
    logger.info("测试3: 任务持久化")
    logger.info("=" * 80)

    scheduler = TaskScheduler()

    # 获取所有任务
    all_tasks = scheduler.get_all_tasks()
    logger.info(f"存储中共有 {len(all_tasks)} 个任务")

    # 按状态分类
    status_counts = {}
    for task in all_tasks:
        status = task.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    logger.info("任务状态统计:")
    for status, count in status_counts.items():
        logger.info(f"  {status}: {count}")


def test_game_status_check():
    """测试比赛状态获取"""
    logger.info("=" * 80)
    logger.info("测试4: 比赛状态获取")
    logger.info("=" * 80)

    from src.schedule import GameFetcher

    fetcher = GameFetcher()

    # 获取当天比赛
    games = fetcher.get_today_nba_games()
    logger.info(f"获取到 {len(games)} 场比赛")

    # 测试获取每场比赛的状态
    for game in games[:3]:  # 只测试前3场
        match_id = game.get("matchId") or game.get("match_id", "")
        if not match_id:
            continue

        logger.info(f"检查比赛 {match_id}")
        status = fetcher.get_game_status(match_id)
        logger.info(f"状态: {status}")
        logger.info("-" * 40)


def main():
    """运行所有测试"""
    logger.info("开始测试定时任务系统")
    logger.info("当前时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("")

    try:
        # 测试1: 每日检查
        test_daily_check()
        logger.info("")

        # 测试2: 等待任务检查
        test_waiting_check()
        logger.info("")

        # 测试3: 任务持久化
        test_task_persistence()
        logger.info("")

        # 测试4: 比赛状态获取
        test_game_status_check()
        logger.info("")

        logger.info("=" * 80)
        logger.info("所有测试完成")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
