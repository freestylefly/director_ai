"""
AI Storyboard Pro - Configuration

This module provides backwards compatibility with the old config structure.
New code should import from settings.py instead.
"""

from settings import settings, get_settings

# API Configuration - now loaded from settings
NANA_BANANA_API_KEY = settings.api_key
NANA_BANANA_BASE_URL = settings.api_base_url

# Paths - now loaded from settings
BASE_DIR = settings.base_dir
ASSETS_DIR = settings.assets_dir
PROJECTS_DIR = settings.projects_dir
OUTPUTS_DIR = settings.outputs_dir

# Ensure directories exist
settings.ensure_directories()

# Sub-directories for assets
ASSETS_SUBDIRS = ["characters", "scenes", "props", "styles"]

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7860

# Image Generation Defaults
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 576
DEFAULT_STEPS = 30
DEFAULT_GUIDANCE = 7.5

# Aspect Ratio Presets
ASPECT_RATIOS = {
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "1:1": (768, 768),
    "4:3": (896, 672),
    "3:4": (672, 896),
    "21:9": (1024, 440)
}

# Style Presets
STYLE_PRESETS = {
    "Cinematic": {
        "render_type": "realistic",
        "color_tone": "neutral",
        "lighting_style": "cinematic",
        "texture": "film_grain",
        "description": "Cinematic film look with natural lighting and subtle grain"
    },
    "Anime": {
        "render_type": "anime",
        "color_tone": "high_saturation",
        "lighting_style": "natural",
        "texture": "digital_clean",
        "description": "Japanese anime style with vibrant colors"
    },
    "Comic": {
        "render_type": "comic",
        "color_tone": "high_saturation",
        "lighting_style": "studio",
        "texture": "digital_clean",
        "description": "Western comic book style"
    },
    "Watercolor": {
        "render_type": "watercolor",
        "color_tone": "low_saturation",
        "lighting_style": "natural",
        "texture": "noise",
        "description": "Soft watercolor painting aesthetic"
    },
    "3D Render": {
        "render_type": "3d_render",
        "color_tone": "neutral",
        "lighting_style": "studio",
        "texture": "digital_clean",
        "description": "Clean 3D rendered look"
    },
    "Realistic": {
        "render_type": "realistic",
        "color_tone": "neutral",
        "lighting_style": "natural",
        "texture": "digital_clean",
        "description": "Photorealistic rendering"
    }
}
