from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from compositor import CompositionError, compositor
from config import KELING_IMAGE_TO_VIDEO_MODEL, MAX_PROVIDER_PARALLEL, OUTPUT_DIR, PUBLIC_BASE_URL, UPLOAD_DIR, ensure_directories
from database import db
from keling import keling
from quality_service import quality_reviewer
from schemas import (
    AssetType, CandidateSelectionRequest, CandidateTaskRequest, ManualQualityReviewRequest,
    ProductAssetCreate, ProductCreate, StoryboardCreate, StoryboardSceneUpdate,
)


ensure_directories()
app = FastAPI(title="商品资产驱动图生视频服务", version="0.1.0")
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


def require_public_asset_url(url: str) -> None:
    """可灵需要从公网拉取参考图，本地 localhost URL 不能用于图生视频。"""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=422,
            detail="商品图必须是可被可灵访问的公网 HTTPS URL；请配置对象存储/CDN 的 PUBLIC_BASE_URL 后再提交生成",
        )


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "max_provider_parallel": MAX_PROVIDER_PARALLEL,
        "public_base_url": PUBLIC_BASE_URL,
        "keling_configured": bool(os.environ.get("KELING_API_KEY")),
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
def create_asset(product_id: int, payload: ProductAssetCreate) -> dict:
    require_product(product_id)
    return db.create_asset(product_id, payload.model_dump())


@app.post("/api/products/{product_id}/assets/upload", status_code=201)
def upload_asset(
    product_id: int,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    is_primary: bool = Form(False),
) -> dict:
    """本地上传用于资产管理；生产环境需将 PUBLIC_BASE_URL 指向可访问的对象存储/CDN。"""
    require_product(product_id)
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
        return db.create_asset(product_id, {
            "asset_type": normalized_asset_type,
            "url": f"{PUBLIC_BASE_URL}/assets/{filename}",
            "is_primary": is_primary,
            "metadata": {"filename": file.filename, "content_type": file.content_type},
        })
    except Exception:
        destination.unlink(missing_ok=True)
        raise


@app.post("/api/products/{product_id}/storyboards", status_code=201)
def create_storyboard(product_id: int, payload: StoryboardCreate) -> dict:
    require_product(product_id)
    scenes = [scene.model_dump() for scene in payload.scenes]
    for scene in scenes:
        if scene["generation_strategy"] == "image_to_video":
            verify_asset_belongs_to_product(scene.get("asset_id"), product_id)
        verify_reference_assets(scene.get("reference_assets", []), product_id)
        verify_postprocess_assets(scene.get("postprocess_config", {}), product_id)
    return db.create_storyboard(product_id, payload.title, scenes)


@app.get("/api/storyboards/{storyboard_id}")
def get_storyboard(storyboard_id: int) -> dict:
    return require_storyboard(storyboard_id)


@app.put("/api/storyboard-scenes/{scene_id}")
def update_scene(scene_id: int, payload: StoryboardSceneUpdate) -> dict:
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
    updated = db.update_scene(scene_id, values)
    return updated


@app.post("/api/storyboards/{storyboard_id}/generation-tasks", status_code=201)
def queue_generation_tasks(storyboard_id: int) -> list[dict]:
    storyboard = require_storyboard(storyboard_id)
    for scene in storyboard["scenes"]:
        if scene["generation_strategy"] == "image_to_video":
            if not scene["asset_id"] or not scene["asset_url"]:
                raise HTTPException(status_code=422, detail=f"分镜 {scene['scene_no']} 未关联商品图")
            require_public_asset_url(scene["asset_url"])
    return db.queue_storyboard_tasks(storyboard_id, KELING_IMAGE_TO_VIDEO_MODEL)


@app.post("/api/storyboards/{storyboard_id}/candidate-tasks", status_code=201)
def queue_candidate_tasks(storyboard_id: int, payload: CandidateTaskRequest) -> list[dict]:
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
    return db.queue_storyboard_tasks(
        storyboard_id, KELING_IMAGE_TO_VIDEO_MODEL, payload.candidate_count, payload.force_new,
    )


@app.post("/api/storyboards/{storyboard_id}/dispatch-next")
async def dispatch_next_task(storyboard_id: int) -> dict:
    require_storyboard(storyboard_id)
    if db.active_provider_task_count() >= MAX_PROVIDER_PARALLEL:
        return {"status": "waiting_for_provider_slot", "message": "正在等待可灵并行资源位"}
    task = db.get_next_queued_task(storyboard_id)
    if not task:
        return {"status": "queue_empty", "message": "没有待提交的图生视频任务"}
    require_public_asset_url(task["image_url"])
    try:
        reference_urls = [reference["url"] for reference in task.get("reference_manifest", [])]
        result = await keling.create_image_to_video(task["image_url"], task["prompt"], task["model"], reference_urls)
    except Exception as error:
        # 资源不足或临时网络错误保留 queued 状态，稍后可再次调度。
        db.update_generation_task(task["id"], error=str(error))
        raise HTTPException(status_code=503, detail=f"图生视频暂未提交成功: {error}")
    return db.update_generation_task(
        task["id"], provider_task_id=result["provider_task_id"], status=result["status"], error=None
    )


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
        result = await keling.get_image_to_video_status(task["provider_task_id"])
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"图生视频状态查询失败: {error}")
    return db.update_generation_task(task_id, **result)


@app.post("/api/generation-tasks/{task_id}/compose")
def compose_generation_task(task_id: int) -> dict:
    """将图生视频底片与透明商品图、Logo、字幕/价格/CTA 模板合成为确定性片段。"""
    context = db.get_composition_context(task_id)
    if not context:
        raise HTTPException(status_code=404, detail="生成任务不存在")
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
