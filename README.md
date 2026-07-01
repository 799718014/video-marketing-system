# 商品宣传视频生成系统

基于 **DeepSeek** 生成视频脚本 + **可灵影音 KeLing** 生成视频的全自动短视频营销工具。

## 业务流程

```
关键词 → 商品信息 → AI生成脚本(DeepSeek) → AI生成视频(可灵影音) → 下载 → 手动发布
```

## 技术栈

- **前端**：React 18 + TypeScript + Vite + TailwindCSS
- **后端**：Python FastAPI + uvicorn
- **AI**：DeepSeek-V3（脚本）+ 可灵影音 KeLing（视频）

## 快速启动

### 1. 配置 API Key

```bash
cd backend
copy .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY 和 KELING_ACCESS_KEY_ID/SECRET
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# 服务运行在 http://localhost:8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 页面访问 http://localhost:5173
```

## 生产部署

将项目部署到 Ubuntu 22.04 服务器（Nginx + systemd + HTTPS）请参考 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## API Key 获取

| 服务 | 控制台地址 |
|------|-----------|
| DeepSeek | https://platform.deepseek.com/api_keys |
| 可灵影音 | https://klingai.com/ → 开发者中心 |

## 功能说明

| 步骤 | 说明 |
|------|------|
| Step 1 | 填写商品关键词、名称、描述、亮点、目标人群 |
| Step 2 | 选择视频风格/时长/平台，DeepSeek AI 自动生成可编辑脚本 |
| Step 3 | 选择可灵影音参数，提交生成任务，自动轮询状态 |
| Step 4 | 预览视频，下载 MP4，前往各平台创作者中心发布 |
