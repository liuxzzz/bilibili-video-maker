#!/bin/bash
# 快速安装和测试脚本

echo "====================================="
echo "Bilibili Video Maker - 安装脚本"
echo "====================================="
echo ""

# 检查Python版本
echo "检查Python版本..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "当前Python版本: $python_version"

if ! command -v python &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python 3.11+"
    exit 1
fi

echo ""
echo "1. 安装项目依赖..."
if command -v uv &> /dev/null; then
    echo "使用 uv 安装依赖..."
    uv sync
else
    echo "使用 pip 安装依赖..."
    pip install -e .
fi

echo ""
echo "2. 安装 Playwright 浏览器..."
playwright install chromium
playwright install-deps

echo ""
echo "3. 创建必要的目录..."
mkdir -p data
mkdir -p materials/videos
mkdir -p materials/images
mkdir -p materials/audio

echo ""
echo "====================================="
echo "安装完成！"
echo "====================================="
echo ""
echo "接下来你可以："
echo ""
echo "1. 运行示例查看功能:"
echo "   python example_usage.py"
echo ""
echo "2. 运行测试:"
echo "   python test_scheduler.py"
echo ""
echo "3. 一次性运行（测试用）:"
echo "   python main.py"
echo ""
echo "4. 启动定时任务模式（生产环境）:"
echo "   python main.py --cron"
echo ""
echo "5. 查看详细文档:"
echo "   cat SCHEDULER_README.md"
echo ""

