from pydantic import BaseModel
from typing import Optional, List


class ProductInfo(BaseModel):
    keywords: List[str]
    name: str
    brand: Optional[str] = None
    price: Optional[str] = None
    description: str
    features: List[str]
    target_audience: str


class ScriptRequest(BaseModel):
    product: ProductInfo
    style: str = "活力"  # 活力 / 专业 / 温情 / 搞笑
    duration: int = 30   # 15 / 30 / 60 秒
    platform: str = "抖音"


class ScriptScene(BaseModel):
    scene_no: int
    duration: float
    visual: str       # 画面描述
    narration: str    # 旁白台词
    subtitle: str     # 字幕文字


class ScriptResult(BaseModel):
    title: str
    total_duration: int
    style: str
    scenes: List[ScriptScene]
    full_prompt: str  # 汇总成可灵视频生成 prompt


class VideoCreateRequest(BaseModel):
    prompt: str
    model: str = "kling-v1"
    duration: int = 5          # 可灵单次最长 5 秒（kling-v1）
    aspect_ratio: str = "9:16" # 竖屏短视频
    cfg_scale: float = 0.5


class VideoTask(BaseModel):
    task_id: str
    status: str                # submitted / processing / succeed / failed
    video_url: Optional[str] = None
    cover_url: Optional[str] = None
    error: Optional[str] = None
