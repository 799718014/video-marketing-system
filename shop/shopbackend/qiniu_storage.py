"""七牛云 Kodo 商品素材上传适配器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from config import KELING_ASSET_BASE_URL, QINIU_ACCESS_KEY, QINIU_BUCKET, QINIU_KEY_PREFIX, QINIU_SECRET_KEY


class QiniuStorageError(RuntimeError):
    """七牛云配置或上传失败。"""


class QiniuStorage:
    @property
    def configured(self) -> bool:
        return bool(QINIU_ACCESS_KEY and QINIU_SECRET_KEY and QINIU_BUCKET and KELING_ASSET_BASE_URL)

    def require_config(self) -> None:
        missing = [
            name for name, value in {
                "QINIU_ACCESS_KEY": QINIU_ACCESS_KEY,
                "QINIU_SECRET_KEY": QINIU_SECRET_KEY,
                "QINIU_BUCKET": QINIU_BUCKET,
                "KELING_ASSET_BASE_URL": KELING_ASSET_BASE_URL,
            }.items() if not value
        ]
        if missing:
            raise QiniuStorageError(f"七牛云素材存储未配置: {', '.join(missing)}")
        parsed = urlparse(KELING_ASSET_BASE_URL)
        if parsed.scheme != "https" or not parsed.netloc:
            raise QiniuStorageError("KELING_ASSET_BASE_URL 必须是七牛云 CDN 的 HTTPS 域名")

    def upload_image(self, local_file: Path, object_key: str) -> dict[str, Any]:
        """同步调用 SDK 上传；由 FastAPI 路由放入线程执行，避免阻塞事件循环。"""
        self.require_config()
        try:
            from qiniu import Auth, put_file_v2
        except ImportError as error:
            raise QiniuStorageError("未安装 qiniu SDK；请执行 pip install -r requirements.txt") from error

        auth = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
        policy = {"insertOnly": 1, "mimeLimit": "image/*"}
        token = auth.upload_token(QINIU_BUCKET, object_key, 3600, policy)
        try:
            result, info = put_file_v2(token, object_key, str(local_file), version="v2")
        except Exception as error:
            raise QiniuStorageError(f"七牛云上传请求失败: {error}") from error

        status_code = getattr(info, "status_code", None)
        if not result or result.get("key") != object_key or (status_code is not None and status_code // 100 != 2):
            detail = getattr(info, "error", None) or str(info)
            raise QiniuStorageError(f"七牛云上传失败: {detail}")
        return {
            "key": object_key,
            "url": f"{KELING_ASSET_BASE_URL}/{quote(object_key, safe='/')}",
            "hash": result.get("hash"),
        }

    @staticmethod
    def build_object_key(product_id: int, filename: str) -> str:
        prefix = f"{QINIU_KEY_PREFIX}/" if QINIU_KEY_PREFIX else ""
        return f"{prefix}{product_id}/{filename}"


qiniu_storage = QiniuStorage()
