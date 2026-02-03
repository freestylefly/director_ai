"""
AI Storyboard Pro v2.2 - 配置兼容层

此模块提供与旧配置结构的向后兼容。
新代码应从 settings.py 导入。
"""

from settings import settings, get_settings

# =============================================
# API 配置 - 苍何 API (新)
# =============================================
CANGHE_API_KEY = settings.api_key
CANGHE_API_BASE_URL = settings.api_base_url

# 向后兼容别名 (旧代码可能使用这些名称)
NANA_BANANA_API_KEY = settings.api_key  # 已弃用，使用 CANGHE_API_KEY
NANA_BANANA_BASE_URL = settings.api_base_url  # 已弃用

# =============================================
# 路径配置
# =============================================
BASE_DIR = settings.base_dir
ASSETS_DIR = settings.assets_dir
PROJECTS_DIR = settings.projects_dir
OUTPUTS_DIR = settings.outputs_dir

# 确保目录存在
settings.ensure_directories()

# 资产子目录
ASSETS_SUBDIRS = ["characters", "scenes", "props", "styles"]

# =============================================
# 服务器配置
# =============================================
SERVER_HOST = settings.gradio_host
SERVER_PORT = settings.gradio_port

# =============================================
# 图像生成默认值
# =============================================
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 576
DEFAULT_STEPS = 30
DEFAULT_GUIDANCE = 7.5

# =============================================
# 宽高比预设
# =============================================
ASPECT_RATIOS = {
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "1:1": (768, 768),
    "4:3": (896, 672),
    "3:4": (672, 896),
    "21:9": (1024, 440)
}

# =============================================
# 风格预设
# =============================================
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

# =============================================
# 图像生成后端
# =============================================
IMAGE_BACKEND = settings.image_backend  # "canghe" 或 "comfyui"
