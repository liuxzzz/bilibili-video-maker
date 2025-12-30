"""
Chrome Cookies读取工具

从Chrome浏览器的cookies数据库中读取B站登录凭证。
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger


def get_chrome_cookies_path() -> Optional[Path]:
    """
    获取Chrome cookies数据库路径

    Returns:
        Optional[Path]: cookies数据库路径，如果未找到则返回None
    """
    # macOS Chrome默认路径
    home = Path.home()
    chrome_paths = [
        home / "Library/Application Support/Google/Chrome/Default/Cookies",
        home / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
    ]

    # 检查是否存在
    for path in chrome_paths:
        if path.exists():
            logger.debug(f"找到Chrome cookies数据库: {path}")
            return path

    logger.warning("未找到Chrome cookies数据库")
    return None


def get_bilibili_credentials_from_chrome() -> Tuple[Optional[str], Optional[str]]:
    """
    从Chrome cookies中获取B站登录凭证

    优先从 https://www.bilibili.com/ 页面的cookies中读取。

    Returns:
        Tuple[Optional[str], Optional[str]]: (sessdata, bili_jct)，如果未找到则返回(None, None)
    """
    cookies_path = get_chrome_cookies_path()
    if not cookies_path:
        logger.error("无法找到Chrome cookies数据库")
        return None, None

    sessdata = None
    bili_jct = None

    try:
        # Chrome的cookies数据库可能被锁定，需要复制一份来读取
        import tempfile
        import shutil

        # 创建临时副本
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
            tmp_path = tmp_file.name

        try:
            # 复制cookies数据库到临时文件
            shutil.copy2(cookies_path, tmp_path)

            # 连接SQLite数据库
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()

            # 查询SESSDATA（优先查询 www.bilibili.com，然后查询其他bilibili.com域名）
            # Chrome中host_key可能的值：'www.bilibili.com', '.bilibili.com', 'bilibili.com' 等
            cursor.execute(
                """
                SELECT value, host_key FROM cookies 
                WHERE (
                    host_key = 'www.bilibili.com' 
                    OR host_key = '.bilibili.com'
                    OR host_key LIKE '%bilibili.com'
                )
                AND name = 'SESSDATA'
                ORDER BY 
                    CASE 
                        WHEN host_key = 'www.bilibili.com' THEN 1
                        WHEN host_key = '.bilibili.com' THEN 2
                        ELSE 3
                    END,
                    creation_utc DESC
                LIMIT 1
            """
            )
            sessdata_result = cursor.fetchone()
            if sessdata_result:
                sessdata = sessdata_result[0]
                host_key = sessdata_result[1]
                logger.info(f"成功从Chrome cookies中获取SESSDATA (来源: {host_key})")

            # 查询bili_jct（优先查询 www.bilibili.com，然后查询其他bilibili.com域名）
            cursor.execute(
                """
                SELECT value, host_key FROM cookies 
                WHERE (
                    host_key = 'www.bilibili.com' 
                    OR host_key = '.bilibili.com'
                    OR host_key LIKE '%bilibili.com'
                )
                AND name = 'bili_jct'
                ORDER BY 
                    CASE 
                        WHEN host_key = 'www.bilibili.com' THEN 1
                        WHEN host_key = '.bilibili.com' THEN 2
                        ELSE 3
                    END,
                    creation_utc DESC
                LIMIT 1
            """
            )
            bili_jct_result = cursor.fetchone()
            if bili_jct_result:
                bili_jct = bili_jct_result[0]
                host_key = bili_jct_result[1]
                logger.info(f"成功从Chrome cookies中获取bili_jct (来源: {host_key})")

            conn.close()

        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if sessdata and bili_jct:
            logger.info("成功从Chrome cookies中获取B站登录凭证")
            return sessdata, bili_jct
        else:
            missing = []
            if not sessdata:
                missing.append("SESSDATA")
            if not bili_jct:
                missing.append("bili_jct")
            logger.warning(f"未能从Chrome cookies中获取: {', '.join(missing)}")
            logger.info("提示: 请确保已在Chrome中访问 https://www.bilibili.com/ 并登录")
            return sessdata, bili_jct

    except Exception as e:
        logger.error(f"从Chrome cookies读取凭证失败: {e}", exc_info=True)
        return None, None


def get_bilibili_sessdata() -> Optional[str]:
    """
    获取B站SESSDATA凭证

    优先从Chrome cookies中获取，如果失败则从环境变量读取。

    Returns:
        Optional[str]: SESSDATA值，如果未找到则返回None
    """
    sessdata, _ = get_bilibili_credentials_from_chrome()
    if sessdata:
        return sessdata

    # 如果从Chrome获取失败，尝试从环境变量读取
    sessdata = os.getenv("BILIBILI_SESSDATA")
    if sessdata:
        logger.info("从环境变量获取SESSDATA")
        return sessdata

    logger.warning("未能获取SESSDATA（既不在Chrome cookies中，也不在环境变量中）")
    return None


def get_bilibili_bili_jct() -> Optional[str]:
    """
    获取B站bili_jct凭证

    优先从Chrome cookies中获取，如果失败则从环境变量读取。

    Returns:
        Optional[str]: bili_jct值，如果未找到则返回None
    """
    _, bili_jct = get_bilibili_credentials_from_chrome()
    if bili_jct:
        return bili_jct

    # 如果从Chrome获取失败，尝试从环境变量读取
    bili_jct = os.getenv("BILIBILI_BILI_JCT")
    if bili_jct:
        logger.info("从环境变量获取bili_jct")
        return bili_jct

    logger.warning("未能获取bili_jct（既不在Chrome cookies中，也不在环境变量中）")
    return None
