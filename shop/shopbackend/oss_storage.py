"""阿里云 OSS 商品素材上传适配器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from config import (
    KELING_ASSET_BASE_URL,
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_BUCKET,
    OSS_ENDPOINT,
    OSS_KEY_PREFIX,
)


class OssStorageError(RuntimeError):
    """阿里云 OSS 配置或上传失败。"""


class OssStorage:
    @property
    def configured(self) -> bool:
        endpoint = urlparse(OSS_ENDPOINT)
        public_base = urlparse(KELING_ASSET_BASE_URL)
        return bool(
            OSS_ACCESS_KEY_ID
            and OSS_ACCESS_KEY_SECRET
            and OSS_BUCKET
            and endpoint.scheme == "https"
            and endpoint.netloc
            and public_base.scheme == "https"
            and public_base.netloc
        )

    def require_config(self) -> None:
        settings = {
            "OSS_ACCESS_KEY_ID": OSS_ACCESS_KEY_ID,
            "OSS_ACCESS_KEY_SECRET": OSS_ACCESS_KEY_SECRET,
            "OSS_BUCKET": OSS_BUCKET,
            "OSS_ENDPOINT": OSS_ENDPOINT,
            "KELING_ASSET_BASE_URL": KELING_ASSET_BASE_URL,
        }
        missing = [name for name, value in settings.items() if not value]
        if missing:
            raise OssStorageError(f"阿里云 OSS 素材存储未配置: {', '.join(missing)}")
        invalid = []
        for name, value in settings.items():
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                invalid.append(name)
        if invalid:
            raise OssStorageError(
                f"OSS 配置必须只包含英文、数字和 URL 符号；请检查: {', '.join(invalid)}"
            )
        if not self.configured:
            raise OssStorageError(
                "OSS_ENDPOINT 和 KELING_ASSET_BASE_URL 必须是有效的 HTTPS 地址"
            )

    def upload_image(self, local_file: Path, object_key: str) -> dict[str, Any]:
        """同步调用 OSS SDK；路由在工作线程中运行，避免阻塞事件循环。"""
        self.require_config()
        try:
            import oss2
        except ImportError as error:
            raise OssStorageError("未安装 oss2 SDK；请执行 pip install -r requirements.txt") from error

        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)
            result = bucket.put_object_from_file(object_key, str(local_file))
        except Exception as error:
            raise OssStorageError(f"阿里云 OSS 上传失败: {error}") from error

        status_code = getattr(result, "status", None)
        if status_code is not None and status_code // 100 != 2:
            request_id = getattr(result, "request_id", None) or "unknown"
            raise OssStorageError(f"阿里云 OSS 上传失败: HTTP {status_code}, request_id={request_id}")
        return {
            "key": object_key,
            "url": f"{KELING_ASSET_BASE_URL}/{quote(object_key, safe='/')}",
            "etag": getattr(result, "etag", None),
            "request_id": getattr(result, "request_id", None),
        }

    @staticmethod
    def build_object_key(product_id: int, filename: str) -> str:
        prefix = f"{OSS_KEY_PREFIX}/" if OSS_KEY_PREFIX else ""
        return f"{prefix}{product_id}/{filename}"


oss_storage = OssStorage()
