"""
ComfyUI API Client - Local ComfyUI Integration
Support for text-to-image, image-to-image with reference images
All prompts in Chinese
"""

import os
import json
import uuid
import time
import base64
import requests
import websocket
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class ComfyUIConfig:
    """ComfyUI configuration"""
    host: str = "127.0.0.1"
    port: int = 8188
    use_https: bool = False
    timeout: int = 300  # seconds
    workflow_dir: Optional[str] = None  # Directory for custom workflow JSON files
    workflow_file: Optional[str] = None  # Direct path to a workflow JSON file
    enabled: bool = True  # Whether ComfyUI integration is enabled
    model: str = ""  # Default model name (empty = auto-detect)

    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        protocol = "wss" if self.use_https else "ws"
        return f"{protocol}://{self.host}:{self.port}/ws"

    @classmethod
    def from_settings(cls) -> 'ComfyUIConfig':
        """Create config from settings module"""
        try:
            from settings import settings
            # Get workflow file path
            workflow_file = None
            if settings.comfyui_workflow_file:
                wf_path = Path(settings.comfyui_workflow_file)
                if wf_path.is_absolute():
                    workflow_file = str(wf_path)
                else:
                    workflow_file = str(settings.base_dir / settings.comfyui_workflow_file)

            return cls(
                host=settings.comfyui_host or "127.0.0.1",
                port=settings.comfyui_port or 8188,
                workflow_dir=str(settings.comfyui_workflows_dir) if settings.comfyui_workflows_dir else None,
                workflow_file=workflow_file,
                enabled=settings.comfyui_enabled,
                model=settings.comfyui_model or ""
            )
        except ImportError:
            return cls()


@dataclass
class GenerationParams:
    """Image generation parameters"""
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 576
    steps: int = 20
    cfg_scale: float = 7.0
    sampler: str = "euler"
    scheduler: str = "normal"
    seed: int = -1  # -1 for random
    denoise: float = 1.0  # For img2img

    # Reference image settings
    ref_image_path: str = ""
    ref_strength: float = 0.75  # For img2img


@dataclass
class GenerationResult:
    """Result of image generation"""
    success: bool = False
    images: List[str] = field(default_factory=list)  # List of image paths
    error: str = ""
    prompt_id: str = ""
    generation_time: float = 0.0


class ComfyUIClient:
    """
    ComfyUI API Client
    Supports text-to-image and image-to-image generation
    """

    # Default workflow for text-to-image
    DEFAULT_TXT2IMG_WORKFLOW = {
        "3": {
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": 1024,
                "height": 576,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    # Default workflow for image-to-image
    DEFAULT_IMG2IMG_WORKFLOW = {
        "1": {
            "inputs": {
                "image": "",
                "upload": "image"
            },
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEEncode"
        },
        "3": {
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 0.75,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["2", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "6": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    def __init__(self, config: Optional[ComfyUIConfig] = None):
        self.config = config or ComfyUIConfig()
        self.client_id = str(uuid.uuid4())
        self.custom_workflow: Optional[Dict] = None
        self._workflow_cache: Dict[str, Dict] = {}  # Cache loaded workflows
        self._available_models: Optional[List[str]] = None
        self._default_model: Optional[str] = None

        # Auto-load workflow file if configured
        if self.config.workflow_file:
            self._load_configured_workflow()

    def _load_configured_workflow(self):
        """Load the configured workflow file"""
        if not self.config.workflow_file:
            return

        workflow_path = Path(self.config.workflow_file)
        if workflow_path.exists():
            try:
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    self.custom_workflow = json.load(f)
                print(f"[ComfyUI] Loaded custom workflow: {workflow_path.name}")
            except Exception as e:
                print(f"[ComfyUI] Failed to load workflow: {e}")

    def is_enabled(self) -> bool:
        """Check if ComfyUI integration is enabled"""
        return self.config.enabled

    def has_custom_workflow(self) -> bool:
        """Check if a custom workflow is loaded"""
        return self.custom_workflow is not None

    def get_default_model(self) -> str:
        """Get the default model to use (from config or auto-detect)"""
        # Use configured model if specified
        if self.config.model:
            return self.config.model

        # Auto-detect first available model
        if self._default_model is None:
            models = self.get_models()
            if models:
                self._default_model = models[0]
                print(f"[ComfyUI] Auto-detected model: {self._default_model}")
            else:
                self._default_model = ""

        return self._default_model

    def list_workflows(self) -> List[str]:
        """List available workflow JSON files in the workflow directory"""
        if not self.config.workflow_dir:
            return []

        workflow_path = Path(self.config.workflow_dir)
        if not workflow_path.exists():
            return []

        workflows = []
        for f in workflow_path.glob("*.json"):
            workflows.append(f.stem)  # Return name without .json extension
        return sorted(workflows)

    def load_workflow(self, name: str) -> Tuple[bool, str]:
        """
        Load a workflow by name from the workflow directory

        Args:
            name: Workflow name (without .json extension)

        Returns:
            (success, message or error)
        """
        if not self.config.workflow_dir:
            return False, "Workflow directory not configured"

        workflow_path = Path(self.config.workflow_dir) / f"{name}.json"
        if not workflow_path.exists():
            return False, f"Workflow not found: {name}"

        return self.load_workflow_from_file(str(workflow_path))

    def get_workflow(self, name: str) -> Optional[Dict]:
        """
        Get a workflow by name (with caching)

        Args:
            name: Workflow name (without .json extension)

        Returns:
            Workflow dict or None
        """
        if name in self._workflow_cache:
            return self._workflow_cache[name]

        if not self.config.workflow_dir:
            return None

        workflow_path = Path(self.config.workflow_dir) / f"{name}.json"
        if not workflow_path.exists():
            return None

        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            self._workflow_cache[name] = workflow
            return workflow
        except Exception:
            return None

    def clear_workflow_cache(self):
        """Clear the workflow cache"""
        self._workflow_cache.clear()

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to ComfyUI server
        Returns: (success, message)
        """
        try:
            response = requests.get(
                f"{self.config.base_url}/system_stats",
                timeout=5
            )
            if response.status_code == 200:
                stats = response.json()
                return True, f"ComfyUI connected. GPU: {stats.get('devices', [{}])[0].get('name', 'Unknown')}"
            else:
                return False, f"Connection failed: HTTP {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to {self.config.base_url}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_models(self) -> List[str]:
        """Get available checkpoint models"""
        try:
            response = requests.get(
                f"{self.config.base_url}/object_info/CheckpointLoaderSimple",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            return []
        except:
            return []

    def upload_image(self, image_path: str, subfolder: str = "") -> Tuple[bool, str]:
        """
        Upload image to ComfyUI
        Returns: (success, filename or error)
        """
        if not os.path.exists(image_path):
            return False, f"Image not found: {image_path}"

        try:
            with open(image_path, 'rb') as f:
                files = {
                    'image': (os.path.basename(image_path), f, 'image/png')
                }
                data = {}
                if subfolder:
                    data['subfolder'] = subfolder

                response = requests.post(
                    f"{self.config.base_url}/upload/image",
                    files=files,
                    data=data,
                    timeout=30
                )

            if response.status_code == 200:
                result = response.json()
                return True, result.get('name', '')
            else:
                return False, f"Upload failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Upload error: {str(e)}"

    def set_custom_workflow(self, workflow: Dict):
        """Set custom workflow JSON"""
        self.custom_workflow = workflow

    def load_workflow_from_file(self, filepath: str) -> Tuple[bool, str]:
        """Load workflow from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            self.custom_workflow = workflow
            return True, "Workflow loaded successfully"
        except Exception as e:
            return False, f"Failed to load workflow: {str(e)}"

    def _prepare_txt2img_workflow(self, params: GenerationParams, model: str = "") -> Dict:
        """Prepare text-to-image workflow"""
        workflow = json.loads(json.dumps(self.DEFAULT_TXT2IMG_WORKFLOW))

        # Set parameters
        workflow["3"]["inputs"]["seed"] = params.seed if params.seed >= 0 else int(time.time() * 1000) % (2**32)
        workflow["3"]["inputs"]["steps"] = params.steps
        workflow["3"]["inputs"]["cfg"] = params.cfg_scale
        workflow["3"]["inputs"]["sampler_name"] = params.sampler
        workflow["3"]["inputs"]["scheduler"] = params.scheduler

        workflow["5"]["inputs"]["width"] = params.width
        workflow["5"]["inputs"]["height"] = params.height

        workflow["6"]["inputs"]["text"] = params.prompt
        workflow["7"]["inputs"]["text"] = params.negative_prompt

        # Use provided model, or auto-detect
        model_to_use = model or self.get_default_model()
        if model_to_use:
            workflow["4"]["inputs"]["ckpt_name"] = model_to_use

        return workflow

    def _prepare_img2img_workflow(self, params: GenerationParams, uploaded_image: str, model: str = "") -> Dict:
        """Prepare image-to-image workflow"""
        workflow = json.loads(json.dumps(self.DEFAULT_IMG2IMG_WORKFLOW))

        # Set reference image
        workflow["1"]["inputs"]["image"] = uploaded_image

        # Set parameters
        workflow["3"]["inputs"]["seed"] = params.seed if params.seed >= 0 else int(time.time() * 1000) % (2**32)
        workflow["3"]["inputs"]["steps"] = params.steps
        workflow["3"]["inputs"]["cfg"] = params.cfg_scale
        workflow["3"]["inputs"]["sampler_name"] = params.sampler
        workflow["3"]["inputs"]["scheduler"] = params.scheduler
        workflow["3"]["inputs"]["denoise"] = params.denoise

        workflow["6"]["inputs"]["text"] = params.prompt
        workflow["7"]["inputs"]["text"] = params.negative_prompt

        # Use provided model, or auto-detect
        model_to_use = model or self.get_default_model()
        if model_to_use:
            workflow["4"]["inputs"]["ckpt_name"] = model_to_use

        return workflow

    def queue_prompt(self, workflow: Dict) -> Tuple[bool, str]:
        """
        Queue a workflow for execution
        Returns: (success, prompt_id or error)
        """
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }

            response = requests.post(
                f"{self.config.base_url}/prompt",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get('prompt_id', '')
                if prompt_id:
                    return True, prompt_id
                # Check for error in response
                if 'error' in result:
                    return False, f"ComfyUI error: {result['error']}"
                return True, prompt_id
            else:
                # Parse error details from response
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', response.text)
                    node_errors = error_data.get('node_errors', {})
                    if node_errors:
                        for node_id, node_error in node_errors.items():
                            errors = node_error.get('errors', [])
                            if errors:
                                error_msg += f" | Node {node_id}: {errors[0].get('message', '')} - {errors[0].get('details', '')}"
                    return False, f"Queue failed: {error_msg}"
                except:
                    return False, f"Queue failed: HTTP {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Queue error: {str(e)}"

    def wait_for_completion(
        self,
        prompt_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Wait for prompt completion using WebSocket
        Returns: (success, list of output image filenames or error messages)
        """
        try:
            ws = websocket.create_connection(
                f"{self.config.ws_url}?clientId={self.client_id}",
                timeout=self.config.timeout
            )

            output_images = []
            execution_error = None

            while True:
                message = ws.recv()
                if not message:
                    continue

                # Handle binary messages (preview images, etc.)
                if isinstance(message, bytes):
                    # Binary data - skip (usually preview images)
                    continue

                # Parse JSON message
                try:
                    data = json.loads(message)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Skip malformed messages
                    continue

                msg_type = data.get('type', '')

                if msg_type == 'progress':
                    current = data['data'].get('value', 0)
                    total = data['data'].get('max', 100)
                    if progress_callback:
                        progress_callback(current, total)

                elif msg_type == 'executing':
                    node = data['data'].get('node', '')
                    if node is None:  # Execution finished
                        break

                elif msg_type == 'executed':
                    node_output = data['data'].get('output', {})
                    # Handle images
                    images = node_output.get('images', [])
                    for img in images:
                        output_images.append(img.get('filename', ''))
                    # Handle videos (for video generation workflows)
                    videos = node_output.get('videos', [])
                    for vid in videos:
                        output_images.append(vid.get('filename', ''))
                    # Handle gifs
                    gifs = node_output.get('gifs', [])
                    for gif in gifs:
                        output_images.append(gif.get('filename', ''))

                elif msg_type == 'execution_error':
                    # Capture execution errors
                    error_data = data.get('data', {})
                    execution_error = error_data.get('exception_message', 'Unknown execution error')
                    node_id = error_data.get('node_id', 'unknown')
                    node_type = error_data.get('node_type', 'unknown')
                    execution_error = f"Node {node_id} ({node_type}): {execution_error}"
                    break

                elif msg_type == 'execution_cached':
                    # Some nodes were cached, continue
                    pass

            ws.close()

            if execution_error:
                return False, [execution_error]

            if not output_images:
                return False, ["No output files generated"]

            return True, output_images

        except websocket.WebSocketTimeoutException:
            return False, ["Timeout waiting for completion"]
        except Exception as e:
            return False, [f"WebSocket error: {str(e)}"]

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """Download generated image"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            response = requests.get(
                f"{self.config.base_url}/view",
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                return response.content
            return None
        except:
            return None

    def text_to_image(
        self,
        params: GenerationParams,
        model: str = "",
        output_dir: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> GenerationResult:
        """
        Generate image from text prompt

        Args:
            params: Generation parameters including prompt
            model: Checkpoint model name (optional)
            output_dir: Directory to save output images
            progress_callback: Callback for progress updates

        Returns:
            GenerationResult with success status and image paths
        """
        start_time = time.time()
        result = GenerationResult()

        # Use custom workflow if set
        if self.custom_workflow:
            workflow = json.loads(json.dumps(self.custom_workflow))
            # Try to inject parameters into custom workflow
            self._inject_params_to_workflow(workflow, params)
        else:
            workflow = self._prepare_txt2img_workflow(params, model)

        # Queue the prompt
        success, prompt_id = self.queue_prompt(workflow)
        if not success:
            result.error = prompt_id
            return result

        result.prompt_id = prompt_id

        # Wait for completion
        success, output_files = self.wait_for_completion(prompt_id, progress_callback)
        if not success:
            result.error = output_files[0] if output_files else "Unknown error"
            return result

        # Download and save images
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        for filename in output_files:
            if filename:
                image_data = self.get_image(filename)
                if image_data:
                    if output_dir:
                        save_path = os.path.join(output_dir, filename)
                        with open(save_path, 'wb') as f:
                            f.write(image_data)
                        result.images.append(save_path)
                    else:
                        # Return base64 if no output dir
                        result.images.append(base64.b64encode(image_data).decode())

        result.success = len(result.images) > 0
        result.generation_time = time.time() - start_time
        return result

    def image_to_image(
        self,
        params: GenerationParams,
        model: str = "",
        output_dir: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> GenerationResult:
        """
        Generate image from reference image

        Args:
            params: Generation parameters including ref_image_path
            model: Checkpoint model name (optional)
            output_dir: Directory to save output images
            progress_callback: Callback for progress updates

        Returns:
            GenerationResult with success status and image paths
        """
        start_time = time.time()
        result = GenerationResult()

        if not params.ref_image_path:
            result.error = "Reference image path is required"
            return result

        # Upload reference image
        success, uploaded_name = self.upload_image(params.ref_image_path)
        if not success:
            result.error = f"Failed to upload reference image: {uploaded_name}"
            return result

        # Prepare workflow
        workflow = self._prepare_img2img_workflow(params, uploaded_name, model)

        # Queue the prompt
        success, prompt_id = self.queue_prompt(workflow)
        if not success:
            result.error = prompt_id
            return result

        result.prompt_id = prompt_id

        # Wait for completion
        success, output_files = self.wait_for_completion(prompt_id, progress_callback)
        if not success:
            result.error = output_files[0] if output_files else "Unknown error"
            return result

        # Download and save images
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        for filename in output_files:
            if filename:
                image_data = self.get_image(filename)
                if image_data:
                    if output_dir:
                        save_path = os.path.join(output_dir, filename)
                        with open(save_path, 'wb') as f:
                            f.write(image_data)
                        result.images.append(save_path)
                    else:
                        result.images.append(base64.b64encode(image_data).decode())

        result.success = len(result.images) > 0
        result.generation_time = time.time() - start_time
        return result

    def _inject_params_to_workflow(self, workflow: Dict, params: GenerationParams):
        """Try to inject parameters into custom workflow"""
        prompt_injected = False

        for node_id, node in workflow.items():
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # Inject prompt - PrimitiveStringMultiline (Z-Image style)
            if class_type == 'PrimitiveStringMultiline':
                if 'value' in inputs:
                    inputs['value'] = params.prompt
                    prompt_injected = True

            # Inject prompt - CLIPTextEncode (standard style)
            elif class_type == 'CLIPTextEncode':
                if 'text' in inputs:
                    # Only inject if it's a string (not a connection)
                    if isinstance(inputs['text'], str):
                        if inputs['text'] == '' or inputs['text'] == 'positive':
                            inputs['text'] = params.prompt
                            prompt_injected = True
                        elif inputs['text'] == 'negative':
                            inputs['text'] = params.negative_prompt

            # Inject dimensions - EmptyLatentImage (standard)
            elif class_type == 'EmptyLatentImage':
                if 'width' in inputs:
                    inputs['width'] = params.width
                if 'height' in inputs:
                    inputs['height'] = params.height

            # Inject dimensions - EmptySD3LatentImage (SD3/Z-Image style)
            elif class_type == 'EmptySD3LatentImage':
                if 'width' in inputs:
                    inputs['width'] = params.width
                if 'height' in inputs:
                    inputs['height'] = params.height

            # Inject sampler settings - KSampler
            elif class_type == 'KSampler':
                if 'seed' in inputs:
                    inputs['seed'] = params.seed if params.seed >= 0 else int(time.time() * 1000) % (2**32)
                # Note: Don't override steps/cfg if using custom workflow
                # as they may be tuned specifically for that workflow

            # Inject reference image - LoadImage
            elif class_type == 'LoadImage':
                if params.ref_image_path and 'image' in inputs:
                    # Need to upload and set the image name
                    pass  # Handled separately in image_to_image

        return prompt_injected

    def interrupt(self) -> bool:
        """Interrupt current generation"""
        try:
            response = requests.post(
                f"{self.config.base_url}/interrupt",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        try:
            response = requests.get(
                f"{self.config.base_url}/queue",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}


# Helper functions
def create_comfyui_client(host: str = "127.0.0.1", port: int = 8188, workflow_dir: str = None) -> ComfyUIClient:
    """Create ComfyUI client with specified host and port"""
    config = ComfyUIConfig(host=host, port=port, workflow_dir=workflow_dir)
    return ComfyUIClient(config)


def create_comfyui_client_from_settings() -> ComfyUIClient:
    """Create ComfyUI client from settings module"""
    config = ComfyUIConfig.from_settings()
    return ComfyUIClient(config)


# Test function
if __name__ == "__main__":
    client = create_comfyui_client()

    # Test connection
    success, message = client.test_connection()
    print(f"Connection: {success} - {message}")

    if success:
        # Test text-to-image
        params = GenerationParams(
            prompt="beautiful landscape, mountains, sunset, high quality",
            negative_prompt="ugly, blurry, low quality",
            width=1024,
            height=576,
            steps=20
        )

        result = client.text_to_image(params, output_dir="./test_output")
        print(f"Generation: {result.success}")
        if result.success:
            print(f"Images: {result.images}")
        else:
            print(f"Error: {result.error}")
