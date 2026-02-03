"""
AI Storyboard Pro v2.2 - 统一配置管理

支持两种图像生成后端:
1. 苍何 API (Canghe API) - 云端生成
2. ComfyUI - 本地生成
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field


def _load_dotenv():
    """加载 .env 文件"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith("#"):
                        continue
                    # 解析 key=value
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # 移除引号
                        if value and value[0] in ('"', "'") and value[-1] == value[0]:
                            value = value[1:-1]
                        # 仅当环境变量不存在时设置
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            print(f"警告: 加载 .env 文件失败: {e}")


# 模块导入时加载 .env
_load_dotenv()


@dataclass
class Settings:
    """应用配置 - 从环境变量加载"""

    # ===========================================
    # 苍何 API 配置
    # ===========================================
    api_key: str = field(default_factory=lambda: os.environ.get(
        "CANGHE_API_KEY", ""
    ))
    api_base_url: str = field(default_factory=lambda: os.environ.get(
        "CANGHE_API_BASE_URL", "https://api.canghe.ai"
    ))

    # ===========================================
    # 图像生成后端
    # ===========================================
    # 选项: "canghe" (苍何云端), "comfyui" (本地 ComfyUI)
    image_backend: str = field(default_factory=lambda: os.environ.get(
        "IMAGE_BACKEND", "canghe"
    ).lower())

    # ===========================================
    # 服务器配置
    # ===========================================
    gradio_port: int = field(default_factory=lambda: int(os.environ.get(
        "GRADIO_PORT", "7861"
    )))
    gradio_host: str = field(default_factory=lambda: os.environ.get(
        "GRADIO_HOST", "0.0.0.0"
    ))
    api_port: int = field(default_factory=lambda: int(os.environ.get(
        "API_PORT", "8000"
    )))
    api_host: str = field(default_factory=lambda: os.environ.get(
        "API_HOST", "0.0.0.0"
    ))

    # ===========================================
    # CORS 配置
    # ===========================================
    cors_origins: List[str] = field(default_factory=lambda: [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ])

    # ===========================================
    # 文件上传配置
    # ===========================================
    max_upload_size_mb: int = field(default_factory=lambda: int(os.environ.get(
        "MAX_UPLOAD_SIZE_MB", "50"
    )))
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ext.strip().lower()
        for ext in os.environ.get(
            "ALLOWED_EXTENSIONS",
            ".pdf,.docx,.doc,.md,.markdown,.html,.htm,.txt,.jpg,.jpeg,.png"
        ).split(",")
        if ext.strip()
    ])

    # ===========================================
    # ComfyUI 配置
    # ===========================================
    comfyui_enabled: bool = field(default_factory=lambda: os.environ.get(
        "COMFYUI_ENABLED", "false"
    ).lower() in ("true", "1", "yes"))

    comfyui_host: Optional[str] = field(default_factory=lambda: os.environ.get(
        "COMFYUI_HOST", "127.0.0.1"
    ))
    comfyui_port: Optional[int] = field(default_factory=lambda: int(os.environ.get(
        "COMFYUI_PORT", "8188"
    )))
    comfyui_workflow_dir: Optional[str] = field(default_factory=lambda: os.environ.get(
        "COMFYUI_WORKFLOW_DIR"
    ))
    comfyui_workflow_file: Optional[str] = field(default_factory=lambda: os.environ.get(
        "COMFYUI_WORKFLOW_FILE"
    ))
    comfyui_model: str = field(default_factory=lambda: os.environ.get(
        "COMFYUI_MODEL", ""
    ))

    # ===========================================
    # Ollama 配置 (可选)
    # ===========================================
    ollama_host: str = field(default_factory=lambda: os.environ.get(
        "OLLAMA_HOST", "localhost"
    ))
    ollama_port: int = field(default_factory=lambda: int(os.environ.get(
        "OLLAMA_PORT", "11434"
    )))

    # ===========================================
    # 调试模式
    # ===========================================
    debug: bool = field(default_factory=lambda: os.environ.get(
        "DEBUG", "false"
    ).lower() in ("true", "1", "yes"))

    # ===========================================
    # 目录路径
    # ===========================================
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.resolve())

    @property
    def assets_dir(self) -> Path:
        return self.base_dir / "assets"

    @property
    def projects_dir(self) -> Path:
        return self.base_dir / "projects"

    @property
    def outputs_dir(self) -> Path:
        return self.base_dir / "outputs"

    @property
    def exports_dir(self) -> Path:
        return self.base_dir / "exports"

    @property
    def examples_dir(self) -> Path:
        return self.base_dir / "examples"

    @property
    def uploads_dir(self) -> Path:
        return self.base_dir / "uploads"

    @property
    def comfyui_workflows_dir(self) -> Optional[Path]:
        """ComfyUI 工作流目录"""
        if self.comfyui_workflow_dir:
            path = Path(self.comfyui_workflow_dir)
            if path.is_absolute():
                return path
            return self.base_dir / path
        return None

    @property
    def max_upload_size_bytes(self) -> int:
        """最大上传大小(字节)"""
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """创建所有必需的目录"""
        directories = [
            self.assets_dir,
            self.projects_dir,
            self.outputs_dir,
            self.exports_dir,
            self.examples_dir,
            self.uploads_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # 创建资产子目录
        for subdir in ["characters", "scenes", "props", "styles"]:
            (self.assets_dir / subdir).mkdir(exist_ok=True)

    def validate(self, strict: bool = False) -> List[str]:
        """
        验证配置

        Args:
            strict: 严格模式 - 将警告视为错误

        Returns:
            错误消息列表 (空表示验证通过)
        """
        errors = []

        # 检查 API 密钥
        if self.image_backend == "canghe":
            if not self.api_key or self.api_key == "your_api_key_here":
                if strict:
                    errors.append("CANGHE_API_KEY 未配置 - 图像生成将无法使用")
                else:
                    print("\n[警告] 苍何 API 密钥未配置 - 图像生成将无法使用")
                    print("       请在 .env 中设置 CANGHE_API_KEY\n")

        # 检查 ComfyUI 配置
        if self.image_backend == "comfyui":
            if not self.comfyui_enabled:
                if strict:
                    errors.append("IMAGE_BACKEND=comfyui 但 COMFYUI_ENABLED=false")
                else:
                    print("\n[警告] IMAGE_BACKEND=comfyui 但 COMFYUI_ENABLED=false")
                    print("       请在 .env 中设置 COMFYUI_ENABLED=true\n")

        # 验证端口
        if not (1 <= self.gradio_port <= 65535):
            errors.append(f"GRADIO_PORT 必须在 1-65535 之间 (当前: {self.gradio_port})")
        if not (1 <= self.api_port <= 65535):
            errors.append(f"API_PORT 必须在 1-65535 之间 (当前: {self.api_port})")

        # 验证上传大小
        if self.max_upload_size_mb <= 0:
            errors.append(f"MAX_UPLOAD_SIZE_MB 必须为正数 (当前: {self.max_upload_size_mb})")

        return errors

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return len(self.validate()) == 0

    def print_config(self, show_secrets: bool = False) -> None:
        """打印当前配置"""
        print("\n" + "=" * 50)
        print("AI Storyboard Pro v2.2 - 配置信息")
        print("=" * 50)

        # 图像后端
        print(f"\n图像生成后端: {self.image_backend.upper()}")

        # API 配置 (苍何)
        if self.image_backend == "canghe":
            api_key_display = "***" + self.api_key[-8:] if self.api_key and len(self.api_key) > 8 else "未设置"
            if show_secrets:
                api_key_display = self.api_key or "未设置"
            print(f"苍何 API Key: {api_key_display}")
            print(f"苍何 API URL: {self.api_base_url}")

        # ComfyUI 配置
        if self.image_backend == "comfyui":
            print(f"ComfyUI 启用: {self.comfyui_enabled}")
            print(f"ComfyUI 地址: {self.comfyui_host}:{self.comfyui_port}")

        # 服务器
        print(f"\nGradio 服务: {self.gradio_host}:{self.gradio_port}")
        print(f"API 服务: {self.api_host}:{self.api_port}")

        # CORS
        print(f"\nCORS 源: {', '.join(self.cors_origins)}")

        # 上传
        print(f"\n最大上传: {self.max_upload_size_mb} MB")
        print(f"允许扩展名: {', '.join(self.allowed_extensions)}")

        # 调试
        print(f"\n调试模式: {self.debug}")
        print("=" * 50 + "\n")


# 全局设置单例
settings = Settings()


def get_settings() -> Settings:
    """获取全局设置实例"""
    return settings


def reload_settings() -> Settings:
    """重新加载设置"""
    global settings
    _load_dotenv()
    settings = Settings()
    return settings


def needs_setup() -> bool:
    """检查是否需要运行设置向导"""
    env_path = Path(__file__).parent / ".env"
    return not env_path.exists()
