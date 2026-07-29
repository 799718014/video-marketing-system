from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from compositor import CompositionError, compositor
from config import (
    KELING_ASSET_BASE_URL, KELING_IMAGE_TO_VIDEO_MODEL, MAX_PROVIDER_PARALLEL,
    OUTPUT_DIR, PUBLIC_BASE_URL, UPLOAD_DIR, ensure_directories,
)
from database import db
from keling import keling
from preflight import PreflightError, asset_preflight
from qiniu_storage import QiniuStorageError, qiniu_storage
from quality_service import quality_reviewer
from worker import generation_worker
from schemas import (
    AssetType, CandidateSelectionRequest, CandidateTaskRequest, ManualQualityReviewRequest,
    KlingLibraryVideoImportRequest, ProductAssetCreate, ProductCreate, StoryboardCreate, StoryboardSceneUpdate,
)


ensure_directories()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await generation_worker.start()
    try:
        yield
    finally:
        await generation_worker.stop()


app = FastAPI(title="商品资产驱动图生视频服务", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=UPLOAD_DIR), name="assets")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


def require_product(product_id: int) -> dict:
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def require_storyboard(storyboard_id: int) -> dict:
    storyboard = db.get_storyboard(storyboard_id)
    if not storyboard:
        raise HTTPException(status_code=404, detail="分镜不存在")
    return storyboard


def verify_asset_belongs_to_product(asset_id: int | None, product_id: int) -> None:
    if asset_id is None:
        raise HTTPException(status_code=422, detail="图生视频分镜必须关联真实商品资产")
    asset = db.get_asset(asset_id)
    if not asset or asset["product_id"] != product_id:
        raise HTTPException(status_code=422, detail="商品资产不存在或不属于当前商品")


def verify_postprocess_assets(config: dict, product_id: int) -> None:
    """后期图层只能引用当前商品的透明底图和品牌 Logo，防止串品。"""
    expected_types = {"transparent_asset_id": "transparent", "logo_asset_id": "logo"}
    for field, expected_type in expected_types.items():
        asset_id = config.get(field)
        if asset_id is None:
            continue
        asset = db.get_asset(asset_id)
        if not asset or asset["product_id"] != product_id:
            raise HTTPException(status_code=422, detail=f"{field} 不属于当前商品")
        if asset["asset_type"] != expected_type:
            raise HTTPException(status_code=422, detail=f"{field} 必须引用 {expected_type} 类型资产")


def verify_reference_assets(references: list[dict], product_id: int) -> None:
    """多参考图只能绑定当前商品资产，确保候选生成和质检可完整追溯。"""
    for reference in references:
        asset = db.get_asset(reference["asset_id"])
        if not asset or asset["product_id"] != product_id:
            raise HTTPException(status_code=422, detail=f"参考资产 #{reference['asset_id']} 不属于当前商品")


async def preflight_registered_asset(asset_id: int, product_id: int) -> dict:
    """重新验证已登记资产，避免外链失效或被替换后仍进入生成队列。"""
    asset = db.get_asset(asset_id)
    if not asset or asset["product_id"] != product_id:
        raise HTTPException(status_code=422, detail=f"商品资产 #{asset_id} 不存在或不属于当前商品")
    try:
        result = await asset_preflight.inspect_url(asset["url"], asset["asset_type"])
    except PreflightError as error:
        db.save_asset_preflight(asset_id, None, str(error))
        raise HTTPException(status_code=422, detail=f"商品资产 #{asset_id} 预检失败: {error}") from error
    return db.save_asset_preflight(asset_id, result) or asset


async def preflight_scene_assets(scene: dict, product_id: int) -> None:
    """在创建分镜、修改分镜和入队时验证该分镜实际会使用到的所有商品素材。"""
    asset_ids = set()
    if scene.get("generation_strategy") == "image_to_video" and scene.get("asset_id"):
        asset_ids.add(scene["asset_id"])
    asset_ids.update(reference["asset_id"] for reference in scene.get("reference_assets", []))

    assets = db.list_assets(product_id)
    config = scene.get("postprocess_config", {})
    layers = set(scene.get("postprocess_layers", []))
    for layer, field, asset_type in (
        ("transparent_product", "transparent_asset_id", "transparent"),
        ("brand_logo", "logo_asset_id", "logo"),
    ):
        if layer not in layers:
            continue
        asset_id = config.get(field)
        if asset_id is None:
            asset_id = next((asset["id"] for asset in assets if asset["asset_type"] == asset_type), None)
        if asset_id is None:
            raise HTTPException(status_code=422, detail=f"分镜模板需要 {asset_type} 素材，请先登记并通过预检")
        asset_ids.add(asset_id)

    for asset_id in asset_ids:
        await preflight_registered_asset(asset_id, product_id)


def require_public_asset_url(url: str) -> None:
    """只允许可灵从配置的七牛云 CDN 域名拉取商品素材。"""
    parsed = urlparse(url)
    asset_base = urlparse(KELING_ASSET_BASE_URL)
    base_path = asset_base.path.rstrip("/")
    matches_asset_base = (
        parsed.scheme == "https" and asset_base.scheme == "https" and parsed.netloc == asset_base.netloc
        and (not base_path or parsed.path == base_path or parsed.path.startswith(f"{base_path}/"))
    )
    if not matches_asset_base:
        raise HTTPException(
            status_code=422,
            detail="商品图必须位于 KELING_ASSET_BASE_URL 配置的七牛云 HTTPS 域名下；请通过 /assets/upload 上传后再提交生成",
        )


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "max_provider_parallel": MAX_PROVIDER_PARALLEL,
        "public_base_url": PUBLIC_BASE_URL,
        "keling_asset_base_url": KELING_ASSET_BASE_URL,
        "keling_configured": bool(os.environ.get("KELING_API_KEY")),
        "qiniu_configured": qiniu_storage.configured,
        "generation_worker_enabled": generation_worker.enabled,
        "generation_worker_running": generation_worker.running,
    }


@app.post("/api/products", status_code=201)
def create_product(payload: ProductCreate) -> dict:
    return db.create_product(payload.model_dump())


@app.get("/api/products/{product_id}")
def get_product(product_id: int) -> dict:
    return require_product(product_id)


@app.get("/api/products/{product_id}/assets")
def list_assets(product_id: int) -> list[dict]:
    require_product(product_id)
    return db.list_assets(product_id)


@app.post("/api/products/{product_id}/assets", status_code=201)
async def create_asset(product_id: int, payload: ProductAssetCreate) -> dict:
    require_product(product_id)
    values = payload.model_dump()
    try:
        result = await asset_preflight.inspect_url(str(values["url"]), values["asset_type"])
    except PreflightError as error:
        raise HTTPException(status_code=422, detail=f"商品素材预检失败: {error}") from error
    values["metadata"]["preflight"] = {"status": "passed", "result": result, "error": None}
    return db.create_asset(product_id, values)


@app.post("/api/products/{product_id}/assets/upload", status_code=201)
async def upload_asset(
    product_id: int,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    is_primary: bool = Form(False),
) -> dict:
    """先在本地预检，再上传至七牛云 Kodo，并以 CDN URL 登记商品资产。"""
    require_product(product_id)
    try:
        qiniu_storage.require_config()
    except QiniuStorageError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="仅支持图片资产")
    try:
        normalized_asset_type = AssetType(asset_type).value
    except ValueError:
        raise HTTPException(status_code=422, detail="不支持的商品资产类型")
    suffix = Path(file.filename or "asset.png").suffix.lower() or ".png"
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        # 本地先做格式、尺寸和透明通道检查，避免无效素材占用云端空间。
        await asset_preflight.inspect_url(f"{PUBLIC_BASE_URL}/assets/{filename}", normalized_asset_type)
        object_key = qiniu_storage.build_object_key(product_id, filename)
        uploaded = await asyncio.to_thread(qiniu_storage.upload_image, destination, object_key)
        result = await asset_preflight.inspect_url(uploaded["url"], normalized_asset_type)
        return db.create_asset(product_id, {
            "asset_type": normalized_asset_type,
            "url": uploaded["url"],
            "is_primary": is_primary,
            "metadata": {
                "filename": file.filename, "content_type": file.content_type,
                "qiniu_key": uploaded["key"], "qiniu_hash": uploaded.get("hash"),
                "preflight": {"status": "passed", "result": result, "error": None},
            },
        })
    except PreflightError as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"商品素材预检失败: {error}") from error
    except QiniuStorageError as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception:
        destination.unlink(missing_ok=True)
        raise


@app.post("/api/products/{product_id}/assets/{asset_id}/preflight")
async def run_asset_preflight(product_id: int, asset_id: int) -> dict:
    """对历史资产或外链刷新后的素材执行显式预检。"""
    require_product(product_id)
    return await preflight_registered_asset(asset_id, product_id)


@app.post("/api/products/{product_id}/storyboards", status_code=201)
async def create_storyboard(product_id: int, payload: StoryboardCreate) -> dict:
    require_product(product_id)
    scenes = [scene.model_dump() for scene in payload.scenes]
    for scene in scenes:
        if scene["generation_strategy"] == "image_to_video":
            verify_asset_belongs_to_product(scene.get("asset_id"), product_id)
        verify_reference_assets(scene.get("reference_assets", []), product_id)
        verify_postprocess_assets(scene.get("postprocess_config", {}), product_id)
        await preflight_scene_assets(scene, product_id)
    return db.create_storyboard(product_id, payload.title, scenes)


@app.get("/api/storyboards/{storyboard_id}")
def get_storyboard(storyboard_id: int) -> dict:
    return require_storyboard(storyboard_id)


@app.get("/api/kling-video-library")
async def get_kling_video_library(
    task_type: str = Query("text2video", pattern="^(text2video|image2video)$"),
    page_num: int = Query(1, ge=1, le=1000),
    page_size: int = Query(12, ge=1, le=100),
) -> dict:
    """读取当前可灵账号历史任务，用于候选片段复用；视频 URL 可能过期。"""
    try:
        return await keling.list_video_library(task_type, page_num, page_size)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"可灵视频库查询失败: {error}")


@app.put("/api/storyboard-scenes/{scene_id}")
async def update_scene(scene_id: int, payload: StoryboardSceneUpdate) -> dict:
    scene = db.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="分镜不存在")
    values = payload.model_dump(exclude_unset=True)
    if values.get("asset_id") is not None:
        verify_asset_belongs_to_product(values["asset_id"], scene["product_id"])
    if values.get("postprocess_config") is not None:
        verify_postprocess_assets(values["postprocess_config"], scene["product_id"])
    if values.get("reference_assets") is not None:
        verify_reference_assets(values["reference_assets"], scene["product_id"])
    prospective_scene = {**scene, **values}
    await preflight_scene_assets(prospective_scene, scene["product_id"])
    updated = db.update_scene(scene_id, values)
    return updated


@app.post("/api/storyboard-scenes/{scene_id}/import-kling-video", status_code=201)
async def import_kling_library_video(scene_id: int, payload: KlingLibraryVideoImportRequest) -> dict:
    """校验当前账号可灵任务后，将已完成视频引入本分镜候选池。"""
    scene = db.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="分镜不存在")
    await preflight_scene_assets(scene, scene["product_id"])
    try:
        library_item = await keling.get_library_video(payload.task_id, payload.task_type)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"可灵视频库任务查询失败: {error}")
    if library_item["status"] not in {"succeed", "succeeded"} or not library_item.get("video_url"):
        raise HTTPException(status_code=409, detail="该可灵视频尚未生成完成或下载链接不可用")
    task = db.import_kling_library_video(scene_id, library_item)
    if not task:
        raise HTTPException(status_code=404, detail="分镜不存在")
    return task


@app.post("/api/storyboards/{storyboard_id}/generation-tasks", status_code=201)
async def queue_generation_tasks(storyboard_id: int) -> list[dict]:
    storyboard = require_storyboard(storyboard_id)
    for scene in storyboard["scenes"]:
        if scene["generation_strategy"] == "image_to_video":
            if not scene["asset_id"] or not scene["asset_url"]:
                raise HTTPException(status_code=422, detail=f"分镜 {scene['scene_no']} 未关联商品图")
            require_public_asset_url(scene["asset_url"])
            await preflight_scene_assets(scene, storyboard["product_id"])
    tasks = db.queue_storyboard_tasks(storyboard_id, KELING_IMAGE_TO_VIDEO_MODEL)
    generation_worker.wake()
    return tasks


@app.post("/api/storyboards/{storyboard_id}/candidate-tasks", status_code=201)
async def queue_candidate_tasks(storyboard_id: int, payload: CandidateTaskRequest) -> list[dict]:
    """为每个分镜创建可人工对比的候选片段组，最多四个候选，避免无限并发。"""
    storyboard = require_storyboard(storyboard_id)
    for scene in storyboard["scenes"]:
        if scene["generation_strategy"] != "image_to_video":
            continue
        if not scene["asset_url"]:
            raise HTTPException(status_code=422, detail=f"分镜 {scene['scene_no']} 未关联商品图")
        require_public_asset_url(scene["asset_url"])
        for reference in scene["reference_assets"]:
            require_public_asset_url(reference["url"])
        await preflight_scene_assets(scene, storyboard["product_id"])
    tasks = db.queue_storyboard_tasks(
        storyboard_id, KELING_IMAGE_TO_VIDEO_MODEL, payload.candidate_count, payload.force_new,
    )
    generation_worker.wake()
    return tasks


@app.post("/api/storyboards/{storyboard_id}/dispatch-next")
async def dispatch_next_task(storyboard_id: int) -> dict:
    """兼容旧入口：不直接提交，改为唤醒后台 Worker 原子认领队列任务。"""
    require_storyboard(storyboard_id)
    generation_worker.wake()
    return {
        "status": "queued_for_dispatch",
        "message": "后台 Worker 将按全局并发配额原子认领并提交任务",
    }


@app.get("/api/generation-tasks/{task_id}")
def get_generation_task(task_id: int) -> dict:
    task = db.get_generation_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    return task


@app.get("/api/storyboards/{storyboard_id}/generation-tasks")
def list_generation_tasks(storyboard_id: int) -> list[dict]:
    require_storyboard(storyboard_id)
    return db.list_generation_tasks(storyboard_id)


@app.post("/api/generation-tasks/{task_id}/select")
def select_generation_candidate(task_id: int, payload: CandidateSelectionRequest) -> dict:
    task = db.get_generation_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    if not task.get("video_url"):
        raise HTTPException(status_code=409, detail="候选片段尚未生成完成，不能选片")
    selected = db.select_candidate(task_id, payload.reviewer, payload.note)
    return selected or task


@app.post("/api/generation-tasks/{task_id}/quality-review")
async def run_quality_review(task_id: int) -> dict:
    context = db.get_quality_context(task_id)
    if not context:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    try:
        review = await quality_reviewer.inspect(context)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error))
    saved = db.save_quality_check(task_id, review)
    return {"task": saved, "review": review}


@app.post("/api/generation-tasks/{task_id}/quality-review/manual")
def save_manual_quality_review(task_id: int, payload: ManualQualityReviewRequest) -> dict:
    task = db.get_generation_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    saved = db.save_quality_check(task_id, {
        "engine": "manual_review", "status": "completed", "reviewer": payload.reviewer,
        "product_similarity_score": payload.product_similarity_score, "logo_status": payload.logo_status,
        "ocr_status": payload.ocr_status, "decision": payload.decision, "summary": payload.note or "人工质检完成",
        "details": payload.model_dump(),
    })
    return saved or task


@app.get("/api/storyboards/{storyboard_id}/trace")
def get_storyboard_trace(storyboard_id: int) -> list[dict]:
    require_storyboard(storyboard_id)
    return db.get_storyboard_trace(storyboard_id)


@app.post("/api/generation-tasks/{task_id}/refresh")
async def refresh_generation_task(task_id: int) -> dict:
    task = db.get_generation_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    if not task["provider_task_id"]:
        raise HTTPException(status_code=409, detail="任务尚未提交到可灵")
    try:
        if task.get("source_type") == "kling_library":
            item = await keling.get_library_video(task["source_provider_task_id"], task["source_task_type"])
            result = {"status": item["status"], "video_url": item.get("video_url"), "cover_url": item.get("cover_url"), "error": item.get("error")}
        else:
            result = await keling.get_image_to_video_status(task["provider_task_id"])
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"图生视频状态查询失败: {error}")
    return db.update_generation_task(task_id, **result)


@app.post("/api/generation-tasks/{task_id}/compose")
async def compose_generation_task(task_id: int) -> dict:
    """将图生视频底片与透明商品图、Logo、字幕/价格/CTA 模板合成为确定性片段。"""
    context = db.get_composition_context(task_id)
    if not context:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    scene = db.get_scene(context["scene_id"])
    if not scene:
        raise HTTPException(status_code=404, detail="分镜不存在")
    await preflight_scene_assets(scene, scene["product_id"])
    db.update_generation_task(task_id, composition_status="processing", composition_error=None)
    try:
        composed_video_url = compositor.compose_scene(context)
    except CompositionError as error:
        db.update_generation_task(task_id, composition_status="failed", composition_error=str(error))
        raise HTTPException(status_code=422, detail=str(error))
    return db.update_generation_task(
        task_id, composed_video_url=composed_video_url, composition_status="succeeded", composition_error=None
    )


@app.post("/api/storyboards/{storyboard_id}/compose-final")
def compose_final_video(storyboard_id: int) -> dict:
    """按分镜顺序拼接已完成后期合成的片段，得到可直接发布的最终视频。"""
    require_storyboard(storyboard_id)
    unselected_scenes = db.list_unselected_candidate_scenes(storyboard_id)
    if unselected_scenes:
        raise HTTPException(status_code=409, detail=f"分镜 {', '.join(map(str, unselected_scenes))} 存在候选片段，请先人工选片")
    tasks = db.list_storyboard_composed_tasks(storyboard_id)
    db.update_storyboard_final(storyboard_id, final_composition_status="processing", final_composition_error=None)
    try:
        final_video_url = compositor.merge_storyboard(storyboard_id, tasks)
    except CompositionError as error:
        db.update_storyboard_final(storyboard_id, final_composition_status="failed", final_composition_error=str(error))
        raise HTTPException(status_code=422, detail=str(error))
    return db.update_storyboard_final(
        storyboard_id,
        final_video_url=final_video_url,
        final_composition_status="succeeded",
        final_composition_error=None,
    )
