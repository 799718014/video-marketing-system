from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import ScriptRequest, ScriptResult
from services import deepseek_service
from database.db import db

router = APIRouter()


@router.post("/generate", response_model=ScriptResult)
async def generate_script(req: ScriptRequest, background_tasks: BackgroundTasks, save_to_history: bool = True):
    """
    生成视频脚本

    Args:
        req: 脚本生成请求
        save_to_history: 是否保存到历史记录，默认为 True
    """
    try:
        result = await deepseek_service.generate_script(
            product=req.product,
            style=req.style,
            duration=req.duration,
            platform=req.platform,
        )

        # 保存到历史记录
        if save_to_history:
            def save_history():
                try:
                    db.save_script_history(
                        title=result.title,
                        script_data=result.dict(),
                        product_info=req.product.dict(),
                        style=req.style,
                        duration=req.duration,
                        platform=req.platform,
                        is_favorite=False
                    )
                except Exception as e:
                    import logging
                    logging.error(f"保存历史记录失败: {e}")

            background_tasks.add_task(save_history)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"脚本生成失败：{str(e)}")