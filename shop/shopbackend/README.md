# 商品资产驱动图生视频服务（P0）

该服务实现“真实商品资产锁定身份 + 图生视频生成运动 + 后期图层配置”的后端基础能力。

Windows 10 新机部署请见 [DEPLOYMENT_WINDOWS10.md](DEPLOYMENT_WINDOWS10.md)。

## 能力

- 商品事实库：名称、品牌、价格、卖点、禁用词；
- 商品资产库：主图、多角度图、细节图、佩戴图、透明底图和 Logo；
- 分镜与商品资产强关联；
- 商品主体仅允许 `image_to_video` 策略；
- 图生视频任务队列与单任务调度，默认仅提交一个可灵任务；
- P1 确定性合成：透明底商品图、Logo、字幕、价格和 CTA 均由模板渲染；
- 统一编码后按分镜顺序拼接，输出可发布的最终视频。
- P2 多参考图：主图、细节图、材质图和元素图按分镜角色关联，并随候选任务保存参考清单；
- P2 候选评审：一个分镜可创建 2–4 个候选，人工选片后最终拼接优先采用被选中的候选；
- P2 质检与追溯：预留商品相似度、Logo、OCR 质检服务接入，并记录资产、任务、选片、质检、合成和成片事件。

## 启动

```powershell
cd shopbackend
pip install -r requirements.txt
$env:KELING_API_KEY = "你的可灵 API Key"
$env:PUBLIC_BASE_URL = "https://cdn.example.com"
$env:FFMPEG_BINARY = "ffmpeg"
$env:FFMPEG_FONT_FILE = "C:\\Windows\\Fonts\\msyh.ttc"
uvicorn main:app --reload --port 8010
```

`PUBLIC_BASE_URL` 用于本地 API、静态预览和成片 URL，可在本地调试时使用 `http://localhost:8010`。商品素材通过 `/assets/upload` 上传后会自动进入七牛云 Kodo；可灵只会拉取 `KELING_ASSET_BASE_URL`（七牛云自定义 CDN HTTPS 域名）下的商品图。需配置 `QINIU_ACCESS_KEY`、`QINIU_SECRET_KEY`、`QINIU_BUCKET` 与 `KELING_ASSET_BASE_URL`。

P1 合成依赖 FFmpeg。生产环境应在镜像内安装 FFmpeg，并将 `FFMPEG_FONT_FILE` 配置为包含中文字符的字体文件。成片输出至 `data/outputs`，通过 `/outputs/{filename}` 提供访问。

素材预检依赖 Pillow：资产入库时会验证 JPEG/PNG/WebP 格式、文件大小、尺寸、长宽比、透明通道和 SHA-256；`transparent` 素材必须具有 Alpha 通道。创建、修改分镜及任务入队时会再次预检实际会使用的商品图、参考图、透明图和 Logo，以防外链失效或内容被替换。可通过 `POST /api/products/{product_id}/assets/{asset_id}/preflight` 主动复检历史资产。

合成预检依赖 `ffprobe`（可通过 `FFPROBE_BINARY` 配置）：底片必须有视频流且时长不短于分镜目标；每个合成片段和最终成片必须为 1080×1920、30fps、H.264、yuv420p，且时长符合分镜配置。素材最大文件大小、普通商品图最小边长和 Logo 最小边长可用 `ASSET_PREFLIGHT_MAX_BYTES`、`ASSET_PREFLIGHT_MIN_SIDE`、`ASSET_PREFLIGHT_LOGO_MIN_SIDE` 配置。

P2 自动视觉质检需配置 `QUALITY_REVIEW_URL`（可选 `QUALITY_REVIEW_API_KEY`）。该服务接收 `video_url`、`reference_assets` 与商品事实，并返回 `product_similarity_score`（0–1）、`logo_status`、`ocr_status` 和 `decision`。未配置时接口会明确返回 `manual_required`，由人工审核，绝不会生成虚假评分。若供应商网关支持多图请求，可配置 `KELING_REFERENCE_IMAGES_FIELD` 为对应字段名；未配置时服务安全使用主图提交，并保留全部参考图清单用于提示词、质检与追溯。

## 推荐调用顺序

1. `POST /api/products` 创建商品事实；
2. `POST /api/products/{id}/assets` 注册 CDN 商品图，或上传图片资产；
3. `POST /api/products/{id}/storyboards` 创建关联资产的图生视频分镜；
4. `POST /api/storyboards/{id}/generation-tasks` 创建待提交队列；
5. 创建任务后，后台 Worker 会按全局并发配额自动、原子地认领并提交任务；`POST /api/storyboards/{id}/dispatch-next` 仅用于手工唤醒 Worker；
6. Worker 会定时刷新可灵状态；也可调用 `POST /api/generation-tasks/{id}/refresh` 立即查询。
7. 对每个已得到 `video_url` 的任务调用 `POST /api/generation-tasks/{id}/compose`；
8. 全部分镜合成成功后调用 `POST /api/storyboards/{id}/compose-final` 获取最终成片。

## P2 候选、质检与追溯

1. 在分镜 `reference_assets` 中配置多张当前商品资产及其角色；
2. `POST /api/storyboards/{id}/candidate-tasks`，请求体 `{"candidate_count": 3}`；
3. 等待后台 Worker 自动提交并刷新候选状态，再调用 `POST /api/generation-tasks/{task_id}/quality-review`；
4. 人工确认后调用 `POST /api/generation-tasks/{task_id}/select`；
5. `GET /api/storyboards/{id}/trace` 获取从资产创建到最终成片的审计事件。

## 分镜示例

```json
{
  "title": "耳环商品展示",
  "scenes": [{
    "scene_no": 1,
    "scene_type": "product_closeup",
    "target_duration": 5,
    "asset_id": 1,
    "generation_strategy": "image_to_video",
    "motion_prompt": "镜头缓慢推进，耳环轻微摆动，柔和光线突出金属光泽",
    "identity_constraints": [
      "保持参考图中的耳环形状、材质、颜色和比例",
      "不得增加、删除或替换商品部件",
      "不得生成商品文字、价格或品牌 Logo"
    ],
    "postprocess_layers": ["transparent_product", "brand_logo", "price_tag", "subtitle", "cta"],
    "postprocess_config": {
      "template": "product_promo_portrait",
      "subtitle": "睡觉也能戴的轻盈耳环",
      "price_text": "限时 ¥299",
      "cta": "立即购买",
      "transparent_asset_id": 2,
      "logo_asset_id": 3
    }
  }]
}
```

`transparent_asset_id` 必须引用当前商品的 `transparent` 类型资产，`logo_asset_id` 必须引用 `logo` 类型资产。若没有显式指定，服务会从当前商品资产中自动选择对应类型的第一张素材；模板启用该图层但缺少资产时会拒绝合成，而不是生成一个不确定的替代品。
