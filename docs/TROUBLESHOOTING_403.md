# B站视频上传失败 - 403错误排查指南

## 错误信息
```
上传视频到B站失败: 网络错误，状态码：403
```

## 原因分析

403 Forbidden 错误通常表示**权限不足或认证失败**，在B站上传场景中，主要有以下几个原因：

---

## 解决方案

### 1. 重新获取登录凭证 ⭐ 最优先

B站的登录凭证有时效性（通常24小时左右），过期后会返回403错误。

#### 步骤：

1. **在浏览器中登录B站**
   - 访问 https://www.bilibili.com
   - 确保已登录你的账号

2. **打开开发者工具**
   - Windows/Linux: 按 `F12` 或 `Ctrl+Shift+I`
   - macOS: 按 `Cmd+Option+I`

3. **获取Cookie值**
   - 点击 `Application` (应用程序) 或 `Storage` (存储) 标签
   - 左侧展开 `Cookies` → 点击 `https://www.bilibili.com`
   - 找到以下三个值并复制：

   | Cookie名称 | 说明 | 是否必需 |
   |-----------|------|---------|
   | `SESSDATA` | 会话令牌 | ✅ 必需 |
   | `bili_jct` | CSRF令牌 | ✅ 必需 |
   | `buvid3` | 设备标识 | ⭐ 强烈推荐 |

4. **设置环境变量**

   **临时设置（当前终端会话有效）：**
   ```bash
   export BILIBILI_SESSDATA='你的_SESSDATA值'
   export BILIBILI_BILI_JCT='你的_bili_jct值'
   export BILIBILI_BUVID3='你的_buvid3值'
   ```

   **永久设置（推荐）：**
   
   在 `~/.zshrc` 或 `~/.bashrc` 中添加：
   ```bash
   # B站上传凭证
   export BILIBILI_SESSDATA='你的_SESSDATA值'
   export BILIBILI_BILI_JCT='你的_bili_jct值'
   export BILIBILI_BUVID3='你的_buvid3值'
   ```
   
   然后执行：
   ```bash
   source ~/.zshrc  # 或 source ~/.bashrc
   ```

5. **验证环境变量**
   ```bash
   echo $BILIBILI_SESSDATA
   echo $BILIBILI_BILI_JCT
   echo $BILIBILI_BUVID3
   ```

---

### 2. 检查账号状态

确保你的B站账号：
- ✅ 已完成实名认证
- ✅ 具有上传视频的权限
- ✅ 没有被限制或封禁
- ✅ 创作等级达到要求（通常需要LV1及以上）

---

### 3. 检查视频文件

运行检查脚本：
```bash
python check_video_info.py
```

确保视频符合B站要求：
- ✅ 分辨率：≥ 640x360
- ✅ 时长：1秒 - 2小时（7200秒）
- ✅ 文件大小：≤ 8GB
- ✅ 编码格式：H.264 或 H.265（推荐）
- ✅ 容器格式：MP4、FLV、WebM等

---

### 4. 检查网络环境

#### 4.1 确保网络畅通
```bash
# 测试B站API连接
curl -I https://member.bilibili.com

# 如果有代理，可能需要配置
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
```

#### 4.2 关闭VPN/代理
某些VPN或代理可能导致B站API拒绝访问。

---

### 5. 使用最新的代码

我已经更新了代码，添加了 `buvid3` 支持。确保运行最新版本：

```bash
# 重新安装依赖
uv sync

# 运行测试
python test_video_upload.py
```

---

## 诊断工具

### 工具1: 检查视频信息
```bash
python check_video_info.py
```
输出：
- 视频编码格式
- 分辨率、时长、文件大小
- 是否符合B站要求
- 登录凭证配置状态

### 工具2: 使用 ffprobe 查看视频信息
```bash
# 查看完整信息
ffprobe -v error -show_format -show_streams materials/videos/你的视频.mp4

# 只看关键信息
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,duration,bit_rate \
  -of default=noprint_wrappers=1 \
  materials/videos/你的视频.mp4
```

---

## 常见问题 FAQ

### Q1: 为什么之前能上传，现在不行了？
**A**: 登录凭证过期了，重新获取即可。

### Q2: buvid3 是什么？必须要设置吗？
**A**: buvid3 是B站的设备指纹标识，虽然不是强制的，但强烈推荐设置，可以提高上传成功率。

### Q3: 如何知道凭证是否有效？
**A**: 运行 `python check_video_info.py` 会显示凭证配置状态。

### Q4: 403错误还有其他可能吗？
**A**: 是的，还可能是：
- IP被限制（频繁请求）
- 视频内容违规（自动检测）
- 账号权限不足
- B站API变更

### Q5: 视频格式不对怎么办？
**A**: 使用 ffmpeg 转换：
```bash
ffmpeg -i input.webm -c:v libx264 -c:a aac output.mp4
```

---

## 测试步骤

1. **更新环境变量**
   ```bash
   export BILIBILI_SESSDATA='最新的值'
   export BILIBILI_BILI_JCT='最新的值'
   export BILIBILI_BUVID3='最新的值'
   ```

2. **检查视频信息**
   ```bash
   python check_video_info.py
   ```

3. **重新测试上传**
   ```bash
   python test_video_upload.py
   ```

---

## 如果问题仍未解决

1. **查看详细日志**
   - 检查是否有更详细的错误信息
   - 记录错误发生的时间和场景

2. **尝试手动上传**
   - 在B站网页端手动上传同一个视频文件
   - 确认账号和视频文件本身没有问题

3. **检查 bilibili-api-python 库**
   ```bash
   # 更新到最新版本
   pip install --upgrade bilibili-api-python
   
   # 查看版本
   pip show bilibili-api-python
   ```

4. **查看B站API文档**
   - https://nemo2011.github.io/bilibili-api/

---

## 联系支持

如果以上方法都无法解决问题，可能是：
- B站API发生了变化
- 账号存在特殊限制
- 需要查看 bilibili-api-python 的最新文档和issue

建议：
1. 检查 bilibili-api-python 的 GitHub Issues
2. 确认你的账号在网页端能正常上传视频
3. 尝试使用其他账号测试

