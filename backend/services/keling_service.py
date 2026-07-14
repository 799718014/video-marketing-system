import os
import logging
import httpx
from models.schemas import VideoCreateRequest, VideoTask, Image2VideoCreateRequest

logger = logging.getLogger(__name__)

KELING_API_BASE = "https://api-beijing.klingai.com"


def _get_bearer_token() -> str:
    """
    可灵AI 认证方式：直接将 API Key 作为 Bearer Token
    从 https://klingai.com/dev/api-key 获取，格式：api-key-kling-xxx
    """
    api_key = os.getenv("KELING_API_KEY", "")
    if not api_key:
        raise RuntimeError("KELING_API_KEY 未配置，请在 .env 中设置")
    # 调试日志：检查Key是否正确加载（只打印前缀和长度，隐藏敏感信息）
    logger.info(f"KELING_API_KEY loaded: prefix={api_key[:15]}... length={len(api_key)}")
    return api_key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
    }


async def create_text2video(req: VideoCreateRequest) -> VideoTask:
    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "duration": req.duration,          # 整数，单位：秒
        "aspect_ratio": req.aspect_ratio,
        "cfg_scale": req.cfg_scale,
    }
    logger.info("KeLing create_text2video payload: %s", payload)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{KELING_API_BASE}/v1/videos/text2video",
            headers=_headers(),
            json=payload,
        )
        if not resp.is_success:
            body = resp.text
            logger.error("KeLing API error %s: %s", resp.status_code, body)
            raise RuntimeError(f"可灵影音 API 错误 {resp.status_code}: {body}")
        data = resp.json()

    logger.info("KeLing response: %s", data)
    code = data.get("code", -1)
    if code != 0:
        msg = data.get("message", str(data))
        raise RuntimeError(f"可灵影音业务错误: {msg}")

    task_data = data.get("data", {})
    return VideoTask(
        task_id=task_data.get("task_id", ""),
        status=task_data.get("task_status", "submitted"),
    )


async def get_task_status(task_id: str) -> VideoTask:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{KELING_API_BASE}/v1/videos/text2video/{task_id}",
            headers=_headers(),
        )
        if not resp.is_success:
            body = resp.text
            logger.error("KeLing status error %s: %s", resp.status_code, body)
            raise RuntimeError(f"可灵影音查询错误 {resp.status_code}: {body}")
        data = resp.json()

    task_data = data.get("data", {})
    status = task_data.get("task_status", "processing")

    video_url = None
    cover_url = None
    error = None

    if status == "succeed":
        works = task_data.get("task_result", {}).get("videos", [])
        if works:
            video_url = works[0].get("url")
            cover_url = works[0].get("cover_image_url")
    elif status == "failed":
        error = task_data.get("task_status_msg", "视频生成失败")

    return VideoTask(
        task_id=task_id,
        status=status,
        video_url=video_url,
        cover_url=cover_url,
        error=error,
    )


async def create_image2video(req: Image2VideoCreateRequest) -> VideoTask:
    """可灵3.0 turbo 图生视频"""
    payload = {
        "model": req.model,
        "image": req.image_url,
        "prompt": req.prompt,
        "duration": req.duration,
        "aspect_ratio": req.aspect_ratio,
        "watermark_info": {
            "enabled": req.watermark_enabled
        }
    }

    # 可选参数
    if req.callback_url:
        payload["callback_url"] = req.callback_url
    if req.external_task_id:
        payload["external_task_id"] = req.external_task_id

    logger.info("KeLing create_image2video payload: %s", payload)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{KELING_API_BASE}/v1/videos/image2video",
            headers=_headers(),
            json=payload,
        )
        if not resp.is_success:
            body = resp.text
            logger.error("KeLing image2video API error %s: %s", resp.status_code, body)
            raise RuntimeError(f"可灵图生视频 API 错误 {resp.status_code}: {body}")
        data = resp.json()

    logger.info("KeLing image2video response: %s", data)
    code = data.get("code", -1)
    if code != 0:
        msg = data.get("message", str(data))
        raise RuntimeError(f"可灵图生视频业务错误: {msg}")

    task_data = data.get("data", {})
    return VideoTask(
        task_id=task_data.get("id", ""),
        status=task_data.get("status", "submitted"),
    )


async def get_image2video_status(task_id: str) -> VideoTask:
    """查询图生视频任务状态"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{KELING_API_BASE}/v1/videos/image2video/{task_id}",
            headers=_headers(),
        )
        if not resp.is_success:
            body = resp.text
            logger.error("KeLing image2video status error %s: %s", resp.status_code, body)
            raise RuntimeError(f"可灵图生视频查询错误 {resp.status_code}: {body}")
        data = resp.json()

    task_data = data.get("data", {})
    status = task_data.get("status", "processing")

    video_url = None
    cover_url = None
    error = None

    if status == "succeeded":
        works = task_data.get("works", [])
        if works:
            video_url = works[0].get("url")
            cover_url = works[0].get("cover_image_url")
    elif status == "failed":
        error = task_data.get("message", "图生视频失败")

    return VideoTask(
        task_id=task_id,
        status=status,
        video_url=video_url,
        cover_url=cover_url,
        error=error,
    )
