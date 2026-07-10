"""
模板库 API 路由

提供脚本模板的管理接口
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from database.db import db

router = APIRouter()


# ==================== 请求/响应模型 ====================

class TemplateResponse(BaseModel):
    """模板响应模型"""
    id: int
    name: str
    category: str
    description: str
    product_name: str
    keywords: List[str]
    style: str
    duration: int
    platform: str
    is_system: bool
    created_by: Optional[str] = None
    created_at: str
    usage_count: int


class TemplateDetailResponse(BaseModel):
    """模板详情响应模型"""
    id: int
    name: str
    category: str
    description: str
    product_name: str
    keywords: List[str]
    style: str
    duration: int
    platform: str
    script_data: dict
    is_system: bool
    created_by: Optional[str] = None
    created_at: str
    usage_count: int


class CreateTemplateRequest(BaseModel):
    """创建模板请求"""
    name: str
    category: str
    description: str
    product_name: str
    keywords: List[str]
    style: str
    duration: int
    platform: str
    script_data: dict


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    script_data: Optional[dict] = None


class UseTemplateRequest(BaseModel):
    """使用模板请求"""
    template_id: int


# ==================== API 接口 ====================

@router.get("/list", response_model=List[TemplateResponse])
async def get_template_list(
    category: Optional[str] = None,
    is_system: Optional[bool] = None,
    limit: int = 50
):
    """
    获取模板列表

    Args:
        category: 分类筛选，可选
        is_system: 是否只返回系统模板，可选
        limit: 返回数量，默认50

    Returns:
        模板列表
    """
    try:
        templates = db.get_templates(
            category=category,
            is_system=is_system,
            limit=limit
        )
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败：{str(e)}")


@router.get("/categories")
async def get_template_categories():
    """
    获取所有模板分类

    Returns:
        分类列表
    """
    try:
        categories = db.get_template_categories()
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败：{str(e)}")


@router.get("/detail/{template_id}", response_model=TemplateDetailResponse)
async def get_template_detail(template_id: int):
    """
    获取模板详情

    Args:
        template_id: 模板 ID

    Returns:
        模板详情，包含完整的脚本数据
    """
    try:
        detail = db.get_template_detail(template_id)
        if not detail:
            raise HTTPException(status_code=404, detail="模板不存在")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板详情失败：{str(e)}")


@router.get("/search")
async def search_templates(
    keyword: str,
    category: Optional[str] = None,
    limit: int = 20
):
    """
    搜索模板

    Args:
        keyword: 搜索关键词
        category: 分类筛选，可选
        limit: 返回数量，默认20

    Returns:
        匹配的模板列表
    """
    try:
        results = db.search_templates(
            keyword=keyword,
            category=category,
            limit=limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.post("/create")
async def create_template(
    req: CreateTemplateRequest,
    created_by: str = "user"
):
    """
    创建新模板

    Args:
        req: 创建模板请求
        created_by: 创建者，默认为 "user"

    Returns:
        创建的模板 ID
    """
    try:
        # 准备产品信息
        product_info = {
            'name': req.product_name,
            'keywords': req.keywords,
            'style': req.style,
            'duration': req.duration,
            'platform': req.platform
        }

        template_id = db.save_template(
            name=req.name,
            category=req.category,
            description=req.description,
            product_info=product_info,
            script_data=req.script_data,
            is_system=False,
            created_by=created_by
        )

        return {"id": template_id, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建模板失败：{str(e)}")


@router.put("/update/{template_id}")
async def update_template(template_id: int, req: UpdateTemplateRequest):
    """
    更新模板（仅用户模板可更新）

    Args:
        template_id: 模板 ID
        req: 更新内容

    Returns:
        操作结果
    """
    try:
        success = db.update_template(
            template_id=template_id,
            name=req.name,
            description=req.description,
            script_data=req.script_data
        )

        if not success:
            raise HTTPException(status_code=404, detail="模板不存在或更新失败")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新模板失败：{str(e)}")


@router.delete("/{template_id}")
async def delete_template(template_id: int):
    """
    删除模板（仅用户模板可删除，系统模板不可删除）

    Args:
        template_id: 模板 ID

    Returns:
        操作结果
    """
    try:
        success = db.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="模板不存在或系统模板不可删除")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板失败：{str(e)}")


@router.post("/use/{template_id}")
async def use_template(template_id: int):
    """
    使用模板（增加使用计数）

    Args:
        template_id: 模板 ID

    Returns:
        操作结果
    """
    try:
        success = db.use_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="模板不存在")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"使用模板失败：{str(e)}")


@router.post("/save-to-history/{template_id}")
async def save_template_to_history(
    template_id: int,
    title: str,
    is_favorite: bool = False
):
    """
    将模板保存到历史记录

    Args:
        template_id: 模板 ID
        title: 历史记录标题
        is_favorite: 是否收藏

    Returns:
        保存后的历史记录 ID
    """
    try:
        # 获取模板详情
        template = db.get_template_detail(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        # 增加使用计数
        db.use_template(template_id)

        # 保存到历史记录
        product_info = {
            'name': template['product_name'],
            'keywords': template['keywords'],
            'style': template['style'],
            'duration': template['duration'],
            'platform': template['platform']
        }

        history_id = db.save_script_history(
            title=title,
            script_data=template['script_data'],
            product_info=product_info,
            style=template['style'],
            duration=template['duration'],
            platform=template['platform'],
            is_favorite=is_favorite
        )

        return {"id": history_id, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存到历史记录失败：{str(e)}")