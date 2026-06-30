import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from models.schemas import VideoCreateRequest, VideoTask
from services import keling_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=VideoTask)
async def create_video(req: VideoCreateRequest):
    try:
        task = await keling_service.create_text2video(req)
        return task
    except Exception as e:
        logger.exception("create_video failed")
        raise HTTPException(status_code=500, detail=f"视频创建失败：{str(e)}")


@router.get("/status/{task_id}", response_model=VideoTask)
async def get_video_status(task_id: str):
    try:
        task = await keling_service.get_task_status(task_id)
        return task
    except Exception as e:
        logger.exception("get_video_status failed")
        raise HTTPException(status_code=500, detail=f"查询状态失败：{str(e)}")


@router.get("/download/{task_id}")
async def download_video(task_id: str):
    task = await keling_service.get_task_status(task_id)
    if task.status != "succeed" or not task.video_url:
        raise HTTPException(status_code=404, detail="视频尚未生成完成")

    async def stream_video():
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", task.video_url) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    filename = f"video_{task_id}.mp4"
    return StreamingResponse(
        stream_video(),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
