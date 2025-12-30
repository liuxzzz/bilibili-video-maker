"""
测试Chrome Cookies读取功能

测试从Chrome浏览器cookies中读取B站登录凭证的功能。
"""

import os
import sys
from pathlib import Path
from loguru import logger
from bilibili_api import Credential

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.cookie_reader import (
    get_chrome_cookies_path,
    get_bilibili_credentials_from_chrome,
    get_bilibili_sessdata,
    get_bilibili_bili_jct,
)


def test_chrome_cookies_path():
    """测试获取Chrome cookies路径"""
    logger.info("=" * 60)
    logger.info("测试1: 获取Chrome cookies数据库路径")
    logger.info("=" * 60)

    cookies_path = get_chrome_cookies_path()

    if cookies_path:
        logger.info(f"✓ 找到Chrome cookies数据库: {cookies_path}")
        logger.info(f"  路径存在: {cookies_path.exists()}")
        if cookies_path.exists():
            file_size = cookies_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"  文件大小: {file_size:.2f} MB")
        return True
    else:
        logger.warning("✗ 未找到Chrome cookies数据库")
        logger.info("提示: 请确保已安装Chrome浏览器")
        return False


def test_get_credentials_from_chrome():
    """测试从Chrome cookies中获取凭证"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 从Chrome cookies中获取B站登录凭证")
    logger.info("=" * 60)

    sessdata, bili_jct = get_bilibili_credentials_from_chrome()

    logger.info("\n获取结果:")
    if sessdata:
        logger.info(f"  ✓ SESSDATA: {sessdata[:30]}...{sessdata[-10:]}")
        logger.info(f"    长度: {len(sessdata)} 字符")
    else:
        logger.error("  ✗ SESSDATA: 未获取到")

    if bili_jct:
        logger.info(f"  ✓ bili_jct: {bili_jct[:30]}...{bili_jct[-10:]}")
        logger.info(f"    长度: {len(bili_jct)} 字符")
    else:
        logger.error("  ✗ bili_jct: 未获取到")

    if sessdata and bili_jct:
        logger.info("\n✓ 成功从Chrome cookies中获取到完整凭证")
        return True, sessdata, bili_jct
    else:
        logger.warning("\n⚠ 未能从Chrome cookies中获取完整凭证")
        logger.info("\n提示:")
        logger.info("  1. 请确保已在Chrome中访问 https://www.bilibili.com/ 并登录")
        logger.info("  2. 检查Chrome cookies数据库中是否存在SESSDATA和bili_jct")
        logger.info("  3. 如果Chrome未安装或cookies数据库不存在，将回退到环境变量")
        return False, sessdata, bili_jct


def test_get_sessdata():
    """测试获取SESSDATA（优先从Chrome，失败则从环境变量）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 获取SESSDATA（优先Chrome，失败则环境变量）")
    logger.info("=" * 60)

    sessdata = get_bilibili_sessdata()

    if sessdata:
        logger.info(f"✓ 成功获取SESSDATA: {sessdata[:30]}...{sessdata[-10:]}")
        logger.info(f"  长度: {len(sessdata)} 字符")
        return True
    else:
        logger.error("✗ 未能获取SESSDATA")
        logger.info("提示: 请确保Chrome中有cookies或设置了环境变量BILIBILI_SESSDATA")
        return False


def test_get_bili_jct():
    """测试获取bili_jct（优先从Chrome，失败则从环境变量）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 获取bili_jct（优先Chrome，失败则环境变量）")
    logger.info("=" * 60)

    bili_jct = get_bilibili_bili_jct()

    if bili_jct:
        logger.info(f"✓ 成功获取bili_jct: {bili_jct[:30]}...{bili_jct[-10:]}")
        logger.info(f"  长度: {len(bili_jct)} 字符")
        return True
    else:
        logger.error("✗ 未能获取bili_jct")
        logger.info("提示: 请确保Chrome中有cookies或设置了环境变量BILIBILI_BILI_JCT")
        return False


def test_credential_validity(sessdata: str, bili_jct: str):
    """测试凭证有效性"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 验证凭证有效性")
    logger.info("=" * 60)

    if not sessdata or not bili_jct:
        logger.warning("⚠ 凭证不完整，跳过有效性测试")
        return False

    try:
        logger.info("创建凭证对象...")
        credential = Credential(sessdata=sessdata, bili_jct=bili_jct)
        logger.info("✓ 凭证对象创建成功")

        logger.info("验证凭证有效性...")
        import asyncio

        async def check_credential():
            result = await credential.check_valid()
            return result

        is_valid = asyncio.run(check_credential())

        if is_valid:
            logger.info("✓ 凭证有效！可以正常使用")
            return True
        else:
            logger.error("✗ 凭证无效！")
            logger.error("\n可能的原因：")
            logger.error("  1. 凭证已过期，请重新登录B站")
            logger.error("  2. Chrome中的cookies已过期")
            logger.error("  3. 账号状态异常")
            logger.error("\n解决方法：")
            logger.error("  1. 在Chrome中访问 https://www.bilibili.com/ 并重新登录")
            logger.error("  2. 确保登录状态有效")
            return False

    except Exception as e:
        logger.error(f"✗ 验证凭证时出错: {e}")
        logger.exception(e)
        return False


def compare_with_env_vars():
    """对比Chrome cookies和环境变量中的凭证"""
    logger.info("\n" + "=" * 60)
    logger.info("测试6: 对比Chrome cookies和环境变量")
    logger.info("=" * 60)

    # 从Chrome获取
    chrome_sessdata, chrome_bili_jct = get_bilibili_credentials_from_chrome()

    # 从环境变量获取
    env_sessdata = os.getenv("BILIBILI_SESSDATA")
    env_bili_jct = os.getenv("BILIBILI_BILI_JCT")

    logger.info("\nChrome cookies:")
    if chrome_sessdata:
        logger.info(f"  SESSDATA: {chrome_sessdata[:20]}...{chrome_sessdata[-10:]}")
    else:
        logger.info("  SESSDATA: 未找到")

    if chrome_bili_jct:
        logger.info(f"  bili_jct: {chrome_bili_jct[:20]}...{chrome_bili_jct[-10:]}")
    else:
        logger.info("  bili_jct: 未找到")

    logger.info("\n环境变量:")
    if env_sessdata:
        logger.info(f"  BILIBILI_SESSDATA: {env_sessdata[:20]}...{env_sessdata[-10:]}")
    else:
        logger.info("  BILIBILI_SESSDATA: 未设置")

    if env_bili_jct:
        logger.info(f"  BILIBILI_BILI_JCT: {env_bili_jct[:20]}...{env_bili_jct[-10:]}")
    else:
        logger.info("  BILIBILI_BILI_JCT: 未设置")

    # 对比
    logger.info("\n对比结果:")
    if chrome_sessdata and env_sessdata:
        if chrome_sessdata == env_sessdata:
            logger.info("  ✓ SESSDATA: Chrome cookies和环境变量一致")
        else:
            logger.warning("  ⚠ SESSDATA: Chrome cookies和环境变量不一致")
            logger.info("    系统将优先使用Chrome cookies中的值")

    if chrome_bili_jct and env_bili_jct:
        if chrome_bili_jct == env_bili_jct:
            logger.info("  ✓ bili_jct: Chrome cookies和环境变量一致")
        else:
            logger.warning("  ⚠ bili_jct: Chrome cookies和环境变量不一致")
            logger.info("    系统将优先使用Chrome cookies中的值")


def main():
    """主测试函数"""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    )

    logger.info("\n" + "=" * 60)
    logger.info("Chrome Cookies读取功能测试")
    logger.info("=" * 60)

    results = {}

    # 测试1: 获取Chrome cookies路径
    results["cookies_path"] = test_chrome_cookies_path()

    # 测试2: 从Chrome获取凭证
    success, sessdata, bili_jct = test_get_credentials_from_chrome()
    results["get_credentials"] = success

    # 测试3: 获取SESSDATA
    results["get_sessdata"] = test_get_sessdata()

    # 测试4: 获取bili_jct
    results["get_bili_jct"] = test_get_bili_jct()

    # 测试5: 验证凭证有效性（如果获取到了）
    if sessdata and bili_jct:
        results["credential_validity"] = test_credential_validity(sessdata, bili_jct)
    else:
        logger.warning("\n⚠ 跳过凭证有效性测试（未获取到完整凭证）")
        results["credential_validity"] = None

    # 测试6: 对比Chrome和环境变量
    compare_with_env_vars()

    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if v is not None)

    for test_name, result in results.items():
        if result is True:
            logger.info(f"  ✓ {test_name}: 通过")
        elif result is False:
            logger.error(f"  ✗ {test_name}: 失败")
        else:
            logger.warning(f"  ⚠ {test_name}: 跳过")

    logger.info(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total and total > 0:
        logger.info("\n✓ 所有测试通过！Chrome cookies读取功能正常")
        return True
    else:
        logger.warning("\n⚠ 部分测试未通过，请检查上述提示")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
