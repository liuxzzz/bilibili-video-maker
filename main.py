"""
主程序入口
支持多种视频制作模式，通过 --mode 参数选择：
1. NBA模式（--mode nba）：只支持定时任务模式（--cron）
2. 新模式（--mode new）：只支持一次性运行模式
"""

import argparse
from pathlib import Path

from loguru import logger


def run_nba_cron():
    """NBA模式 - 定时任务模式"""
    from src.schedule import CronScheduler

    logger.info("=" * 80)
    logger.info("🏀 NBA视频制作模式 - 定时任务模式")
    logger.info("=" * 80)
    logger.info("📋 定时任务说明：")
    logger.info("  ✅ 每天12:00自动检查当天NBA比赛")
    logger.info("  ✅ 每小时检查等待中的任务状态")
    logger.info("  ✅ 比赛结束后自动生成视频并上传")
    logger.info("  ✅ 程序将持续运行，直到手动停止（Ctrl+C）")
    logger.info("")
    logger.info("💡 提示：程序启动时会立即执行一次检查")
    logger.info("=" * 80)
    logger.info("")

    cron_scheduler = CronScheduler()
    cron_scheduler.start()


def run_new_mode_once():
    """新模式 - 一次性运行模式"""
    from src.new_mode import NewModeRunner

    logger.info("=" * 80)
    logger.info("🆕 新模式视频制作 - 一次性运行模式")
    logger.info("=" * 80)

    runner = NewModeRunner()
    runner.run()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="B站视频制作发布系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # NBA模式 - 定时任务（推荐用于生产环境）
  python main.py --mode nba --cron
  
  # 新模式 - 一次性运行
  python main.py --mode new
        """,
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["nba", "new"],
        default="nba",
        help="选择视频制作模式: nba (NBA比赛视频) 或 new (新模式，默认: nba)",
    )

    parser.add_argument(
        "--cron",
        action="store_true",
        help="启用定时任务模式（仅适用于NBA模式）",
    )

    args = parser.parse_args()

    # 模式分流
    if args.mode == "nba":
        # NBA模式：只支持定时任务模式
        if not args.cron:
            logger.error("=" * 80)
            logger.error("❌ NBA模式只支持定时任务模式")
            logger.error("=" * 80)
            logger.error("请使用 --cron 参数启动定时任务模式")
            logger.error("示例: python main.py --mode nba --cron")
            logger.error("=" * 80)
            parser.print_help()
            return

        run_nba_cron()

    elif args.mode == "new":
        # 新模式：只支持一次性运行，不支持定时任务
        if args.cron:
            logger.error("=" * 80)
            logger.error("❌ 新模式不支持定时任务模式")
            logger.error("=" * 80)
            logger.error("新模式只支持一次性运行模式")
            logger.error("示例: python main.py --mode new")
            logger.error("=" * 80)
            parser.print_help()
            return

        run_new_mode_once()

    else:
        logger.error(f"未知模式: {args.mode}")
        parser.print_help()
        return


if __name__ == "__main__":
    main()
