# 更新日志

## [0.2.0] - 2025-12-27

### 新增功能 🎉

#### 定时任务系统
- ✅ **自动比赛检测** - 每天12:00自动检查当天的NBA比赛
- ✅ **智能状态管理** - 实时获取比赛状态（未开始/进行中/已结束）
- ✅ **延迟重试机制** - 未结束的比赛每小时自动重新检查
- ✅ **任务持久化** - 使用JSON文件存储任务状态
- ✅ **自动执行** - 比赛结束后自动生成视频并上传

#### 新增模块
1. **`GameFetcher.get_game_status()`** - 获取指定比赛的实时状态
   - 通过data-match属性定位比赛元素
   - 解析HTML获取状态信息
   - 支持三种状态识别

2. **`TaskStore`** - 任务持久化存储管理器
   - JSON文件存储
   - 完整的CRUD操作
   - 按状态查询任务
   - 自动保存任务变更

3. **`CronScheduler`** - 定时任务调度器
   - 基于APScheduler实现
   - 每天12:00执行每日检查
   - 每小时执行等待任务检查
   - 自动清理临时文件

4. **`TaskScheduler`** 增强
   - 添加 `check_waiting_tasks()` - 检查等待任务
   - 添加 `recheck_game_status_and_update()` - 重新检查比赛状态
   - 集成任务持久化存储
   - 智能任务状态管理

#### 新增任务状态
- `WAITING_GAME_END` - 等待比赛结束状态

#### 新增文件
- `src/schedule/task_store.py` - 任务存储模块
- `src/schedule/cron_scheduler.py` - 定时任务调度器
- `test_scheduler.py` - 调度器测试脚本
- `example_usage.py` - 使用示例
- `SCHEDULER_README.md` - 详细使用文档
- `install.sh` - 快速安装脚本
- `.gitignore` - Git忽略配置

### 改进优化 🔧

#### main.py
- 支持命令行参数 `--cron` 启用定时任务模式
- 重构为两种运行模式（一次性/定时）
- 添加更清晰的日志输出

#### 依赖管理
- 添加 `apscheduler>=3.10.0` 依赖

#### 代码结构
- 更新 `src/schedule/__init__.py` 导出新模块
- 改进模块间的解耦
- 统一错误处理机制

### 技术栈更新 📚
- **APScheduler** - 定时任务调度
- **JSON** - 任务数据持久化

### 部署支持 🚀
- systemd 服务配置示例
- Docker 部署配置示例
- supervisor 配置示例

### 文档 📖
- 新增完整的使用文档（SCHEDULER_README.md）
- 更新README.md主文档
- 添加快速开始指南
- 添加常见问题解答

### 测试 🧪
- 添加调度器功能测试
- 添加使用示例代码
- 添加状态检查测试

---

## [0.1.0] - 之前版本

### 初始功能
- NBA比赛信息获取
- 视频内容采集
- 视频生成和处理
- B站视频上传
- 基础任务调度

---

## 使用说明

### 升级到 0.2.0

```bash
# 1. 更新代码
git pull

# 2. 安装新依赖
uv sync
# 或
pip install -e .

# 3. 创建数据目录
mkdir -p data

# 4. 运行测试
python test_scheduler.py

# 5. 启动定时任务
python main.py --cron
```

### 兼容性
- ✅ 完全向后兼容
- ✅ 原有的一次性运行模式仍可用
- ✅ 所有原有功能保持不变

### 注意事项
- 定时任务会创建 `data/tasks.json` 文件存储任务状态
- 首次运行会立即执行一次检查
- 按 Ctrl+C 可以安全停止定时任务

---

## 未来计划 🔮

- [ ] 支持更多体育赛事（NFL、英超等）
- [ ] Web界面查看任务状态
- [ ] 邮件/微信通知
- [ ] 视频质量优化
- [ ] 多账号支持
- [ ] 数据库存储（替代JSON）
- [ ] 集群部署支持

