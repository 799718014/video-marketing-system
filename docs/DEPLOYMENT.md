# Ubuntu 22.04 部署文档

本文档介绍如何将 **商品宣传视频生成系统** 部署到一台 Ubuntu 22.04 服务器（生产环境）。

架构概览：

```
                          ┌─────────────────────────────────────────┐
                          │            Ubuntu 22.04 服务器            │
   浏览器 ──HTTPS(443)──▶ │  Nginx                                   │
                          │   ├─ /            静态文件(前端 dist)     │
                          │   └─ /api/*  ──反向代理──▶ 127.0.0.1:8000 │
                          │                              │           │
                          │                        Uvicorn(FastAPI)  │
                          │                        (systemd 托管)     │
                          └─────────────────────────────────────────┘
                                        │              │
                                        ▼              ▼
                                  DeepSeek API     可灵影音 API
```

- **前端**：Vite 构建为静态文件，由 Nginx 直接托管。
- **后端**：FastAPI 由 Uvicorn 运行，systemd 守护进程管理，仅监听 `127.0.0.1:8000`。
- **Nginx**：对外统一入口，托管前端静态资源，并把 `/api` 反向代理到后端。

---

## 0. 前置要求

- 一台 Ubuntu 22.04 服务器，具备 sudo 权限。
- 一个可选的域名，解析到服务器公网 IP（用于 HTTPS）。
- API Key：
  - `DEEPSEEK_API_KEY`（https://platform.deepseek.com/api_keys）
  - `KELING_API_KEY`（https://klingai.com/dev/api-key，格式 `api-key-kling-xxx`）
- 服务器安全组 / 防火墙放行 `80`、`443` 端口。**不要**对外开放 `8000`。

---

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git curl

# 安装 Node.js 20 LTS（用于构建前端）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 校验版本
python3 --version   # 应 >= 3.10（本项目 pyc 为 3.12，3.10+ 均可）
node --version       # v20.x
```

---

## 2. 获取代码

```bash
sudo mkdir -p /opt/video-marketing-system
sudo chown "$USER":"$USER" /opt/video-marketing-system
git clone https://github.com/799718014/video-marketing-system.git /opt/video-marketing-system
cd /opt/video-marketing-system
```

---

## 3. 部署后端（FastAPI + Uvicorn）

### 3.1 创建虚拟环境并安装依赖

```bash
cd /opt/video-marketing-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# 生产环境建议额外安装 gunicorn 作为进程管理器
pip install "gunicorn>=22.0"
deactivate
```

### 3.2 配置环境变量

```bash
cd /opt/video-marketing-system/backend
cp .env.example .env
# 编辑 .env，填写真实的 API Key
nano .env
```

`.env` 内容示例：

```ini
DEEPSEEK_API_KEY=sk-你的deepseek密钥
KELING_API_KEY=api-key-kling-你的可灵密钥
BACKEND_PORT=8000
# 生产环境填写你的对外访问地址（用于 CORS 白名单）
FRONTEND_URL=https://your-domain.com
```

> 注意：`.env` 已在 `.gitignore` 中，不会被提交。请妥善保管密钥，权限设为 `chmod 600 .env`。

### 3.3 使用 systemd 托管后端

将仓库中的 `deploy/video-marketing-backend.service` 复制到 systemd 目录：

```bash
sudo cp /opt/video-marketing-system/deploy/video-marketing-backend.service \
        /etc/systemd/system/video-marketing-backend.service
```

（如果你的部署路径 / 用户名不是默认值，请编辑该文件中的 `WorkingDirectory`、`ExecStart`、`User`。）

创建运行用户（可选，推荐用非 root 专用用户）：

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin vmapp || true
sudo chown -R vmapp:vmapp /opt/video-marketing-system
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now video-marketing-backend
sudo systemctl status video-marketing-backend --no-pager
```

验证后端健康检查：

```bash
curl http://127.0.0.1:8000/api/health
# 期望输出：{"status":"ok","keling_configured":true}
```

---

## 4. 部署前端（Vite 构建 + Nginx 静态托管）

### 4.1 构建静态文件

```bash
cd /opt/video-marketing-system/frontend
npm ci        # 无 lock 变更时比 npm install 更快更稳定
npm run build # 产物输出到 frontend/dist
```

> 前端通过相对路径 `/api` 调用后端（见 `frontend/src/api.ts`），生产环境由 Nginx 统一反向代理，无需修改前端代码。

### 4.2 配置 Nginx

复制仓库提供的站点配置：

```bash
sudo cp /opt/video-marketing-system/deploy/nginx.conf \
        /etc/nginx/sites-available/video-marketing
sudo ln -sf /etc/nginx/sites-available/video-marketing \
            /etc/nginx/sites-enabled/video-marketing
# 可选：移除默认站点
sudo rm -f /etc/nginx/sites-enabled/default
```

编辑 `/etc/nginx/sites-available/video-marketing`，将 `server_name` 改为你的域名（或服务器 IP），确认 `root` 指向 `frontend/dist` 路径。

测试并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

此时访问 `http://your-domain.com` 即可打开系统。

---

## 5. 配置 HTTPS（推荐）

使用 Let's Encrypt 免费证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# 按提示选择自动跳转 HTTPS；证书会自动续期
```

续期测试：

```bash
sudo certbot renew --dry-run
```

---

## 6. 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # 放行 80 + 443
sudo ufw enable
sudo ufw status
```

---

## 7. 升级 / 重新部署

```bash
cd /opt/video-marketing-system
git pull

# 后端依赖变更时
cd backend && source .venv/bin/activate && pip install -r requirements.txt && deactivate
sudo systemctl restart video-marketing-backend

# 前端变更时
cd ../frontend && npm ci && npm run build
sudo systemctl reload nginx
```

---

## 8. 日志与排障

| 场景 | 命令 |
|------|------|
| 后端日志 | `sudo journalctl -u video-marketing-backend -f` |
| 后端状态 | `sudo systemctl status video-marketing-backend` |
| Nginx 错误日志 | `sudo tail -f /var/log/nginx/error.log` |
| Nginx 访问日志 | `sudo tail -f /var/log/nginx/access.log` |
| 健康检查 | `curl http://127.0.0.1:8000/api/health` |

常见问题：

- **前端能打开但接口 502/504**：后端未启动或崩溃，查 `journalctl`；确认 `.env` 中 API Key 正确。
- **接口 CORS 报错**：确认 `.env` 的 `FRONTEND_URL` 与实际访问域名一致。
- **脚本生成失败**：检查 `DEEPSEEK_API_KEY` 是否有效、账户是否有余额。
- **视频生成/下载失败**：检查 `KELING_API_KEY`；可灵视频生成为异步任务，前端会轮询状态，生成可能需要数分钟。
- **上传大小限制**：本项目为文本请求，无需调大；如后续新增文件上传，需在 Nginx 调整 `client_max_body_size`。

---

## 9. 目录约定小结

| 项 | 路径 |
|----|------|
| 项目根目录 | `/opt/video-marketing-system` |
| 后端虚拟环境 | `/opt/video-marketing-system/backend/.venv` |
| 后端环境变量 | `/opt/video-marketing-system/backend/.env` |
| 前端构建产物 | `/opt/video-marketing-system/frontend/dist` |
| systemd 服务 | `/etc/systemd/system/video-marketing-backend.service` |
| Nginx 站点 | `/etc/nginx/sites-available/video-marketing` |
