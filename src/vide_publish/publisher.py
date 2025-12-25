"""
视频发布器

负责将生成好的视频发布到B站平台。
"""

import os
import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger

from src.utils import call_llm

# GameInfo 在函数内部延迟导入，避免循环导入

import ffmpeg

from bilibili_api import (
    video_uploader,
    Credential,
    video_zone,
)


class VideoPublisher:
    """视频发布器"""

    def __init__(
        self,
        sessdata: Optional[str] = None,
        bili_jct: Optional[str] = None,
    ):
        """
        初始化视频发布器

        Args:
            sessdata: B站登录凭证 sessdata（从环境变量 BILIBILI_SESSDATA 读取或直接传入）
            bili_jct: B站登录凭证 bili_jct（从环境变量 BILIBILI_BILI_JCT 读取或直接传入）
            buvid3: B站登录凭证 buvid3（从环境变量 BILIBILI_BVID3 读取或直接传入，可选）
        """
        self.sessdata = sessdata or os.getenv("BILIBILI_SESSDATA")
        self.bili_jct = bili_jct or os.getenv("BILIBILI_BILI_JCT")
        logger.debug(
            f"凭证初始化: sessdata={'已设置' if self.sessdata else 'None'}, bili_jct={'已设置' if self.bili_jct else 'None'}"
        )

        if not self.sessdata or not self.bili_jct:
            logger.warning("登录凭证未设置: sessdata 或 bili_jct 为空")
            self.credential = None
        else:
            try:
                self.credential = Credential(sessdata=self.sessdata, bili_jct=self.bili_jct)
                logger.info("B站登录凭证配置成功")
            except Exception as e:
                logger.error(f"B站登录凭证配置失败: {e}")
                self.credential = None

        logger.info("视频发布器初始化完成")

    def publish_video(self, video_path: str | Path, game_info) -> bool:
        """
        发布视频到B站

        Args:
            video_path: 视频文件路径
            game_info: 比赛信息 (GameInfo 对象)

        Returns:
            bool: 发布是否成功
        """
        # 延迟导入避免循环导入
        from src.schedule.models import GameInfo

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

            # 2. 生成比赛详细信息（用于视频简介）
            video_description = self._generate_game_description(game_info)
            logger.info(f"生成的比赛详细信息: {video_description[:500]}...")

            # 3. 生成视频标签
            video_tags = self._generate_video_tags(game_info)

            # 4. 制作封面图（从视频第30帧提取上方0-200px区域）
            cover_path = self._generate_cover_image(video_path)
            if not cover_path:
                logger.warning("封面图生成失败，将不使用封面图上传")

            # 5. 获取体育篮球分区ID
            zone_tid = self._get_basketball_zone_id()
            if not zone_tid:
                logger.warning("无法获取篮球分区ID，使用默认值 171")
                zone_tid = 171

            # 6. 调用B站API上传视频
            upload_success = self._upload_to_bilibili(
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

    def _generate_video_title(self, game_info) -> str:
        """
        生成视频标题

        标题格式参考：独木难支！东契奇伤退、詹姆斯空砍36分，湖人88-103不敌快船
        包含：吸引人的开头、比赛关键信息、比分和胜负关系

        Args:
            game_info: 比赛信息 (GameInfo 对象)

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

    def _generate_game_description(self, game_info) -> str:
        """
        生成比赛详细信息

        用于视频简介，包含比赛的详细描述、关键时刻、球员表现等。

        Args:
            game_info: 比赛信息 (GameInfo 对象)

        Returns:
            str: 生成的比赛详细信息
        """
        try:
            # 构造提示词，只提供比赛标识信息，让模型自己搜索详细信息
            system_prompt = """你是一个专业的体育比赛分析助手。你需要根据比赛信息生成详细的比赛描述。

描述要求：
1. 开头简要介绍比赛双方和比赛结果
2. 详细描述比赛的关键时刻和亮点
3. 介绍主要球员的表现和数据
4. 分析比赛的转折点和精彩瞬间
5. 结尾可以总结比赛的意义或影响

描述应该：
- 详细且生动，能够吸引观众
- 包含具体的比分、数据等信息
- 语言流畅，适合作为视频简介
- 长度控制在200-500字左右

请只返回描述内容，不要包含其他说明文字。"""

            user_prompt = f"""请为以下NBA比赛生成详细的比赛描述：

比赛：{game_info.away_team_name} vs {game_info.home_team_name}

请搜索这场比赛的最新信息（包括比分、胜负关系、球员表现、比赛亮点、关键时刻等），然后生成一份详细的比赛描述，用于视频简介。"""

            description = call_llm(
                user_content=user_prompt,
                system_content=system_prompt,
                enable_search=True,  # 启用搜索功能，让模型自己查找比赛信息
            )

            # 清理描述（移除可能的引号、多余换行等）
            description = description.strip().strip('"').strip("'").strip()
            # 移除可能的"描述："等前缀
            if "描述：" in description:
                description = description.split("描述：", 1)[-1]
            if "描述:" in description:
                description = description.split("描述:", 1)[-1]
            if "简介：" in description:
                description = description.split("简介：", 1)[-1]
            if "简介:" in description:
                description = description.split("简介:", 1)[-1]

            logger.info(f"成功生成比赛详细信息，长度: {len(description)} 字符")
            return description

        except Exception as e:
            logger.error(f"生成比赛详细信息失败: {e}", exc_info=True)
            # 如果生成失败，返回一个简单的默认描述
            home_score = game_info.home_score if game_info.home_score else "0"
            away_score = game_info.away_score if game_info.away_score else "0"
            default_description = (
                f"本场比赛是 {game_info.away_team_name} 对阵 {game_info.home_team_name} 的精彩对决。"
                f"最终比分为 {game_info.away_team_name} {away_score}-{home_score} {game_info.home_team_name}。"
                f"比赛阶段：{game_info.competition_stage_desc}。"
            )
            logger.warning(f"使用默认描述")
            return default_description

    def _generate_cover_image(self, video_path: Path) -> Optional[str]:
        """
        生成视频封面图

        从视频的第30帧提取，并裁剪上方0-450px区域。

        Args:
            video_path: 视频文件路径

        Returns:
            Optional[str]: 封面图文件路径，如果失败返回None
        """
        if not ffmpeg:
            logger.error("ffmpeg-python 未安装，无法生成封面图")
            return None

        try:
            logger.info(f"开始生成封面图: {video_path}")

            # 获取视频信息以确定宽度
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
            )

            if not video_stream:
                logger.error("未找到视频流")
                return None

            width = int(video_stream.get("width", 0))
            if width == 0:
                logger.error("无法获取视频宽度")
                return None

            # 生成封面图输出路径
            cover_path = video_path.parent / f"{video_path.stem}_cover.jpg"

            logger.info(f"从视频第30帧提取，裁剪上方0-450px区域")
            logger.info(f"视频宽度: {width}px，裁剪高度: 450px")

            # 使用 ffmpeg 提取第30帧并裁剪
            # select=eq(n\,29): 选择第30帧（从0开始计数，所以是29）
            # crop=width:450:0:0: 裁剪上方450px区域（宽度:高度:x:y）
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.filter(stream, "select", "eq(n,29)")  # 选择第30帧（索引从0开始）
            stream = ffmpeg.filter(stream, "crop", width, 450, 0, 0)  # 裁剪上方450px
            stream = ffmpeg.output(
                stream,
                str(cover_path),
                vframes=1,  # 只输出1帧
            )

            # 执行提取，覆盖已存在的输出文件
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            if cover_path.exists():
                file_size_kb = cover_path.stat().st_size / 1024
                logger.info(f"封面图生成成功: {cover_path} ({file_size_kb:.2f} KB)")
                return str(cover_path)
            else:
                logger.error("封面图文件未生成")
                return None

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg 处理失败: {e}")
            if e.stderr:
                logger.error(f"FFmpeg 错误信息: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"生成封面图失败: {e}", exc_info=True)
            return None

    def _get_basketball_zone_id(self) -> Optional[int]:
        """
        获取体育篮球分区的ID

        参考文档: https://nemo2011.github.io/bilibili-api/#/modules/video_zone

        Returns:
            Optional[int]: 篮球分区的 tid，如果未找到返回 None
        """
        if not video_zone:
            logger.error("video_zone 模块不可用，无法获取分区信息")
            return None

        try:
            # 方法1: 根据名称查找"篮球"分区
            main_zone, sub_zone = video_zone.get_zone_info_by_name("篮球")

            if sub_zone and "tid" in sub_zone:
                tid = sub_zone["tid"]
                logger.info(f"找到篮球分区: {sub_zone.get('name', 'N/A')}, tid={tid}")
                return tid
            elif main_zone and "tid" in main_zone:
                tid = main_zone["tid"]
                logger.info(f"找到篮球分区: {main_zone.get('name', 'N/A')}, tid={tid}")
                return tid

            # 方法2: 遍历所有分区查找体育-篮球
            logger.info("通过名称未找到，遍历所有分区查找体育-篮球...")
            zone_list = video_zone.get_zone_list_sub()

            for main_zone in zone_list:
                # 查找体育分区
                if "体育" in main_zone.get("name", ""):
                    if "sub" in main_zone:
                        for sub_zone in main_zone["sub"]:
                            if "篮球" in sub_zone.get("name", ""):
                                tid = sub_zone.get("tid")
                                if tid:
                                    logger.info(
                                        f"找到体育-篮球分区: {main_zone.get('name', 'N/A')} - "
                                        f"{sub_zone.get('name', 'N/A')}, tid={tid}"
                                    )
                                    return tid

            logger.warning("未找到篮球分区，使用默认值 171")
            return 171  # 默认篮球分区ID

        except Exception as e:
            logger.error(f"获取篮球分区ID失败: {e}", exc_info=True)
            logger.warning("使用默认值 171")
            return 171  # 默认篮球分区ID

    def _generate_video_tags(self, game_info) -> list[str]:
        """
        生成视频标签

        Args:
            game_info: 比赛信息

        Returns:
            list[str]: 视频标签列表
        """
        try:
            # 生成基础标签
            tags = [
                "NBA",
                "篮球",
                game_info.away_team_name,
                game_info.home_team_name,
            ]

            # 如果比赛阶段不为空，添加为标签
            if game_info.competition_stage_desc:
                tags.append(game_info.competition_stage_desc)

            # 使用大模型生成更多相关标签
            system_prompt = """你是一个专业的视频标签生成助手。根据比赛信息生成5-10个相关的视频标签。

标签要求：
- 与比赛内容相关
- 能够吸引目标观众
- 包含球队、球员、比赛类型等关键词
- 每个标签2-6个字

请只返回标签，用逗号分隔，不要包含其他说明文字。"""

            user_prompt = f"""请为以下NBA比赛生成视频标签：

比赛：{game_info.away_team_name} vs {game_info.home_team_name}

请生成3-5个相关的视频标签："""

            try:
                llm_tags = call_llm(
                    user_content=user_prompt,
                    system_content=system_prompt,
                    enable_search=False,
                )
                # 解析标签
                llm_tags_list = [
                    tag.strip() for tag in llm_tags.replace("，", ",").split(",") if tag.strip()
                ]
                tags.extend(llm_tags_list)
            except Exception as e:
                logger.warning(f"使用大模型生成标签失败: {e}，使用默认标签")

            # 去重并限制数量（B站最多20个标签）
            tags = list(dict.fromkeys(tags))[:20]

            logger.info(f"生成的视频标签: {tags}")
            return tags

        except Exception as e:
            logger.error(f"生成视频标签失败: {e}", exc_info=True)
            # 返回默认标签
            return ["NBA", "篮球", game_info.away_team_name, game_info.home_team_name]

    def _upload_to_bilibili(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        copyright: int = 1,  # 1=原创，2=转载
        tid: Optional[int] = None,  # 分区ID，如果为None则自动获取篮球分区
        source: str = "",  # 转载来源，原创时为空
        cover: Optional[str] = None,  # 封面图片路径，可选
    ) -> bool:
        """
        上传视频到B站

        参考文档: https://nemo2011.github.io/bilibili-api/#/modules/video_uploader

        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频简介
            tags: 视频标签列表
            copyright: 版权类型，1=原创，2=转载
            tid: 分区ID，171=篮球
            source: 转载来源，原创时为空
            cover: 封面图片路径，可选

        Returns:
            bool: 上传是否成功
        """
        if not video_uploader or not Credential:
            logger.error("bilibili-api-python 未安装，无法上传视频")
            logger.info("请运行: pip install bilibili-api-python")
            return False

        if not self.credential:
            logger.error("未配置B站登录凭证，无法上传视频")
            logger.info(
                "请设置环境变量 BILIBILI_SESSDATA 和 BILIBILI_BILI_JCT，"
                "或通过构造函数传入登录凭证"
            )
            return False

        try:
            # 如果没有提供 tid，自动获取篮球分区
            if tid is None:
                tid = self._get_basketball_zone_id()
                if not tid:
                    logger.warning("无法获取篮球分区ID，使用默认值 171")
                    tid = 171

            logger.info(f"开始上传视频到B站: {video_path}")
            logger.info(f"标题: {title}")
            logger.info(f"标签: {tags}")
            logger.info(f"分区ID (tid): {tid}")

            # 使用 video_uploader 上传视频
            # 根据文档: https://nemo2011.github.io/bilibili-api/#/modules/video_uploader
            # VideoUploader 的使用方式：
            # 1. 创建 VideoUploaderPage 对象（包含视频路径）
            # 2. 创建 VideoUploader 对象（传入 pages 列表和 meta）
            # 3. 调用 start() 方法开始上传

            # 创建 VideoUploaderPage，path 参数是视频文件路径
            page = video_uploader.VideoUploaderPage(
                path=str(video_path),
                title=title,
                description=description,
            )

            # 创建 VideoUploader，pages 参数是 VideoUploaderPage 列表
            # 将标签列表转换为字符串（用逗号分隔）
            tag_str = ",".join(tags) if tags else ""

            # 构建 meta 数据，使用标准初始结构
            vu_meta = video_uploader.VideoMeta(
                tid=tid,
                title=title,
                tags=tags,
                desc=description,
                cover=cover if cover and Path(cover).exists() else "",
                no_reprint=True,
            )
            uploader = video_uploader.VideoUploader(
                pages=[page],  # 视频文件路径通过 pages 参数传入
                meta=vu_meta,
                credential=self.credential,
                cover=cover if cover and Path(cover).exists() else "",
            )

            # 开始上传
            logger.info("开始上传视频文件...")
            logger.info("上传过程可能需要较长时间，请耐心等待...")

            # start() 方法是异步的，使用 asyncio.run() 同步等待上传完成
            # 成功时返回包含 bvid 的字典，失败时返回 None 或抛出异常
            result = asyncio.run(uploader.start())

            if result and isinstance(result, dict):
                bvid = result.get("bvid") or result.get("data", {}).get("bvid")
                if bvid:
                    logger.info(f"✓ 视频上传成功！")
                    logger.info(f"  视频ID (BVID): {bvid}")
                    logger.info(f"  视频链接: https://www.bilibili.com/video/{bvid}")
                    return True
                else:
                    logger.warning(f"上传返回结果但未找到 bvid: {result}")
                    # 即使没有 bvid，如果返回了结果，也认为上传成功
                    return True
            elif result:
                # 如果返回了非字典类型的结果，也认为可能成功
                logger.info(f"视频上传完成，返回结果: {result}")
                return True
            else:
                logger.error("视频上传失败：未返回结果")
                return False

        except Exception as e:
            logger.error(f"上传视频到B站失败: {e}", exc_info=True)
            return False
