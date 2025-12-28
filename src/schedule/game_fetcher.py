"""
NBA比赛信息获取模块
"""

import json
import re
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from loguru import logger


class GameFetcher:
    """比赛信息获取器"""

    def __init__(self):
        self.base_url = "https://m.hupu.com/nba/schedule"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )

    def get_today_nba_games(self) -> List[dict]:
        """
        获取当天NBA比赛信息

        Returns:
            List[dict]: 比赛信息列表，每个元素包含：
                - game_id: 唯一标识
                - home_team: 主队
                - away_team: 客队
                - game_date: 比赛日期
                - game_time: 比赛时间（可选）
                - status: 比赛状态（可选）
                - score: 比分（可选）
                - source_url: 来源URL（可选）
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"开始获取 {today} 的NBA比赛信息")

            # 尝试从虎扑NBA页面获取比赛信息
            games = self._fetch_from_hupu()

            if not games:
                logger.warning("未能从虎扑获取到比赛信息，返回空列表")
                return []

            print(len(games), "games")
            # 为每场比赛生成唯一ID
            for game in games:
                if "game_id" not in game or not game["game_id"]:

                    game["game_id"] = self._generate_game_id(game, today)

            logger.info(f"成功获取 {len(games)} 场NBA比赛")
            return games

        except Exception as e:
            logger.error(f"获取NBA比赛信息失败: {e}")
            return []

    def _fetch_from_hupu(self) -> List[dict]:
        """
        从虎扑网站获取比赛信息

        Returns:
            List[dict]: 比赛信息列表
        """
        try:
            # 虎扑NBA赛程页面URL
            url = self.base_url
            logger.info(f"正在请求: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # 设置正确的编码
            response.encoding = "utf-8"

            # 解析HTML获取比赛信息
            games = self._parse_hupu_schedule(response.text)

            return games

        except requests.RequestException as e:
            logger.error(f"请求虎扑网站失败: {e}")
            return []

    def _parse_hupu_schedule(self, html: str) -> List[dict]:
        """
        解析虎扑赛程页面HTML，提取当天的比赛信息

        Args:
            html: HTML内容

        Returns:
            List[dict]: 比赛信息列表
        """

        try:
            soup = BeautifulSoup(html, "lxml")
            games = []
            today = datetime.now().strftime("%Y-%m-%d")

            # 将日期转换为 20251222这样的格式
            today = today.replace("-", "")

            # 从soup中获取script标签
            today_schedule = soup.find("script", id="__NEXT_DATA__", type="application/json")
            # 从 today_schedule 中提取对象数据
            today_schedule_data = json.loads(today_schedule.get_text())

            props = today_schedule_data.get("props", {})
            pageProps = props.get("pageProps", {})
            gameList = pageProps.get("gameList", [])

            for game in gameList:
                if game.get("day") == today:
                    games = game.get("matchList")

            return games

        except Exception as e:
            logger.error(f"解析HTML失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return []

    def _generate_game_id(self, game_info: dict, date: str) -> str:
        """
        为比赛生成唯一ID

        Args:
            game_info: 比赛信息字典

        Returns:
            str: 唯一标识符
        """
        # 使用比赛信息生成唯一ID
        # 格式: {date}_{home_team}_{away_team}_{uuid}
        home = game_info.get("homeTeamName", "").replace(" ", "_")
        away = game_info.get("awayTeamName", "").replace(" ", "_")
        uuid_part = str(uuid4())[:8]

        game_id = f"{date}_{away}_vs_{home}_{uuid_part}"

        print(game_id, "game_id")
        return game_id

    def get_game_status(self, match_id: str) -> Optional[dict]:
        """
        获取指定比赛的当前状态和评分数量

        Args:
            match_id: 比赛ID (data-match属性值)

        Returns:
            Optional[dict]: 包含以下字段的字典，获取失败返回None:
                - status: 比赛状态 - "未开始"/"进行中"/"已结束"
                - rating_count: 评分数量（整数），如果无法解析返回0
        """
        try:
            url = self.base_url
            logger.info(f"正在获取比赛 {match_id} 的状态，请求URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "lxml")

            # 查找指定match_id的比赛元素
            match_element = soup.find("div", {"class": "match-item", "data-match": match_id})

            if not match_element:
                logger.warning(f"未找到比赛ID为 {match_id} 的元素")
                return None

            # 在比赛元素内查找状态信息
            # 状态结构: <div class="mend"><span class="text-m-bold">已结束</span><a>4.4万评分</a></div>
            status_element = match_element.find("div", {"class": "mend"})

            if not status_element:
                logger.warning(f"比赛 {match_id} 未找到状态元素")
                return None

            # 提取状态文本
            status_span = status_element.find("span", {"class": "text-m-bold"})
            if not status_span:
                logger.warning(f"比赛 {match_id} 状态元素中未找到span标签")
                return None

            status = status_span.get_text(strip=True)

            # 提取评分数量
            rating_count = 0
            rating_link = status_element.find("a")
            if rating_link:
                rating_text = rating_link.get_text(strip=True)
                # 解析评分数量（如 "4.4万评分" -> 44000）
                rating_count = self._parse_rating_count(rating_text)
                logger.info(f"比赛 {match_id} 评分数量: {rating_count}")
            else:
                logger.debug(f"比赛 {match_id} 未找到评分信息")

            result = {"status": status, "rating_count": rating_count}
            logger.info(f"比赛 {match_id} 当前状态: {status}, 评分数量: {rating_count}")
            return result

        except requests.RequestException as e:
            logger.error(f"获取比赛状态失败 (网络错误): {e}")
            return None
        except Exception as e:
            logger.error(f"获取比赛状态失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return None

    def _parse_rating_count(self, rating_text: str) -> int:
        """
        解析评分数量文本，转换为整数

        Args:
            rating_text: 评分文本，如 "4.4万评分", "10.2万评分", "1234评分"

        Returns:
            int: 评分数量（整数）
        """
        try:
            # 移除"评分"字样
            rating_text = rating_text.replace("评分", "").strip()

            # 处理"万"单位
            if "万" in rating_text:
                # 提取数字部分（如 "4.4万" -> "4.4"）
                number_str = rating_text.replace("万", "").strip()
                number = float(number_str)
                # 转换为实际数量（乘以10000）
                return int(number * 10000)
            else:
                # 没有单位，直接转换为整数
                return int(float(rating_text))
        except Exception as e:
            logger.warning(f"解析评分数量失败: {rating_text}, 错误: {e}")
            return 0
