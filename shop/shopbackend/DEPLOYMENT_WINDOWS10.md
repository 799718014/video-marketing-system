# Windows 10 部署指南

本文说明如何将 `shopbackend` 部署到一台新的 Windows 10 电脑，作为内部商品图生视频服务运行。

> 适用范围：本服务可在内网供业务人员使用。`/assets/upload` 会将商品素材自动上传到七牛云 Kodo；可灵从七牛云自定义 CDN HTTPS 域名拉取素材，因此本机 API 无需对公网开放。

## 1. 部署前准备

### 1.1 推荐目录

以下示例统一使用：

```text
D:\video-marketing-system\
└─ shopbackend\
   ├─ .venv\
   ├─ data\
   ├─ run.ps1
   └─ ...
```

`data` 目录默认保存 SQLite 数据库、上传素材与成片。生产环境建议把它放在有定期备份的数据盘，并通过 `SHOP_DATA_DIR` 指向该目录。

### 1.2 所需软件

| 软件 | 建议版本/要求 | 用途 |
| --- | --- | --- |
| Git | 最新稳定版 | 获取和更新代码 |
| Python | 3.11 x64 | 运行后端；代码要求 Python 3.10+ |
| FFmpeg | 完整版 | 视频合成 |
| FFprobe | 与 FFmpeg 一起安装 | 合成前后的成片规格预检 |
| 中文字体 | 如 `msyh.ttc` | 渲染中文字幕、价格和 CTA |

安装 Python 时务必勾选 **Add Python to PATH**。安装 FFmpeg 后，将其 `bin` 目录加入系统 `Path`，并在新的 PowerShell 窗口确认：

```powershell
python --version
ffmpeg -version
ffprobe -version
```

若其中任一命令不可用，请先修复环境变量再继续。FFprobe 缺失时，服务会拒绝执行合成，以避免产出规格不合格的视频。

## 2. 获取代码并安装依赖

```powershell
git clone <项目仓库地址> D:\video-marketing-system
cd D:\video-marketing-system\shopbackend

python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

依赖中已包含 FastAPI、HTTP 客户端和 Pillow。Pillow 用于素材格式、尺寸、透明通道和哈希预检。

## 3. 配置七牛云素材访问

### 3.1 关键限制

可灵创建图生视频时会从 `KELING_ASSET_BASE_URL` 下载商品主图。因此：

- `PUBLIC_BASE_URL` 可为 `http://localhost:8010`，只用于本地 API、预览和本地成片 URL；
- `KELING_ASSET_BASE_URL` 必须是可灵可访问的 **七牛云 CDN HTTPS** 地址；
- 上传接口会将文件上传至七牛云，并登记：`{KELING_ASSET_BASE_URL}/products/<商品ID>/<文件名>`；
- 合成成片 URL 仍为：`{PUBLIC_BASE_URL}/outputs/<文件名>`。

### 3.2 推荐方案

1. 创建七牛云 Kodo Bucket，并准备公开读取的自定义 CDN HTTPS 域名，例如 `https://assets.example.com`；
2. 在七牛云控制台获取 Access Key、Secret Key、Bucket 名称；
3. 将 CDN 域名填写到 `KELING_ASSET_BASE_URL`，并填写 `QINIU_ACCESS_KEY`、`QINIU_SECRET_KEY`、`QINIU_BUCKET`；
4. 通过本项目的 `/api/products/{id}/assets/upload` 上传商品图，后端会先本地预检、再上传七牛云、最后复检 CDN URL；
5. 本地 API 可以继续监听 `127.0.0.1:8010`，无需为可灵开放端口。

## 4. 配置运行环境

在 `D:\video-marketing-system\shopbackend` 创建 `run.ps1`。不要把真实 API Key 提交到 Git。

```powershell
$ErrorActionPreference = "Stop"

# 商品数据、上传素材、SQLite 数据库和成片输出目录。
$env:SHOP_DATA_DIR = "D:\video-marketing-data"

# 可灵配置。
$env:KELING_API_KEY = "替换为你的可灵 API Key"
$env:KELING_API_BASE = "https://api-beijing.klingai.com"
$env:KELING_IMAGE_TO_VIDEO_MODEL = "kling-v1-5"

# 本地 API 和本地成片访问地址；本地调试可使用 localhost。
$env:PUBLIC_BASE_URL = "http://localhost:8010"

# 七牛云 Kodo：可灵只从此 CDN HTTPS 域名下载商品素材。
$env:KELING_ASSET_BASE_URL = "https://assets.example.com"
$env:QINIU_ACCESS_KEY = "替换为七牛云 Access Key"
$env:QINIU_SECRET_KEY = "替换为七牛云 Secret Key"
$env:QINIU_BUCKET = "替换为七牛云 Bucket 名称"
$env:QINIU_KEY_PREFIX = "products"

# 视频合成和规格预检。
$env:FFMPEG_BINARY = "ffmpeg"
$env:FFPROBE_BINARY = "ffprobe"
$env:FFMPEG_FONT_FILE = "C:\Windows\Fonts\msyh.ttc"

# 后台调度 Worker。
$env:MAX_PROVIDER_PARALLEL = "1"
$env:GENERATION_WORKER_ENABLED = "true"
$env:GENERATION_WORKER_POLL_SECONDS = "3"
$env:GENERATION_REFRESH_SECONDS = "15"
$env:GENERATION_CLAIM_LEASE_SECONDS = "120"

# 素材预检：最大 20MB；普通商品图最小 512px；Logo 最小 128px。
$env:ASSET_PREFLIGHT_MAX_BYTES = "20971520"
$env:ASSET_PREFLIGHT_MIN_SIDE = "512"
$env:ASSET_PREFLIGHT_LOGO_MIN_SIDE = "128"

# 可选：接入视觉质检服务后再配置。
# $env:QUALITY_REVIEW_URL = "https://quality.example.com/review"
# $env:QUALITY_REVIEW_API_KEY = "你的质检服务密钥"

& "D:\video-marketing-system\shopbackend\.venv\Scripts\python.exe" `
  -m uvicorn main:app --host 127.0.0.1 --port 8010
```

如果使用支持幂等请求的可灵网关，默认会传递 `Idempotency-Key` 请求头。网关使用其他字段时可设置 `KELING_IDEMPOTENCY_HEADER`；明确不支持时可设为空字符串。

## 5. 首次启动与验收

在 PowerShell 中执行：

```powershell
cd D:\video-marketing-system\shopbackend
Set-ExecutionPolicy -Scope Process Bypass
.\run.ps1
```

另开一个 PowerShell 窗口检查健康状态：

```powershell
Invoke-RestMethod http://127.0.0.1:8010/api/health
```

至少确认：

```text
status: ok
keling_configured: true
generation_worker_enabled: true
generation_worker_running: true
```

然后用一张不小于 512×512 的 PNG/JPEG/WebP 商品图完成一次业务验收：

1. 创建商品；
2. 注册可灵可访问的主图，并补充透明商品图和 Logo；
3. 创建分镜；
4. 创建生成任务；
5. 等待 Worker 自动提交和刷新状态；
6. 合成分镜，再合成最终成片。

资产预检失败会返回 HTTP 422。透明商品图不带 Alpha、素材尺寸过小、外链失效或成片不符合规格均会被拦截。

## 6. 配置为开机自启

推荐使用 NSSM（Non-Sucking Service Manager）或 Windows 任务计划程序运行 `run.ps1`。以下为任务计划程序方式：

1. 打开“任务计划程序”→“创建任务”；
2. “常规”中选择“无论用户是否登录都要运行”，使用具备数据目录读写权限的专用账号；
3. “触发器”选择“启动时”；
4. “操作”填写：

```text
程序/脚本：powershell.exe
参数：-ExecutionPolicy Bypass -File D:\video-marketing-system\shopbackend\run.ps1
起始于：D:\video-marketing-system\shopbackend
```

5. 保存后手动运行一次任务，并检查 `http://127.0.0.1:8010/api/health`。

生产环境不要使用 `uvicorn --reload`，否则文件变化会导致服务重启。

## 7. 备份、更新与回滚

### 7.1 备份

至少备份 `SHOP_DATA_DIR` 指向的整个目录，尤其是：

```text
shop.db
uploads\
outputs\
```

建议在服务停止后执行 SQLite 文件备份，或使用 SQLite 在线备份方式，避免复制到写入中的数据库文件。

### 7.2 更新

```powershell
cd D:\video-marketing-system
git pull
cd shopbackend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

完成后重启 Windows 服务或任务计划程序中的任务。服务启动时会自动补齐 SQLite 表的新增字段；更新前仍应先备份数据目录。

## 8. 常见故障

| 现象 | 排查与处理 |
| --- | --- |
| 生成任务提示商品图不是公网 HTTPS | 检查 `PUBLIC_BASE_URL`，确认可灵从外网可访问对应素材 URL。 |
| 素材预检返回 422 | 检查图片格式、大小、边长；透明商品图必须带 Alpha；外链必须可以下载。 |
| 合成提示未找到 FFmpeg/FFprobe | 修复系统 `Path`，或在 `run.ps1` 设置 `FFMPEG_BINARY`、`FFPROBE_BINARY` 的绝对路径。 |
| 合成提示未找到中文字体 | 确认 `FFMPEG_FONT_FILE` 是存在且支持中文的字体文件。 |
| Worker 未提交任务 | 调用 `/api/health` 确认 Worker 运行和 API Key 已配置；检查任务状态和 `error` 字段。 |
| 成片规格校验失败 | 检查 FFmpeg/FFprobe 是否来自同一完整发行版；重新合成会统一输出 1080×1920、30fps、H.264、yuv420p。 |
| 任务计划程序启动失败 | 用任务账号手工执行 `run.ps1`，确认其拥有项目目录、数据目录和 Python/FFmpeg 的访问权限。 |
