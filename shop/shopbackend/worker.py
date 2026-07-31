"""应用内图生视频调度 Worker：原子认领、幂等提交、状态轮询。"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from config import (
    GENERATION_CLAIM_LEASE_SECONDS, GENERATION_REFRESH_SECONDS,
    GENERATION_WORKER_ENABLED, GENERATION_WORKER_POLL_SECONDS, MAX_PROVIDER_PARALLEL,
)
from database import db
from keling import keling


logger = logging.getLogger(__name__)


class GenerationWorker:
    def __init__(self) -> None:
        self._wake_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._last_refresh = 0.0

    @property
    def enabled(self) -> bool:
        return GENERATION_WORKER_ENABLED

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(), name="generation-dispatch-worker")

    async def stop(self) -> None:
        self._stopping = True
        self._wake_event.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    def wake(self) -> None:
        """新任务入队或人工触发时立即唤醒，不等待下一次轮询。"""
        if self.enabled:
            self._wake_event.set()

    async def _run(self) -> None:
        while not self._stopping:
            try:
                db.recover_stale_submission_claims(GENERATION_CLAIM_LEASE_SECONDS)
                if keling.is_configured():
                    claimed = db.claim_next_queued_task(MAX_PROVIDER_PARALLEL)
                    if claimed:
                        await self._submit(claimed)
                        continue
                    await self._refresh_active_tasks_if_due()
            except Exception:
                logger.exception("图生视频后台调度异常；将在下一轮重试")
            self._wake_event.clear()
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=GENERATION_WORKER_POLL_SECONDS)
            except asyncio.TimeoutError:
                pass

    async def _submit(self, task: dict) -> None:
        strategy = task.get("generation_strategy", "image_to_video")
        try:
            if strategy == "text_to_video":
                result = await keling.create_text_to_video(
                    task["prompt"], task["model"], task["submission_key"],
                )
            else:
                references = [reference["url"] for reference in task.get("reference_manifest", [])]
                result = await keling.create_image_to_video(
                    task["image_url"], task["prompt"], task["model"], references, task["submission_key"],
                )
        except Exception as error:
            db.release_submission_claim(task["id"], task["submission_key"], str(error))
            logger.warning("视频生成任务 %s 提交失败，已安排重试：%s", task["id"], error)
            return
        if not db.complete_submission_claim(task["id"], task["submission_key"], result):
            logger.error("视频生成任务 %s 提交结果未写入；将依靠幂等键恢复", task["id"])

    async def _refresh_active_tasks_if_due(self) -> None:
        now = asyncio.get_running_loop().time()
        if now - self._last_refresh < GENERATION_REFRESH_SECONDS:
            return
        self._last_refresh = now
        for task in db.list_tasks_to_refresh():
            try:
                if task.get("source_type") == "kling_library":
                    item = await keling.get_library_video(task["source_provider_task_id"], task["source_task_type"])
                    result = {
                        "status": item["status"], "video_url": item.get("video_url"),
                        "cover_url": item.get("cover_url"), "error": item.get("error"),
                    }
                elif task.get("generation_strategy") == "text_to_video":
                    result = await keling.get_text_to_video_status(task["provider_task_id"])
                else:
                    result = await keling.get_image_to_video_status(task["provider_task_id"])
                db.update_generation_task(task["id"], **result)
            except Exception as error:
                logger.warning("视频生成任务 %s 状态刷新失败：%s", task["id"], error)


generation_worker = GenerationWorker()
