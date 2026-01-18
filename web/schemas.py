"""
API 数据模型 - Pydantic schemas
用于请求验证和响应序列化
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ========================================
# 枚举类型
# ========================================

class StyleType(str, Enum):
    CINEMATIC = "电影感"
    ANIME = "动漫风"
    COMIC = "漫画风"
    REALISTIC = "写实风"
    WATERCOLOR = "水彩画"


class AspectRatio(str, Enum):
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_4_3 = "4:3"
    RATIO_1_1 = "1:1"


class ShotTemplateType(str, Enum):
    WIDE = "全景"
    MEDIUM = "中景"
    CLOSEUP = "特写"
    OVER_SHOULDER = "过肩"
    LOW_ANGLE = "低角度"
    FOLLOWING = "跟随"


class ExportFormat(str, Enum):
    JSON = "json"
    ZIP = "zip"
    TXT = "txt"
    FULL = "full"


# ========================================
# 基础响应模型
# ========================================

class BaseResponse(BaseModel):
    """基础响应"""
    success: bool
    message: str


class DataResponse(BaseResponse):
    """带数据的响应"""
    data: Optional[Dict[str, Any]] = None


# ========================================
# 项目相关模型
# ========================================

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.RATIO_16_9, description="画面比例")


class ProjectStyleUpdate(BaseModel):
    """更新项目风格"""
    style: StyleType


class CharacterInfo(BaseModel):
    """角色信息"""
    id: str
    name: str
    description: str
    ref_images: List[str] = []
    ref_image_count: int = 0


class SceneInfo(BaseModel):
    """场景信息"""
    id: str
    name: str
    description: str


class ShotInfo(BaseModel):
    """镜头信息"""
    id: str
    shot_number: int
    template: str
    description: str
    characters: List[str] = []
    scene_id: str = ""
    scene: str = ""
    status: str = "pending"
    output_image: Optional[str] = None
    generated_prompt: Optional[str] = None


class ProjectStats(BaseModel):
    """项目统计"""
    character_count: int
    scene_count: int
    shot_count: int
    completed_count: int


class ProjectInfo(BaseModel):
    """项目完整信息"""
    id: str
    name: str
    aspect_ratio: str
    characters: List[CharacterInfo] = []
    scenes: List[SceneInfo] = []
    shots: List[ShotInfo] = []
    stats: ProjectStats


class ProjectResponse(BaseResponse):
    """项目响应"""
    project: Optional[ProjectInfo] = None


# ========================================
# 角色相关模型
# ========================================

class CharacterCreate(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    description: str = Field(default="", max_length=500, description="角色描述")
    ref_images: List[str] = Field(default=[], description="参考图片路径列表")


class CharacterDelete(BaseModel):
    """删除角色请求"""
    character_id: str = Field(..., description="角色ID或名称")


class CharacterResponse(BaseResponse):
    """角色响应"""
    character: Optional[CharacterInfo] = None


class CharacterListResponse(BaseResponse):
    """角色列表响应"""
    characters: List[CharacterInfo] = []


# ========================================
# 场景相关模型
# ========================================

class SceneCreate(BaseModel):
    """创建场景请求"""
    name: str = Field(..., min_length=1, max_length=50, description="场景名称")
    description: str = Field(default="", max_length=500, description="场景描述")
    ref_image: str = Field(default="", description="参考图片路径")


class SceneDelete(BaseModel):
    """删除场景请求"""
    scene_id: str = Field(..., description="场景ID或名称")


class SceneResponse(BaseResponse):
    """场景响应"""
    scene: Optional[SceneInfo] = None


class SceneListResponse(BaseResponse):
    """场景列表响应"""
    scenes: List[SceneInfo] = []


# ========================================
# 镜头相关模型
# ========================================

class ShotCreate(BaseModel):
    """创建镜头请求"""
    template: ShotTemplateType = Field(default=ShotTemplateType.MEDIUM, description="镜头类型")
    description: str = Field(..., min_length=1, max_length=500, description="镜头描述")
    character_ids: List[str] = Field(default=[], description="出镜角色ID列表")
    scene_id: str = Field(default="", description="场景ID")


class ShotDelete(BaseModel):
    """删除镜头请求"""
    shot_number: int = Field(..., ge=1, description="镜头编号")


class ShotMove(BaseModel):
    """移动镜头请求"""
    shot_number: int = Field(..., ge=1, description="镜头编号")
    direction: str = Field(..., pattern="^(up|down)$", description="移动方向")


class ShotResponse(BaseResponse):
    """镜头响应"""
    shot: Optional[ShotInfo] = None


class ShotListResponse(BaseResponse):
    """镜头列表响应"""
    shots: List[ShotInfo] = []


# ========================================
# 生成相关模型
# ========================================

class GenerateShotRequest(BaseModel):
    """生成单镜头请求"""
    shot_number: int = Field(..., ge=1, description="镜头编号")
    custom_prompt: str = Field(default="", description="自定义提示词")


class GenerationResult(BaseModel):
    """单镜头生成结果"""
    shot_number: int
    success: bool
    image_path: Optional[str] = None
    error: Optional[str] = None


class GenerateShotResponse(BaseResponse):
    """生成镜头响应"""
    image_path: Optional[str] = None
    consistency_score: Optional[float] = None


class GenerateAllResponse(BaseResponse):
    """批量生成响应"""
    results: List[GenerationResult] = []


# ========================================
# 导入导出相关模型
# ========================================

class SmartImportRequest(BaseModel):
    """智能导入请求"""
    filepath: str = Field(..., description="文件路径")
    use_claude: bool = Field(default=True, description="是否使用Claude分析")


class SmartImportResponse(BaseResponse):
    """智能导入响应"""
    file_type: str = ""
    raw_content: str = ""
    analyzed_json: str = ""


class ApplyImportRequest(BaseModel):
    """应用导入请求"""
    json_content: str = Field(..., description="JSON内容")


class ExportRequest(BaseModel):
    """导出请求"""
    format: ExportFormat = Field(default=ExportFormat.JSON, description="导出格式")


class ExportResponse(BaseResponse):
    """导出响应"""
    filepath: Optional[str] = None


# ========================================
# 示例故事模型
# ========================================

class ExampleStoryInfo(BaseModel):
    """示例故事信息"""
    name: str
    description: str
    character_count: int
    scene_count: int
    shot_count: int


class ExampleStoryListResponse(BaseResponse):
    """示例故事列表响应"""
    examples: List[ExampleStoryInfo] = []


class LoadExampleRequest(BaseModel):
    """加载示例请求"""
    story_name: str = Field(..., description="示例故事名称")


# ========================================
# 文件上传模型
# ========================================

class FileUploadResponse(BaseResponse):
    """文件上传响应"""
    filepath: str = ""
    filename: str = ""
    file_type: str = ""
