"""
苍何 API 客户端
支持图像生成 (Fal.ai) 和视频生成 (VEO/即梦)
"""

import os
import time
import httpx
import asyncio
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


# ============================================
# 常量定义
# ============================================

class CangheAPIConfig:
    """API 配置"""
    BASE_URL = "https://api.canghe.ai"

    # 端点
    ENDPOINTS = {
        # 聊天
        "chat": "/v1/chat/completions",
        # 图像
        "image_generate": "/fal-ai/nano-banana",
        "image_edit": "/fal-ai/nano-banana/edit",
        "image_result": "/fal-ai/{model_name}/requests/{request_id}",
        # 视频 (统一接口)
        "video_create": "/v1/video/create",
        "video_query": "/v1/video/query",
        # 即梦原生接口
        "jimeng_submit": "/jimeng/submit/videos",
        "jimeng_fetch": "/jimeng/fetch/{task_id}",
    }

    # 轮询配置
    IMAGE_POLL_INTERVAL = 2.0  # 秒
    IMAGE_MAX_ATTEMPTS = 60
    VIDEO_POLL_INTERVAL = 5.0  # 秒
    VIDEO_MAX_ATTEMPTS = 120


class FalAIStatus(str, Enum):
    """Fal.ai 任务状态"""
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VeoStatus(str, Enum):
    """VEO 视频任务状态"""
    PENDING = "pending"
    IMAGE_DOWNLOADING = "image_downloading"
    VIDEO_GENERATING = "video_generating"
    VIDEO_GENERATION_COMPLETED = "video_generation_completed"
    VIDEO_GENERATION_FAILED = "video_generation_failed"
    VIDEO_UPSAMPLING = "video_upsampling"
    VIDEO_UPSAMPLING_COMPLETED = "video_upsampling_completed"
    VIDEO_UPSAMPLING_FAILED = "video_upsampling_failed"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class JimengStatus(str, Enum):
    """即梦任务状态"""
    NOT_START = "NOT_START"
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"


class VideoModel(str, Enum):
    """视频模型"""
    # VEO2 系列
    VEO2 = "veo2"
    VEO2_FAST = "veo2-fast"
    VEO2_FAST_FRAMES = "veo2-fast-frames"
    VEO2_FAST_COMPONENTS = "veo2-fast-components"
    VEO2_PRO = "veo2-pro"
    VEO2_PRO_COMPONENTS = "veo2-pro-components"
    # VEO3 系列
    VEO3 = "veo3"
    VEO3_FAST = "veo3-fast"
    VEO3_FAST_FRAMES = "veo3-fast-frames"
    VEO3_FRAMES = "veo3-frames"
    VEO3_PRO = "veo3-pro"
    VEO3_PRO_FRAMES = "veo3-pro-frames"
    # VEO3.1 系列
    VEO3_1 = "veo3.1"
    VEO3_1_FAST = "veo3.1-fast"
    VEO3_1_PRO = "veo3.1-pro"
    VEO3_1_COMPONENTS = "veo3.1-components"
    # 即梦
    JIMENG_VIDEO_3 = "jimeng-video-3.0"


# ============================================
# 数据类
# ============================================

@dataclass
class ImageResult:
    """图像生成结果"""
    url: str
    width: int
    height: int
    content_type: str
    seed: Optional[int] = None


@dataclass
class VideoResult:
    """视频生成结果"""
    video_url: str
    status: str
    enhanced_prompt: Optional[str] = None


@dataclass
class TaskStatus:
    """任务状态"""
    task_id: str
    status: str
    is_completed: bool
    is_failed: bool
    result: Optional[Any] = None
    error: Optional[str] = None


# ============================================
# API 客户端
# ============================================

class CangheAPIClient:
    """苍何 API 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CANGHE_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set CANGHE_API_KEY environment variable or pass api_key parameter.")

        self.base_url = CangheAPIConfig.BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _get_url(self, endpoint: str, **kwargs) -> str:
        """构建完整 URL"""
        path = CangheAPIConfig.ENDPOINTS[endpoint].format(**kwargs)
        return f"{self.base_url}{path}"

    # ============================================
    # 图像生成
    # ============================================

    async def generate_image(
        self,
        prompt: str,
        num_images: int = 1,
        timeout: float = 120.0
    ) -> List[ImageResult]:
        """
        文生图 (nano-banana)

        Args:
            prompt: 生成图片的提示词
            num_images: 生成数量 1-4
            timeout: 超时时间(秒)

        Returns:
            List[ImageResult]: 生成的图片列表
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 提交任务
            url = self._get_url("image_generate")
            payload = {
                "prompt": prompt,
                "num_images": min(max(num_images, 1), 4)
            }

            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            request_id = data.get("request_id")
            if not request_id:
                raise Exception("Failed to get request_id from response")

            # 2. 轮询结果
            result = await self._poll_image_result("nano-banana", request_id, client)

            # 3. 解析结果
            images = []
            for img in result.get("images", []):
                images.append(ImageResult(
                    url=img["url"],
                    width=img.get("width", 1024),
                    height=img.get("height", 1024),
                    content_type=img.get("content_type", "image/jpeg"),
                    seed=result.get("seed")
                ))

            return images

    async def edit_image(
        self,
        prompt: str,
        image_urls: List[str],
        num_images: int = 1,
        timeout: float = 120.0
    ) -> List[ImageResult]:
        """
        图片编辑 (nano-banana/edit)

        Args:
            prompt: 编辑提示词
            image_urls: 需要编辑的图片 URL 列表
            num_images: 生成数量 1-4
            timeout: 超时时间(秒)

        Returns:
            List[ImageResult]: 编辑后的图片列表
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 提交任务
            url = self._get_url("image_edit")
            payload = {
                "prompt": prompt,
                "image_urls": image_urls,
                "num_images": min(max(num_images, 1), 4)
            }

            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            request_id = data.get("request_id")
            if not request_id:
                raise Exception("Failed to get request_id from response")

            # 2. 轮询结果
            result = await self._poll_image_result("nano-banana", request_id, client)

            # 3. 解析结果
            images = []
            for img in result.get("images", []):
                images.append(ImageResult(
                    url=img["url"],
                    width=img.get("width", 1024),
                    height=img.get("height", 1024),
                    content_type=img.get("content_type", "image/jpeg"),
                    seed=result.get("seed")
                ))

            return images

    async def _poll_image_result(
        self,
        model_name: str,
        request_id: str,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """轮询图像生成结果"""
        url = self._get_url("image_result", model_name=model_name, request_id=request_id)

        for _ in range(CangheAPIConfig.IMAGE_MAX_ATTEMPTS):
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")

            if status == FalAIStatus.COMPLETED or "images" in data:
                return data
            elif status == FalAIStatus.FAILED:
                raise Exception(f"Image generation failed: {data}")

            await asyncio.sleep(CangheAPIConfig.IMAGE_POLL_INTERVAL)

        raise TimeoutError("Image generation timed out")

    # ============================================
    # 视频生成 (VEO)
    # ============================================

    async def create_video(
        self,
        prompt: str,
        model: str = "veo3.1-fast",
        images: Optional[List[str]] = None,
        enhance_prompt: bool = True,
        enable_upsample: bool = False,
        aspect_ratio: str = "16:9",
        timeout: float = 600.0
    ) -> VideoResult:
        """
        创建视频 (VEO 统一接口)

        Args:
            prompt: 提示词
            model: 模型名称
            images: 图片 URL 列表 (用于 frames/components 模型)
            enhance_prompt: 中文自动转英文
            enable_upsample: 启用超分辨率
            aspect_ratio: 宽高比 "16:9" 或 "9:16"
            timeout: 超时时间(秒)

        Returns:
            VideoResult: 视频生成结果
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 提交任务
            url = self._get_url("video_create")
            payload = {
                "model": model,
                "prompt": prompt,
                "enhance_prompt": enhance_prompt,
                "enable_upsample": enable_upsample,
            }

            if images:
                payload["images"] = images

            # 只有 veo3 系列支持 aspect_ratio
            if "veo3" in model:
                payload["aspect_ratio"] = aspect_ratio

            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            task_id = data.get("id")
            if not task_id:
                raise Exception("Failed to get task id from response")

            # 2. 轮询结果
            result = await self._poll_video_result(task_id, client)

            return VideoResult(
                video_url=result.get("video_url", ""),
                status=result.get("status", ""),
                enhanced_prompt=result.get("enhanced_prompt")
            )

    async def _poll_video_result(
        self,
        task_id: str,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """轮询视频生成结果"""
        url = self._get_url("video_query")

        for _ in range(CangheAPIConfig.VIDEO_MAX_ATTEMPTS):
            response = await client.get(
                url,
                params={"id": task_id},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")

            if status == VeoStatus.COMPLETED:
                return data
            elif status in [VeoStatus.FAILED, VeoStatus.ERROR,
                          VeoStatus.VIDEO_GENERATION_FAILED,
                          VeoStatus.VIDEO_UPSAMPLING_FAILED]:
                raise Exception(f"Video generation failed: {data}")

            await asyncio.sleep(CangheAPIConfig.VIDEO_POLL_INTERVAL)

        raise TimeoutError("Video generation timed out")

    # ============================================
    # 视频生成 (即梦)
    # ============================================

    async def create_jimeng_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: Optional[str] = None,
        cfg_scale: float = 0.5,
        timeout: float = 600.0
    ) -> VideoResult:
        """
        即梦视频生成 (原生接口)

        Args:
            prompt: 提示词
            duration: 视频时长 5 或 10 秒
            aspect_ratio: "1:1", "21:9", "16:9", "9:16", "4:3", "3:4"
            image_url: 图生视频的图片 URL
            cfg_scale: 引导系数
            timeout: 超时时间(秒)

        Returns:
            VideoResult: 视频生成结果
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 提交任务
            url = self._get_url("jimeng_submit")
            payload = {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "cfg_scale": cfg_scale
            }

            if image_url:
                payload["image_url"] = image_url

            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "success":
                raise Exception(f"Failed to submit jimeng video task: {data}")

            task_id = data.get("data")
            if not task_id:
                raise Exception("Failed to get task id from response")

            # 2. 轮询结果
            result = await self._poll_jimeng_result(task_id, client)

            # 获取视频 URL
            video_url = ""
            if isinstance(result.get("data"), dict):
                inner_data = result["data"].get("data", {})
                if isinstance(inner_data, dict):
                    video_url = inner_data.get("data", {}).get("video", "")

            return VideoResult(
                video_url=video_url,
                status=result.get("data", {}).get("status", ""),
                enhanced_prompt=None
            )

    async def _poll_jimeng_result(
        self,
        task_id: str,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """轮询即梦视频结果"""
        url = self._get_url("jimeng_fetch", task_id=task_id)

        for _ in range(CangheAPIConfig.VIDEO_MAX_ATTEMPTS):
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "success":
                raise Exception(f"Failed to fetch jimeng task: {data}")

            task_data = data.get("data", {})
            status = task_data.get("status", "")

            if status == JimengStatus.SUCCESS:
                return data
            elif status == JimengStatus.FAILURE:
                raise Exception(f"Jimeng video generation failed: {data}")

            await asyncio.sleep(CangheAPIConfig.VIDEO_POLL_INTERVAL)

        raise TimeoutError("Jimeng video generation timed out")

    # ============================================
    # 即梦视频 (统一接口)
    # ============================================

    async def create_jimeng_video_unified(
        self,
        prompt: str,
        aspect_ratio: str = "3:2",
        size: str = "720P",
        images: Optional[List[str]] = None,
        timeout: float = 600.0
    ) -> VideoResult:
        """
        即梦视频生成 (统一接口)

        Args:
            prompt: 提示词
            aspect_ratio: "2:3", "3:2", "1:1"
            size: "720P"
            images: 图片链接列表 (图生视频)
            timeout: 超时时间(秒)

        Returns:
            VideoResult: 视频生成结果
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 提交任务
            url = self._get_url("video_create")
            payload = {
                "model": "jimeng-video-3.0",
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "size": size,
                "images": images or []
            }

            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            task_id = data.get("id")
            if not task_id:
                raise Exception("Failed to get task id from response")

            # 2. 轮询结果 (使用统一查询接口)
            result = await self._poll_video_result(task_id, client)

            return VideoResult(
                video_url=result.get("video_url", ""),
                status=result.get("status", ""),
                enhanced_prompt=result.get("enhanced_prompt")
            )

    # ============================================
    # 同步方法包装
    # ============================================

    def generate_image_sync(
        self,
        prompt: str,
        num_images: int = 1,
        timeout: float = 120.0
    ) -> List[ImageResult]:
        """同步版本的文生图"""
        return asyncio.run(self.generate_image(prompt, num_images, timeout))

    def edit_image_sync(
        self,
        prompt: str,
        image_urls: List[str],
        num_images: int = 1,
        timeout: float = 120.0
    ) -> List[ImageResult]:
        """同步版本的图片编辑"""
        return asyncio.run(self.edit_image(prompt, image_urls, num_images, timeout))

    def create_video_sync(
        self,
        prompt: str,
        model: str = "veo3.1-fast",
        images: Optional[List[str]] = None,
        enhance_prompt: bool = True,
        enable_upsample: bool = False,
        aspect_ratio: str = "16:9",
        timeout: float = 600.0
    ) -> VideoResult:
        """同步版本的视频生成"""
        return asyncio.run(self.create_video(
            prompt, model, images, enhance_prompt, enable_upsample, aspect_ratio, timeout
        ))

    def create_jimeng_video_sync(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_url: Optional[str] = None,
        cfg_scale: float = 0.5,
        timeout: float = 600.0
    ) -> VideoResult:
        """同步版本的即梦视频生成"""
        return asyncio.run(self.create_jimeng_video(
            prompt, duration, aspect_ratio, image_url, cfg_scale, timeout
        ))


# ============================================
# 便捷函数
# ============================================

def get_client(api_key: Optional[str] = None) -> CangheAPIClient:
    """获取 API 客户端实例"""
    return CangheAPIClient(api_key)


# ============================================
# 测试
# ============================================

if __name__ == "__main__":
    import sys

    async def test():
        # 需要设置环境变量 CANGHE_API_KEY
        api_key = os.getenv("CANGHE_API_KEY")
        if not api_key:
            print("Please set CANGHE_API_KEY environment variable")
            sys.exit(1)

        client = CangheAPIClient(api_key)

        # 测试文生图
        print("Testing text-to-image...")
        try:
            images = await client.generate_image("A beautiful sunset over the ocean")
            for img in images:
                print(f"  Generated: {img.url}")
        except Exception as e:
            print(f"  Error: {e}")

        # 测试视频生成
        print("\nTesting video generation...")
        try:
            video = await client.create_video(
                prompt="A cat playing with a ball",
                model="veo3.1-fast"
            )
            print(f"  Video URL: {video.video_url}")
        except Exception as e:
            print(f"  Error: {e}")

    asyncio.run(test())
