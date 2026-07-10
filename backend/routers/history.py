"""
历史记录 API 路由

提供脚本生成历史记录的管理接口
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from database.db import db

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ScriptHistoryResponse(BaseModel):
    """历史记录响应模型"""
    id: int
    title: str
    product_name: str
    brand: Optional[str] = None
    keywords: List[str]
    style: str
    duration: int
    platform: str
    created_at: str
    is_favorite: bool


class ScriptHistoryDetailResponse(BaseModel):
    """历史记录详情响应模型"""
    id: int
    title: str
    product_name: str
    brand: Optional[str] = None
    keywords: List[str]
    style: str
    duration: int
    platform: str
    script_data: dict
    created_at: str
    is_favorite: bool


class UpdateFavoriteRequest(BaseModel):
    """更新收藏状态请求"""
    is_favorite: bool


class HistoryStatsResponse(BaseModel):
    """历史记录统计响应"""
    total: int
    favorite_count: int
    style_stats: dict
    platform_stats: dict


# ==================== API 接口 ====================

@router.get("/list", response_model=List[ScriptHistoryResponse])
async def get_history_list(
    limit: int = 20,
    offset: int = 0,
    favorite_only: bool = False
):
    """
    获取脚本历史记录列表

    Args:
        limit: 返回数量，默认20
        offset: 偏移量，用于分页
        favorite_only: 是否只返回收藏的记录

    Returns:
        历史记录列表
    """
    try:
        records = db.get_script_history(
            limit=limit,
            offset=offset,
            favorite_only=favorite_only
        )
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败：{str(e)}")


@router.get("/detail/{history_id}", response_model=ScriptHistoryDetailResponse)
async def get_history_detail(history_id: int):
    """
    获取历史记录详情

    Args:
        history_id: 历史记录 ID

    Returns:
        历史记录详情，包含完整的脚本数据
    """
    detail = db.get_script_detail(history_id)
    if not detail:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return detail


@router.get("/search")
async def search_history(keyword: str, limit: int = 20):
    """
    搜索历史记录

    Args:
        keyword: 搜索关键词
        limit: 返回数量，默认20

    Returns:
        匹配的历史记录列表
    """
    try:
        results = db.search_history(keyword=keyword, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.put("/favorite/{history_id}")
async def update_favorite(history_id: int, req: UpdateFavoriteRequest):
    """
    更新历史记录的收藏状态

    Args:
        history_id: 历史记录 ID
        req: 包含 is_favorite 的请求体

    Returns:
        操作结果
    """
    try:
        success = db.update_favorite(history_id, req.is_favorite)
        if not success:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        return {"success": True, "is_favorite": req.is_favorite}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新收藏状态失败：{str(e)}")


@router.delete("/{history_id}")
async def delete_history(history_id: int):
    """
    删除历史记录

    Args:
        history_id: 历史记录 ID

    Returns:
        操作结果
    """
    try:
        success = db.delete_script_history(history_id)
        if not success:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


@router.get("/stats", response_model=HistoryStatsResponse)
async def get_history_stats():
    """
    获取历史记录统计信息

    Returns:
        统计信息，包括总数、收藏数、风格分布、平台分布
    """
    try:
        stats = db.get_history_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败：{str(e)}")


@router.post("/save")
async def save_history(
    title: str,
    script_data: dict,
    product_info: dict,
    style: str,
    duration: int,
    platform: str,
    is_favorite: bool = False
):
    """
    保存脚本到历史记录

    通常在生成脚本成功后自动调用

    Args:
        title: 标题
        script_data: 脚本数据
        product_info: 产品信息
        style: 风格
        duration: 时长
        platform: 平台
        is_favorite: 是否收藏

    Returns:
        保存后的历史记录 ID
    """
    try:
        history_id = db.save_script_history(
            title=title,
            script_data=script_data,
            product_info=product_info,
            style=style,
            duration=duration,
            platform=platform,
            is_favorite=is_favorite
        )
        return {"id": history_id, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存历史记录失败：{str(e)}")