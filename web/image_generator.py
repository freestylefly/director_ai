"""
AI Storyboard Pro - Image Generator v2.2
支持两种图像生成后端:
1. 苍何 API (Canghe API) - 云端生成
   - nano-banana: Google Imagen 模型 (推荐)
   - jimeng: 即梦图像生成模型
2. ComfyUI - 本地图像生成
"""

import os
import time
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from models import Shot, StoryboardProject, Character, Scene


# ============================================
# 数据结构
# ============================================

@dataclass
class GenerationResult:
    """图像生成结果"""
    success: bool
    image_path: str = ""
    error_message: str = ""
    consistency_score: float = 0.0
    generation_time: float = 0.0


class ImageBackend(str, Enum):
    """图像生成后端类型"""
    CANGHE = "canghe"      # 苍何 API
    COMFYUI = "comfyui"    # 本地 ComfyUI


class CangheImageModel(str, Enum):
    """苍何 API 支持的图像模型"""
    NANO_BANANA = "nano-banana"  # Google Imagen (Fal.ai)
    JIMENG = "jimeng"            # 即梦图像生成
    DALLE3 = "dall-e-3"          # DALL-E 3 (OpenAI)


class FalAIStatus(str, Enum):
    """Fal.ai 任务状态"""
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JimengStatus(str, Enum):
    """即梦任务状态"""
    NOT_START = "NOT_START"
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"


# ============================================
# 全局配置
# ============================================

# 当前选择的模型 (可通过 set_canghe_model 修改)
_current_canghe_model = CangheImageModel.NANO_BANANA  # 即梦仅支持视频，图像使用 nano-banana
_canghe_api_key = ""


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    import re
    # 替换 Windows 非法字符: \ / : * ? " < > |
    # 同时替换中文冒号、全角字符等
    illegal_chars = r'[\\/:*?"<>|：；]'
    sanitized = re.sub(illegal_chars, '_', name)
    # 去除首尾空格和点
    sanitized = sanitized.strip(' .')
    return sanitized or "unnamed"


def set_canghe_api_key(api_key: str):
    """设置苍何 API 密钥"""
    global _canghe_api_key
    _canghe_api_key = api_key


def get_canghe_api_key() -> str:
    """获取苍何 API 密钥"""
    global _canghe_api_key
    if _canghe_api_key:
        return _canghe_api_key
    # 尝试从 settings 获取
    try:
        from settings import settings
        return settings.api_key
    except:
        return ""


def set_canghe_model(model: str):
    """设置苍何 API 图像模型"""
    global _current_canghe_model
    model_lower = model.lower()
    if "jimeng" in model_lower or "即梦" in model:
        _current_canghe_model = CangheImageModel.JIMENG
    elif "dall" in model_lower or "dalle" in model_lower:
        _current_canghe_model = CangheImageModel.DALLE3
    else:
        # 默认使用 nano-banana
        _current_canghe_model = CangheImageModel.NANO_BANANA


def get_canghe_model() -> CangheImageModel:
    """获取当前苍何 API 图像模型"""
    return _current_canghe_model


# ============================================
# 苍何 API 图像生成器
# ============================================

class CangheImageGenerator:
    """
    苍何 API 图像生成器
    支持多种模型: nano-banana (Imagen), jimeng (即梦)
    """

    # API 配置
    BASE_URL = "https://api.canghe.ai"
    POLL_INTERVAL = 2.0  # 轮询间隔(秒)
    MAX_POLL_ATTEMPTS = 60  # 最大轮询次数
    REQUEST_TIMEOUT = 180.0  # 请求超时(秒)

    def __init__(self, api_key: str = "", output_dir: str = "outputs", model: str = None):
        """
        初始化苍何 API 客户端

        Args:
            api_key: 苍何 API 密钥
            output_dir: 输出目录
            model: 图像模型 ("nano-banana" 或 "jimeng")
        """
        self.api_key = api_key or get_canghe_api_key()
        if not self.api_key:
            raise ValueError("苍何 API 密钥不能为空")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置模型
        if model:
            set_canghe_model(model)
        self.model = get_canghe_model()

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def get_aspect_ratio_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """获取宽高比对应的像素尺寸"""
        ratios = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "1:1": (768, 768),
            "4:3": (896, 672),
            "3:4": (672, 896),
            "21:9": (1024, 440)
        }
        return ratios.get(aspect_ratio, (1024, 576))

    def collect_reference_images(
        self,
        shot: Shot,
        project: StoryboardProject
    ) -> Tuple[List[str], List[float]]:
        """收集参考图片和权重"""
        images = []
        weights = []
        slot_weights = shot.slot_weights

        # 角色参考
        for char_id in shot.characters_in_shot:
            char = project.get_character_by_id(char_id)
            if char and char.ref_images:
                for ref_img in char.ref_images[:2]:
                    if os.path.exists(ref_img):
                        images.append(ref_img)
                        weights.append(slot_weights.character * char.consistency_weight)

        # 场景参考
        scene = project.get_scene_by_id(shot.scene_id)
        if scene:
            if scene.space_ref_image and os.path.exists(scene.space_ref_image):
                images.append(scene.space_ref_image)
                weights.append(slot_weights.scene * scene.consistency_weight)
            if scene.atmosphere_ref_image and os.path.exists(scene.atmosphere_ref_image):
                images.append(scene.atmosphere_ref_image)
                weights.append(slot_weights.scene * 0.5)

        # 道具参考
        for prop_id in shot.props_in_shot:
            prop = project.get_prop_by_id(prop_id)
            if prop and prop.ref_image and os.path.exists(prop.ref_image):
                images.append(prop.ref_image)
                weights.append(slot_weights.props * prop.consistency_weight)

        # 风格参考
        if project.style.ref_image and os.path.exists(project.style.ref_image):
            images.append(project.style.ref_image)
            weights.append(slot_weights.style * project.style.weight)

        return images, weights

    # ========================================
    # Nano-Banana (Fal.ai Imagen) 生成
    # ========================================

    async def _generate_nano_banana_async(
        self,
        prompt: str,
        num_images: int = 1
    ) -> Tuple[bool, List[Dict], str]:
        """使用 nano-banana 模型生成图像"""
        print(f"[Nano-Banana] 开始调用 API...")
        print(f"[Nano-Banana] API URL: {self.BASE_URL}/fal-ai/nano-banana")
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            try:
                # 1. 提交生成任务
                url = f"{self.BASE_URL}/fal-ai/nano-banana"
                payload = {
                    "prompt": prompt,
                    "num_images": min(max(num_images, 1), 4)
                }
                print(f"[Nano-Banana] 发送请求中...")

                response = await client.post(url, json=payload, headers=self.headers)
                print(f"[Nano-Banana] 响应状态: {response.status_code}")

                # 先尝试解析 JSON，即使是错误响应也可能包含有用信息
                try:
                    data = response.json()
                except:
                    data = {}

                # 检查 HTTP 错误或 API 返回错误状态
                if response.status_code >= 400 or data.get("status") == "FAILED":
                    error_msg = data.get("message", f"HTTP {response.status_code}")
                    print(f"[Nano-Banana] API 错误: {error_msg}")
                    return False, [], f"Nano-Banana 不可用: {error_msg}"

                request_id = data.get("request_id")
                if not request_id:
                    print(f"[Nano-Banana] 错误: 未获取到 request_id, 响应: {data}")
                    return False, [], "未获取到 request_id"

                print(f"[Nano-Banana] 任务已提交, request_id: {request_id}")

                # 2. 轮询获取结果
                result_url = f"{self.BASE_URL}/fal-ai/nano-banana/requests/{request_id}"

                for attempt in range(self.MAX_POLL_ATTEMPTS):
                    await asyncio.sleep(self.POLL_INTERVAL)

                    result_response = await client.get(result_url, headers=self.headers)
                    result_response.raise_for_status()
                    result_data = result_response.json()

                    status = result_data.get("status", "")
                    if attempt % 5 == 0:  # 每5次打印一次状态
                        print(f"[Nano-Banana] 轮询 {attempt+1}/{self.MAX_POLL_ATTEMPTS}, 状态: {status}")

                    if status == FalAIStatus.COMPLETED or "images" in result_data:
                        images = result_data.get("images", [])
                        print(f"[Nano-Banana] ✓ 生成成功! 获取到 {len(images)} 张图片")
                        return True, images, ""
                    elif status == FalAIStatus.FAILED:
                        print(f"[Nano-Banana] ✗ 生成失败: {result_data}")
                        return False, [], f"生成失败: {result_data}"

                print(f"[Nano-Banana] ✗ 生成超时")
                return False, [], "生成超时"

            except httpx.HTTPStatusError as e:
                return False, [], f"HTTP 错误: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return False, [], f"生成失败: {str(e)}"

    # ========================================
    # DALL-E 3 图像生成
    # ========================================

    async def _generate_dalle3_async(
        self,
        prompt: str,
        size: str = "1024x1024"
    ) -> Tuple[bool, List[Dict], str]:
        """使用 DALL-E 3 模型生成图像"""
        print(f"[DALL-E 3] 开始调用 API...")
        print(f"[DALL-E 3] 尺寸: {size}")
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            try:
                url = f"{self.BASE_URL}/v1/images/generations"
                payload = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": "standard"
                }

                print(f"[DALL-E 3] 发送请求中...")
                response = await client.post(url, json=payload, headers=self.headers)
                print(f"[DALL-E 3] 响应状态: {response.status_code}")
                response.raise_for_status()
                data = response.json()

                # DALL-E 3 直接返回结果，不需要轮询
                images = data.get("data", [])
                if images:
                    print(f"[DALL-E 3] ✓ 生成成功! 获取到 {len(images)} 张图片")
                    return True, images, ""
                else:
                    print(f"[DALL-E 3] ✗ 未获取到图像数据")
                    return False, [], "未获取到图像数据"

            except httpx.HTTPStatusError as e:
                print(f"[DALL-E 3] ✗ HTTP 错误: {e.response.status_code}")
                return False, [], f"HTTP 错误: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return False, [], f"生成失败: {str(e)}"

    # ========================================
    # 即梦 (Jimeng) 图像生成
    # ========================================

    async def _generate_jimeng_async(
        self,
        prompt: str,
        aspect_ratio: str = "16:9"
    ) -> Tuple[bool, List[Dict], str]:
        """使用即梦模型生成图像"""
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            try:
                # 1. 提交生成任务
                url = f"{self.BASE_URL}/jimeng/submit/images"

                # 转换宽高比格式
                jimeng_ratios = {
                    "16:9": "16:9",
                    "9:16": "9:16",
                    "1:1": "1:1",
                    "4:3": "4:3",
                    "3:4": "3:4",
                    "21:9": "21:9"
                }

                payload = {
                    "prompt": prompt,
                    "aspect_ratio": jimeng_ratios.get(aspect_ratio, "16:9"),
                    "num_images": 1
                }

                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                # 检查响应
                if data.get("code") != "success":
                    return False, [], f"提交失败: {data.get('message', '未知错误')}"

                task_id = data.get("data")
                if not task_id:
                    return False, [], "未获取到 task_id"

                # 2. 轮询获取结果
                result_url = f"{self.BASE_URL}/jimeng/fetch/{task_id}"

                for attempt in range(self.MAX_POLL_ATTEMPTS):
                    await asyncio.sleep(self.POLL_INTERVAL)

                    result_response = await client.get(result_url, headers=self.headers)
                    result_response.raise_for_status()
                    result_data = result_response.json()

                    if result_data.get("code") != "success":
                        continue

                    task_info = result_data.get("data", {})
                    status = task_info.get("status", "")

                    if status == JimengStatus.SUCCESS:
                        # 解析图片数据
                        inner_data = task_info.get("data", {})
                        if isinstance(inner_data, dict):
                            image_data = inner_data.get("data", {})
                            if isinstance(image_data, dict):
                                image_url = image_data.get("image") or image_data.get("images", [{}])[0].get("url", "")
                                if image_url:
                                    return True, [{"url": image_url}], ""
                        return False, [], "未找到图片 URL"
                    elif status == JimengStatus.FAILURE:
                        return False, [], f"即梦生成失败: {task_info.get('fail_reason', '未知原因')}"

                return False, [], "即梦生成超时"

            except httpx.HTTPStatusError as e:
                return False, [], f"HTTP 错误: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return False, [], f"即梦生成失败: {str(e)}"

    # ========================================
    # 通用方法
    # ========================================

    def _download_image(self, url: str, save_path: Path) -> bool:
        """下载图片到本地"""
        print(f"[下载] 开始下载图片...")
        print(f"[下载] URL: {url[:100]}...")
        print(f"[下载] 保存路径: {save_path}")
        try:
            response = httpx.get(url, timeout=60.0, follow_redirects=True)
            response.raise_for_status()
            print(f"[下载] HTTP 状态: {response.status_code}, 内容大小: {len(response.content)} bytes")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"[下载] ✓ 保存成功: {save_path}")
            return True
        except Exception as e:
            print(f"[下载] ✗ 下载失败: {e}")
            return False

    def generate_shot(
        self,
        shot: Shot,
        project: StoryboardProject,
        prompt: str
    ) -> GenerationResult:
        """生成单个镜头的图像"""
        start_time = time.time()

        try:
            # 生成负提示词
            from prompt_generator import generate_negative_prompt
            from templates import get_template
            template = get_template(shot.template)
            negative_prompt = generate_negative_prompt(template) if template else ""

            # 构建完整提示词
            full_prompt = prompt
            if negative_prompt:
                full_prompt = f"{prompt}. Avoid: {negative_prompt}"

            # 添加一致性前缀
            consistency_prefix = project.get_consistency_prefix()
            if consistency_prefix:
                full_prompt = f"{consistency_prefix} {full_prompt}"

            # 根据模型选择生成方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            used_model = None
            try:
                current_model = get_canghe_model()
                dalle_sizes = {
                    "16:9": "1792x1024",
                    "9:16": "1024x1792",
                    "1:1": "1024x1024",
                    "4:3": "1024x1024",
                    "3:4": "1024x1024",
                }

                if current_model == CangheImageModel.JIMENG:
                    # 即梦API不支持图像生成，自动回退到 nano-banana
                    print(f"[INFO] 即梦仅支持视频生成，自动使用 nano-banana 生成图像...")
                    used_model = CangheImageModel.NANO_BANANA
                    success, images, error = loop.run_until_complete(
                        self._generate_nano_banana_async(full_prompt, num_images=1)
                    )
                    # 如果 nano-banana 也失败，继续回退到 DALL-E 3
                    if not success:
                        print(f"[INFO] Nano-Banana 失败，继续切换到 DALL-E 3...")
                        used_model = CangheImageModel.DALLE3
                        size = dalle_sizes.get(project.aspect_ratio, "1024x1024")
                        success, images, error = loop.run_until_complete(
                            self._generate_dalle3_async(full_prompt, size=size)
                        )
                elif current_model == CangheImageModel.DALLE3:
                    print(f"[INFO] 使用 DALL-E 3 模型生成图像...")
                    used_model = CangheImageModel.DALLE3
                    size = dalle_sizes.get(project.aspect_ratio, "1024x1024")
                    success, images, error = loop.run_until_complete(
                        self._generate_dalle3_async(full_prompt, size=size)
                    )
                else:
                    # Nano-Banana，如果失败自动切换到 DALL-E 3
                    print(f"[INFO] 使用 nano-banana 模型生成图像...")
                    used_model = CangheImageModel.NANO_BANANA
                    success, images, error = loop.run_until_complete(
                        self._generate_nano_banana_async(full_prompt, num_images=1)
                    )

                    # 如果 Nano-Banana 失败，自动尝试 DALL-E 3
                    if not success:
                        print(f"[INFO] Nano-Banana 失败 ({error[:80] if error else '未知错误'})，自动切换到 DALL-E 3...")
                        used_model = CangheImageModel.DALLE3
                        size = dalle_sizes.get(project.aspect_ratio, "1024x1024")
                        success, images, error = loop.run_until_complete(
                            self._generate_dalle3_async(full_prompt, size=size)
                        )
                        print(f"[DEBUG] DALL-E 3 结果: success={success}, images_count={len(images) if images else 0}, error={error[:80] if error else 'None'}")
            finally:
                loop.close()

            generation_time = time.time() - start_time

            if success and images:
                # 下载并保存图片
                image_data = images[0]
                image_url = image_data.get("url", "")
                print(f"[DEBUG] 获取到图片 URL: {image_url[:80] if image_url else 'None'}...")

                if image_url:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_map = {
                        CangheImageModel.JIMENG: "jimeng",
                        CangheImageModel.DALLE3: "dalle3",
                        CangheImageModel.NANO_BANANA: "nb"
                    }
                    # 使用实际使用的模型，而不是配置的模型（因为可能有 fallback）
                    model_suffix = model_map.get(used_model or get_canghe_model(), "img")
                    filename = f"shot_{shot.shot_number:03d}_{timestamp}_{model_suffix}.png"
                    safe_project_name = sanitize_filename(project.name)
                    output_path = self.output_dir / safe_project_name / filename
                    print(f"[DEBUG] 项目名: {project.name} -> {safe_project_name}")
                    print(f"[DEBUG] 保存路径: {output_path}")

                    if self._download_image(image_url, output_path):
                        print(f"[DEBUG] 下载成功，文件存在: {output_path.exists()}, 大小: {output_path.stat().st_size if output_path.exists() else 0}")
                        return GenerationResult(
                            success=True,
                            image_path=str(output_path),
                            consistency_score=0.9,
                            generation_time=generation_time
                        )
                    else:
                        return GenerationResult(
                            success=False,
                            error_message="下载图片失败",
                            generation_time=generation_time
                        )
                else:
                    return GenerationResult(
                        success=False,
                        error_message="未获取到图片 URL",
                        generation_time=generation_time
                    )
            else:
                return GenerationResult(
                    success=False,
                    error_message=error or "生成失败",
                    generation_time=generation_time
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=f"生成异常: {str(e)}",
                generation_time=time.time() - start_time
            )

    def generate_all_shots(
        self,
        project: StoryboardProject,
        prompts: Dict[int, str],
        progress_callback=None
    ) -> List[GenerationResult]:
        """批量生成所有镜头"""
        results = []

        for i, shot in enumerate(project.shots):
            if progress_callback:
                progress_callback(i, len(project.shots), f"正在生成镜头 {shot.shot_number}...")

            prompt = prompts.get(shot.shot_number, shot.generated_prompt)
            result = self.generate_shot(shot, project, prompt)
            results.append(result)

            if result.success:
                shot.output_image = result.image_path
                shot.consistency_score = result.consistency_score

        return results


# ============================================
# ComfyUI 图像生成器
# ============================================

class ComfyUIImageGenerator:
    """ComfyUI 本地图像生成器"""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self._initialized = False
        self._project_seed = None

    def _ensure_client(self):
        """确保 ComfyUI 客户端已初始化"""
        if self._initialized:
            return

        try:
            from comfyui_client import create_comfyui_client_from_settings
            self.client = create_comfyui_client_from_settings()
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"初始化 ComfyUI 客户端失败: {e}")

    def get_aspect_ratio_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """获取宽高比对应的像素尺寸"""
        ratios = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "1:1": (768, 768),
            "4:3": (896, 672),
            "3:4": (672, 896),
            "21:9": (1024, 440)
        }
        return ratios.get(aspect_ratio, (1024, 576))

    def _get_seed_for_project(self, project: StoryboardProject) -> int:
        """获取生成种子"""
        if project.lock_seed:
            if project.generation_seed > 0:
                return project.generation_seed
            else:
                if self._project_seed is None:
                    self._project_seed = int(time.time() * 1000) % (2**32)
                return self._project_seed
        else:
            return -1

    def generate_shot(
        self,
        shot: Shot,
        project: StoryboardProject,
        prompt: str
    ) -> GenerationResult:
        """使用 ComfyUI 生成图像"""
        start_time = time.time()

        try:
            self._ensure_client()

            if not self.client.is_enabled():
                return GenerationResult(
                    success=False,
                    error_message="ComfyUI 未启用。请在 .env 中设置 IMAGE_BACKEND=comfyui 和 COMFYUI_ENABLED=true"
                )

            # 测试连接
            connected, msg = self.client.test_connection()
            if not connected:
                return GenerationResult(
                    success=False,
                    error_message=f"ComfyUI 连接失败: {msg}"
                )

            from comfyui_client import GenerationParams

            # 获取尺寸
            width, height = self.get_aspect_ratio_dimensions(project.aspect_ratio)

            # 生成负提示词
            from prompt_generator import generate_negative_prompt
            from templates import get_template
            template = get_template(shot.template)
            negative_prompt = generate_negative_prompt(template) if template else "low quality, blurry, deformed"

            # 添加一致性前缀
            consistency_prefix = project.get_consistency_prefix()
            if consistency_prefix:
                prompt = f"{consistency_prefix} {prompt}"

            # 获取种子
            seed = self._get_seed_for_project(project)

            params = GenerationParams(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=20,
                cfg_scale=7.0,
                seed=seed
            )

            # 收集参考图像
            ref_images = []
            for char_id in shot.characters_in_shot:
                char = project.get_character_by_id(char_id)
                if char and char.ref_images:
                    for ref_img in char.ref_images[:1]:
                        if os.path.exists(ref_img):
                            ref_images.append(ref_img)
                            break

            # 准备输出目录
            safe_project_name = sanitize_filename(project.name)
            project_output = self.output_dir / safe_project_name
            project_output.mkdir(parents=True, exist_ok=True)

            if ref_images:
                params.ref_image_path = ref_images[0]
                params.denoise = 0.7
                result = self.client.image_to_image(
                    params,
                    output_dir=str(project_output)
                )
            else:
                result = self.client.text_to_image(
                    params,
                    output_dir=str(project_output)
                )

            generation_time = time.time() - start_time

            if result.success and result.images:
                return GenerationResult(
                    success=True,
                    image_path=result.images[0],
                    consistency_score=0.85,
                    generation_time=generation_time
                )
            else:
                return GenerationResult(
                    success=False,
                    error_message=result.error or "ComfyUI 生成失败",
                    generation_time=generation_time
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=f"ComfyUI 生成异常: {str(e)}",
                generation_time=time.time() - start_time
            )


# ============================================
# 工厂函数
# ============================================

def create_generator(api_key: str = "", output_dir: str = "outputs", backend: str = None, model: str = None):
    """
    创建图像生成器

    Args:
        api_key: 苍何 API 密钥 (backend="canghe" 时需要)
        output_dir: 输出目录
        backend: 生成后端 ("canghe" 或 "comfyui")
        model: 苍何 API 模型 ("nano-banana" 或 "jimeng")

    Returns:
        CangheImageGenerator 或 ComfyUIImageGenerator
    """
    # 优先检查统一苍何 API 配置
    unified_api_key = None
    unified_image_enabled = True

    # 方法1: 尝试从 app 模块获取统一配置
    try:
        import sys
        if 'app' in sys.modules:
            app_module = sys.modules['app']
            if hasattr(app_module, '_canghe_unified_config'):
                unified_config = app_module._canghe_unified_config
                unified_api_key = unified_config.get("api_key", "")
                unified_image_enabled = unified_config.get("image_enabled", True)
                print(f"[create_generator] 从 app 模块获取配置: api_key={unified_api_key[:10] if unified_api_key else 'None'}..., image_enabled={unified_image_enabled}")
                if unified_api_key and unified_image_enabled:
                    api_key = unified_api_key
                    model = model or unified_config.get("image_model", "nano-banana")
                    backend = "canghe"  # 强制使用苍何 API
                    print(f"[create_generator] 强制使用苍何 API, model={model}")
    except Exception as e:
        print(f"[create_generator] 从 app 模块获取配置失败: {e}")

    # 方法2: 尝试从用户配置文件直接读取
    if not unified_api_key:
        try:
            import json
            # 尝试多个可能的配置文件路径
            possible_paths = [
                Path(__file__).parent / "projects" / "_user_config.json",
                Path(output_dir).parent / "projects" / "_user_config.json",
                Path("projects") / "_user_config.json",
            ]
            for config_path in possible_paths:
                if config_path.exists():
                    print(f"[create_generator] 找到配置文件: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        canghe_unified = config.get("canghe_unified", {})
                        if canghe_unified.get("enabled") and canghe_unified.get("image_enabled"):
                            unified_api_key = canghe_unified.get("api_key", "")
                            if unified_api_key:
                                api_key = unified_api_key
                                model = model or canghe_unified.get("image_model", "nano-banana")
                                backend = "canghe"
                                print(f"[create_generator] 从配置文件获取: api_key={unified_api_key[:10]}..., model={model}")
                                break
        except Exception as e:
            print(f"[create_generator] 从配置文件读取失败: {e}")

    # 从设置获取后端类型
    if backend is None:
        try:
            from settings import settings
            backend = settings.image_backend
        except ImportError:
            backend = "canghe" if api_key else "comfyui"

    backend = backend.lower()

    # 如果有统一配置的 API Key 且图像生成启用，优先使用苍何
    if unified_api_key and unified_image_enabled:
        backend = "canghe"

    if backend == "comfyui":
        print("[INFO] 使用 ComfyUI 本地生成")
        return ComfyUIImageGenerator(output_dir)
    else:
        # 默认使用苍何 API
        if not api_key:
            api_key = get_canghe_api_key()

        if not api_key:
            raise ValueError(
                "苍何 API 密钥未配置。请在 .env 中设置 CANGHE_API_KEY，"
                "或使用 IMAGE_BACKEND=comfyui 切换到本地生成。"
            )

        model_name = model or get_canghe_model().value
        print(f"[INFO] 使用苍何 API 云端生成 (模型: {model_name})")
        return CangheImageGenerator(api_key, output_dir, model)


# ============================================
# 兼容旧代码的别名
# ============================================

ImageGenerator = CangheImageGenerator
