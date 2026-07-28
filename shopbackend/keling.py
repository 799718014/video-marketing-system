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

    @staticmethod
    def _parse_library_item(task_data: dict, task_type: str) -> dict:
        task_id = task_data.get("task_id") or task_data.get("id")
        if not task_id:
            raise RuntimeError(f"可灵视频库任务缺少 task_id: {task_data}")
        status = task_data.get("task_status") or task_data.get("status") or "processing"
        works = task_data.get("works") or task_data.get("task_result", {}).get("videos", [])
        video = works[0] if works else {}
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": status,
            "video_url": video.get("url"),
            "cover_url": video.get("cover_image_url"),
            "duration": video.get("duration"),
            "created_at": task_data.get("created_at"),
            "updated_at": task_data.get("updated_at"),
            "error": (task_data.get("task_status_msg") or task_data.get("message")) if status == "failed" else None,
        }

    async def list_video_library(self, task_type: str, page_num: int, page_size: int) -> dict:
        if task_type not in {"text2video", "image2video"}:
            raise ValueError("视频库仅支持 text2video 或 image2video")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{KELING_API_BASE}/v1/videos/{task_type}", headers=self._headers(),
                params={"pageNum": page_num, "pageSize": page_size},
            )
        if not response.is_success:
            raise RuntimeError(f"可灵视频库查询失败 {response.status_code}: {response.text}")
        data = response.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"可灵视频库业务错误: {data.get('message', data)}")
        tasks = data.get("data") or []
        if not isinstance(tasks, list):
            raise RuntimeError(f"可灵视频库响应格式异常: {data}")
        return {
            "items": [self._parse_library_item(task, task_type) for task in tasks],
            "page_num": page_num, "page_size": page_size, "task_type": task_type,
        }

    async def get_library_video(self, task_id: str, task_type: str) -> dict:
        if task_type not in {"text2video", "image2video"}:
            raise ValueError("视频库仅支持 text2video 或 image2video")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{KELING_API_BASE}/v1/videos/{task_type}/{task_id}", headers=self._headers()
            )
        if not response.is_success:
            raise RuntimeError(f"可灵视频库任务查询失败 {response.status_code}: {response.text}")
        data = response.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"可灵视频库任务业务错误: {data.get('message', data)}")
        return self._parse_library_item(data.get("data", {}), task_type)


keling = KelingClient()
