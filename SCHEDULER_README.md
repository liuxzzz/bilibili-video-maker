# 定时任务系统使用说明

## 功能概述

本系统实现了自动化的NBA比赛视频制作和发布流程，支持两种运行模式：

### 1. 一次性运行模式（默认）
立即获取当天的比赛并执行视频制作和上传。

### 2. 定时任务模式（推荐）
- **每天12:00** 自动检查当天的比赛
- **每小时** 检查未结束比赛的状态
- 比赛结束后自动生成视频并上传

## 核心功能

### 比赛状态检测
系统会自动检测比赛的三种状态：
- **未开始** - 比赛尚未开始
- **进行中** - 比赛正在进行
- **已结束** - 比赛已结束，可以生成视频

### 智能重试机制
- 对于未结束的比赛，系统会记录下来
- 1小时后自动重新检查比赛状态
- 比赛结束后立即生成视频并上传

### 任务持久化
- 所有任务信息保存在 `data/tasks.json` 文件中
- 系统重启后仍能继续处理未完成的任务
- 避免重复处理已完成的比赛

## 使用方法

### 安装依赖

```bash
# 安装项目依赖
uv sync

# 或者使用 pip
pip install -e .
```

### 运行模式

#### 方式1: 一次性运行（测试用）

```bash
python main.py
```

这会立即：
1. 获取当天的NBA比赛
2. 检查比赛状态
3. 为已结束的比赛生成视频并上传
4. 为未结束的比赛创建等待任务

#### 方式2: 定时任务模式（生产环境）

```bash
python main.py --cron
```

这会启动定时任务调度器：
- 立即执行一次检查
- 每天12:00自动检查当天比赛
- 每小时检查等待中的任务
- 持续运行，按 `Ctrl+C` 停止

### 测试功能

```bash
python test_scheduler.py
```

测试脚本会：
1. 测试每日检查功能
2. 测试等待任务检查功能
3. 测试任务持久化功能
4. 测试比赛状态获取功能

## 系统架构

### 主要模块

#### 1. `GameFetcher` - 比赛信息获取器
- 从虎扑网站获取当天的NBA比赛
- 检查指定比赛的当前状态（未开始/进行中/已结束）

#### 2. `TaskStore` - 任务持久化存储
- 使用JSON文件存储任务信息
- 支持任务的创建、查询、更新、删除
- 自动保存任务状态变化

#### 3. `TaskScheduler` - 任务调度器
- 创建和管理任务
- 执行视频制作流程（采集→生成→发布）
- 检查等待任务并更新状态

#### 4. `CronScheduler` - 定时任务调度器
- 管理定时任务（每天12:00和每小时）
- 协调任务检查和执行流程
- 自动清理临时文件

### 任务状态流转

```
PENDING (待执行)
    ↓
RUNNING (执行中)
    ↓
COLLECTING (采集中)
    ↓
GENERATING (生成中)
    ↓
PUBLISHING (发布中)
    ↓
COMPLETED (已完成)

或者：

WAITING_GAME_END (等待比赛结束)
    ↓ (1小时后重新检查)
PENDING (待执行)
```

### 数据存储结构

任务数据保存在 `data/tasks.json`：

```json
{
  "tasks": {
    "task_xxx": {
      "task_id": "task_xxx",
      "game_info": {
        "game_id": "xxx",
        "match_id": "xxx",
        "home_team_name": "湖人",
        "away_team_name": "勇士",
        "match_status": "已结束"
      },
      "status": "completed",
      "create_time": "2025-12-27T12:00:00",
      "start_time": "2025-12-27T12:05:00",
      "end_time": "2025-12-27T13:30:00",
      "config": {
        "next_check_time": "2025-12-27T13:00:00",
        "game_status": "已结束"
      }
    }
  }
}
```

## 实现原理

### 比赛状态检测

系统通过以下方式检测比赛状态：

1. 访问虎扑NBA赛程页面：`https://m.hupu.com/nba/schedule`
2. 使用BeautifulSoup解析HTML
3. 根据 `data-match` 属性定位比赛元素
4. 提取状态信息：

```html
<div class="match-item" data-match="1405864802949005312">
  ...
  <div class="mend">
    <span class="text-m-bold">已结束</span>
  </div>
  ...
</div>
```

### 定时任务调度

使用 `APScheduler` 库实现定时任务：

```python
# 每天12:00执行
scheduler.add_job(
    daily_check_job,
    trigger=CronTrigger(hour=12, minute=0),
    id="daily_check"
)

# 每小时执行
scheduler.add_job(
    hourly_check_job,
    trigger=IntervalTrigger(hours=1),
    id="hourly_check"
)
```

## 部署建议

### 使用 systemd 服务（Linux）

创建服务文件 `/etc/systemd/system/bilibili-video-maker.service`：

```ini
[Unit]
Description=Bilibili Video Maker Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bilibili-video-maker
ExecStart=/path/to/python main.py --cron
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable bilibili-video-maker
sudo systemctl start bilibili-video-maker
sudo systemctl status bilibili-video-maker
```

### 使用 Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e .
RUN playwright install chromium
RUN playwright install-deps

CMD ["python", "main.py", "--cron"]
```

构建和运行：

```bash
docker build -t bilibili-video-maker .
docker run -d --name bilibili-video-maker \
  -v /path/to/data:/app/data \
  -v /path/to/materials:/app/materials \
  bilibili-video-maker
```

### 使用 supervisor（通用方案）

安装 supervisor：

```bash
pip install supervisor
```

创建配置文件 `supervisor.conf`：

```ini
[program:bilibili-video-maker]
command=python main.py --cron
directory=/path/to/bilibili-video-maker
autostart=true
autorestart=true
stderr_logfile=/var/log/bilibili-video-maker.err.log
stdout_logfile=/var/log/bilibili-video-maker.out.log
```

启动：

```bash
supervisord -c supervisor.conf
supervisorctl status
```

## 监控和维护

### 查看日志

日志会输出到控制台，包含详细的执行信息：
- 任务创建和状态变化
- 比赛状态检查结果
- 视频生成和上传进度
- 错误信息和堆栈跟踪

### 查看任务状态

```bash
python -c "from src.schedule import TaskStore; store = TaskStore(); print([t.to_dict() for t in store.get_all_tasks()])"
```

### 清理已完成任务

可以手动编辑 `data/tasks.json` 删除已完成的旧任务，或编写清理脚本。

## 常见问题

### Q: 如何修改检查时间？

A: 编辑 `src/schedule/cron_scheduler.py`：

```python
# 修改每日检查时间（例如改为上午10点）
trigger=CronTrigger(hour=10, minute=0)

# 修改检查间隔（例如改为30分钟）
trigger=IntervalTrigger(minutes=30)
```

### Q: 任务持久化文件太大怎么办？

A: 定期清理已完成的旧任务，或实现自动清理机制：

```python
# 清理7天前的已完成任务
from datetime import datetime, timedelta
old_date = datetime.now() - timedelta(days=7)
# ... 清理逻辑
```

### Q: 如何测试而不实际上传视频？

A: 可以修改 `TaskScheduler.execute_task()` 方法，注释掉发布部分，或者在测试环境中使用模拟的 `VideoPublisher`。

## 技术栈

- **Python 3.11+**
- **Playwright** - 浏览器自动化
- **APScheduler** - 定时任务调度
- **BeautifulSoup** - HTML解析
- **Loguru** - 日志记录
- **Requests** - HTTP请求

## 许可证

本项目仅供学习和研究使用。

