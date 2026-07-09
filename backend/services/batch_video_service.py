import math
import time
import asyncio
import logging
from typing import List, Dict, Optional
from models.schemas import (
    ScriptResult, ScriptScene, VideoSegment, BatchVideoTask
)
from services import keling_service

logger = logging.getLogger(__name__)

# 内存存储批量任务（生产环境应使用数据库）
_batch_tasks: Dict[str, BatchVideoTask] = {}


def get_batch_task(batch_id: str) -> Optional[BatchVideoTask]:
    """获取批量任务"""
    return _batch_tasks.get(batch_id)


def save_batch_task(task: BatchVideoTask) -> None:
    """保存批量任务"""
    _batch_tasks[task.batch_id] = task


def create_segment_from_scenes(scenes: List[ScriptScene], segment_no: int) -> dict:
    """
    从场景列表创建一个片段的数据

    Args:
        scenes: 场景列表
        segment_no: 片段序号

    Returns:
        片段数据字典
    """
    # 合并场景描述作为 prompt
    prompt_parts = []
    for scene in scenes:
        prompt_parts.append(f"Scene {scene.scene_no}: {scene.visual}")

    prompt = " ".join(prompt_parts)
    total_duration = sum(s.duration for s in scenes)

    return {
        'prompt': prompt,
        'duration': total_duration,
        'scene_index': scenes[0].scene_no - 1,  # 使用第一个场景的索引
    }


def split_script_to_segments(script: ScriptResult, max_duration: float = 5.0) -> List[dict]:
    """
    将脚本拆分为多个片段，每个片段不超过 max_duration 秒

    策略：
    - 优先按场景边界拆分
    - 单个场景超过 5 秒则按时间切分
    - 保持场景描述完整性

    Args:
        script: 脚本对象
        max_duration: 单个片段最大时长（秒）

    Returns:
        片段数据列表
    """
    segments = []
    current_duration = 0.0
    current_scenes = []

    for scene in script.scenes:
        # 如果添加当前场景会超时，先保存当前片段
        if current_duration + scene.duration > max_duration:
            if current_scenes:
                segments.append(create_segment_from_scenes(current_scenes, len(segments) + 1))
                current_scenes = []
                current_duration = 0.0

        # 处理超长场景（超过 5 秒）
        if scene.duration > max_duration:
            # 先保存已有内容
            if current_scenes:
                segments.append(create_segment_from_scenes(current_scenes, len(segments) + 1))
                current_scenes = []
                current_duration = 0.0

            # 拆分长场景
            split_count = math.ceil(scene.duration / max_duration)
            for i in range(split_count):
                sub_duration = min(max_duration, scene.duration - i * max_duration)
                segments.append({
                    'prompt': f"Scene {scene.scene_no} part {i+1}: {scene.visual}",
                    'duration': sub_duration,
                    'scene_index': scene.scene_no - 1,
                })
        else:
            current_scenes.append(scene)
            current_duration += scene.duration

    # 保存最后一段
    if current_scenes:
        segments.append(create_segment_from_scenes(current_scenes, len(segments) + 1))

    logger.info(f"脚本拆分完成: {script.total_duration}秒 -> {len(segments)}个片段")
    return segments


async def generate_single_segment(
    segment: VideoSegment,
    params: Dict,
    max_retries: int = 3
) -> None:
    """
    生成单个视频片段，失败自动重试

    Args:
        segment: 片段对象
        params: 视频生成参数
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            segment.status = "processing"

            # 调用可灵 API
            keling_task = await keling_service.create_text2video({
                "prompt": segment.prompt,
                "model": params["model"],
                "duration": int(segment.duration),
                "aspect_ratio": params["aspect_ratio"],
                "cfg_scale": params["cfg_scale"],
            })

            segment.keling_task_id = keling_task.task_id
            logger.info(f"片段 {segment.segment_no} 任务创建成功: {keling_task.task_id}")

            # 轮询等待完成
            while True:
                await asyncio.sleep(5)
                status = await keling_service.get_task_status(keling_task.task_id)

                if status.status == "succeed":
                    segment.status = "succeed"
                    segment.video_url = status.video_url
                    segment.cover_url = status.cover_url
                    logger.info(f"片段 {segment.segment_no} 生成成功")
                    return
                elif status.status == "failed":
                    raise RuntimeError(status.error or "视频生成失败")

        except Exception as e:
            segment.retry_count += 1
            logger.warning(f"片段 {segment.segment_no} 生成失败 (第{attempt + 1}次): {e}")

            if attempt == max_retries - 1:
                segment.status = "failed"
                segment.error = str(e)
                logger.error(f"片段 {segment.segment_no} 重试 {max_retries} 次后仍失败")
            else:
                # 指数退避
                backoff_time = 2 ** attempt
                logger.info(f"片段 {segment.segment_no} {backoff_time}秒后重试...")
                await asyncio.sleep(backoff_time)


async def generate_segments_concurrent(
    segments: List[VideoSegment],
    params: Dict,
    max_concurrent: int = 3
) -> None:
    """
    并发生成视频片段，控制最大并发数

    使用 asyncio.Semaphore 控制并发

    Args:
        segments: 片段列表
        params: 视频生成参数
        max_concurrent: 最大并发数
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_one(segment: VideoSegment):
        async with semaphore:
            await generate_single_segment(segment, params)

    # 并发执行所有片段生成
    logger.info(f"开始并发生成 {len(segments)} 个片段，最大并发 {max_concurrent}")
    await asyncio.gather(*[generate_one(s) for s in segments], return_exceptions=True)


async def poll_segments_status(batch_id: str) -> BatchVideoTask:
    """
    查询批量任务状态，更新所有片段状态

    Args:
        batch_id: 批量任务 ID

    Returns:
        更新后的批量任务
    """
    task = get_batch_task(batch_id)
    if not task:
        raise ValueError(f"任务不存在: {batch_id}")

    has_update = False
    for segment in task.segments:
        if segment.status in ["pending", "processing"] and segment.keling_task_id:
            try:
                keling_status = await keling_service.get_task_status(segment.keling_task_id)

                if keling_status.status != segment.status:
                    segment.status = keling_status.status
                    has_update = True
                    logger.info(f"片段 {segment.segment_no} 状态更新: {keling_status.status}")

                if keling_status.status == "succeed":
                    segment.video_url = keling_status.video_url
                    segment.cover_url = keling_status.cover_url
                elif keling_status.status == "failed":
                    segment.error = keling_status.error

            except Exception as e:
                logger.error(f"查询片段 {segment.segment_no} 状态失败: {e}")

    # 更新整体状态
    succeed_count = sum(1 for s in task.segments if s.status == "succeed")
    failed_count = sum(1 for s in task.segments if s.status == "failed")
    total_count = len(task.segments)

    if succeed_count == total_count:
        if task.status != "merging" and task.status != "succeed":
            task.status = "merging"
            logger.info(f"批量任务 {batch_id} 所有片段完成，准备合并视频")
    elif failed_count > 0 and succeed_count + failed_count == total_count:
        task.status = "failed"
        task.error = f"{failed_count} 个片段生成失败"
        logger.error(f"批量任务 {batch_id} 部分片段失败")
    else:
        task.status = "processing"

    if has_update:
        save_batch_task(task)

    return task


async def retry_failed_segments(batch_id: str) -> BatchVideoTask:
    """
    重试所有失败的片段

    Args:
        batch_id: 批量任务 ID

    Returns:
        更新后的批量任务
    """
    task = get_batch_task(batch_id)
    if not task:
        raise ValueError(f"任务不存在: {batch_id}")

    params = task.video_params

    failed_segments = [s for s in task.segments if s.status == "failed"]
    if not failed_segments:
        logger.info(f"批量任务 {batch_id} 没有需要重试的片段")
        return task

    logger.info(f"重试 {len(failed_segments)} 个失败片段")

    # 重置失败片段状态
    for segment in failed_segments:
        segment.retry_count = 0
        segment.error = None
        segment.keling_task_id = None

    # 重新生成
    await generate_segments_concurrent(failed_segments, params, params.get("max_concurrent", 3))

    save_batch_task(task)
    return task


async def start_batch_generation(
    batch_id: str,
    model: str,
    aspect_ratio: str,
    cfg_scale: float,
    max_concurrent: int
) -> None:
    """
    启动批量视频生成（后台任务）

    Args:
        batch_id: 批量任务 ID
        model: 视频模型
        aspect_ratio: 画面比例
        cfg_scale: 创意强度
        max_concurrent: 最大并发数
    """
    task = get_batch_task(batch_id)
    if not task:
        logger.error(f"任务不存在: {batch_id}")
        return

    try:
        task.status = "processing"
        save_batch_task(task)

        params = {
            "model": model,
            "aspect_ratio": aspect_ratio,
            "cfg_scale": cfg_scale,
            "max_concurrent": max_concurrent,
        }

        # 并发生成所有片段
        await generate_segments_concurrent(task.segments, params, max_concurrent)

        # 检查是否全部成功
        succeed_count = sum(1 for s in task.segments if s.status == "succeed")
        if succeed_count == len(task.segments):
            logger.info(f"批量任务 {batch_id} 所有片段生成成功，等待合并")
        else:
            failed_count = len(task.segments) - succeed_count
            task.status = "failed"
            task.error = f"{failed_count} 个片段生成失败"
            logger.error(f"批量任务 {batch_id} 生成失败: {failed_count}/{len(task.segments)}")

        save_batch_task(task)

    except Exception as e:
        logger.exception(f"批量任务 {batch_id} 执行失败: {e}")
        task.status = "failed"
        task.error = str(e)
        save_batch_task(task)