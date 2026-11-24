"""MiniMax H3 text-to-image generation for storyboard shots."""

import base64
import time
from pathlib import Path
from uuid import uuid4

import httpx

from image_generator import GenerationResult, sanitize_filename

ENDPOINTS = {
    "global": "https://api.minimax.io/v1/images/generations",
    "cn": "https://api.minimax.cn/v1/images/generations",
}
MODELS = ("MiniMax-H3-Image", "MiniMax-H3-Image-Highspeed")


class MiniMaxImageGenerator:
    def __init__(self, api_key, region, model, output_dir):
        if not api_key:
            raise ValueError("Set MINIMAX_API_KEY for storyboard image generation.")
        if region not in ENDPOINTS:
            raise ValueError("MINIMAX_IMAGE_REGION must be global or cn.")
        if model not in MODELS:
            raise ValueError(f"MINIMAX_IMAGE_MODEL must be one of {', '.join(MODELS)}.")
        self.api_key = api_key
        self.endpoint = ENDPOINTS[region]
        self.model = model
        self.output_dir = Path(output_dir)

    def generate_shot(self, shot, project, prompt):
        started = time.monotonic()
        try:
            # Generation is billable and non-idempotent. Submit each shot once.
            response = httpx.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "aspect_ratio": project.aspect_ratio,
                    "response_format": "b64_json",
                    "output_format": "png",
                },
                timeout=600.0,
            )
            if response.is_error:
                try:
                    message = response.json()["error"]["message"]
                except (ValueError, KeyError, TypeError):
                    message = response.reason_phrase
                raise ValueError(f"MiniMax HTTP {response.status_code}: {message}")
            response.raise_for_status()
            item = response.json()["data"][0]
            if "error" in item:
                raise ValueError(item["error"]["message"])
            image = base64.b64decode(item["b64_json"], validate=True)
            if not image:
                raise ValueError("MiniMax returned empty image data.")

            directory = self.output_dir / sanitize_filename(project.name)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"shot_{shot.shot_number:03d}_{uuid4().hex}_h3.png"
            path.write_bytes(image)
        except (
            httpx.HTTPError,
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            return GenerationResult(success=False, error_message=str(exc))
        return GenerationResult(
            success=True,
            image_path=str(path),
            generation_time=time.monotonic() - started,
        )
