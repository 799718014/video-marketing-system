import logging
import time
import os
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import httpx
from models.schemas import (
    BatchVideoCreateRequest, BatchVideoTask, VideoSegment
)
from services import batch_video_service
from utils import video_merge

logger = logging.getLogger(__name__)

router = APIRouter()

# 输出目录配置
OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", "./output_videos")


def ensure_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)


# 1. 创建批量视频任务
@router.post("/create", response_model=BatchVideoTask)
async def create_batch_video(
    req: BatchVideoCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    创建批量视频生成任务

    流程：
    1. 生成 batch_id
    2. 将脚本拆分为多个片段
    3. 初始化任务状态
    4. 启动后台任务并发生成片段
    """
    ensure_output_dir()

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    # 拆分脚本为片段
    segments_data = batch_video_service.split_script_to_segments(req.script, max_duration=5.0)

    # 创建片段对象
    segments = []
    for i, seg_data in enumerate(segments_data):
        segments.append(VideoSegment(
            segment_id=f"{batch_id}_seg_{i}",
            segment_no=i + 1,
            scene_index=seg_data['scene_index'],
            duration=seg_data['duration'],
            prompt=seg_data['prompt'],
            status="pending",
        ))

    # 创建批量任务
    task = BatchVideoTask(
        batch_id=batch_id,
        script=req.script,
        video_params={
            "model": req.model,
            "aspect_ratio": req.aspect_ratio,
            "cfg_scale": req.cfg_scale,
            "transition": req.transition,
            "max_concurrent": req.max_concurrent,
        },
        segments=segments,
        status="submitted",
        total_duration=sum(s.duration for s in segments),
        created_at=time.time(),
    )

    batch_video_service.save_batch_task(task)

    # 启动后台任务
    background_tasks.add_task(
        batch_video_service.start_batch_generation,
        batch_id,
        req.model,
        req.aspect_ratio,
        req.cfg_scale,
        req.max_concurrent,
    )

    logger.info(f"批量任务创建成功: {batch_id}, 片段数: {len(segments)}")
    return task


# 2. 查询批量任务状态
@router.get("/status/{batch_id}", response_model=BatchVideoTask)
async def get_batch_status(batch_id: str):
    """
    查询批量任务状态，更新所有片段状态

    如果所有片段都成功，触发视频合并
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 更新片段状态
    task = await batch_video_service.poll_segments_status(batch_id)

    # 检查是否需要合并视频
    if task.status == "merging" and task.merged_video_path is None:
        succeed_count = sum(1 for s in task.segments if s.status == "succeed")
        if succeed_count == len(task.segments):
            # 启动合并任务
            logger.info(f"启动视频合并任务: {batch_id}")
            # 注意：这里使用 BackgroundTasks 会在当前请求结束后执行
            # 但实际上合并可能需要较长时间，更好的方式是使用单独的异步任务
            # 这里简化处理，让前端轮询时检查合并状态

    return task


# 3. 合并视频（内部接口，由任务状态触发）
async def merge_video_if_ready(batch_id: str):
    """
    检查并合并视频（内部使用）

    Args:
        batch_id: 批量任务 ID
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        logger.error(f"任务不存在: {batch_id}")
        return

    # 检查是否所有片段都成功
    succeed_segments = [s for s in task.segments if s.status == "succeed"]
    if len(succeed_segments) != len(task.segments):
        logger.warning(f"任务 {batch_id} 并非所有片段都成功，跳过合并")
        return

    # 提取视频 URL
    segment_urls = [s.video_url for s in succeed_segments if s.video_url]
    if not segment_urls:
        logger.error(f"任务 {batch_id} 没有有效的视频 URL")
        task.status = "failed"
        task.error = "没有可用的视频片段"
        batch_video_service.save_batch_task(task)
        return

    # 输出路径
    output_path = os.path.join(OUTPUT_DIR, f"merged_{batch_id}.mp4")
    video_merge.VideoMerger.ensure_output_dir(output_path)

    try:
        logger.info(f"开始合并视频: {batch_id}, {len(segment_urls)} 个片段")

        # 合并视频
        await video_merge.VideoMerger.merge_videos(
            segment_urls=segment_urls,
            output_path=output_path,
            transition=task.video_params.get("transition", "fade"),
            transition_duration=0.5,
        )

        # 更新任务状态
        task.merged_video_path = output_path
        task.merged_video_url = f"/api/batch-video/merged/{batch_id}"
        task.status = "succeed"
        task.completed_at = time.time()

        # 使用第一个片段的封面
        if succeed_segments and succeed_segments[0].cover_url:
            task.merged_cover_url = succeed_segments[0].cover_url

        batch_video_service.save_batch_task(task)
        logger.info(f"视频合并成功: {batch_id}, 输出: {output_path}")

    except Exception as e:
        logger.exception(f"视频合并失败: {batch_id}, {e}")
        task.status = "failed"
        task.error = f"视频合并失败: {str(e)}"
        batch_video_service.save_batch_task(task)


# 4. 下载拼接后的视频
@router.get("/download/{batch_id}")
async def download_merged_video(batch_id: str):
    """
    下载拼接后的完整视频
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查是否需要合并
    if task.status == "merging" and task.merged_video_path is None:
        await merge_video_if_ready(batch_id)
        task = batch_video_service.get_batch_task(batch_id)

    if task.status != "succeed" or not task.merged_video_path:
        raise HTTPException(
            status_code=404,
            detail=f"视频尚未完成拼接 (当前状态: {task.status})"
        )

    if not os.path.exists(task.merged_video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    return FileResponse(
        task.merged_video_path,
        media_type="video/mp4",
        filename=f"video_{batch_id}.mp4"
    )


# 5. 重试失败片段
@router.post("/retry/{batch_id}", response_model=BatchVideoTask)
async def retry_segments(batch_id: str, background_tasks: BackgroundTasks):
    """
    重试所有失败的片段
    """
    task = get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["processing", "failed"]:
        raise HTTPException(status_code=400, detail="当前状态不支持重试")

    # 启动重试任务
    background_tasks.add_task(batch_video_service.retry_failed_segments, batch_id)

    return task


# 6. 取消任务
@router.post("/cancel/{batch_id}", response_model=BatchVideoTask)
async def cancel_batch(batch_id: str):
    """
    取消批量任务（将未开始的片段标记为取消）
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    for segment in task.segments:
        if segment.status == "pending":
            segment.status = "cancelled"

    task.status = "failed"
    task.error = "用户取消任务"
    batch_video_service.save_batch_task(task)

    logger.info(f"批量任务已取消: {batch_id}")
    return task


# 7. 获取片段视频（单独下载）
@router.get("/segment/{batch_id}/{segment_no}")
async def download_segment_video(batch_id: str, segment_no: int):
    """
    下载单个片段的视频（用于预览或单独使用）
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    segment = next((s for s in task.segments if s.segment_no == segment_no), None)
    if not segment:
        raise HTTPException(status_code=404, detail="片段不存在")

    if segment.status != "succeed" or not segment.video_url:
        raise HTTPException(status_code=404, detail="片段视频尚未生成")

    async def stream_video_url(url: str):
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", url) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(
        stream_video_url(segment.video_url),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="segment_{segment_no}.mp4"'},
    )


# 8. 检查合并状态（前端轮询用）
@router.get("/check-merge/{batch_id}", response_model=BatchVideoTask)
async def check_merge_status(batch_id: str):
    """
    检查视频合并状态
    前端可以轮询此接口来了解视频是否合并完成
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 如果状态是 merging 且未合并，触发合并
    if task.status == "merging" and task.merged_video_path is None:
        await merge_video_if_ready(batch_id)
        task = batch_video_service.get_batch_task(batch_id)

    return task


# 修复 get_batch_id 函数调用错误
def get_batch_task(batch_id: str) -> BatchVideoTask:
    """
    获取批量任务（路由内部使用）

    Args:
        batch_id: 批量任务 ID

    Returns:
        批量任务对象
    """
    task = batch_video_service.get_batch_task(batch_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


# 重试接口修正
@router.post("/retry/{batch_id}", response_model=BatchVideoTask)
async def retry_segments_fixed(batch_id: str, background_tasks: BackgroundTasks):
    """
    重试所有失败的片段
    """
    task = get_batch_task(batch_id)

    if task.status not in ["processing", "failed"]:
        raise HTTPException(status_code=400, detail="当前状态不支持重试")

    # 启动重试任务
    background_tasks.add_task(batch_video_service.retry_failed_segments, batch_id)

    return task