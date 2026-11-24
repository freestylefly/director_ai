import base64
import json
from pathlib import Path

import httpx
import pytest

from image_generator import create_generator
from models import Shot, StoryboardProject
from settings import settings


@pytest.fixture
def storyboard(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "image_backend", "minimax")
    monkeypatch.setattr(settings, "minimax_api_key", "test-key")
    project = StoryboardProject(name="Opening scene", aspect_ratio="9:16")
    return project, Shot(shot_number=3), tmp_path


@pytest.mark.parametrize(
    "region, host, model",
    [
        ("global", "api.minimax.io", "MiniMax-H3-Image"),
        ("cn", "api.minimax.cn", "MiniMax-H3-Image-Highspeed"),
    ],
)
def test_generates_storyboard_image(storyboard, monkeypatch, region, host, model):
    project, shot, output_dir = storyboard
    monkeypatch.setattr(settings, "minimax_image_region", region)
    monkeypatch.setattr(settings, "minimax_image_model", model)
    image_bytes = b"image fixture"
    requests = []

    def handle(_transport, request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(image_bytes).decode()}]},
        )

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    result = create_generator("unused", str(output_dir)).generate_shot(
        shot, project, "A blue doorway"
    )

    assert result.success, result.error_message
    assert Path(result.image_path).parent == output_dir / project.name
    assert Path(result.image_path).read_bytes() == image_bytes
    (request,) = requests
    assert request.method == "POST"
    assert str(request.url) == f"https://{host}/v1/images/generations"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.extensions["timeout"]["read"] >= 600
    assert json.loads(request.content) == {
        "model": model,
        "prompt": "A blue doorway",
        "aspect_ratio": "9:16",
        "response_format": "b64_json",
        "output_format": "png",
    }


@pytest.mark.parametrize(
    "status, payload, message",
    [
        (None, None, "timed out"),
        (429, {"error": {"message": "Rate limited (1002)"}}, "Rate limited"),
        (
            200,
            {"data": [{"error": {"code": "1027", "message": "Filtered"}}]},
            "Filtered",
        ),
        (200, {"data": [{"b64_json": "!"}]}, "base64"),
    ],
)
def test_generation_error_does_not_retry(
    storyboard, monkeypatch, status, payload, message
):
    project, shot, output_dir = storyboard
    requests = []

    def handle(_transport, request):
        requests.append(request)
        if status is None:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(status, json=payload)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    result = create_generator(output_dir=str(output_dir)).generate_shot(
        shot, project, "A blue doorway"
    )

    assert not result.success
    assert message in result.error_message
    assert len(requests) == 1
    assert not list(output_dir.iterdir())
