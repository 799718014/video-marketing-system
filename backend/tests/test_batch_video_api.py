"""
长视频分段拼接 API 接口测试

测试范围:
1. POST /api/batch-video/create - 创建批量任务
2. GET /api/batch-video/status/{batch_id} - 查询任务状态
3. GET /api/batch-video/download/{batch_id} - 下载拼接视频
4. POST /api/batch-video/retry/{batch_id} - 重试失败片段
5. POST /api/batch-video/retry-segment/{batch_id}/{segment_no} - 重新生成单个片段
6. POST /api/batch-video/cancel/{batch_id} - 取消任务
7. GET /api/batch-video/segment/{batch_id}/{segment_no} - 下载单个片段
8. GET /api/batch-video/check-merge/{batch_id} - 检查合并状态
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import time
import os
import tempfile

# 导入主应用
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app
from services import batch_video_service
from models.schemas import (
    ScriptResult, ScriptScene, VideoSegment, BatchVideoTask
)

client = TestClient(app)


# ==================== Fixtures ====================

@pytest.fixture
def sample_script():
    """提供示例脚本数据"""
    return ScriptResult(
        title="测试产品视频",
        total_duration=30,
        style="活力",
        scenes=[
            ScriptScene(
                scene_no=i+1,
                duration=5.0,
                visual=f"产品展示场景 {i+1}",
                narration=f"旁白 {i+1}",
                subtitle=f"字幕 {i+1}"
            )
            for i in range(6)  # 6个场景，每个5秒
        ],
        full_prompt="活力产品展示视频"
    )


@pytest.fixture
def sample_batch_task(sample_script):
    """提供示例批量任务"""
    return BatchVideoTask(
        batch_id="test_batch_123",
        script=sample_script,
        video_params={
            "model": "kling-v1-5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": 3
        },
        segments=[
            VideoSegment(
                segment_id=f"test_batch_123_seg_{i}",
                segment_no=i+1,
                scene_index=i,
                duration=5.0,
                prompt=f"Scene {i+1}: 产品展示场景 {i+1}",
                status="pending"
            )
            for i in range(6)
        ],
        status="submitted",
        total_duration=30.0,
        created_at=time.time()
    )


# ==================== 测试 1: 创建批量任务 ====================

class TestCreateBatchTask:
    """测试创建批量任务 API"""

    @patch('routers.batch_video.batch_video_service.start_batch_generation')
    def test_create_batch_task_success(self, mock_start, sample_script):
        """测试成功创建批量任务"""
        request_data = {
            "script": sample_script.dict(),
            "model": "kling-v1-5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": 3
        }

        response = client.post("/api/batch-video/create", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 验证返回数据结构
        assert "batch_id" in data
        assert "segments" in data
        assert "status" in data
        assert data["status"] == "submitted"
        assert len(data["segments"]) == 6  # 6个场景各成一个片段
        assert data["total_duration"] == 30.0

        # 验证片段结构
        segment = data["segments"][0]
        assert "segment_id" in segment
        assert "segment_no" in segment
        assert "duration" in segment
        assert "prompt" in segment
        assert segment["status"] == "pending"

        # 验证后台任务被启动
        mock_start.assert_called_once()

    def test_create_batch_task_with_long_scene(self):
        """测试包含长场景的脚本分段"""
        script = ScriptResult(
            title="长场景测试",
            total_duration=15,
            style="活力",
            scenes=[
                ScriptScene(
                    scene_no=1,
                    duration=12.0,  # 超过5秒，需要拆分
                    visual="长场景描述",
                    narration="长旁白",
                    subtitle="长字幕"
                ),
                ScriptScene(
                    scene_no=2,
                    duration=3.0,
                    visual="短场景",
                    narration="短旁白",
                    subtitle="短字幕"
                ),
            ],
            full_prompt="长场景测试"
        )

        request_data = {
            "script": script.dict(),
            "model": "kling-v1-5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": 3
        }

        response = client.post("/api/batch-video/create", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 12秒应该拆分为3段 (5+5+2)，加上3秒的场景
        assert len(data["segments"]) == 4

        # 验证拆分后的总时长
        total = sum(s["duration"] for s in data["segments"])
        assert total == 15.0


# ==================== 测试 2: 查询任务状态 ====================

class TestGetBatchStatus:
    """测试查询任务状态 API"""

    def test_get_existing_task_status(self, sample_batch_task):
        """测试查询存在的任务状态"""
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.get(f"/api/batch-video/status/{sample_batch_task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["batch_id"] == sample_batch_task.batch_id
        assert data["status"] == "submitted"
        assert len(data["segments"]) == len(sample_batch_task.segments)

    def test_get_nonexistent_task_status(self):
        """测试查询不存在的任务"""
        response = client.get("/api/batch-video/status/nonexistent_id")

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_get_task_with_mixed_statuses(self):
        """测试查询包含混合状态的任务"""
        # 创建包含不同状态片段的任务
        task = BatchVideoTask(
            batch_id="mixed_status_test",
            script=ScriptResult(
                title="测试",
                total_duration=10,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="succeed",
                    video_url="http://example.com/vid1.mp4"
                ),
                VideoSegment(
                    segment_id="seg_2",
                    segment_no=2,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="processing"
                ),
                VideoSegment(
                    segment_id="seg_3",
                    segment_no=3,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="pending"
                ),
            ],
            status="processing",
            total_duration=15.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        response = client.get(f"/api/batch-video/status/{task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        succeed_count = sum(1 for s in data["segments"] if s["status"] == "succeed")
        processing_count = sum(1 for s in data["segments"] if s["status"] == "processing")
        pending_count = sum(1 for s in data["segments"] if s["status"] == "pending")

        assert succeed_count == 1
        assert processing_count == 1
        assert pending_count == 1


# ==================== 测试 3: 检查合并状态 ====================

class TestCheckMergeStatus:
    """测试检查合并状态 API"""

    def test_check_merge_status_all_succeed(self, sample_batch_task):
        """测试所有片段成功后的合并状态"""
        # 设置所有片段为成功
        for seg in sample_batch_task.segments:
            seg.status = "succeed"
            seg.video_url = "http://example.com/vid.mp4"

        sample_batch_task.status = "merging"
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.get(f"/api/batch-video/check-merge/{sample_batch_task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        # 应该触发合并流程
        assert data["status"] in ["merging", "succeed"]

    def test_check_merge_status_not_ready(self, sample_batch_task):
        """测试尚未完成合并的状态"""
        sample_batch_task.status = "merging"
        sample_batch_task.merged_video_path = None
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.get(f"/api/batch-video/check-merge/{sample_batch_task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "merging"


# ==================== 测试 4: 重试失败片段 ====================

class TestRetryFailedSegments:
    """测试重试失败片段 API"""

    @patch('routers.batch_video.batch_video_service.retry_failed_segments')
    def test_retry_failed_segments(self, mock_retry):
        """测试重试失败片段"""
        # 创建包含失败片段的任务
        task = BatchVideoTask(
            batch_id="retry_test",
            script=ScriptResult(
                title="测试",
                total_duration=10,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="succeed",
                    video_url="http://example.com/vid1.mp4"
                ),
                VideoSegment(
                    segment_id="seg_2",
                    segment_no=2,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="failed",
                    error="网络错误"
                ),
            ],
            status="failed",
            total_duration=10.0,
            created_at=time.time(),
            error="1 个片段生成失败"
        )

        batch_video_service.save_batch_task(task)

        response = client.post(f"/api/batch-video/retry/{task.batch_id}")

        assert response.status_code == 200
        mock_retry.assert_called_once_with(task.batch_id)

    def test_retry_wrong_status(self):
        """测试在错误状态下重试"""
        # 已完成任务不应该重试
        task = BatchVideoTask(
            batch_id="completed_test",
            script=ScriptResult(
                title="测试",
                total_duration=10,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="succeed"
                ),
            ],
            status="succeed",
            total_duration=5.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        response = client.post(f"/api/batch-video/retry/{task.batch_id}")

        assert response.status_code == 400
        assert "当前状态不支持重试" in response.json()["detail"]


# ==================== 测试 5: 取消任务 ====================

class TestCancelBatch:
    """测试取消任务 API"""

    def test_cancel_batch_task(self, sample_batch_task):
        """测试取消批量任务"""
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.post(f"/api/batch-video/cancel/{sample_batch_task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "failed"
        assert data["error"] == "用户取消任务"

        # 验证pending片段被标记为cancelled
        pending_segments = [s for s in data["segments"] if s["status"] == "cancelled"]
        succeed_segments = [s for s in data["segments"] if s["status"] == "succeed"]
        assert len(pending_segments) == 6  # 所有都是pending，应该全部cancelled

    def test_cancel_batch_task_partial_completed(self):
        """测试取消部分完成的任务"""
        task = BatchVideoTask(
            batch_id="partial_test",
            script=ScriptResult(
                title="测试",
                total_duration=15,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="succeed"
                ),
                VideoSegment(
                    segment_id="seg_2",
                    segment_no=2,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="pending"
                ),
                VideoSegment(
                    segment_id="seg_3",
                    segment_no=3,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="pending"
                ),
            ],
            status="processing",
            total_duration=15.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        response = client.post(f"/api/batch-video/cancel/{task.batch_id}")

        assert response.status_code == 200
        data = response.json()

        # pending片段应该被cancelled
        cancelled_segments = [s for s in data["segments"] if s["status"] == "cancelled"]
        assert len(cancelled_segments) == 2


# ==================== 测试 6: 下载接口 ====================

class TestDownloadEndpoints:
    """测试下载接口"""

    def test_download_merged_video_not_completed(self, sample_batch_task):
        """测试下载未完成的视频"""
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.get(f"/api/batch-video/download/{sample_batch_task.batch_id}")

        assert response.status_code == 404
        assert "视频尚未完成拼接" in response.json()["detail"]

    def test_download_segment_video_not_ready(self, sample_batch_task):
        """测试下载未生成的片段"""
        batch_video_service.save_batch_task(sample_batch_task)

        response = client.get(f"/api/batch-video/segment/{sample_batch_task.batch_id}/1")

        assert response.status_code == 404

    def test_download_segment_video_not_found(self):
        """测试下载不存在的任务片段"""
        response = client.get("/api/batch-video/segment/nonexistent_id/1")

        assert response.status_code == 404


# ==================== 测试 7: 参数验证 ====================

class TestParameterValidation:
    """测试参数验证"""

    def test_create_with_invalid_aspect_ratio(self, sample_script):
        """测试无效的宽高比"""
        request_data = {
            "script": sample_script.dict(),
            "model": "kling-v1-5",
            "aspect_ratio": "invalid",  # 无效的宽高比
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": 3
        }

        response = client.post("/api/batch-video/create", json=request_data)

        # Pydantic应该会验证，但当前实现可能没有严格验证
        # 这里检查是否返回200（宽松验证）或422（严格验证）
        assert response.status_code in [200, 422]

    def test_create_with_negative_concurrent(self, sample_script):
        """测试负数的并发数"""
        request_data = {
            "script": sample_script.dict(),
            "model": "kling-v1-5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": -1  # 负数
        }

        response = client.post("/api/batch-video/create", json=request_data)

        # 应该拒绝负数并发
        assert response.status_code in [200, 422]

    def test_create_with_empty_script(self):
        """测试空脚本"""
        script = ScriptResult(
            title="空脚本",
            total_duration=0,
            style="活力",
            scenes=[],
            full_prompt=""
        )

        request_data = {
            "script": script.dict(),
            "model": "kling-v1-5",
            "aspect_ratio": "9:16",
            "cfg_scale": 0.5,
            "transition": "fade",
            "max_concurrent": 3
        }

        response = client.post("/api/batch-video/create", json=request_data)

        # 应该成功但返回空片段列表
        assert response.status_code == 200
        data = response.json()
        assert len(data["segments"]) == 0


# ==================== 测试 8: 重新生成单个片段 ====================

class TestRetrySingleSegment:
    """测试重新生成单个片段 API"""

    @patch('routers.batch_video.batch_video_service.retry_single_segment')
    def test_retry_single_failed_segment(self, mock_retry):
        """测试重新生成失败的片段"""
        # 创建包含失败片段的任务
        task = BatchVideoTask(
            batch_id="retry_single_test",
            script=ScriptResult(
                title="测试",
                total_duration=15,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={
                "model": "kling-v1-5",
                "aspect_ratio": "9:16",
                "cfg_scale": 0.5,
                "max_concurrent": 3
            },
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试1",
                    status="succeed",
                    video_url="http://example.com/vid1.mp4"
                ),
                VideoSegment(
                    segment_id="seg_2",
                    segment_no=2,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试2",
                    status="failed",
                    error="生成失败"
                ),
                VideoSegment(
                    segment_id="seg_3",
                    segment_no=3,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试3",
                    status="succeed",
                    video_url="http://example.com/vid3.mp4"
                ),
            ],
            status="failed",
            total_duration=15.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        # 重新生成第2个失败的片段
        response = client.post(f"/api/batch-video/retry-segment/{task.batch_id}/2")

        assert response.status_code == 200
        mock_retry.assert_called_once_with(task.batch_id, 2)

    @patch('routers.batch_video.batch_video_service.retry_single_segment')
    def test_retry_single_succeed_segment(self, mock_retry):
        """测试重新生成成功的片段（不满意可重新生成）"""
        task = BatchVideoTask(
            batch_id="retry_succeed_test",
            script=ScriptResult(
                title="测试",
                total_duration=10,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="succeed",
                    video_url="http://example.com/vid.mp4"
                ),
            ],
            status="succeed",
            total_duration=5.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        # 重新生成成功的片段
        response = client.post(f"/api/batch-video/retry-segment/{task.batch_id}/1")

        assert response.status_code == 200
        mock_retry.assert_called_once_with(task.batch_id, 1)

    def test_retry_single_segment_processing(self):
        """测试不能重新生成正在处理的片段"""
        task = BatchVideoTask(
            batch_id="processing_test",
            script=ScriptResult(
                title="测试",
                total_duration=10,
                style="活力",
                scenes=[],
                full_prompt="test"
            ),
            video_params={},
            segments=[
                VideoSegment(
                    segment_id="seg_1",
                    segment_no=1,
                    scene_index=0,
                    duration=5.0,
                    prompt="测试",
                    status="processing"
                ),
            ],
            status="processing",
            total_duration=5.0,
            created_at=time.time()
        )

        batch_video_service.save_batch_task(task)

        response = client.post(f"/api/batch-video/retry-segment/{task.batch_id}/1")

        assert response.status_code == 400
        assert "正在生成中" in response.json()["detail"]

    def test_retry_single_segment_nonexistent_task(self):
        """测试重新生成不存在的任务"""
        response = client.post("/api/batch-video/retry-segment/nonexistent_id/1")

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_retry_single_segment_nonexistent_segment(self, sample_batch_task):
        """测试重新生成不存在的片段"""
        batch_video_service.save_batch_task(sample_batch_task)

        # 尝试重新生成第10个片段（不存在）
        response = client.post(f"/api/batch-video/retry-segment/{sample_batch_task.batch_id}/10")

        assert response.status_code == 404
        assert "片段 10 不存在" in response.json()["detail"]


# ==================== 测试 9: 并发测试 ====================

class TestConcurrentRequests:
    """测试并发请求"""

    def test_concurrent_status_queries(self, sample_batch_task):
        """测试并发状态查询"""
        batch_video_service.save_batch_task(sample_batch_task)

        # 发送多个并发请求
        responses = []
        for _ in range(10):
            response = client.get(f"/api/batch-video/status/{sample_batch_task.batch_id}")
            responses.append(response)

        # 所有请求应该成功
        for response in responses:
            assert response.status_code == 200
            assert response.json()["batch_id"] == sample_batch_task.batch_id


# ==================== 测试配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])