import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("SHOP_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = Path(os.getenv("SHOP_UPLOAD_DIR", DATA_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("SHOP_OUTPUT_DIR", DATA_DIR / "outputs"))
DATABASE_PATH = Path(os.getenv("SHOP_DATABASE_PATH", DATA_DIR / "shop.db"))

# 图生视频必须由可灵服务访问商品图。生产环境应配置为对象存储/CDN 对外域名。
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8010").rstrip("/")
# 可灵生成任务使用的商品素材 CDN 域名；与本地 API/成片访问地址 PUBLIC_BASE_URL 分离。
KELING_ASSET_BASE_URL = os.getenv("KELING_ASSET_BASE_URL", "").rstrip("/")
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET = os.getenv("OSS_BUCKET", "")
# 例如：https://oss-cn-shenzhen.aliyuncs.com。它用于服务端上传，不是图片公网地址。
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "").rstrip("/")
OSS_KEY_PREFIX = os.getenv("OSS_KEY_PREFIX", "products").strip("/")
KELING_API_BASE = os.getenv("KELING_API_BASE", "https://api-beijing.klingai.com").rstrip("/")
KELING_IMAGE_TO_VIDEO_MODEL = os.getenv("KELING_IMAGE_TO_VIDEO_MODEL", "kling-v1-5")
KELING_TEXT_TO_VIDEO_MODEL = os.getenv("KELING_TEXT_TO_VIDEO_MODEL", "kling-v1-5")
# 供应商/网关支持多参考图时，配置其请求字段名（如 reference_images）；留空则安全降级为主图 + 参考清单追溯。
KELING_REFERENCE_IMAGES_FIELD = os.getenv("KELING_REFERENCE_IMAGES_FIELD", "")
# 可灵/网关支持幂等请求时使用的请求头；留空可关闭该头（不建议）。
KELING_IDEMPOTENCY_HEADER = os.getenv("KELING_IDEMPOTENCY_HEADER", "Idempotency-Key").strip()
# 分镜参考稿使用与 OpenAI 兼容的文本模型；默认适配 DeepSeek，未配置时不影响手工编辑分镜。
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
MAX_PROVIDER_PARALLEL = max(1, int(os.getenv("MAX_PROVIDER_PARALLEL", "1")))
# 应用内调度器会原子认领队列任务并提交给可灵。多进程部署时依靠 SQLite 认领保证同一任务只会被一个 Worker 持有。
GENERATION_WORKER_ENABLED = os.getenv("GENERATION_WORKER_ENABLED", "true").lower() not in {"0", "false", "no"}
GENERATION_WORKER_POLL_SECONDS = max(1, int(os.getenv("GENERATION_WORKER_POLL_SECONDS", "3")))
GENERATION_REFRESH_SECONDS = max(5, int(os.getenv("GENERATION_REFRESH_SECONDS", "15")))
GENERATION_CLAIM_LEASE_SECONDS = max(45, int(os.getenv("GENERATION_CLAIM_LEASE_SECONDS", "120")))
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
FFPROBE_BINARY = os.getenv("FFPROBE_BINARY", "ffprobe")
# 中文文字图层需要显式指定支持中文的字体；生产环境请配置为镜像内的字体文件。
FFMPEG_FONT_FILE = os.getenv("FFMPEG_FONT_FILE", r"C:\Windows\Fonts\msyh.ttc")
# 商品图在进入分镜和生成队列前必须满足的基础规格。
ASSET_PREFLIGHT_MAX_BYTES = max(1_048_576, int(os.getenv("ASSET_PREFLIGHT_MAX_BYTES", str(20 * 1024 * 1024))))
ASSET_PREFLIGHT_MIN_SIDE = max(64, int(os.getenv("ASSET_PREFLIGHT_MIN_SIDE", "512")))
ASSET_PREFLIGHT_LOGO_MIN_SIDE = max(64, int(os.getenv("ASSET_PREFLIGHT_LOGO_MIN_SIDE", "128")))
ASSET_PREFLIGHT_TIMEOUT_SECONDS = max(5, int(os.getenv("ASSET_PREFLIGHT_TIMEOUT_SECONDS", "30")))
# 可选的视觉质检服务。服务接收视频 URL、参考图和商品事实，返回相似度、Logo 与 OCR 结果。
QUALITY_REVIEW_URL = os.getenv("QUALITY_REVIEW_URL", "").rstrip("/")
QUALITY_REVIEW_API_KEY = os.getenv("QUALITY_REVIEW_API_KEY", "")


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
