# Bilibili Video Maker

一个自动化的NBA比赛视频制作和发布系统，支持从虎扑获取比赛数据，生成视频并自动上传到B站。

## ✨ 新功能：定时任务系统

系统现已支持智能定时调度：

### 🎯 核心特性

- **自动比赛检测** - 每天12:00自动检查当天的NBA比赛
- **智能状态管理** - 自动识别比赛状态（未开始/进行中/已结束）
- **延迟重试机制** - 未结束的比赛每小时自动重新检查
- **任务持久化** - 所有任务状态保存到本地，重启不丢失
- **自动执行** - 比赛结束后自动生成视频并上传

### 🚀 快速开始

#### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

#### 2. 运行模式

**一次性运行**（测试用）：
```bash
python main.py
```

**定时任务模式**（生产环境）：
```bash
python main.py --cron
```

定时任务模式会：
- 立即执行一次检查
- 每天12:00自动检查当天比赛
- 每小时检查等待中的任务
- 持续运行直到手动停止（Ctrl+C）

#### 3. 运行示例

```bash
# 查看功能演示
python example_usage.py

# 运行完整测试
python test_scheduler.py
```

### 📖 详细文档

查看 [SCHEDULER_README.md](SCHEDULER_README.md) 了解：
- 详细使用说明
- 系统架构设计
- 部署方案（systemd、Docker、supervisor）
- 常见问题解答

## 系统架构

### 主要模块

```
bilibili-video-maker/
├── src/
│   ├── schedule/              # 任务调度模块
│   │   ├── game_fetcher.py   # 比赛信息获取
│   │   ├── scheduler.py      # 任务调度器
│   │   ├── cron_scheduler.py # 定时任务调度
│   │   ├── task_store.py     # 任务持久化
│   │   └── models.py         # 数据模型
│   ├── content_acquisition/   # 内容采集
│   ├── video_maker/          # 视频生成
│   └── vide_publish/         # 视频发布
├── data/                      # 任务数据存储
├── materials/                 # 素材目录
└── main.py                   # 主程序入口
```

### 工作流程

```
1. 每天12:00 或 手动触发
   ↓
2. 获取当天NBA比赛列表
   ↓
3. 检查每场比赛的状态
   ↓
4a. 已结束 → 立即生成视频
   ↓
   采集内容 → 生成视频 → 上传到B站
   
4b. 未结束 → 记录等待任务
   ↓
   1小时后重新检查 → 返回步骤3
```

## 功能特性

### 比赛状态检测
- 从虎扑网站实时获取比赛状态
- 支持三种状态：未开始、进行中、已结束
- 自动更新任务状态

### 智能重试
- 未结束的比赛自动进入等待队列
- 每小时自动检查一次
- 比赛结束后立即执行

### 任务持久化
- JSON文件存储，简单可靠
- 记录完整的任务生命周期
- 支持断点续传

### 视频生成
- 使用Playwright自动采集比赛数据
- 生成高质量视频内容
- 自动添加背景音乐

### 自动发布
- 自动上传到B站
- 智能生成标题和封面
- 支持自定义配置

## 环境要求

- Python 3.11+
- Chromium（Playwright自动安装）
- FFmpeg（视频处理）

## 配置说明

### 比赛源配置
系统默认从虎扑网站获取比赛信息，可在 `src/schedule/game_fetcher.py` 中修改。

### 定时任务配置
在 `src/schedule/cron_scheduler.py` 中可以修改：
- 每日检查时间（默认12:00）
- 重试间隔（默认1小时）

### B站上传配置
参考 `src/vide_publish/publisher.py` 配置B站账号信息。

## 测试

```bash
# 测试比赛获取
python -c "from src.schedule import GameFetcher; print(GameFetcher().get_today_nba_games())"

# 测试任务系统
python test_scheduler.py

# 运行示例
python example_usage.py
```

## 部署建议

### 开发环境
```bash
python main.py --cron
```

### 生产环境（systemd）
```bash
sudo systemctl enable bilibili-video-maker
sudo systemctl start bilibili-video-maker
```

详见 [SCHEDULER_README.md](SCHEDULER_README.md) 的部署章节。

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交Issue和Pull Request！
