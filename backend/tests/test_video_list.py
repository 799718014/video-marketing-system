"""可灵视频任务列表接口测试。"""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from models.schemas import VideoListItem, VideoListResponse
from services import keling_service


client = TestClient(app)


@patch("services.keling_service.httpx.AsyncClient")
def test_get_text2video_list_normalizes_native_response(mock_client_class):
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "code": 0,
        "data": [{
            "task_id": "text-task-1",
            "task_status": "succeed",
            "created_at": 1722769557708,
            "updated_at": 1722769560000,
            "task_result": {
                "videos": [{
                    "url": "https://example.com/video.mp4",
                    "cover_image_url": "https://example.com/cover.jpg",
                    "duration": "5.2",
                }]
            },
        }],
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = asyncio.run(keling_service.get_video_list("text2video", 2, 12))

    assert result.page_num == 2
    assert result.page_size == 12
    assert result.items[0].task_id == "text-task-1"
    assert result.items[0].task_type == "text2video"
    assert result.items[0].video_url == "https://example.com/video.mp4"
    assert result.items[0].duration == "5.2"
    assert mock_client.get.call_args.kwargs["params"] == {"pageNum": 2, "pageSize": 12}


def test_video_list_endpoint_passes_pagination_and_type():
    result = VideoListResponse(
        items=[VideoListItem(task_id="image-task-1", status="succeed", task_type="image2video")],
        page_num=3,
        page_size=20,
        task_type="image2video",
    )
    with patch("routers.video.keling_service.get_video_list", new=AsyncMock(return_value=result)) as mock_list:
        response = client.get("/api/video/list", params={
            "task_type": "image2video", "page_num": 3, "page_size": 20,
        })

    assert response.status_code == 200
    assert response.json()["items"][0]["task_type"] == "image2video"
    mock_list.assert_awaited_once_with("image2video", 3, 20)


def test_video_list_endpoint_rejects_invalid_pagination():
    response = client.get("/api/video/list", params={"page_num": 0})
    assert response.status_code == 422
