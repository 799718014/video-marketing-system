"""Generate editable A-Roll, B-Roll and video-model prompt references."""

from __future__ import annotations

import json

import httpx

from config import DEEPSEEK_API_BASE, DEEPSEEK_API_KEY, DEEPSEEK_MODEL


class PromptGeneratorError(RuntimeError):
    """Raised when the optional text-model integration cannot create a draft."""


class PromptGenerator:
    @staticmethod
    def is_configured() -> bool:
        return bool(DEEPSEEK_API_KEY)

    async def generate(self, product: dict, scene: dict) -> dict[str, str]:
        if not self.is_configured():
            raise PromptGeneratorError("未配置 DEEPSEEK_API_KEY，无法生成 AI 参考稿；你仍可手工填写三段分镜内容")

        selling_points = "；".join(product.get("selling_points") or []) or "未提供"
        prohibited_terms = "；".join(product.get("prohibited_terms") or []) or "无"
        system_prompt = """你是商品短视频分镜策划。只返回一个 JSON 对象，字段固定为 narration、visual_description、ai_prompt。
narration 是适合 TTS 的中文旁白，须与给定时长相称；visual_description 是供人审核的中文 B-Roll 画面描述；ai_prompt 是直接提交给可灵视频模型的中文提示词。
不要编造商品事实、价格、品牌、性能或人物身份；三个字段都不得要求在画面生成文字、价格或品牌 Logo。AI Prompt 需要包含主体、动作、镜头、光线和画幅感受，并保持商品形状、材质、颜色及比例不变。"""
        user_prompt = f"""商品事实：
- 名称：{product.get('name') or '未命名商品'}
- 品牌：{product.get('brand') or '未提供'}
- 价格：{product.get('price') or '未提供'}
- 卖点：{selling_points}
- 禁用表述：{prohibited_terms}

请生成分镜 {scene['scene_no']} 的三段式参考稿：
- 分镜类型：{scene['scene_type']}
- 时长：{scene['target_duration']} 秒
- 生成方式：{scene['generation_strategy']}
只返回 JSON，不要 Markdown。"""
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{DEEPSEEK_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": DEEPSEEK_MODEL,
                        "temperature": 0.6,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            raise PromptGeneratorError(f"AI 参考稿生成请求失败: {error}") from error

        try:
            raw = payload["choices"][0]["message"]["content"]
            result = json.loads(raw)
            values = {field: str(result[field]).strip() for field in ("narration", "visual_description", "ai_prompt")}
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise PromptGeneratorError("AI 未返回可用的三段式分镜 JSON，请重试") from error
        if not all(values.values()):
            raise PromptGeneratorError("AI 返回的分镜参考稿不完整，请重试")
        return values


prompt_generator = PromptGenerator()
