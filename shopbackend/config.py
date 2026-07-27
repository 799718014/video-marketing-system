import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("SHOP_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = Path(os.getenv("SHOP_UPLOAD_DIR", DATA_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("SHOP_OUTPUT_DIR", DATA_DIR / "outputs"))
DATABASE_PATH = Path(os.getenv("SHOP_DATABASE_PATH", DATA_DIR / "shop.db"))

# 图生视频必须由可灵服务访问商品图。生产环境应配置为对象存储/CDN 对外域名。
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8010").rstrip("/")
KELING_API_BASE = os.getenv("KELING_API_BASE", "https://api-beijing.klingai.com").rstrip("/")
KELING_IMAGE_TO_VIDEO_MODEL = os.getenv("KELING_IMAGE_TO_VIDEO_MODEL", "kling-v1-5")
MAX_PROVIDER_PARALLEL = max(1, int(os.getenv("MAX_PROVIDER_PARALLEL", "1")))
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
# 中文文字图层需要显式指定支持中文的字体；生产环境请配置为镜像内的字体文件。
FFMPEG_FONT_FILE = os.getenv("FFMPEG_FONT_FILE", r"C:\Windows\Fonts\msyh.ttc")


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
