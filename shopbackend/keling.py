from __future__ import annotations

import os

import httpx

from config import KELING_API_BASE, KELING_REFERENCE_IMAGES_FIELD


class KelingClient:
    """仅负责图生视频任务的提交与状态标准化。"""

    @staticmethod
    def _headers() -> dict[str, str]:
        api_key = os.getenv("KELING_API_KEY", "")
        if not api_key:
            raise RuntimeError("KELING_API_KEY 未配置")
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def create_image_to_video(
        self, image_url: str, prompt: str, model: str, reference_image_urls: list[str] | None = None,
    ) -> dict:
        payload = {
            "model": model,
            "image": image_url,
            "prompt": prompt,
            "duration": 5,
            "aspect_ratio": "9:16",
        }
        if KELING_REFERENCE_IMAGES_FIELD and reference_image_urls:
            payload[KELING_REFERENCE_IMAGES_FIELD] = reference_image_urls
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{KELING_API_BASE}/v1/videos/image2video", headers=self._headers(), json=payload
            )
        if not response.is_success:
            raise RuntimeError(f"可灵图生视频创建失败 {response.status_code}: {response.text}")
        data = response.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"可灵图生视频业务错误: {data.get('message', data)}")
        task = data.get("data", {})
        task_id = task.get("task_id") or task.get("id")
        if not task_id:
            raise RuntimeError(f"可灵图生视频未返回任务 ID: {data}")
        return {"provider_task_id": task_id, "status": task.get("task_status") or task.get("status") or "submitted"}

    async def get_image_to_video_status(self, provider_task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{KELING_API_BASE}/v1/videos/image2video/{provider_task_id}", headers=self._headers()
            )
        if not response.is_success:
            raise RuntimeError(f"可灵图生视频查询失败 {response.status_code}: {response.text}")
        data = response.json()
        task = data.get("data", {})
        status = task.get("task_status") or task.get("status") or "processing"
        works = task.get("task_result", {}).get("videos") or task.get("works") or []
        video = works[0] if works else {}
        return {
            "status": status,
            "video_url": video.get("url"),
            "cover_url": video.get("cover_image_url"),
            "error": task.get("task_status_msg") or task.get("message"),
        }


keling = KelingClient()
