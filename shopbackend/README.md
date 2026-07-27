# 商品资产驱动图生视频服务（P0）

该服务实现“真实商品资产锁定身份 + 图生视频生成运动 + 后期图层配置”的后端基础能力。

## 能力

- 商品事实库：名称、品牌、价格、卖点、禁用词；
- 商品资产库：主图、多角度图、细节图、佩戴图、透明底图和 Logo；
- 分镜与商品资产强关联；
- 商品主体仅允许 `image_to_video` 策略；
- 图生视频任务队列与单任务调度，默认仅提交一个可灵任务；
- P1 确定性合成：透明底商品图、Logo、字幕、价格和 CTA 均由模板渲染；
- 统一编码后按分镜顺序拼接，输出可发布的最终视频。

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

`PUBLIC_BASE_URL` 必须是可灵能够访问的公网 HTTPS 域名。`localhost` 上传的文件只能用于本地预览，不能直接提交给可灵。

P1 合成依赖 FFmpeg。生产环境应在镜像内安装 FFmpeg，并将 `FFMPEG_FONT_FILE` 配置为包含中文字符的字体文件。成片输出至 `data/outputs`，通过 `/outputs/{filename}` 提供访问。

## 推荐调用顺序

1. `POST /api/products` 创建商品事实；
2. `POST /api/products/{id}/assets` 注册 CDN 商品图，或上传图片资产；
3. `POST /api/products/{id}/storyboards` 创建关联资产的图生视频分镜；
4. `POST /api/storyboards/{id}/generation-tasks` 创建待提交队列；
5. 重复调用 `POST /api/storyboards/{id}/dispatch-next`，每次只提交一个任务；
6. `POST /api/generation-tasks/{id}/refresh` 查询可灵状态；任务结束后再调度下一项。
7. 对每个已得到 `video_url` 的任务调用 `POST /api/generation-tasks/{id}/compose`；
8. 全部分镜合成成功后调用 `POST /api/storyboards/{id}/compose-final` 获取最终成片。

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
