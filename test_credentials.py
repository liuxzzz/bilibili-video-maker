"""
快速测试B站登录凭证是否有效
"""

import os
import sys
from loguru import logger
from bilibili_api import Credential, user


def test_credentials():
    """测试B站登录凭证"""
    logger.info("=" * 60)
    logger.info("测试B站登录凭证")
    logger.info("=" * 60)

    # 读取环境变量
    sessdata = os.getenv("BILIBILI_SESSDATA")
    bili_jct = os.getenv("BILIBILI_BILI_JCT")
    buvid3 = os.getenv("BILIBILI_BUVID3")

    # 检查是否设置
    logger.info("\n1. 检查环境变量:")
    if sessdata:
        logger.info(f"  ✓ SESSDATA: {sessdata[:20]}...{sessdata[-10:]}")
    else:
        logger.error("  ✗ SESSDATA: 未设置")

    if bili_jct:
        logger.info(f"  ✓ bili_jct: {bili_jct[:20]}...{bili_jct[-10:]}")
    else:
        logger.error("  ✗ bili_jct: 未设置")

    if buvid3:
        logger.info(f"  ✓ buvid3: {buvid3[:20]}...{buvid3[-10:]}")
    else:
        logger.warning("  ⚠ buvid3: 未设置（推荐设置）")

    if not sessdata or not bili_jct:
        logger.error("\n凭证不完整，无法测试")
        logger.error("请设置环境变量：")
        logger.error("  export BILIBILI_SESSDATA='your_sessdata'")
        logger.error("  export BILIBILI_BILI_JCT='your_bili_jct'")
        logger.error("  export BILIBILI_BUVID3='your_buvid3'")
        return False

    # 创建凭证对象
    logger.info("\n2. 创建凭证对象...")
    try:
        if buvid3:
            credential = Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)
            logger.info("  ✓ 凭证对象创建成功（包含 buvid3）")
        else:
            credential = Credential(sessdata=sessdata, bili_jct=bili_jct)
            logger.info("  ✓ 凭证对象创建成功")
    except Exception as e:
        logger.error(f"  ✗ 凭证对象创建失败: {e}")
        return False

    # 测试凭证有效性
    logger.info("\n3. 测试凭证有效性...")
    try:
        import asyncio

        async def check_credential():
            # 尝试获取当前用户信息
            result = await credential.check_valid()
            return result

        is_valid = asyncio.run(check_credential())

        if is_valid:
            logger.info("  ✓ 凭证有效！")

            # 获取用户信息
            try:

                async def get_user_info():
                    # 获取用户ID（从cookie中解析）
                    import http.cookies

                    cookie = http.cookies.SimpleCookie()
                    cookie.load(f"SESSDATA={sessdata}")

                    # 从SESSDATA中解析用户信息
                    # 注意：这里只是示例，实际获取用户信息需要调用API
                    logger.info("\n4. 用户信息:")
                    logger.info("  凭证验证通过，可以使用")

                asyncio.run(get_user_info())
            except Exception as e:
                logger.warning(f"  获取用户信息失败: {e}")

            return True
        else:
            logger.error("  ✗ 凭证无效！")
            logger.error("\n可能的原因：")
            logger.error("  1. 凭证已过期")
            logger.error("  2. 凭证值复制错误")
            logger.error("  3. 账号状态异常")
            logger.error("\n请重新获取凭证：")
            logger.error("  1. 在浏览器中登录 B站")
            logger.error("  2. 打开开发者工具 (F12)")
            logger.error("  3. Application → Cookies → https://www.bilibili.com")
            logger.error("  4. 复制 SESSDATA、bili_jct、buvid3 的值")
            return False

    except Exception as e:
        logger.error(f"  ✗ 测试凭证时出错: {e}")
        logger.exception(e)
        return False


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stdout, level="INFO")

    result = test_credentials()

    logger.info("\n" + "=" * 60)
    if result:
        logger.info("✓ 凭证测试通过！可以正常使用上传功能")
    else:
        logger.error("✗ 凭证测试失败！请按照提示重新配置凭证")
    logger.info("=" * 60)

    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
