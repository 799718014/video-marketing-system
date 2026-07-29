"""商品素材的可用性与规格预检。"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, UnidentifiedImageError

from config import (
    ASSET_PREFLIGHT_MAX_BYTES, ASSET_PREFLIGHT_MIN_SIDE, ASSET_PREFLIGHT_TIMEOUT_SECONDS,
    ASSET_PREFLIGHT_LOGO_MIN_SIDE,
    OUTPUT_DIR, PUBLIC_BASE_URL, UPLOAD_DIR,
)


class PreflightError(RuntimeError):
    """素材无法满足生成或模板合成要求。"""


class AssetPreflightService:
    _FORMAT_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

    async def inspect_url(self, url: str, asset_type: str) -> dict[str, Any]:
        local_file = self._local_public_file(url)
        if local_file:
            try:
                content = local_file.read_bytes()
            except OSError as error:
                raise PreflightError(f"无法读取本地素材: {error}") from error
        else:
            content = await self._download(url)
        return self._inspect(content, asset_type)

    async def _download(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=ASSET_PREFLIGHT_TIMEOUT_SECONDS, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    declared_size = response.headers.get("content-length")
                    if declared_size and int(declared_size) > ASSET_PREFLIGHT_MAX_BYTES:
                        raise PreflightError(f"素材超过 {ASSET_PREFLIGHT_MAX_BYTES // 1024 // 1024}MB 限制")
                    chunks, total = [], 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > ASSET_PREFLIGHT_MAX_BYTES:
                            raise PreflightError(f"素材超过 {ASSET_PREFLIGHT_MAX_BYTES // 1024 // 1024}MB 限制")
                        chunks.append(chunk)
                    return b"".join(chunks)
        except (httpx.HTTPError, ValueError) as error:
            if isinstance(error, PreflightError):
                raise
            raise PreflightError(f"下载素材失败: {error}") from error

    def _inspect(self, content: bytes, asset_type: str) -> dict[str, Any]:
        if not content:
            raise PreflightError("素材为空")
        if len(content) > ASSET_PREFLIGHT_MAX_BYTES:
            raise PreflightError(f"素材超过 {ASSET_PREFLIGHT_MAX_BYTES // 1024 // 1024}MB 限制")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                image_format = (image.format or "").upper()
                if image_format not in self._FORMAT_MIME:
                    raise PreflightError("仅支持 JPEG、PNG 或 WebP 素材")
                width, height = image.size
                has_alpha = "A" in image.getbands() or image.info.get("transparency") is not None
        except (UnidentifiedImageError, OSError) as error:
            raise PreflightError("素材不是可解码的图片") from error

        minimum_side = ASSET_PREFLIGHT_LOGO_MIN_SIDE if asset_type == "logo" else ASSET_PREFLIGHT_MIN_SIDE
        if width < minimum_side or height < minimum_side:
            raise PreflightError(f"素材尺寸至少为 {minimum_side}×{minimum_side}px")
        ratio = max(width / height, height / width)
        if ratio > 4:
            raise PreflightError("素材长宽比不能超过 4:1")
        if asset_type == "transparent" and not has_alpha:
            raise PreflightError("transparent 资产必须包含 Alpha 透明通道")
        return {
            "format": image_format,
            "mime_type": self._FORMAT_MIME[image_format],
            "width": width,
            "height": height,
            "has_alpha": bool(has_alpha),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    @staticmethod
    def _local_public_file(url: str) -> Path | None:
        parsed = urlparse(url)
        if not url.startswith(PUBLIC_BASE_URL + "/"):
            return None
        if parsed.path.startswith("/assets/"):
            return UPLOAD_DIR / Path(parsed.path).name
        if parsed.path.startswith("/outputs/"):
            return OUTPUT_DIR / Path(parsed.path).name
        return None


asset_preflight = AssetPreflightService()
