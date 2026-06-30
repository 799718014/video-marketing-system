import os
import json
from openai import AsyncOpenAI
from models.schemas import ProductInfo, ScriptResult, ScriptScene

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url="https://api.deepseek.com",
        )
    return _client

STYLE_GUIDE = {
    "活力": "节奏快、充满能量、年轻化，使用动感的场景切换，语气积极热情",
    "专业": "严谨权威、数据驱动、突出品质与技术，语气正式可信",
    "温情": "情感共鸣、生活化场景、真实感强，语气温暖亲切",
    "搞笑": "幽默轻松、反转情节、夸张表达，语气有趣好玩",
}


async def generate_script(
    product: ProductInfo,
    style: str,
    duration: int,
    platform: str,
) -> ScriptResult:
    style_desc = STYLE_GUIDE.get(style, STYLE_GUIDE["活力"])
    features_text = "\n".join(f"- {f}" for f in product.features)
    keywords_text = "、".join(product.keywords)

    system_prompt = """你是一位专业的短视频广告脚本创作专家，擅长为商品创作适合短视频平台的宣传脚本。
请严格按照 JSON 格式返回脚本，不要包含任何 Markdown 代码块标记。"""

    user_prompt = f"""请为以下商品创作一个 {duration} 秒的短视频宣传脚本。

## 商品信息
- 关键词：{keywords_text}
- 商品名称：{product.name}
- 品牌：{product.brand or "未指定"}
- 价格：{product.price or "未指定"}
- 商品描述：{product.description}
- 产品亮点：
{features_text}
- 目标人群：{product.target_audience}

## 创作要求
- 视频风格：{style}（{style_desc}）
- 目标平台：{platform}
- 视频总时长：{duration} 秒
- 场景数量：{max(3, duration // 10)} 个场景

## 输出格式（JSON）
{{
  "title": "视频标题",
  "total_duration": {duration},
  "style": "{style}",
  "scenes": [
    {{
      "scene_no": 1,
      "duration": 秒数（浮点数）,
      "visual": "画面视觉描述，描述场景、镜头、色调、动作",
      "narration": "旁白或人物台词",
      "subtitle": "屏幕字幕文字"
    }}
  ],
  "full_prompt": "将所有场景描述整合为一段适合 AI 视频生成的英文 prompt，描述视频整体风格、场景和氛围"
}}"""

    response = await _get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()
    data = json.loads(raw)

    scenes = [ScriptScene(**s) for s in data["scenes"]]
    return ScriptResult(
        title=data["title"],
        total_duration=data["total_duration"],
        style=data["style"],
        scenes=scenes,
        full_prompt=data["full_prompt"],
    )
