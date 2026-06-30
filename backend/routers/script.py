from fastapi import APIRouter, HTTPException
from models.schemas import ScriptRequest, ScriptResult
from services import deepseek_service

router = APIRouter()


@router.post("/generate", response_model=ScriptResult)
async def generate_script(req: ScriptRequest):
    try:
        result = await deepseek_service.generate_script(
            product=req.product,
            style=req.style,
            duration=req.duration,
            platform=req.platform,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"脚本生成失败：{str(e)}")
