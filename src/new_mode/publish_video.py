"""
新模式视频发布模块

负责将新模式生成的视频发布到B站平台。
"""

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any

from loguru import logger
from bilibili_api import video_zone
from src.utils import call_llm

if TYPE_CHECKING:
    from src.vide_publish import VideoPublisher


def publish_video(
    video_path: str,
    video_publisher: "VideoPublisher",
    handle_json_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    发布视频到B站

    Args:
        video_path: 视频文件路径
        video_publisher: 视频发布器实例
        handle_json_data: 视频对应的原始数据信息，包含：
            - title: 内容标题
            - scoreCountNum: 评分数量
            - url: 内容URL
            - itemId: 内容ID

    Returns:
        bool: 发布是否成功
    """
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"视频文件不存在: {video_path}")
            return False

        logger.info(f"开始发布视频: {video_path}")

        # 生成视频标题（基于 handle_json_data）
        video_title = generate_video_title(handle_json_data)

        # 生成视频简介（基于 handle_json_data）
        video_description = "-"

        # 生成视频标签（基于 handle_json_data）
        video_tags = generate_video_tags(handle_json_data)

        # 获取视频分区ID（基于标题和分区信息）
        zone_tid = get_zone_tid_by_title(video_title)
        if not zone_tid:
            logger.warning("无法获取视频分区ID，使用默认值")
            zone_tid = None

        # 生成封面图（从视频第30帧提取上方0-450px区域）
        cover_path = video_publisher._generate_cover_image(video_path)
        if not cover_path:
            logger.warning("封面图生成失败，将不使用封面图上传")

        # 调用B站API上传视频
        upload_success = video_publisher._upload_to_bilibili(
            video_path=video_path,
            title=video_title,
            description=video_description,
            tags=video_tags,
            tid=zone_tid,
            cover=cover_path,
        )

        if not upload_success:
            logger.error("视频上传失败")
            return False

        logger.info("视频发布成功")
        return True

    except Exception as e:
        logger.error(f"视频发布失败: {e}", exc_info=True)
        return False


def generate_video_title(handle_json_data: Optional[Dict[str, Any]] = None) -> str:
    """
    生成视频标题

    Args:
        handle_json_data: 视频对应的原始数据信息

    Returns:
        str: 生成的视频标题
    """
    if not handle_json_data:
        return "精彩内容分享"

    title = handle_json_data.get("title", "精彩内容分享")

    return f"{title} ｜ 评分"


def generate_video_description(handle_json_data: Optional[Dict[str, Any]] = None) -> str:
    """
    生成视频简介

    Args:
        handle_json_data: 视频对应的原始数据信息

    Returns:
        str: 生成的视频简介
    """
    if not handle_json_data:
        return "精彩内容分享，欢迎观看！"

    title = handle_json_data.get("title", "精彩内容")
    score_count = handle_json_data.get("scoreCountNum", 0)
    url = handle_json_data.get("url", "")

    # 格式化评分数量
    if score_count >= 10000:
        score_str = f"{score_count / 10000:.1f}万"
    else:
        score_str = str(score_count)

    description = f"【{title}】\n\n"
    description += f"评分人数：{score_str}\n\n"
    if url:
        description += f"来源：{url}\n\n"
    description += "喜欢的话记得一键三连哦！"

    return description


def generate_video_tags(handle_json_data: Optional[Dict[str, Any]] = None) -> list:
    """
    生成视频标签

    使用大模型根据视频标题生成8个独立的标签，所有标签均由AI生成。

    Args:
        handle_json_data: 视频对应的原始数据信息

    Returns:
        list: 生成的视频标签列表，包含8个标签
    """
    if not handle_json_data:
        logger.warning("未提供 handle_json_data，返回默认标签")
        return ["精彩内容", "分享", "视频", "推荐", "热门", "必看", "收藏", "点赞"]

    # 获取视频标题
    title = handle_json_data.get("title", "")
    if not title:
        logger.warning("未找到视频标题，返回默认标签")
        return ["精彩内容", "分享", "视频", "推荐", "热门", "必看", "收藏", "点赞"]

    try:
        logger.info(f"使用大模型生成视频标签，标题: {title}")
        tags = _generate_tags_with_llm(title)

        # 确保返回8个标签
        if len(tags) < 8:
            logger.warning(f"生成的标签数量不足8个（{len(tags)}个），补充默认标签")
            default_tags = ["精彩内容", "分享", "视频", "推荐", "热门", "必看", "收藏", "点赞"]
            # 补充不重复的标签
            for tag in default_tags:
                if tag not in tags and len(tags) < 8:
                    tags.append(tag)
        elif len(tags) > 8:
            logger.warning(f"生成的标签数量超过8个（{len(tags)}个），截取前8个")
            tags = tags[:8]

        logger.info(f"生成的视频标签（共{len(tags)}个）: {tags}")
        return tags

    except Exception as e:
        logger.error(f"生成视频标签失败: {e}", exc_info=True)
        # 失败时返回默认标签
        return ["精彩内容", "分享", "视频", "推荐", "热门", "必看", "收藏", "点赞"]


def _generate_tags_with_llm(title: str) -> list:
    """
    使用大模型根据标题生成8个独立的标签

    Args:
        title: 视频标题

    Returns:
        list: 生成的标签列表
    """
    try:
        system_prompt = """你是一个B站视频标签生成助手。根据视频标题，生成8个相关的、独立的标签。

要求：
1. 生成恰好8个标签
2. 每个标签应该是独立的，不重复
3. 标签应该与视频标题内容相关
4. 标签应该简洁明了，每个标签2-6个汉字
5. 标签应该吸引观众，符合B站用户的兴趣
6. 标签可以包括：内容类型、主题、风格、特点等
7. 只返回标签列表，不要有其他说明文字

返回格式：返回一个JSON数组，包含8个字符串标签
例如：["标签1", "标签2", "标签3", "标签4", "标签5", "标签6", "标签7", "标签8"]"""

        user_prompt = f"""视频标题：{title}

请根据这个视频标题，生成8个相关的、独立的标签。标签应该简洁、吸引人，与视频内容相关。"""

        logger.info("调用大模型生成标签...")
        response = call_llm(
            user_content=user_prompt,
            system_content=system_prompt,
            enable_search=False,  # 标签生成不需要搜索
        )

        logger.info(f"大模型返回: {response[:200]}...")

        # 尝试从响应中提取JSON数组
        tags = _extract_tags_from_response(response)

        if tags and len(tags) > 0:
            logger.info(f"成功生成 {len(tags)} 个标签")
            return tags
        else:
            logger.warning("未能从大模型响应中提取标签，使用默认标签")
            return []

    except Exception as e:
        logger.error(f"使用大模型生成标签失败: {e}", exc_info=True)
        return []


def _extract_tags_from_response(response: str) -> list:
    """
    从大模型响应中提取标签列表

    Args:
        response: 大模型的响应文本

    Returns:
        list: 提取的标签列表
    """
    # 方法1: 尝试直接解析整个响应
    try:
        tags = json.loads(response.strip())
        if isinstance(tags, list):
            # 过滤掉非字符串元素，并清理标签
            tags = [str(tag).strip() for tag in tags if tag]
            return tags
    except json.JSONDecodeError:
        pass

    # 方法2: 尝试提取JSON数组代码块（如果被markdown代码块包裹）
    json_array_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
    if json_array_match:
        try:
            tags = json.loads(json_array_match.group(1))
            if isinstance(tags, list):
                tags = [str(tag).strip() for tag in tags if tag]
                return tags
        except json.JSONDecodeError:
            pass

    # 方法3: 尝试提取JSON数组（支持嵌套）
    json_array_match = re.search(r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]", response, re.DOTALL)
    if json_array_match:
        try:
            tags = json.loads(json_array_match.group(0))
            if isinstance(tags, list):
                tags = [str(tag).strip() for tag in tags if tag]
                return tags
        except json.JSONDecodeError:
            pass

    # 方法4: 尝试提取引号中的内容（作为备选方案）
    quoted_tags = re.findall(r'["\']([^"\']{2,10})["\']', response)
    if quoted_tags and len(quoted_tags) >= 4:  # 至少找到4个标签才认为有效
        return quoted_tags[:8]  # 最多返回8个

    logger.warning(f"无法从响应中提取标签: {response[:500]}")
    return []


def get_zone_tid_by_title(title: str) -> Optional[int]:
    """
    根据视频标题获取最合适的分区ID

    步骤：
    1. 从bilibili_api获取所有分区信息
    2. 将title和分区信息输入给大模型，让大模型输出最符合的分区id

    Args:
        title: 视频标题

    Returns:
        Optional[int]: 分区ID，如果获取失败则返回None
    """
    try:
        logger.info(f"开始获取视频分区ID，标题: {title}")

        # 第一步：从bilibili_api获取所有分区信息
        zone_list = video_zone.get_zone_list()
        logger.info(f"获取到 {len(zone_list)} 个分区信息")

        # 第二步：将title和分区信息输入给大模型，让大模型输出最符合的分区id
        zone_tid = _select_zone_with_llm(title, zone_list)

        if zone_tid:
            logger.info(f"成功获取分区ID: {zone_tid}")
        else:
            logger.warning("未能从大模型响应中提取分区ID")

        return zone_tid

    except Exception as e:
        logger.error(f"获取视频分区ID失败: {e}", exc_info=True)
        return None


def _select_zone_with_llm(title: str, zone_list: list) -> Optional[int]:
    """
    使用大模型根据标题选择最合适的分区ID

    Args:
        title: 视频标题
        zone_list: 所有分区信息列表

    Returns:
        Optional[int]: 分区ID，如果获取失败则返回None
    """
    try:
        # 构建分区信息字符串，只包含tid和name，便于大模型理解
        zone_info_list = []
        for zone in zone_list:
            zone_info = {
                "tid": zone.get("tid"),
                "name": zone.get("name", ""),
            }
            # 如果有父分区信息，也包含进去
            if "father" in zone and zone["father"]:
                father_name = zone["father"].get("name", "")
                zone_info["name"] = f"{father_name} - {zone_info['name']}"
            zone_info_list.append(zone_info)

        # 构建系统提示词
        system_prompt = """你是一个B站视频分区选择助手。根据视频标题，从提供的分区列表中选择一个最符合的分区。

要求：
1. 仔细分析视频标题的内容和主题
2. 从提供的分区列表中选择最匹配的分区
3. 优先选择子分区（更具体），如果没有合适的子分区，再选择主分区
4. 只返回分区的tid（数字ID），不要有其他说明文字
5. 如果实在无法确定，选择一个最接近的分区

返回格式：只返回一个数字，例如：171"""

        # 构建用户提示词
        zones_text = "\n".join(
            [
                f"分区ID: {zone['tid']}, 分区名称: {zone['name']}"
                for zone in zone_info_list
                if zone.get("tid") is not None
            ]
        )

        user_prompt = f"""视频标题：{title}

可用分区列表：
{zones_text}

请根据视频标题，从上述分区列表中选择一个最符合的分区，只返回该分区的ID（tid）数字。"""

        logger.info("调用大模型选择分区...")
        response = call_llm(
            user_content=user_prompt,
            system_content=system_prompt,
            enable_search=False,  # 分区选择不需要搜索
        )

        logger.info(f"大模型返回: {response[:200]}...")

        # 从响应中提取分区ID
        zone_tid = _extract_zone_tid_from_response(response, zone_list)

        if zone_tid:
            logger.info(f"成功选择分区ID: {zone_tid}")
            return zone_tid
        else:
            logger.warning("未能从大模型响应中提取分区ID")
            return None

    except Exception as e:
        logger.error(f"使用大模型选择分区失败: {e}", exc_info=True)
        return None


def _extract_zone_tid_from_response(response: str, zone_list: list) -> Optional[int]:
    """
    从大模型响应中提取分区ID

    Args:
        response: 大模型的响应文本
        zone_list: 所有分区信息列表，用于验证提取的ID是否有效

    Returns:
        Optional[int]: 提取的分区ID，如果提取失败或无效则返回None
    """
    # 构建有效的tid集合，用于验证
    valid_tids = {zone.get("tid") for zone in zone_list if zone.get("tid") is not None}

    # 方法1: 尝试直接提取数字
    numbers = re.findall(r"\d+", response)
    for num_str in numbers:
        try:
            tid = int(num_str)
            if tid in valid_tids:
                logger.info(f"从响应中提取到有效的分区ID: {tid}")
                return tid
        except ValueError:
            continue

    # 方法2: 尝试解析JSON（如果返回的是JSON格式）
    try:
        parsed = json.loads(response.strip())
        if isinstance(parsed, dict) and "tid" in parsed:
            tid = int(parsed["tid"])
            if tid in valid_tids:
                return tid
        elif isinstance(parsed, int):
            if parsed in valid_tids:
                return parsed
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    # 方法3: 尝试从markdown代码块中提取
    code_block_match = re.search(r"```(?:json)?\s*(\d+)\s*```", response)
    if code_block_match:
        try:
            tid = int(code_block_match.group(1))
            if tid in valid_tids:
                return tid
        except ValueError:
            pass

    logger.warning(f"无法从响应中提取有效的分区ID: {response[:500]}")
    return None
