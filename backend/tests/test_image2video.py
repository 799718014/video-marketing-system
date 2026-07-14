"""测试可灵图生视频API"""
import pytest
from fastapi.testclient import TestClient
from models.schemas import Image2VideoCreateRequest
from main import app
from unittest.mock import AsyncMock, patch

client = TestClient(app)


def test_image2video_create_request_schema():
    """测试图生视频请求模型"""
    req = Image2VideoCreateRequest(
        image_url="https://example.com/image.jpg",
        prompt="让画面动起来",
        model="kling-v1-5-video-generation-3.0-turbo",
        duration=5,
        aspect_ratio="9:16",
        watermark_enabled=True
    )
    assert req.image_url == "https://example.com/image.jpg"
    assert req.prompt == "让画面动起来"
    assert req.model == "kling-v1-5-video-generation-3.0-turbo"


import asyncio

@patch("services.keling_service.httpx.AsyncClient")
def test_image2video_create(mock_client_class):
    """测试创建图生视频任务"""
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "id": "test_task_123",
            "status": "submitted"
        }
    }
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    from services import keling_service

    req = Image2VideoCreateRequest(
        image_url="https://example.com/image.jpg",
        prompt="让画面动起来"
    )

    task = asyncio.run(keling_service.create_image2video(req))
    assert task.task_id == "test_task_123"
    assert task.status == "submitted"


@patch("services.keling_service.httpx.AsyncClient")
def test_image2video_status_succeeded(mock_client_class):
    """测试图生视频状态 - 成功"""
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "id": "test_task_123",
            "status": "succeeded",
            "works": [
                {
                    "url": "https://example.com/video.mp4",
                    "cover_image_url": "https://example.com/cover.jpg"
                }
            ]
        }
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    from services import keling_service

    task = asyncio.run(keling_service.get_image2video_status("test_task_123"))
    assert task.status == "succeeded"
    assert task.video_url == "https://example.com/video.mp4"
    assert task.cover_url == "https://example.com/cover.jpg"


@patch("services.keling_service.httpx.AsyncClient")
def test_image2video_status_failed(mock_client_class):
    """测试图生视频状态 - 失败"""
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "id": "test_task_123",
            "status": "failed",
            "message": "图片格式不支持"
        }
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    from services import keling_service

    task = asyncio.run(keling_service.get_image2video_status("test_task_123"))
    assert task.status == "failed"
    assert task.error == "图片格式不支持"


@patch("services.keling_service.httpx.AsyncClient")
def test_image2video_with_callback(mock_client_class):
    """测试带回调URL的图生视频"""
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "id": "test_task_456",
            "status": "submitted"
        }
    }
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    from services import keling_service

    req = Image2VideoCreateRequest(
        image_url="https://example.com/image.jpg",
        prompt="让画面动起来",
        callback_url="https://your-app.com/callback",
        external_task_id="my_custom_id"
    )

    asyncio.run(keling_service.create_image2video(req))

    # 验证请求包含回调参数
    call_args = mock_client.post.call_args
    payload = call_args[1]["json"]
    assert payload["callback_url"] == "https://your-app.com/callback"
    assert payload["external_task_id"] == "my_custom_id"


@patch("services.keling_service.httpx.AsyncClient")
def test_image2video_without_watermark(mock_client_class):
    """测试不启用水印的图生视频"""
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "id": "test_task_789",
            "status": "submitted"
        }
    }
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    from services import keling_service

    req = Image2VideoCreateRequest(
        image_url="https://example.com/image.jpg",
        prompt="让画面动起来",
        watermark_enabled=False
    )

    asyncio.run(keling_service.create_image2video(req))

    # 验证水印设置
    call_args = mock_client.post.call_args
    payload = call_args[1]["json"]
    assert payload["watermark_info"]["enabled"] == False