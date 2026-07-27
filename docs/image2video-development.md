# 图生视频模块开发文档

## 1. 模块目标

图生视频模块将一张参考图片和一段运动描述提示词提交给可灵视频服务，异步生成短视频，并提供任务状态查询、结果预览与下载能力。

用户操作链路如下：

```text
输入公网图片 URL 或选择本地图片
        ↓
填写运动提示词与生成参数
        ↓
POST /api/video/image2video/create
        ↓
获得 task_id，前端每 3 秒查询任务状态
        ↓
成功后预览并下载视频；失败时展示中文错误
```

## 2. 代码结构

| 层级 | 文件 | 职责 |
| --- | --- | --- |
| 页面 | `frontend/src/pages/Image2Video.tsx` | 图片选择、参数配置、任务创建、轮询、预览和下载 |
| 前端 API | `frontend/src/api.ts` | 请求后端创建与状态查询接口 |
| 请求模型 | `backend/models/schemas.py` | `Image2VideoCreateRequest`、`VideoTask` 数据校验 |
| 路由 | `backend/routers/video.py` | 暴露图生视频创建和查询 API |
| 服务 | `backend/services/keling_service.py` | 调用可灵 API、解析并标准化响应 |
| 测试 | `backend/tests/test_image2video.py` | 覆盖创建、查询、失败和响应兼容性 |

## 3. 前端实现

### 3.1 页面状态

`Image2Video.tsx` 使用以下状态控制页面：

| 状态 | 含义 |
| --- | --- |
| `imageUrl` | 提交给后端的图片地址或 Base64 数据 |
| `previewUrl` | 页面图片预览地址 |
| `prompt` | 视频运动、镜头和氛围描述 |
| `ratio` | 画幅比例：`9:16`、`16:9`、`1:1` |
| `model` | 可灵模型标识 |
| `duration` | 视频时长，当前页面提供 5 秒和 10 秒 |
| `watermarkEnabled` | 是否启用水印 |
| `task` | 当前视频生成任务及其状态 |
| `error` | 可展示给用户的错误信息 |

### 3.2 本地图片与公网图片

页面支持两种图片来源：

1. 用户输入可公开访问的图片 URL。
2. 用户选择本地图片，页面通过 `FileReader` 转换为 Data URL 后显示预览并随创建请求提交。

> 生产环境建议优先使用 OSS、COS 或 CDN 的公网 HTTPS 图片 URL。不同可灵接入方式对 Base64/Data URL 的支持并不完全一致；若服务端返回图片不可访问错误，应先将文件上传至对象存储，再提交公网 URL。

### 3.3 创建任务

前端调用：

```ts
createImage2Video({
  image_url: imageUrl,
  prompt,
  model,
  duration,
  aspect_ratio: ratio,
  watermark_enabled: watermarkEnabled,
})
```

创建成功后，页面必须拿到非空的 `task_id` 才会启动轮询。若后端未返回任务 ID，页面会立即报告错误，避免向空路径发请求。

### 3.4 状态轮询

前端每 3 秒请求一次任务状态：

```text
GET /api/video/image2video/status/{task_id}
```

状态为 `succeed`、`succeeded` 或 `failed` 时停止轮询。轮询接口出现网络错误或 HTTP 404 时，也会停止轮询，并将任务标记为失败；这样不会出现页面持续加载的情况。

## 4. 后端 API 契约

### 4.1 创建图生视频任务

```http
POST /api/video/image2video/create
Content-Type: application/json
```

请求示例：

```json
{
  "image_url": "https://example.com/product.jpg",
  "prompt": "镜头缓慢推进，产品旋转展示，柔和棚拍光线",
  "model": "kling-v1-5-video-generation-3.0-turbo",
  "duration": 5,
  "aspect_ratio": "9:16",
  "watermark_enabled": true
}
```

响应示例：

```json
{
  "task_id": "task_xxx",
  "status": "submitted",
  "video_url": null,
  "cover_url": null,
  "error": null
}
```

### 4.2 查询任务状态

```http
GET /api/video/image2video/status/{task_id}
```

成功完成时的响应示例：

```json
{
  "task_id": "task_xxx",
  "status": "succeed",
  "video_url": "https://example.com/result.mp4",
  "cover_url": "https://example.com/cover.jpg",
  "error": null
}
```

## 5. 可灵响应兼容策略

当前服务层同时兼容两类可灵响应格式：

| 字段含义 | 原生格式 | 部分兼容网关格式 |
| --- | --- | --- |
| 任务 ID | `data.task_id` | `data.id` |
| 任务状态 | `data.task_status` | `data.status` |
| 视频结果 | `data.task_result.videos` | `data.works` |

服务层统一转换为 `VideoTask`，对前端只暴露 `task_id`、`status`、`video_url`、`cover_url` 和 `error`。

## 6. 404 问题说明与修复

### 6.1 根因

旧代码仅从创建响应读取 `data.id`。可灵原生接口返回 `data.task_id` 时，后端会返回空任务 ID。前端随后请求：

```text
GET /api/video/image2video/status/
```

该 URL 不匹配后端的 `status/{task_id}` 路由，最终返回 404。

### 6.2 修复措施

1. 后端创建任务时按 `task_id`、`id` 的优先级读取任务 ID。
2. 未拿到任务 ID 时直接抛出明确错误，不返回空任务。
3. 前端创建成功后再次校验 `task_id`，为空时不启动轮询。
4. 前端捕获轮询错误，停止定时器并展示后端 `detail` 错误信息。
5. 新增原生响应格式的单元测试，防止该问题回归。

## 7. 错误处理约定

| 场景 | 页面行为 |
| --- | --- |
| 未选择图片 | 阻止提交并显示提示 |
| 未填写提示词 | 阻止提交并显示提示 |
| API 未返回任务 ID | 显示“服务未返回任务 ID”，不启动轮询 |
| 状态查询 404/网络错误 | 停止轮询，任务显示失败和具体错误 |
| 可灵任务失败 | 展示 `task_status_msg` 或 `message` |
| 视频生成成功 | 展示视频播放器、封面和下载按钮 |

## 8. 配置与启动

后端 `.env` 至少需要配置：

```env
KELING_API_KEY=你的可灵API密钥
```

启动后端：

```powershell
cd backend
python main.py
```

启动前端：

```powershell
cd frontend
npm run dev
```

Vite 会将 `/api` 请求代理到 `http://localhost:8000`。

## 9. 测试与验证

执行后端测试：

```powershell
cd backend
pip install -r requirements-test.txt
pytest tests/test_image2video.py -v
```

执行前端生产构建：

```powershell
cd frontend
npm run build
```

当前测试覆盖：

- 请求模型校验；
- 图生视频任务创建；
- 原生 `task_id/task_status` 响应兼容；
- 图生视频成功、失败状态；
- 原生 `task_result.videos` 结果兼容；
- 回调与水印参数透传。

## 10. 后续建议

1. 接入对象存储，将本地图片上传后转换为公网 HTTPS URL。
2. 配置可灵回调地址，减少前端轮询压力。
3. 持久化任务状态，避免后端重启后无法追踪任务。
4. 增加任务取消、超时和重试策略。
