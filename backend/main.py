import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from routers import script, video, batch_video

app = FastAPI(title="商品宣传视频生成系统", version="1.0.0")

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(script.router, prefix="/api/script", tags=["视频脚本"])
app.include_router(video.router, prefix="/api/video", tags=["视频生成"])
app.include_router(batch_video.router, prefix="/api/batch-video", tags=["批量视频"])


@app.get("/api/health")
def health():
    return {"status": "ok", "keling_configured": bool(os.getenv("KELING_API_KEY"))}


if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
