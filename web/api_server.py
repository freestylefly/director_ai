"""
FastAPI Server - RESTful API for AI Storyboard Pro
支持前后端分离架构，可供 Web/Mobile 前端调用
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from schemas import (
    # 基础响应
    BaseResponse, DataResponse,
    # 项目
    ProjectCreate, ProjectStyleUpdate, ProjectInfo, ProjectResponse,
    # 角色
    CharacterCreate, CharacterDelete, CharacterResponse, CharacterListResponse, CharacterInfo,
    # 场景
    SceneCreate, SceneDelete, SceneResponse, SceneListResponse, SceneInfo,
    # 镜头
    ShotCreate, ShotDelete, ShotMove, ShotResponse, ShotListResponse, ShotInfo,
    # 生成
    GenerateShotRequest, GenerateShotResponse, GenerateAllResponse, GenerationResult,
    # 导入导出
    SmartImportRequest, SmartImportResponse, ApplyImportRequest,
    ExportRequest, ExportResponse, ExportFormat,
    # 示例
    ExampleStoryInfo, ExampleStoryListResponse, LoadExampleRequest,
    # 文件
    FileUploadResponse,
    # 枚举
    StyleType, AspectRatio, ShotTemplateType
)

from services import services, Config
from settings import settings


# ========================================
# 应用配置
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    Config.ensure_dirs()
    print("AI Storyboard Pro API Server starting...")
    yield
    # 关闭时
    print("AI Storyboard Pro API Server shutting down...")


app = FastAPI(
    title="AI Storyboard Pro API",
    description="AI 分镜生成系统 RESTful API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 配置 - 从 settings 加载允许的源
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 从配置加载，生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/outputs", StaticFiles(directory=str(Config.OUTPUTS_DIR)), name="outputs")
app.mount("/exports", StaticFiles(directory=str(Config.EXPORTS_DIR)), name="exports")


# ========================================
# 健康检查
# ========================================

@app.get("/", tags=["System"])
async def root():
    """API 根路径"""
    return {
        "name": "AI Storyboard Pro API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# ========================================
# 项目管理 API
# ========================================

@app.post("/api/project", response_model=ProjectResponse, tags=["Project"])
async def create_project(req: ProjectCreate):
    """创建新项目"""
    result = services.project.create_project(req.name, req.aspect_ratio.value)

    project_info = None
    if result.get("project"):
        project_info = _convert_project_info(result["project"])

    return ProjectResponse(
        success=result["success"],
        message=result["message"],
        project=project_info
    )


@app.get("/api/project", response_model=ProjectResponse, tags=["Project"])
async def get_project():
    """获取当前项目信息"""
    info = services.project.get_project_info()
    if info is None:
        return ProjectResponse(success=False, message="尚未创建项目", project=None)

    return ProjectResponse(
        success=True,
        message="获取成功",
        project=_convert_project_info(info)
    )


@app.put("/api/project/style", response_model=BaseResponse, tags=["Project"])
async def update_project_style(req: ProjectStyleUpdate):
    """更新项目风格"""
    result = services.project.set_style(req.style.value)
    return BaseResponse(success=result["success"], message=result["message"])


# ========================================
# 角色管理 API
# ========================================

@app.post("/api/characters", response_model=CharacterResponse, tags=["Characters"])
async def add_character(req: CharacterCreate):
    """添加角色"""
    result = services.character.add_character(req.name, req.description, req.ref_images)

    char_info = None
    if result.get("character"):
        c = result["character"]
        char_info = CharacterInfo(
            id=c["id"],
            name=c["name"],
            description=c["description"],
            ref_images=[],
            ref_image_count=0
        )

    return CharacterResponse(
        success=result["success"],
        message=result["message"],
        character=char_info
    )


@app.delete("/api/characters/{character_id}", response_model=BaseResponse, tags=["Characters"])
async def delete_character(character_id: str):
    """删除角色"""
    result = services.character.delete_character(character_id)
    return BaseResponse(success=result["success"], message=result["message"])


@app.get("/api/characters", response_model=CharacterListResponse, tags=["Characters"])
async def list_characters():
    """获取角色列表"""
    chars = services.character.list_characters()
    return CharacterListResponse(
        success=True,
        message="获取成功",
        characters=[
            CharacterInfo(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                ref_images=[],
                ref_image_count=c.get("ref_image_count", 0)
            )
            for c in chars
        ]
    )


# ========================================
# 场景管理 API
# ========================================

@app.post("/api/scenes", response_model=SceneResponse, tags=["Scenes"])
async def add_scene(req: SceneCreate):
    """添加场景"""
    result = services.scene.add_scene(req.name, req.description, req.ref_image)

    scene_info = None
    if result.get("scene"):
        s = result["scene"]
        scene_info = SceneInfo(id=s["id"], name=s["name"], description=s["description"])

    return SceneResponse(
        success=result["success"],
        message=result["message"],
        scene=scene_info
    )


@app.delete("/api/scenes/{scene_id}", response_model=BaseResponse, tags=["Scenes"])
async def delete_scene(scene_id: str):
    """删除场景"""
    result = services.scene.delete_scene(scene_id)
    return BaseResponse(success=result["success"], message=result["message"])


@app.get("/api/scenes", response_model=SceneListResponse, tags=["Scenes"])
async def list_scenes():
    """获取场景列表"""
    scenes = services.scene.list_scenes()
    return SceneListResponse(
        success=True,
        message="获取成功",
        scenes=[
            SceneInfo(id=s["id"], name=s["name"], description=s["description"])
            for s in scenes
        ]
    )


# ========================================
# 镜头管理 API
# ========================================

@app.post("/api/shots", response_model=ShotResponse, tags=["Shots"])
async def add_shot(req: ShotCreate):
    """添加镜头"""
    result = services.shot.add_shot(
        template_name=req.template.value,
        description=req.description,
        character_ids=req.character_ids,
        scene_id=req.scene_id
    )

    shot_info = None
    if result.get("shot"):
        s = result["shot"]
        shot_info = ShotInfo(
            id=s["id"],
            shot_number=s["shot_number"],
            template=req.template.value,
            description=req.description,
            characters=req.character_ids,
            scene_id=req.scene_id,
            generated_prompt=s.get("generated_prompt")
        )

    return ShotResponse(
        success=result["success"],
        message=result["message"],
        shot=shot_info
    )


@app.delete("/api/shots/{shot_number}", response_model=BaseResponse, tags=["Shots"])
async def delete_shot(shot_number: int):
    """删除镜头"""
    result = services.shot.delete_shot(shot_number)
    return BaseResponse(success=result["success"], message=result["message"])


@app.put("/api/shots/{shot_number}/move", response_model=BaseResponse, tags=["Shots"])
async def move_shot(shot_number: int, direction: str):
    """移动镜头顺序"""
    if direction not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="direction must be 'up' or 'down'")

    result = services.shot.move_shot(shot_number, direction)
    return BaseResponse(success=result["success"], message=result["message"])


@app.get("/api/shots", response_model=ShotListResponse, tags=["Shots"])
async def list_shots():
    """获取镜头列表"""
    shots = services.shot.list_shots()
    return ShotListResponse(
        success=True,
        message="获取成功",
        shots=[
            ShotInfo(
                id=s["id"],
                shot_number=s["shot_number"],
                template=s["template"],
                description=s["description"],
                characters=s["characters"],
                scene=s["scene"],
                status=s["status"],
                output_image=s.get("output_image")
            )
            for s in shots
        ]
    )


# ========================================
# 图片生成 API
# ========================================

@app.post("/api/generate/shot", response_model=GenerateShotResponse, tags=["Generation"])
async def generate_shot(req: GenerateShotRequest):
    """生成单个镜头图片"""
    result = services.generation.generate_shot(req.shot_number, req.custom_prompt)

    return GenerateShotResponse(
        success=result["success"],
        message=result["message"],
        image_path=result.get("image_path"),
        consistency_score=result.get("consistency_score")
    )


@app.post("/api/generate/all", response_model=GenerateAllResponse, tags=["Generation"])
async def generate_all_shots():
    """批量生成所有镜头"""
    result = services.generation.generate_all()

    results = []
    for r in result.get("results", []):
        results.append(GenerationResult(
            shot_number=r["shot_number"],
            success=r["success"],
            image_path=r.get("image_path"),
            error=r.get("error")
        ))

    return GenerateAllResponse(
        success=result["success"],
        message=result["message"],
        results=results
    )


# ========================================
# 智能导入 API
# ========================================

@app.post("/api/import/analyze", response_model=SmartImportResponse, tags=["Import/Export"])
async def smart_import_analyze(req: SmartImportRequest):
    """智能分析文件内容"""
    result = services.import_export.smart_import(req.filepath, req.use_claude)

    return SmartImportResponse(
        success=result["success"],
        message=result["message"],
        file_type=result.get("file_type", ""),
        raw_content=result.get("raw_content", ""),
        analyzed_json=result.get("analyzed_json", "")
    )


@app.post("/api/import/upload", response_model=FileUploadResponse, tags=["Import/Export"])
async def upload_file(file: UploadFile = File(...)):
    """上传文件用于智能导入"""
    # Security: Validate file extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions)}"
        )

    # Security: Read content with size limit
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb} MB"
        )

    # 保存上传的文件
    upload_dir = settings.uploads_dir
    upload_dir.mkdir(exist_ok=True)

    # 生成唯一文件名
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / unique_name

    with open(filepath, "wb") as f:
        f.write(content)

    # 确定文件类型
    file_types = {
        ".pdf": "PDF",
        ".docx": "Word",
        ".doc": "Word",
        ".md": "Markdown",
        ".markdown": "Markdown",
        ".html": "HTML",
        ".htm": "HTML",
        ".jpg": "Image",
        ".jpeg": "Image",
        ".png": "Image",
        ".txt": "Text"
    }

    return FileUploadResponse(
        success=True,
        message=f"文件上传成功: {file.filename}",
        filepath=str(filepath),
        filename=file.filename,
        file_type=file_types.get(ext, "Unknown")
    )


@app.post("/api/import/apply", response_model=ProjectResponse, tags=["Import/Export"])
async def apply_import(req: ApplyImportRequest):
    """应用导入的JSON创建项目"""
    result = services.import_export.apply_import(req.json_content)

    project_info = None
    if result.get("project"):
        project_info = _convert_project_info(result["project"])

    return ProjectResponse(
        success=result["success"],
        message=result["message"],
        project=project_info
    )


# ========================================
# 导出 API
# ========================================

@app.post("/api/export", response_model=ExportResponse, tags=["Import/Export"])
async def export_project(req: ExportRequest):
    """导出项目"""
    result = services.import_export.export_project(req.format.value)

    return ExportResponse(
        success=result["success"],
        message=result["message"],
        filepath=result.get("filepath")
    )


@app.get("/api/export/download/{filename}", tags=["Import/Export"])
async def download_export(filename: str):
    """下载导出文件"""
    # Security: Validate filename to prevent path traversal
    if not re.match(r'^[\w\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename: contains illegal characters")

    # Security: Ensure the resolved path is within exports directory
    filepath = (Config.EXPORTS_DIR / filename).resolve()
    exports_dir = Config.EXPORTS_DIR.resolve()

    if not str(filepath).startswith(str(exports_dir)):
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/octet-stream"
    )


# ========================================
# 示例故事 API
# ========================================

@app.get("/api/examples", response_model=ExampleStoryListResponse, tags=["Examples"])
async def list_examples():
    """获取示例故事列表"""
    examples = services.get_example_stories()

    return ExampleStoryListResponse(
        success=True,
        message="获取成功",
        examples=[
            ExampleStoryInfo(
                name=e["name"],
                description=e["description"],
                character_count=e["character_count"],
                scene_count=e["scene_count"],
                shot_count=e["shot_count"]
            )
            for e in examples
        ]
    )


@app.post("/api/examples/load", response_model=ProjectResponse, tags=["Examples"])
async def load_example(req: LoadExampleRequest):
    """加载示例故事"""
    result = services.project.load_example(req.story_name)

    project_info = None
    if result.get("project"):
        project_info = _convert_project_info(result["project"])

    return ProjectResponse(
        success=result["success"],
        message=result["message"],
        project=project_info
    )


# ========================================
# 辅助函数
# ========================================

def _convert_project_info(info: dict) -> ProjectInfo:
    """转换项目信息为 Pydantic 模型"""
    from schemas import ProjectStats

    return ProjectInfo(
        id=info["id"],
        name=info["name"],
        aspect_ratio=info["aspect_ratio"],
        characters=[
            CharacterInfo(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                ref_images=c.get("ref_images", []),
                ref_image_count=len(c.get("ref_images", []))
            )
            for c in info.get("characters", [])
        ],
        scenes=[
            SceneInfo(id=s["id"], name=s["name"], description=s["description"])
            for s in info.get("scenes", [])
        ],
        shots=[
            ShotInfo(
                id=s["id"],
                shot_number=s["shot_number"],
                template=s["template"],
                description=s["description"],
                characters=s.get("characters", []),
                scene_id=s.get("scene_id", ""),
                status="completed" if s.get("output_image") else "pending",
                output_image=s.get("output_image"),
                generated_prompt=s.get("generated_prompt")
            )
            for s in info.get("shots", [])
        ],
        stats=ProjectStats(**info.get("stats", {
            "character_count": 0,
            "scene_count": 0,
            "shot_count": 0,
            "completed_count": 0
        }))
    )


# ========================================
# 启动服务器
# ========================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("AI Storyboard Pro API Server")
    print("=" * 50)
    print("API Docs: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8000)
