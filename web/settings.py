"""
AI Storyboard Pro - Unified Configuration Settings

This module provides centralized configuration management,
loading settings from environment variables with sensible defaults.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field


def _load_dotenv():
    """Load .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue
                    # Parse key=value
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value and value[0] in ('"', "'") and value[-1] == value[0]:
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")


# Load .env file on module import
_load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # ===========================================
    # API Configuration
    # ===========================================
    api_key: str = field(default_factory=lambda: os.environ.get(
        "NANA_BANANA_API_KEY", ""
    ))
    api_base_url: str = field(default_factory=lambda: os.environ.get(
        "NANA_BANANA_BASE_URL", "https://api.nanabanana.pro"
    ))

    # ===========================================
    # Image Generation Backend
    # ===========================================
    # Options: "api" (NanaBanana API), "comfyui" (Local ComfyUI), "mock" (Testing)
    image_backend: str = field(default_factory=lambda: os.environ.get(
        "IMAGE_BACKEND", "api"
    ).lower())

    # ===========================================
    # Server Configuration
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
    # CORS Configuration
    # ===========================================
    cors_origins: List[str] = field(default_factory=lambda: [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ])

    # ===========================================
    # File Upload Configuration
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
    # Optional: ComfyUI Configuration
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
    ))  # Direct path to a workflow JSON file
    comfyui_model: str = field(default_factory=lambda: os.environ.get(
        "COMFYUI_MODEL", ""
    ))  # Empty = auto-detect first available model

    # ===========================================
    # Optional: Ollama Configuration
    # ===========================================
    ollama_host: str = field(default_factory=lambda: os.environ.get(
        "OLLAMA_HOST", "localhost"
    ))
    ollama_port: int = field(default_factory=lambda: int(os.environ.get(
        "OLLAMA_PORT", "11434"
    )))

    # ===========================================
    # Debug/Development
    # ===========================================
    debug: bool = field(default_factory=lambda: os.environ.get(
        "DEBUG", "false"
    ).lower() in ("true", "1", "yes"))

    # ===========================================
    # Directory Paths
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
        """ComfyUI workflow JSON directory."""
        if self.comfyui_workflow_dir:
            path = Path(self.comfyui_workflow_dir)
            if path.is_absolute():
                return path
            return self.base_dir / path
        return None

    @property
    def max_upload_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
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

        # Create asset subdirectories
        for subdir in ["characters", "scenes", "props", "styles"]:
            (self.assets_dir / subdir).mkdir(exist_ok=True)

    def validate(self, strict: bool = False) -> List[str]:
        """
        Validate configuration and return list of errors.

        Args:
            strict: If True, treat warnings as errors (e.g., missing API key)

        Returns:
            List of error messages (empty if all valid)
        """
        errors = []

        # Check API key - warning only unless strict mode
        if not self.api_key or self.api_key == "your_api_key_here":
            if strict:
                errors.append("NANA_BANANA_API_KEY is required for image generation")
            else:
                # Just print a warning, don't block startup
                print("\n[WARNING] API key not configured - image generation will not work")
                print("          Run 'python setup_wizard.py' to configure\n")

        # Validate ports
        if not (1 <= self.gradio_port <= 65535):
            errors.append(f"GRADIO_PORT must be between 1 and 65535 (got {self.gradio_port})")
        if not (1 <= self.api_port <= 65535):
            errors.append(f"API_PORT must be between 1 and 65535 (got {self.api_port})")

        # Validate upload size
        if self.max_upload_size_mb <= 0:
            errors.append(f"MAX_UPLOAD_SIZE_MB must be positive (got {self.max_upload_size_mb})")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0

    def print_config(self, show_secrets: bool = False) -> None:
        """Print current configuration for debugging."""
        print("\n" + "=" * 50)
        print("AI Storyboard Pro - Configuration")
        print("=" * 50)

        # API
        api_key_display = "***" + self.api_key[-8:] if self.api_key and len(self.api_key) > 8 else "NOT SET"
        if show_secrets:
            api_key_display = self.api_key or "NOT SET"
        print(f"API Key: {api_key_display}")
        print(f"API Base URL: {self.api_base_url}")

        # Server
        print(f"\nGradio Server: {self.gradio_host}:{self.gradio_port}")
        print(f"API Server: {self.api_host}:{self.api_port}")

        # CORS
        print(f"\nCORS Origins: {', '.join(self.cors_origins)}")

        # Upload
        print(f"\nMax Upload Size: {self.max_upload_size_mb} MB")
        print(f"Allowed Extensions: {', '.join(self.allowed_extensions)}")

        # Optional services
        if self.comfyui_host:
            print(f"\nComfyUI: {self.comfyui_host}:{self.comfyui_port}")
        print(f"Ollama: {self.ollama_host}:{self.ollama_port}")

        # Debug
        print(f"\nDebug Mode: {self.debug}")
        print("=" * 50 + "\n")


# Global settings singleton
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful after .env changes)."""
    global settings
    _load_dotenv()
    settings = Settings()
    return settings


# Convenience function to check if setup is needed
def needs_setup() -> bool:
    """Check if the setup wizard should be run (only if no .env exists)."""
    env_path = Path(__file__).parent / ".env"

    # No .env file exists - need first-time setup
    if not env_path.exists():
        return True

    # .env exists - allow startup even with placeholder key
    # User will see a warning but can still use the UI
    return False
