import asyncio
import os
import tempfile
import logging
from typing import List
import httpx
import aiofiles
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger(__name__)


class VideoMerger:
    """
    使用 moviepy 进行视频拼接
    """

    @staticmethod
    async def download_segment(url: str, dest_path: str) -> None:
        """
        下载单个视频片段
        """
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise RuntimeError(f"下载失败: HTTP {resp.status_code}")
                    async with aiofiles.open(dest_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            await f.write(chunk)
            logger.info(f"下载片段成功: {dest_path}")
        except Exception as e:
            logger.error(f"下载片段失败 {url}: {e}")
            raise

    @staticmethod
    def merge_videos_sync(
        segment_paths: List[str],
        output_path: str,
        transition: str = "fade",
        transition_duration: float = 0.5
    ) -> str:
        """
        合并多个视频片段（同步版本，在事件循环中运行）

        Args:
            segment_paths: 片段文件路径列表
            output_path: 输出文件路径
            transition: 转场效果（fade/none）
            transition_duration: 转场时长

        Returns:
            合并后的视频文件路径
        """
        logger.info(f"开始合并视频，共 {len(segment_paths)} 个片段")

        try:
            # 1. 加载视频片段
            clips = []
            for path in segment_paths:
                try:
                    clip = VideoFileClip(path)
                    clips.append(clip)
                    logger.info(f"加载片段成功: {path} (时长: {clip.duration}s)")
                except Exception as e:
                    logger.error(f"加载片段失败 {path}: {e}")
                    raise

            # 2. 添加转场效果
            if transition == "fade" and len(clips) > 1:
                processed_clips = []
                for i, clip in enumerate(clips):
                    if i == 0:
                        # 第一个片段只淡出
                        processed = clip.crossfadeout(transition_duration)
                    elif i == len(clips) - 1:
                        # 最后一个片段只淡入
                        processed = clip.crossfadein(transition_duration)
                    else:
                        # 中间片段淡入淡出
                        processed = clip.crossfadein(transition_duration).crossfadeout(transition_duration)
                    processed_clips.append(processed)
                final_clip = concatenate_videoclips(processed_clips, method="compose")
                logger.info(f"添加转场效果: fade ({transition_duration}s)")
            else:
                final_clip = concatenate_videoclips(clips)
                logger.info("直接拼接，无转场效果")

            # 3. 计算总时长
            total_duration = final_clip.duration
            logger.info(f"合并后总时长: {total_duration}s")

            # 4. 输出视频
            logger.info(f"开始输出视频到: {output_path}")
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                logger=None,  # 禁用 moviepy 日志
            )
            logger.info(f"视频输出完成: {output_path}")

            # 5. 清理内存
            final_clip.close()
            for clip in clips:
                clip.close()

            return output_path

        except Exception as e:
            logger.error(f"视频合并失败: {e}")
            raise

    @staticmethod
    async def merge_videos(
        segment_urls: List[str],
        output_path: str,
        transition: str = "fade",
        transition_duration: float = 0.5
    ) -> str:
        """
        合并多个视频片段（异步版本）

        Args:
            segment_urls: 片段 URL 列表
            output_path: 输出文件路径
            transition: 转场效果（fade/none）
            transition_duration: 转场时长

        Returns:
            合并后的视频文件路径
        """
        # 1. 创建临时目录
        temp_dir = tempfile.mkdtemp()
        segment_paths = []

        try:
            # 2. 下载所有片段
            download_tasks = [
                VideoMerger.download_segment(
                    url,
                    os.path.join(temp_dir, f"segment_{i}.mp4")
                )
                for i, url in enumerate(segment_urls)
            ]
            await asyncio.gather(*download_tasks)

            # 3. 收集下载路径
            segment_paths = [
                os.path.join(temp_dir, f"segment_{i}.mp4")
                for i in range(len(segment_urls))
            ]

            # 4. 在事件循环中运行同步的合并操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                VideoMerger.merge_videos_sync,
                segment_paths,
                output_path,
                transition,
                transition_duration
            )

            return result

        finally:
            # 5. 清理临时文件
            for path in segment_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"清理临时文件: {path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {path}: {e}")

            try:
                os.rmdir(temp_dir)
                logger.info(f"清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败 {temp_dir}: {e}")

    @staticmethod
    def ensure_output_dir(path: str) -> None:
        """确保输出目录存在"""
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建输出目录: {dir_path}")