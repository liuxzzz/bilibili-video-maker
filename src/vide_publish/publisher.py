"""
视频发布器

负责将生成好的视频发布到B站平台。
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from src.schedule.models import GameInfo
from src.utils import call_llm


class VideoPublisher:
    """视频发布器"""

    def __init__(self):
        """初始化视频发布器"""
        logger.info("视频发布器初始化完成")

    def publish_video(self, video_path: str | Path, game_info: GameInfo) -> bool:
        """
        发布视频到B站

        Args:
            video_path: 视频文件路径
            game_info: 比赛信息

        Returns:
            bool: 发布是否成功
        """
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                logger.error(f"视频文件不存在: {video_path}")
                return False

            logger.info(f"开始发布视频: {video_path}")
            logger.info(f"比赛信息: {game_info}")

            # 1. 生成视频标题（基于比赛信息）
            video_title = self._generate_video_title(game_info)
            logger.info(f"生成的视频标题: {video_title}")

            # 2. 生成视频简介
            video_description = self._generate_video_description(game_info)
            logger.info(f"生成的视频简介: {video_description}")
            # 4. 调用B站API上传视频
            # 5. 处理上传结果

            logger.info("视频发布功能待实现")
            return True

        except Exception as e:
            logger.error(f"视频发布失败: {e}", exc_info=True)
            return False

    def _generate_video_title(self, game_info: GameInfo) -> str:
        """
        生成视频标题

        标题格式参考：独木难支！东契奇伤退、詹姆斯空砍36分，湖人88-103不敌快船
        包含：吸引人的开头、比赛关键信息、比分和胜负关系

        Args:
            game_info: 比赛信息

        Returns:
            str: 生成的视频标题
        """
        try:
            # 构造提示词，只提供比赛标识信息，让模型自己搜索详细信息
            system_prompt = """你是一个专业的体育视频标题生成助手。你需要根据比赛信息生成吸引人的视频标题。

标题要求：
1. 开头要有一个吸引人的短句或感叹（如"独木难支！"、"惊天逆转！"等）
2. 中间包含比赛的关键信息（可以是球员表现、比赛亮点等）
3. 结尾必须包含准确的比分和胜负关系（格式：队伍名 比分-比分 不敌/战胜 队伍名）

标题示例：
- 独木难支！东契奇伤退、詹姆斯空砍36分，湖人88-103不敌快船
- 惊天逆转！末节狂追20分，勇士128-125险胜凯尔特人
- 双星闪耀！库里42分、汤普森30分，勇士120-108大胜湖人

请只返回标题，不要包含其他说明文字。"""

            user_prompt = f"""请为以下NBA比赛生成一个吸引人的视频标题：

比赛：{game_info.away_team_name} vs {game_info.home_team_name}

请搜索这场比赛的最新信息（包括比分、胜负关系、比赛亮点等），然后生成一个吸引人的视频标题。"""

            title = call_llm(
                user_content=user_prompt,
                system_content=system_prompt,
                enable_search=True,  # 启用搜索功能，让模型自己查找比赛信息
            )

            # 清理标题（移除可能的引号、换行等）
            title = title.strip().strip('"').strip("'").strip()
            # 移除可能的"标题："等前缀
            if "：" in title:
                title = title.split("：", 1)[-1]
            if ":" in title:
                title = title.split(":", 1)[-1]

            logger.info(f"成功生成视频标题: {title}")
            return title

        except Exception as e:
            logger.error(f"生成视频标题失败: {e}", exc_info=True)
            # 如果生成失败，返回一个简单的默认标题
            home_score = game_info.home_score if game_info.home_score else "0"
            away_score = game_info.away_score if game_info.away_score else "0"
            default_title = (
                f"{game_info.away_team_name} {away_score}-{home_score} {game_info.home_team_name}"
            )
            logger.warning(f"使用默认标题: {default_title}")
            return default_title
