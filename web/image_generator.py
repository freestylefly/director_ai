"""
AI Storyboard Pro - Image Generator
Integration with Nana Banana Pro API for consistent image generation
"""

import os
import json
import base64
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from models import Shot, StoryboardProject, Character, Scene


@dataclass
class GenerationResult:
    """Result of image generation"""
    success: bool
    image_path: str = ""
    error_message: str = ""
    consistency_score: float = 0.0
    generation_time: float = 0.0


class NanaBananaProClient:
    """Client for Nana Banana Pro API"""

    def __init__(self, api_key: str, base_url: str = "https://api.nanabanana.pro"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def generate_with_reference(
        self,
        prompt: str,
        reference_images: List[str],
        reference_weights: List[float],
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 576,
        num_steps: int = 30,
        guidance_scale: float = 7.5
    ) -> Tuple[bool, Optional[bytes], str]:
        """
        Generate image with reference images for consistency.

        Args:
            prompt: Generation prompt
            reference_images: List of reference image paths
            reference_weights: Weight for each reference (0.0-1.0)
            negative_prompt: Negative prompt
            width: Output width
            height: Output height
            num_steps: Number of generation steps
            guidance_scale: Guidance scale

        Returns:
            Tuple of (success, image_bytes, error_message)
        """
        try:
            # Prepare reference data
            references = []
            for img_path, weight in zip(reference_images, reference_weights):
                if os.path.exists(img_path):
                    references.append({
                        "image": self.encode_image(img_path),
                        "weight": weight
                    })

            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "references": references,
                "width": width,
                "height": height,
                "num_inference_steps": num_steps,
                "guidance_scale": guidance_scale
            }

            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                if "image" in result:
                    image_bytes = base64.b64decode(result["image"])
                    return True, image_bytes, ""
                else:
                    return False, None, "No image in response"
            else:
                return False, None, f"API error: {response.status_code} - {response.text}"

        except Exception as e:
            return False, None, f"Generation failed: {str(e)}"


class ImageGenerator:
    """Main image generator for storyboard system"""

    def __init__(self, api_key: str, output_dir: str = "outputs"):
        self.client = NanaBananaProClient(api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_aspect_ratio_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """Get pixel dimensions for aspect ratio"""
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
        """
        Collect reference images and weights for a shot.

        Returns:
            Tuple of (image_paths, weights)
        """
        images = []
        weights = []
        slot_weights = shot.slot_weights

        # Character references
        for char_id in shot.characters_in_shot:
            char = project.get_character_by_id(char_id)
            if char and char.ref_images:
                # Use first reference image
                for ref_img in char.ref_images[:2]:  # Max 2 per character
                    if os.path.exists(ref_img):
                        images.append(ref_img)
                        weights.append(slot_weights.character * char.consistency_weight)

        # Scene reference
        scene = project.get_scene_by_id(shot.scene_id)
        if scene:
            if scene.space_ref_image and os.path.exists(scene.space_ref_image):
                images.append(scene.space_ref_image)
                weights.append(slot_weights.scene * scene.consistency_weight)
            if scene.atmosphere_ref_image and os.path.exists(scene.atmosphere_ref_image):
                images.append(scene.atmosphere_ref_image)
                weights.append(slot_weights.scene * 0.5)

        # Props references
        for prop_id in shot.props_in_shot:
            prop = project.get_prop_by_id(prop_id)
            if prop and prop.ref_image and os.path.exists(prop.ref_image):
                images.append(prop.ref_image)
                weights.append(slot_weights.props * prop.consistency_weight)

        # Style reference
        if project.style.ref_image and os.path.exists(project.style.ref_image):
            images.append(project.style.ref_image)
            weights.append(slot_weights.style * project.style.weight)

        return images, weights

    def generate_shot(
        self,
        shot: Shot,
        project: StoryboardProject,
        prompt: str
    ) -> GenerationResult:
        """Generate image for a single shot"""
        import time
        start_time = time.time()

        # Get dimensions
        width, height = self.get_aspect_ratio_dimensions(project.aspect_ratio)

        # Collect references
        ref_images, ref_weights = self.collect_reference_images(shot, project)

        # Generate
        from prompt_generator import generate_negative_prompt
        from templates import get_template
        template = get_template(shot.template)
        negative_prompt = generate_negative_prompt(template) if template else ""

        success, image_bytes, error = self.client.generate_with_reference(
            prompt=prompt,
            reference_images=ref_images,
            reference_weights=ref_weights,
            negative_prompt=negative_prompt,
            width=width,
            height=height
        )

        generation_time = time.time() - start_time

        if success and image_bytes:
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shot_{shot.shot_number:03d}_{timestamp}.png"
            output_path = self.output_dir / project.name / filename

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_bytes)

            return GenerationResult(
                success=True,
                image_path=str(output_path),
                consistency_score=0.9,  # TODO: Implement actual scoring
                generation_time=generation_time
            )
        else:
            return GenerationResult(
                success=False,
                error_message=error,
                generation_time=generation_time
            )

    def generate_all_shots(
        self,
        project: StoryboardProject,
        prompts: Dict[int, str],
        progress_callback=None
    ) -> List[GenerationResult]:
        """Generate images for all shots in project"""
        results = []

        for i, shot in enumerate(project.shots):
            if progress_callback:
                progress_callback(i, len(project.shots), f"Generating shot {shot.shot_number}...")

            prompt = prompts.get(shot.shot_number, shot.generated_prompt)
            result = self.generate_shot(shot, project, prompt)
            results.append(result)

            if result.success:
                shot.output_image = result.image_path
                shot.consistency_score = result.consistency_score

        return results


class ComfyUIImageGenerator:
    """Image generator using local ComfyUI"""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self._initialized = False
        self._project_seed = None  # Cached seed for consistency

    def _ensure_client(self):
        """Ensure ComfyUI client is initialized"""
        if self._initialized:
            return

        try:
            from comfyui_client import create_comfyui_client_from_settings
            self.client = create_comfyui_client_from_settings()
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ComfyUI client: {e}")

    def get_aspect_ratio_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """Get pixel dimensions for aspect ratio"""
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
        """Get seed for generation, using locked seed if enabled"""
        import time

        if project.lock_seed:
            # Use locked seed
            if project.generation_seed > 0:
                return project.generation_seed
            else:
                # Generate and cache a seed for this session
                if self._project_seed is None:
                    self._project_seed = int(time.time() * 1000) % (2**32)
                return self._project_seed
        else:
            # Random seed for each shot
            return -1

    def generate_shot(
        self,
        shot: Shot,
        project: StoryboardProject,
        prompt: str
    ) -> GenerationResult:
        """Generate image using ComfyUI"""
        import time
        start_time = time.time()

        try:
            self._ensure_client()

            if not self.client.is_enabled():
                return GenerationResult(
                    success=False,
                    error_message="ComfyUI is not enabled. Set IMAGE_BACKEND=comfyui and COMFYUI_ENABLED=true in .env"
                )

            # Test connection
            connected, msg = self.client.test_connection()
            if not connected:
                return GenerationResult(
                    success=False,
                    error_message=f"ComfyUI connection failed: {msg}"
                )

            from comfyui_client import GenerationParams

            # Get dimensions
            width, height = self.get_aspect_ratio_dimensions(project.aspect_ratio)

            # Generate negative prompt
            from prompt_generator import generate_negative_prompt
            from templates import get_template
            template = get_template(shot.template)
            negative_prompt = generate_negative_prompt(template) if template else "low quality, blurry, deformed"

            # Add consistency prefix to prompt for style/character consistency
            consistency_prefix = project.get_consistency_prefix()
            if consistency_prefix:
                prompt = f"{consistency_prefix} {prompt}"

            # Get seed (locked or random)
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

            # Use reference image if available (img2img)
            ref_images = []
            for char_id in shot.characters_in_shot:
                char = project.get_character_by_id(char_id)
                if char and char.ref_images:
                    for ref_img in char.ref_images[:1]:  # Use first ref image
                        if os.path.exists(ref_img):
                            ref_images.append(ref_img)
                            break

            # Prepare output directory
            project_output = self.output_dir / project.name
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
                    error_message=result.error or "Unknown ComfyUI error",
                    generation_time=generation_time
                )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=f"ComfyUI generation failed: {str(e)}",
                generation_time=time.time() - start_time
            )


class MockImageGenerator:
    """Mock generator for testing without API"""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_shot(
        self,
        shot: Shot,
        project: StoryboardProject,
        prompt: str
    ) -> GenerationResult:
        """Generate placeholder image for testing"""
        import time
        from PIL import Image, ImageDraw, ImageFont

        time.sleep(0.3)  # Simulate generation time

        # Create placeholder image path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shot_{shot.shot_number:03d}_{timestamp}_mock.png"
        output_path = self.output_dir / project.name / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create actual placeholder image
        try:
            # Determine image size based on aspect ratio
            aspect = getattr(project, 'aspect_ratio', '16:9')
            if aspect == '9:16':
                width, height = 576, 1024
            elif aspect == '1:1':
                width, height = 768, 768
            else:  # 16:9 default
                width, height = 1024, 576

            # Create gradient background
            img = Image.new('RGB', (width, height), '#1a1a2e')
            draw = ImageDraw.Draw(img)

            # Draw gradient-like effect
            for y in range(height):
                r = int(26 + (y / height) * 20)
                g = int(26 + (y / height) * 10)
                b = int(46 + (y / height) * 30)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Draw border
            draw.rectangle([10, 10, width-10, height-10], outline='#4ecdc4', width=2)

            # Draw text
            template_name = shot.template.value if hasattr(shot, 'template') and shot.template else 'T4_standard_medium'
            camera_dist = shot.camera.distance if hasattr(shot, 'camera') and shot.camera else 'medium'
            text_lines = [
                f"Shot {shot.shot_number}",
                f"[Mock Image]",
                "",
                f"Template: {template_name}",
                f"Camera: {camera_dist}",
            ]

            y_offset = height // 3
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill='#4ecdc4')
                y_offset += 25

            # Save image
            img.save(str(output_path), 'PNG')

            return GenerationResult(
                success=True,
                image_path=str(output_path),
                consistency_score=0.85,
                generation_time=0.3
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=f"Mock generation failed: {str(e)}",
                generation_time=0.1
            )


def create_generator(api_key: str = "", output_dir: str = "outputs", backend: str = None):
    """
    Factory function to create appropriate generator

    Args:
        api_key: API key for NanaBanana (only used if backend="api")
        output_dir: Directory for generated images
        backend: Generation backend ("api", "comfyui", "mock", or None to use settings)

    Returns:
        ImageGenerator, ComfyUIImageGenerator, or MockImageGenerator
    """
    # Get backend from settings if not specified
    if backend is None:
        try:
            from settings import settings
            backend = settings.image_backend
        except ImportError:
            backend = "api" if api_key else "mock"

    backend = backend.lower()

    if backend == "comfyui":
        return ComfyUIImageGenerator(output_dir)
    elif backend == "mock":
        return MockImageGenerator(output_dir)
    elif backend == "api":
        if api_key:
            return ImageGenerator(api_key, output_dir)
        else:
            print("[WARNING] API backend selected but no API key provided. Using mock generator.")
            return MockImageGenerator(output_dir)
    else:
        # Unknown backend, try API first
        if api_key:
            return ImageGenerator(api_key, output_dir)
        return MockImageGenerator(output_dir)
