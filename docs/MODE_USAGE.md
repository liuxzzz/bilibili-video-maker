# 模式使用说明

本系统支持多种视频制作模式，通过命令行参数进行选择。

## 🏀 NBA模式

NBA模式专门用于制作NBA比赛视频，**只支持定时任务模式**。

### 启动方式

```bash
python main.py --mode nba --cron
```

### 功能特性

- ✅ **每天12:00自动执行**：程序启动后，会在每天12:00自动检查当天的NBA比赛
- ✅ **每小时状态检查**：每小时检查等待中的任务，比赛结束后自动执行
- ✅ **持续运行**：程序会持续运行，直到手动停止（Ctrl+C）
- ✅ **启动时立即执行**：程序启动时会立即执行一次检查，无需等待到12:00

### 工作流程

1. **程序启动**
   - 立即执行一次每日检查任务
   - 设置每天12:00的定时任务
   - 设置每小时的检查任务

2. **每天12:00（自动执行）**
   - 获取当天NBA比赛列表
   - 检查每场比赛的状态和评分数量
   - 为满足条件的比赛（已结束且评分≥10万）创建任务
   - 立即执行待执行的任务

3. **每小时（自动执行）**
   - 检查所有等待中的任务
   - 重新检查比赛状态
   - 对已结束的比赛执行任务

### 注意事项

- ❌ NBA模式**不支持**一次性运行模式
- ✅ 必须使用 `--cron` 参数启动定时任务
- 💡 程序需要持续运行，建议使用 systemd、supervisor 或 Docker 进行后台运行

### 部署建议

#### 使用 systemd（Linux）

创建服务文件 `/etc/systemd/system/nba-video-maker.service`:

```ini
[Unit]
Description=NBA Video Maker Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bilibili-video-maker
ExecStart=/path/to/python main.py --mode nba --cron
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable nba-video-maker
sudo systemctl start nba-video-maker
```

#### 使用 supervisor

创建配置文件 `/etc/supervisor/conf.d/nba-video-maker.conf`:

```ini
[program:nba-video-maker]
command=/path/to/python main.py --mode nba --cron
directory=/path/to/bilibili-video-maker
autostart=true
autorestart=true
stderr_logfile=/var/log/nba-video-maker.err.log
stdout_logfile=/var/log/nba-video-maker.out.log
```

启动服务：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start nba-video-maker
```

---

## 🆕 新模式

新模式用于制作其他类型的视频内容，**只支持一次性运行模式**。

### 启动方式

```bash
python main.py --mode new
```

### 功能特性

- ✅ **一次性运行**：执行完成后程序自动退出
- ✅ **手动触发**：需要手动运行命令来执行
- ❌ **不支持定时任务**：不能使用 `--cron` 参数

### 注意事项

- ❌ 新模式**不支持**定时任务模式
- ✅ 只能使用一次性运行模式
- 💡 如果需要定时执行，可以使用系统的 cron 或任务计划程序

---

## 📋 命令行参数说明

### 基本用法

```bash
python main.py [--mode MODE] [--cron]
```

### 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--mode` | 选择视频制作模式 | `nba`, `new` | `nba` |
| `--cron` | 启用定时任务模式（仅NBA模式） | - | False |

### 参数组合

| 模式 | --cron | 结果 |
|------|--------|------|
| `nba` | ✅ | ✅ 启动定时任务模式 |
| `nba` | ❌ | ❌ 错误：NBA模式必须使用--cron |
| `new` | ✅ | ❌ 错误：新模式不支持--cron |
| `new` | ❌ | ✅ 启动一次性运行模式 |

### 示例

```bash
# NBA模式 - 定时任务（推荐）
python main.py --mode nba --cron

# 新模式 - 一次性运行
python main.py --mode new

# 查看帮助
python main.py --help
```

---

## 🔍 验证定时任务

运行测试脚本验证定时任务配置：

```bash
python -m test.test_cron_schedule
```

这会显示：
- 下次每日检查时间（应该是今天或明天的12:00）
- 下次每小时检查时间
- 距离下次执行的时间

---

## ❓ 常见问题

### Q: NBA模式为什么必须使用--cron？

A: NBA模式设计为自动化运行，需要持续监控比赛状态。定时任务模式可以确保每天12:00自动检查，并在比赛结束后自动处理。

### Q: 如何确保程序每天12:00都会运行？

A: 程序启动后会持续运行，使用 `BlockingScheduler` 保持进程活跃。只要程序在运行，就会在每天12:00自动执行。建议使用 systemd 或 supervisor 确保程序持续运行。

### Q: 程序启动后多久会执行第一次检查？

A: 程序启动时会**立即执行一次**每日检查任务，然后设置定时任务在每天12:00执行。

### Q: 可以修改12:00的执行时间吗？

A: 可以，需要修改 `src/schedule/cron_scheduler.py` 中的 `CronTrigger(hour=12, minute=0)` 部分。

