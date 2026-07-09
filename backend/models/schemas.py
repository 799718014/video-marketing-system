from pydantic import BaseModel
from typing import Optional, List, Dict


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


# ========== 批量视频生成相关模型 ==========

class VideoSegment(BaseModel):
    segment_id: str                    # 片段唯一 ID
    segment_no: int                    # 片段序号 (1, 2, 3...)
    scene_index: int                   # 对应的场景索引
    duration: float                    # 片段时长（秒）
    prompt: str                        # 生成 prompt
    keling_task_id: Optional[str] = None    # 可灵任务 ID
    status: str                        # pending/processing/succeed/failed
    video_url: Optional[str] = None    # 视频下载 URL
    cover_url: Optional[str] = None    # 封面图 URL
    retry_count: int = 0               # 重试次数
    error: Optional[str] = None        # 错误信息


class BatchVideoTask(BaseModel):
    batch_id: str                      # 批量任务 ID
    script: ScriptResult               # 原始脚本
    video_params: Dict                 # 视频参数（模型、比例等）
    segments: List[VideoSegment]       # 片段列表
    status: str                        # submitted/processing/succeed/failed/merging
    merged_video_path: Optional[str] = None  # 拼接后视频本地路径
    merged_video_url: Optional[str] = None  # 拼接后视频 URL
    merged_cover_url: Optional[str] = None  # 拼接后封面 URL
    total_duration: float              # 总时长
    created_at: float                  # 创建时间戳
    completed_at: Optional[float] = None  # 完成时间戳
    error: Optional[str] = None        # 整体错误信息


class BatchVideoCreateRequest(BaseModel):
    script: ScriptResult               # 脚本数据
    model: str = "kling-v1-5"
    aspect_ratio: str = "9:16"
    cfg_scale: float = 0.5
    transition: str = "fade"           # 转场效果：fade/none
    max_concurrent: int = 3            # 最大并发数
