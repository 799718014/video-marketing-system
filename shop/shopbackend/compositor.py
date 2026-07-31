"""可重复执行的确定性后期合成：视频底片 + 商品透明图 + 模板文字。"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from config import (
    DATA_DIR, FFMPEG_BINARY, FFMPEG_FONT_FILE, FFPROBE_BINARY, OUTPUT_DIR, PUBLIC_BASE_URL, UPLOAD_DIR,
)


class CompositionError(RuntimeError):
    """视频、素材或 FFmpeg 条件不满足时的可读错误。"""


class DeterministicCompositor:
    """只以真实商品资产和模板字段做合成，不让模型承担品牌和文案的生成。"""

    CANVAS_WIDTH = 1080
    CANVAS_HEIGHT = 1920
    CANVAS_FPS = 30

    # 合成管线版本：修改模板逻辑时应递增，使旧缓存自然失效。
    _CACHE_VERSION = "v1"

    @property
    def _cache_dir(self) -> Path:
        path = OUTPUT_DIR / "_cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _compute_cache_key(self, context: dict[str, Any]) -> str:
        """基于视频底片、素材 SHA-256 和文字层的内容寻址缓存键。"""
        layers = sorted(context["postprocess_layers"])
        config = context["postprocess_config"]
        target_duration = context["target_duration"]

        transparent_asset = self._select_asset(context, config.get("transparent_asset_id"), "transparent")
        logo_asset = self._select_asset(context, config.get("logo_asset_id"), "logo")

        transparent_sha = transparent_asset["metadata"].get("preflight", {}).get("result", {}).get("sha256", "") if transparent_asset else ""
        logo_sha = logo_asset["metadata"].get("preflight", {}).get("result", {}).get("sha256", "") if logo_asset else ""

        text_layers = self._text_layers(context, set(layers))

        payload = {
            "version": self._CACHE_VERSION,
            "video_url": context["video_url"],
            "target_duration": target_duration,
            "layers": layers,
            "config": config,
            "transparent_sha256": transparent_sha,
            "logo_sha256": logo_sha,
            "text_layers": text_layers,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_hit(self, cache_key: str, task_output: Path, target_duration: float) -> str | None:
        """缓存命中时复制到任务输出路径并验证；损坏或规格不符则删除缓存返回 None。"""
        cached = self._cache_dir / f"{cache_key}.mp4"
        if not cached.is_file():
            return None
        try:
            shutil.copy2(cached, task_output)
            self._validate_output_video(task_output, target_duration)
            return f"{PUBLIC_BASE_URL}/outputs/{task_output.name}"
        except CompositionError:
            task_output.unlink(missing_ok=True)
            cached.unlink(missing_ok=True)
            return None

    def compose_scene(self, context: dict[str, Any]) -> str:
        if not context.get("video_url"):
            raise CompositionError("图生视频尚未生成完成，不能进行后期合成")
        self._require_ffmpeg()
        layers = set(context["postprocess_layers"])
        config = context["postprocess_config"]
        target_duration = context["target_duration"]
        output_file = OUTPUT_DIR / f"task_{context['id']}_composed.mp4"

        # 内容寻址缓存：相同输入 → 跳过 FFmpeg 重编码。
        cache_key = self._compute_cache_key(context)
        cached_result = self._cache_hit(cache_key, output_file, target_duration)
        if cached_result:
            return cached_result

        with tempfile.TemporaryDirectory(prefix=f"compose_task_{context['id']}_", dir=DATA_DIR) as temporary:
            workdir = Path(temporary)
            video_file = self._materialize(context["video_url"], workdir, "source.mp4")
            self._validate_source_video(video_file, target_duration)
            transparent_asset = self._select_asset(context, config.get("transparent_asset_id"), "transparent")
            logo_asset = self._select_asset(context, config.get("logo_asset_id"), "logo")

            input_files = [video_file]
            filter_steps = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x111111,setsar=1[v0]"
            ]
            current = "v0"

            if "transparent_product" in layers:
                if not transparent_asset:
                    raise CompositionError("模板要求透明底商品图，但商品资产库中未配置 transparent 资产")
                product_file = self._materialize(transparent_asset["url"], workdir, "product.png")
                input_files.append(product_file)
                next_label = f"v{len(input_files)}"
                filter_steps.extend([
                    f"[{len(input_files) - 1}:v]scale=320:-1[product]",
                    f"[{current}][product]overlay=x=W-w-48:y=H-h-280:format=auto[{next_label}]",
                ])
                current = next_label

            if "brand_logo" in layers:
                if not logo_asset:
                    raise CompositionError("模板要求 Logo，但商品资产库中未配置 logo 资产")
                logo_file = self._materialize(logo_asset["url"], workdir, "logo.png")
                input_files.append(logo_file)
                next_label = f"v{len(input_files)}"
                filter_steps.extend([
                    f"[{len(input_files) - 1}:v]scale=160:-1[logo]",
                    f"[{current}][logo]overlay=x=48:y=48:format=auto[{next_label}]",
                ])
                current = next_label

            for index, (layer, text, style) in enumerate(self._text_layers(context, layers), start=1):
                text_file = workdir / f"{index}_{layer}.txt"
                text_file.write_text(text, encoding="utf-8")
                next_label = f"text{index}"
                filter_steps.append(
                    f"[{current}]drawtext={self._drawtext_options(text_file, style)}[{next_label}]"
                )
                current = next_label

            command = [FFMPEG_BINARY, "-y", "-i", str(video_file)]
            for image in input_files[1:]:
                command.extend(["-loop", "1", "-i", str(image)])
            command.extend([
                "-filter_complex", ";".join(filter_steps),
                "-map", f"[{current}]", "-map", "0:a?",
                "-c:v", "libx264", "-r", str(self.CANVAS_FPS), "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-t", str(target_duration), "-shortest", "-movflags", "+faststart", str(output_file),
            ])
            self._run_ffmpeg(command)
            self._validate_output_video(output_file, target_duration)

            # 编码成功后存入内容寻址缓存，供后续相同输入复用。
            shutil.copy2(output_file, self._cache_dir / f"{cache_key}.mp4")
            return f"{PUBLIC_BASE_URL}/outputs/{output_file.name}"

    def merge_storyboard(self, storyboard_id: int, tasks: list[dict[str, Any]]) -> str:
        """以统一编码后的分镜成片顺序拼接，不重新生成任何品牌或字幕内容。"""
        if not tasks:
            raise CompositionError("没有可合并的视频片段")
        incomplete = [str(task["scene_no"]) for task in tasks if not task.get("composed_video_url")]
        if incomplete:
            raise CompositionError(f"分镜 {', '.join(incomplete)} 尚未完成确定性合成")
        self._require_ffmpeg()

        with tempfile.TemporaryDirectory(prefix=f"merge_storyboard_{storyboard_id}_", dir=DATA_DIR) as temporary:
            workdir = Path(temporary)
            files = [
                self._materialize(task["composed_video_url"], workdir, f"scene_{task['scene_no']}.mp4")
                for task in tasks
            ]
            manifest = workdir / "concat.txt"
            manifest.write_text(
                "".join(f"file '{self._concat_path(file)}'\n" for file in files), encoding="utf-8"
            )
            output_file = OUTPUT_DIR / f"storyboard_{storyboard_id}_final.mp4"
            self._run_ffmpeg([
                FFMPEG_BINARY, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                "-c", "copy", "-movflags", "+faststart", str(output_file),
            ])
            self._validate_output_video(output_file, sum(float(task["target_duration"]) for task in tasks))
            return f"{PUBLIC_BASE_URL}/outputs/{output_file.name}"

    def _text_layers(self, context: dict[str, Any], layers: set[str]) -> list[tuple[str, str, dict[str, Any]]]:
        if not layers.intersection({"subtitle", "price_tag", "cta"}):
            return []
        if not FFMPEG_FONT_FILE or not Path(FFMPEG_FONT_FILE).is_file():
            raise CompositionError("未找到中文字体；请配置 FFMPEG_FONT_FILE 后再合成文字图层")
        config = context["postprocess_config"]
        result: list[tuple[str, str, dict[str, Any]]] = []
        if "subtitle" in layers:
            subtitle = config.get("subtitle") or (context["selling_points"] or [context["product_name"]])[0]
            result.append(("subtitle", subtitle, {"font_size": 46, "x": "48", "y": "1320", "box_color": "black@0.55"}))
        if "price_tag" in layers:
            price = config.get("price_text") or context.get("product_price")
            if not price:
                raise CompositionError("模板要求价格标签，但商品事实中没有 price 或 price_text")
            result.append(("price", str(price), {"font_size": 62, "x": "48", "y": "1430", "box_color": "0xE53935@0.92"}))
        if "cta" in layers:
            result.append(("cta", config.get("cta") or "立即购买", {"font_size": 48, "x": "(w-text_w)/2", "y": "1760", "box_color": "0xFF5A36@0.95"}))
        return result

    def _drawtext_options(self, text_file: Path, style: dict[str, Any]) -> str:
        return (
            f"fontfile='{self._filter_path(Path(FFMPEG_FONT_FILE))}':"
            f"textfile='{self._filter_path(text_file)}':"
            f"fontcolor=white:fontsize={style['font_size']}:x={style['x']}:y={style['y']}:"
            f"box=1:boxcolor={style['box_color']}:boxborderw=18"
        )

    def _select_asset(self, context: dict[str, Any], requested_id: Any, asset_type: str) -> dict[str, Any] | None:
        assets = context["assets"]
        if requested_id is not None:
            return next(
                (asset for asset in assets if asset["id"] == requested_id and asset["asset_type"] == asset_type),
                None,
            )
        return next((asset for asset in assets if asset["asset_type"] == asset_type), None)

    def _materialize(self, url: str, workdir: Path, filename: str) -> Path:
        local_file = self._local_public_file(url)
        if local_file:
            if not local_file.is_file():
                raise CompositionError(f"本地素材不存在: {url}")
            return local_file
        target = workdir / filename
        try:
            with httpx.stream("GET", url, timeout=90, follow_redirects=True) as response:
                response.raise_for_status()
                with target.open("wb") as stream:
                    for chunk in response.iter_bytes():
                        stream.write(chunk)
        except httpx.HTTPError as error:
            raise CompositionError(f"下载素材失败: {url} ({error})") from error
        return target

    @staticmethod
    def _filter_path(path: Path) -> str:
        return path.as_posix().replace(":", r"\:").replace("'", r"\'")

    @staticmethod
    def _concat_path(path: Path) -> str:
        return path.as_posix().replace("'", r"'\\''")

    @staticmethod
    def _run_ffmpeg(command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise CompositionError(f"FFmpeg 合成失败: {result.stderr[-1200:]}")

    @staticmethod
    def _probe_video(file: Path) -> dict[str, Any]:
        if not shutil.which(FFPROBE_BINARY) and not Path(FFPROBE_BINARY).is_file():
            raise CompositionError("未找到 FFprobe；请安装 ffprobe 或配置 FFPROBE_BINARY 后再合成")
        result = subprocess.run(
            [
                FFPROBE_BINARY, "-v", "error", "-show_entries",
                "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate:format=duration",
                "-of", "json", str(file),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            raise CompositionError(f"无法读取视频规格: {result.stderr[-800:]}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise CompositionError("FFprobe 未返回有效的视频规格") from error

    def _validate_source_video(self, file: Path, target_duration: float) -> None:
        probe = self._probe_video(file)
        video = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"), None)
        if not video:
            raise CompositionError("图生视频底片不包含可用视频流")
        try:
            duration = float(probe.get("format", {}).get("duration", 0))
        except (TypeError, ValueError) as error:
            raise CompositionError("图生视频底片缺少有效时长") from error
        if duration + 0.1 < float(target_duration):
            raise CompositionError(f"图生视频底片时长 {duration:.2f}s 小于分镜目标 {target_duration}s")

    def _validate_output_video(self, file: Path, target_duration: float) -> None:
        """确保每个可发布片段及最终成片统一为 1080×1920、H.264、yuv420p 和目标时长。"""
        probe = self._probe_video(file)
        video = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"), None)
        if not video:
            raise CompositionError("合成结果不包含视频流")
        if (video.get("width"), video.get("height")) != (self.CANVAS_WIDTH, self.CANVAS_HEIGHT):
            raise CompositionError("合成结果不是 1080×1920 竖版视频")
        if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
            raise CompositionError("合成结果必须为 H.264 / yuv420p，不能进入最终拼接")
        try:
            numerator, denominator = str(video.get("avg_frame_rate", "0/1")).split("/", maxsplit=1)
            frame_rate = float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise CompositionError("合成结果缺少有效帧率") from error
        if abs(frame_rate - self.CANVAS_FPS) > 0.05:
            raise CompositionError(f"合成结果帧率必须为 {self.CANVAS_FPS}fps")
        try:
            duration = float(probe.get("format", {}).get("duration", 0))
        except (TypeError, ValueError) as error:
            raise CompositionError("合成结果缺少有效时长") from error
        if abs(duration - float(target_duration)) > 0.35:
            raise CompositionError(f"合成结果时长 {duration:.2f}s 与目标 {target_duration:.2f}s 不一致")

    @staticmethod
    def _require_ffmpeg() -> None:
        if not shutil.which(FFMPEG_BINARY) and not Path(FFMPEG_BINARY).is_file():
            raise CompositionError("未找到 FFmpeg；请安装 ffmpeg 或配置 FFMPEG_BINARY")

    @staticmethod
    def _local_public_file(url: str) -> Path | None:
        parsed = urlparse(url)
        if not url.startswith(PUBLIC_BASE_URL + "/"):
            return None
        if parsed.path.startswith("/assets/"):
            candidate = UPLOAD_DIR / Path(parsed.path).name
            return candidate if candidate.is_file() else None
        if parsed.path.startswith("/outputs/"):
            candidate = OUTPUT_DIR / Path(parsed.path).name
            return candidate if candidate.is_file() else None
        return None


compositor = DeterministicCompositor()
