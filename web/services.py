"""
服务层 - 核心业务逻辑
与 UI 完全解耦，可被 API 和任何前端调用
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import uuid

from models import (
    Character, Scene, Prop, StyleConfig, StyleMode,
    Shot, StoryboardProject, ShotTemplate, SlotWeights,
    CameraSettings, CompositionSettings
)
from templates import get_template
from prompt_generator import generate_shot_prompt
from image_generator import create_generator, GenerationResult
from smart_import import SmartImporter, validate_and_fix_json
from settings import settings


# ========================================
# 目录配置 - 从统一设置加载
# ========================================

BASE_DIR = settings.base_dir
ASSETS_DIR = settings.assets_dir
PROJECTS_DIR = settings.projects_dir
OUTPUTS_DIR = settings.outputs_dir
EXPORTS_DIR = settings.exports_dir

# 确保目录存在
settings.ensure_directories()


# ========================================
# 配置 - 从统一设置加载
# ========================================

class Config:
    """配置类 - 从 settings 模块获取配置"""

    @property
    def API_KEY(self):
        return settings.api_key

    BASE_DIR = settings.base_dir
    ASSETS_DIR = settings.assets_dir
    PROJECTS_DIR = settings.projects_dir
    OUTPUTS_DIR = settings.outputs_dir
    EXPORTS_DIR = settings.exports_dir
    EXAMPLES_DIR = settings.examples_dir

    @classmethod
    def ensure_dirs(cls):
        """确保所有目录存在"""
        settings.ensure_directories()


# 为了兼容性，创建一个带有 API_KEY 属性的实例式访问
class _ConfigInstance:
    @property
    def API_KEY(self):
        return settings.api_key

    BASE_DIR = settings.base_dir
    ASSETS_DIR = settings.assets_dir
    PROJECTS_DIR = settings.projects_dir
    OUTPUTS_DIR = settings.outputs_dir
    EXPORTS_DIR = settings.exports_dir
    EXAMPLES_DIR = settings.examples_dir

    @staticmethod
    def ensure_dirs():
        settings.ensure_directories()


Config = _ConfigInstance()

# 初始化目录
Config.ensure_dirs()


# ========================================
# 故事范例数据
# ========================================

EXAMPLE_STORIES = {
    "咖啡厅邂逅": {
        "name": "咖啡厅邂逅",
        "description": "一个温馨的爱情故事开篇，男女主角在咖啡厅偶遇",
        "aspect_ratio": "16:9",
        "style": "电影感",
        "characters": [
            {"name": "李明", "description": "28岁，年轻作家，戴黑框眼镜，穿深蓝色毛衣，气质文艺"},
            {"name": "王薇", "description": "26岁，设计师，长发披肩，穿白色连衣裙，清新优雅"}
        ],
        "scenes": [
            {"name": "咖啡厅内部", "description": "现代简约风格咖啡厅，落地玻璃窗，午后阳光斜射，木质桌椅，绿植点缀"},
            {"name": "咖啡厅门口", "description": "咖啡厅玻璃门，门上有复古招牌，街道可见"}
        ],
        "shots": [
            {"template": "全景", "description": "咖啡厅外观全景，阳光明媚，温馨的下午时光", "characters": [], "scene": "咖啡厅门口"},
            {"template": "中景", "description": "李明独自坐在靠窗位置，正在笔记本电脑前写作，偶尔抬头思考", "characters": ["李明"], "scene": "咖啡厅内部"},
            {"template": "全景", "description": "王薇推门走进咖啡厅，阳光在她身后形成光晕", "characters": ["王薇"], "scene": "咖啡厅门口"},
            {"template": "中景", "description": "王薇环顾四周寻找座位，目光扫过整个咖啡厅", "characters": ["王薇"], "scene": "咖啡厅内部"},
            {"template": "过肩", "description": "从李明背后视角，看到王薇朝这边走来", "characters": ["李明", "王薇"], "scene": "咖啡厅内部"},
            {"template": "特写", "description": "李明抬头，眼神中带着惊讶和欣赏", "characters": ["李明"], "scene": "咖啡厅内部"},
            {"template": "特写", "description": "王薇微微一笑，礼貌地问能否拼桌", "characters": ["王薇"], "scene": "咖啡厅内部"},
            {"template": "中景", "description": "两人面对面坐着，开始交谈，气氛逐渐热络", "characters": ["李明", "王薇"], "scene": "咖啡厅内部"}
        ]
    },
    "都市追逐": {
        "name": "都市追逐",
        "description": "紧张刺激的动作场景，主角在城市中被追逐",
        "aspect_ratio": "16:9",
        "style": "电影感",
        "characters": [
            {"name": "陈警官", "description": "35岁，刑警，短发干练，穿深色夹克，眼神锐利"},
            {"name": "神秘人", "description": "身穿黑色风衣，戴帽子，面容模糊，身手敏捷"}
        ],
        "scenes": [
            {"name": "夜间街道", "description": "城市夜景，霓虹灯闪烁，雨后湿滑的街道，反射着灯光"},
            {"name": "小巷", "description": "狭窄的后巷，堆满杂物，灯光昏暗，阴影重重"}
        ],
        "shots": [
            {"template": "全景", "description": "雨后的城市夜景，霓虹灯倒映在湿漉漉的街面上", "characters": [], "scene": "夜间街道"},
            {"template": "跟随", "description": "陈警官在街道上奔跑，追逐前方的身影", "characters": ["陈警官"], "scene": "夜间街道"},
            {"template": "低角度", "description": "神秘人跃过障碍物，身形矫健", "characters": ["神秘人"], "scene": "小巷"},
            {"template": "过肩", "description": "陈警官追入小巷，看到前方分岔路口", "characters": ["陈警官"], "scene": "小巷"},
            {"template": "特写", "description": "陈警官喘着粗气，眼神警觉地观察四周", "characters": ["陈警官"], "scene": "小巷"},
            {"template": "全景", "description": "小巷尽头，神秘人的身影消失在黑暗中", "characters": ["神秘人"], "scene": "小巷"}
        ]
    },
    "温馨家庭": {
        "name": "温馨家庭",
        "description": "家庭日常温馨场景，展现亲情",
        "aspect_ratio": "16:9",
        "style": "电影感",
        "characters": [
            {"name": "妈妈", "description": "38岁，温柔贤惠，系着围裙，笑容和蔼"},
            {"name": "小美", "description": "8岁小女孩，扎着双马尾，穿粉色裙子，活泼可爱"}
        ],
        "scenes": [
            {"name": "家庭厨房", "description": "明亮温馨的厨房，阳光从窗户洒入，整洁有序"},
            {"name": "餐厅", "description": "木质餐桌，摆放着精美的餐具，墙上有全家福"}
        ],
        "shots": [
            {"template": "全景", "description": "阳光明媚的厨房，妈妈正在准备早餐", "characters": ["妈妈"], "scene": "家庭厨房"},
            {"template": "中景", "description": "小美跑进厨房，抱住妈妈的腿", "characters": ["妈妈", "小美"], "scene": "家庭厨房"},
            {"template": "特写", "description": "妈妈低头看着小美，眼中满是慈爱", "characters": ["妈妈"], "scene": "家庭厨房"},
            {"template": "中景", "description": "妈妈牵着小美的手走向餐桌", "characters": ["妈妈", "小美"], "scene": "餐厅"},
            {"template": "全景", "description": "母女俩坐在餐桌前，享用温馨的早餐时光", "characters": ["妈妈", "小美"], "scene": "餐厅"}
        ]
    }
}


# ========================================
# 项目服务
# ========================================

class ProjectService:
    """项目管理服务"""

    # 模板映射
    TEMPLATE_MAP = {
        "全景": ShotTemplate.T1_ESTABLISHING_WIDE,
        "中景": ShotTemplate.T4_STANDARD_MEDIUM,
        "特写": ShotTemplate.T6_CLOSEUP,
        "过肩": ShotTemplate.T5_OVER_SHOULDER,
        "低角度": ShotTemplate.T7_LOW_ANGLE,
        "跟随": ShotTemplate.T8_FOLLOWING,
    }

    STYLE_MAP = {
        "电影感": ("Cinematic", "realistic", "cinematic"),
        "动漫风": ("Anime", "anime", "natural"),
        "漫画风": ("Comic", "comic", "natural"),
        "写实风": ("Realistic", "realistic", "natural"),
        "水彩画": ("Watercolor", "watercolor", "natural"),
    }

    def __init__(self):
        self.current_project: Optional[StoryboardProject] = None

    def create_project(self, name: str, aspect_ratio: str = "16:9") -> Dict[str, Any]:
        """创建新项目"""
        self.current_project = StoryboardProject(
            name=name,
            aspect_ratio=aspect_ratio
        )
        return {
            "success": True,
            "message": f"项目「{name}」创建成功",
            "project": self.get_project_info()
        }

    def get_project_info(self) -> Optional[Dict[str, Any]]:
        """获取当前项目信息"""
        if self.current_project is None:
            return None

        # 生成项目ID (使用名称的hash作为简单ID)
        project_id = getattr(self.current_project, 'id', None)
        if project_id is None:
            project_id = uuid.uuid4().hex[:8]

        return {
            "id": project_id,
            "name": self.current_project.name,
            "aspect_ratio": self.current_project.aspect_ratio,
            "characters": [
                {"id": c.id, "name": c.name, "description": c.description, "ref_images": c.ref_images}
                for c in self.current_project.characters
            ],
            "scenes": [
                {"id": s.id, "name": s.name, "description": s.description}
                for s in self.current_project.scenes
            ],
            "shots": [
                {
                    "id": f"shot_{s.shot_number}",  # 使用 shot_number 作为 id
                    "shot_number": s.shot_number,
                    "template": s.template.value if s.template else "medium",
                    "description": s.description,
                    "characters": s.characters_in_shot,
                    "scene_id": s.scene_id,
                    "output_image": s.output_image,
                    "generated_prompt": s.generated_prompt
                }
                for s in self.current_project.shots
            ],
            "stats": {
                "character_count": len(self.current_project.characters),
                "scene_count": len(self.current_project.scenes),
                "shot_count": len(self.current_project.shots),
                "completed_count": sum(1 for s in self.current_project.shots if s.output_image)
            }
        }

    def set_style(self, style_name: str) -> Dict[str, Any]:
        """设置项目风格"""
        if self.current_project is None:
            return {"success": False, "message": "请先创建项目"}

        preset, render, light = self.STYLE_MAP.get(style_name, ("Cinematic", "realistic", "cinematic"))

        self.current_project.style = StyleConfig(
            mode=StyleMode.PRESET,
            preset_name=preset,
            render_type=render,
            lighting_style=light,
            weight=0.4
        )

        return {"success": True, "message": f"风格已设为「{style_name}」"}

    def load_example(self, story_name: str) -> Dict[str, Any]:
        """加载示例故事"""
        if story_name not in EXAMPLE_STORIES:
            return {"success": False, "message": f"未找到范例「{story_name}」"}

        example = EXAMPLE_STORIES[story_name]

        # 创建项目
        self.current_project = StoryboardProject(
            name=example["name"],
            aspect_ratio=example["aspect_ratio"]
        )

        # 设置风格
        self.set_style(example["style"])

        # 添加角色
        for char_data in example["characters"]:
            char = Character(
                name=char_data["name"],
                description=char_data["description"],
                ref_images=[],
                consistency_weight=0.85
            )
            self.current_project.characters.append(char)

        # 添加场景
        for scene_data in example["scenes"]:
            scene = Scene(
                name=scene_data["name"],
                description=scene_data["description"],
                space_ref_image="",
                consistency_weight=0.7
            )
            self.current_project.scenes.append(scene)

        # 添加镜头
        for shot_data in example["shots"]:
            self._add_shot_from_data(shot_data)

        return {
            "success": True,
            "message": f"已加载范例「{story_name}」",
            "project": self.get_project_info()
        }

    def _add_shot_from_data(self, shot_data: Dict) -> Shot:
        """从数据创建镜头"""
        template_type = self.TEMPLATE_MAP.get(shot_data["template"], ShotTemplate.T4_STANDARD_MEDIUM)
        template_def = get_template(template_type)

        # 查找角色ID
        char_ids = []
        for cname in shot_data.get("characters", []):
            for c in self.current_project.characters:
                if c.name == cname:
                    char_ids.append(c.id)
                    break

        # 查找场景ID
        scene_id = ""
        for s in self.current_project.scenes:
            if s.name == shot_data.get("scene", ""):
                scene_id = s.id
                break

        shot = Shot(
            shot_number=len(self.current_project.shots) + 1,
            template=template_type,
            description=shot_data["description"],
            characters_in_shot=char_ids,
            scene_id=scene_id,
            camera=template_def.camera if template_def else CameraSettings(),
            composition=template_def.composition if template_def else CompositionSettings(),
            slot_weights=SlotWeights(character=0.85, scene=0.5, props=0.6, style=0.4)
        )
        shot.generated_prompt = generate_shot_prompt(shot, self.current_project)
        self.current_project.shots.append(shot)
        return shot


# ========================================
# 角色服务
# ========================================

class CharacterService:
    """角色管理服务"""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    @property
    def project(self):
        return self.project_service.current_project

    def add_character(self, name: str, description: str, ref_images: List[str] = None) -> Dict[str, Any]:
        """添加角色"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        if not name.strip():
            return {"success": False, "message": "请输入角色名称"}

        char = Character(
            name=name,
            description=description,
            ref_images=ref_images or [],
            consistency_weight=0.85
        )
        self.project.characters.append(char)

        return {
            "success": True,
            "message": f"角色「{name}」已添加",
            "character": {"id": char.id, "name": char.name, "description": char.description}
        }

    def delete_character(self, character_id: str) -> Dict[str, Any]:
        """删除角色"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        for i, c in enumerate(self.project.characters):
            if c.id == character_id or c.name == character_id:
                self.project.characters.pop(i)
                return {"success": True, "message": f"角色「{c.name}」已删除"}

        return {"success": False, "message": "未找到该角色"}

    def list_characters(self) -> List[Dict[str, Any]]:
        """获取角色列表"""
        if self.project is None:
            return []
        return [
            {"id": c.id, "name": c.name, "description": c.description, "ref_image_count": len(c.ref_images)}
            for c in self.project.characters
        ]


# ========================================
# 场景服务
# ========================================

class SceneService:
    """场景管理服务"""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    @property
    def project(self):
        return self.project_service.current_project

    def add_scene(self, name: str, description: str, ref_image: str = "") -> Dict[str, Any]:
        """添加场景"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        if not name.strip():
            return {"success": False, "message": "请输入场景名称"}

        scene = Scene(
            name=name,
            description=description,
            space_ref_image=ref_image,
            consistency_weight=0.7
        )
        self.project.scenes.append(scene)

        return {
            "success": True,
            "message": f"场景「{name}」已添加",
            "scene": {"id": scene.id, "name": scene.name, "description": scene.description}
        }

    def delete_scene(self, scene_id: str) -> Dict[str, Any]:
        """删除场景"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        for i, s in enumerate(self.project.scenes):
            if s.id == scene_id or s.name == scene_id:
                self.project.scenes.pop(i)
                return {"success": True, "message": f"场景「{s.name}」已删除"}

        return {"success": False, "message": "未找到该场景"}

    def list_scenes(self) -> List[Dict[str, Any]]:
        """获取场景列表"""
        if self.project is None:
            return []
        return [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in self.project.scenes
        ]


# ========================================
# 镜头服务
# ========================================

class ShotService:
    """镜头管理服务"""

    TEMPLATE_MAP = ProjectService.TEMPLATE_MAP

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    @property
    def project(self):
        return self.project_service.current_project

    def add_shot(self, template_name: str, description: str,
                 character_ids: List[str] = None, scene_id: str = "") -> Dict[str, Any]:
        """添加镜头"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        template_type = self.TEMPLATE_MAP.get(template_name, ShotTemplate.T4_STANDARD_MEDIUM)
        template_def = get_template(template_type)

        shot = Shot(
            shot_number=len(self.project.shots) + 1,
            template=template_type,
            description=description,
            characters_in_shot=character_ids or [],
            scene_id=scene_id,
            camera=template_def.camera if template_def else CameraSettings(),
            composition=template_def.composition if template_def else CompositionSettings(),
            slot_weights=SlotWeights(
                character=template_def.default_weights.character if template_def else 0.85,
                scene=template_def.default_weights.scene if template_def else 0.5,
                props=0.6,
                style=0.4
            )
        )

        shot.generated_prompt = generate_shot_prompt(shot, self.project)
        self.project.shots.append(shot)

        return {
            "success": True,
            "message": f"镜头 {shot.shot_number} 已添加",
            "shot": {
                "id": shot.id,
                "shot_number": shot.shot_number,
                "generated_prompt": shot.generated_prompt
            }
        }

    def delete_shot(self, shot_number: int) -> Dict[str, Any]:
        """删除镜头"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        idx = shot_number - 1
        if 0 <= idx < len(self.project.shots):
            self.project.shots.pop(idx)
            # 重新编号
            for i, s in enumerate(self.project.shots):
                s.shot_number = i + 1
            return {"success": True, "message": "镜头已删除"}

        return {"success": False, "message": "无效的镜头编号"}

    def move_shot(self, shot_number: int, direction: str) -> Dict[str, Any]:
        """移动镜头顺序"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        idx = shot_number - 1
        if idx < 0 or idx >= len(self.project.shots):
            return {"success": False, "message": "无效的镜头编号"}

        if direction == "up" and idx > 0:
            self.project.shots[idx], self.project.shots[idx-1] = \
                self.project.shots[idx-1], self.project.shots[idx]
        elif direction == "down" and idx < len(self.project.shots) - 1:
            self.project.shots[idx], self.project.shots[idx+1] = \
                self.project.shots[idx+1], self.project.shots[idx]
        else:
            return {"success": False, "message": "无法移动"}

        # 重新编号
        for i, s in enumerate(self.project.shots):
            s.shot_number = i + 1

        return {"success": True, "message": f"镜头已{'上移' if direction == 'up' else '下移'}"}

    def list_shots(self) -> List[Dict[str, Any]]:
        """获取镜头列表"""
        if self.project is None:
            return []

        result = []
        for s in self.project.shots:
            template = get_template(s.template)

            # 获取角色名
            char_names = []
            for cid in s.characters_in_shot:
                for c in self.project.characters:
                    if c.id == cid:
                        char_names.append(c.name)

            # 获取场景名
            scene_name = ""
            for sc in self.project.scenes:
                if sc.id == s.scene_id:
                    scene_name = sc.name

            result.append({
                "id": f"shot_{s.shot_number}",  # 使用 shot_number 作为 id
                "shot_number": s.shot_number,
                "template": template.name_cn if template else "标准",
                "scene": scene_name,
                "characters": char_names,
                "description": s.description,
                "status": "completed" if s.output_image else "pending",
                "output_image": s.output_image
            })
        return result


# ========================================
# 生成服务
# ========================================

class GenerationService:
    """图片生成服务"""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service
        self.generator = create_generator(Config.API_KEY, str(Config.OUTPUTS_DIR))

    @property
    def project(self):
        return self.project_service.current_project

    def generate_shot(self, shot_number: int, custom_prompt: str = "") -> Dict[str, Any]:
        """生成单个镜头"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        idx = shot_number - 1
        if idx < 0 or idx >= len(self.project.shots):
            return {"success": False, "message": "无效的镜头编号"}

        shot = self.project.shots[idx]
        prompt = custom_prompt.strip() if custom_prompt else shot.generated_prompt

        if not prompt:
            prompt = generate_shot_prompt(shot, self.project)
            shot.generated_prompt = prompt

        result = self.generator.generate_shot(shot, self.project, prompt)

        if result.success:
            shot.output_image = result.image_path
            shot.consistency_score = result.consistency_score
            return {
                "success": True,
                "message": f"镜头 {shot_number} 生成完成",
                "image_path": result.image_path,
                "consistency_score": result.consistency_score
            }
        else:
            return {"success": False, "message": f"生成失败: {result.error_message}"}

    def generate_all(self) -> Dict[str, Any]:
        """批量生成所有镜头"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        if not self.project.shots:
            return {"success": False, "message": "请先添加镜头"}

        success = 0
        total = len(self.project.shots)
        results = []

        for shot in self.project.shots:
            if not shot.output_image:
                if not shot.generated_prompt:
                    shot.generated_prompt = generate_shot_prompt(shot, self.project)

                result = self.generator.generate_shot(shot, self.project, shot.generated_prompt)
                if result.success:
                    shot.output_image = result.image_path
                    shot.consistency_score = result.consistency_score
                    success += 1
                    results.append({"shot_number": shot.shot_number, "success": True, "image_path": result.image_path})
                else:
                    results.append({"shot_number": shot.shot_number, "success": False, "error": result.error_message})

        return {
            "success": True,
            "message": f"已生成 {success}/{total} 个镜头",
            "results": results
        }


# ========================================
# 导入导出服务
# ========================================

class ImportExportService:
    """导入导出服务"""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service
        self.smart_importer = SmartImporter()

    @property
    def project(self):
        return self.project_service.current_project

    def smart_import(self, filepath: str, use_claude: bool = True) -> Dict[str, Any]:
        """智能导入文件"""
        result = self.smart_importer.import_file(filepath, use_claude)

        return {
            "success": result["success"],
            "message": result["message"],
            "file_type": result.get("file_type", ""),
            "raw_content": result.get("raw_content", "")[:3000],
            "analyzed_json": result.get("analyzed_json", "")
        }

    def apply_import(self, json_str: str) -> Dict[str, Any]:
        """应用导入的JSON"""
        valid, fixed_json, error = validate_and_fix_json(json_str)
        if not valid:
            return {"success": False, "message": f"JSON格式错误: {error}"}

        try:
            data = json.loads(fixed_json)

            # 创建项目
            self.project_service.current_project = StoryboardProject(
                name=data.get("project_name", "导入的项目"),
                aspect_ratio=data.get("aspect_ratio", "16:9")
            )

            # 设置风格
            self.project_service.set_style(data.get("style", "电影感"))

            # 添加角色
            for char_data in data.get("characters", []):
                char = Character(
                    name=char_data.get("name", "未命名角色"),
                    description=char_data.get("description", ""),
                    ref_images=[],
                    consistency_weight=0.85
                )
                self.project_service.current_project.characters.append(char)

            # 添加场景
            for scene_data in data.get("scenes", []):
                scene = Scene(
                    name=scene_data.get("name", "未命名场景"),
                    description=scene_data.get("description", ""),
                    space_ref_image="",
                    consistency_weight=0.7
                )
                self.project_service.current_project.scenes.append(scene)

            # 添加镜头
            for shot_data in data.get("shots", []):
                self.project_service._add_shot_from_data(shot_data)

            return {
                "success": True,
                "message": f"成功导入项目「{self.project_service.current_project.name}」",
                "project": self.project_service.get_project_info()
            }

        except Exception as e:
            return {"success": False, "message": f"导入失败: {str(e)}"}

    def export_project(self, format_type: str) -> Dict[str, Any]:
        """导出项目"""
        if self.project is None:
            return {"success": False, "message": "请先创建项目"}

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format_type == "json":
            filename = f"{self.project.name}_{timestamp}.json"
            filepath = Config.EXPORTS_DIR / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.project.to_dict(), f, ensure_ascii=False, indent=2)

            return {"success": True, "message": f"已导出 {filename}", "filepath": str(filepath)}

        elif format_type == "zip":
            filename = f"{self.project.name}_{timestamp}.zip"
            filepath = Config.EXPORTS_DIR / filename

            with zipfile.ZipFile(filepath, 'w') as zf:
                for shot in self.project.shots:
                    if shot.output_image and os.path.exists(shot.output_image):
                        zf.write(shot.output_image, f"shots/shot_{shot.shot_number:02d}.png")

            return {"success": True, "message": f"已导出 {filename}", "filepath": str(filepath)}

        elif format_type == "txt":
            filename = f"{self.project.name}_script_{timestamp}.txt"
            filepath = Config.EXPORTS_DIR / filename

            lines = self._generate_script_text()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return {"success": True, "message": f"已导出 {filename}", "filepath": str(filepath)}

        elif format_type == "full":
            filename = f"{self.project.name}_backup_{timestamp}.zip"
            filepath = Config.EXPORTS_DIR / filename

            with zipfile.ZipFile(filepath, 'w') as zf:
                zf.writestr("project.json", json.dumps(self.project.to_dict(), ensure_ascii=False, indent=2))

                for shot in self.project.shots:
                    if shot.output_image and os.path.exists(shot.output_image):
                        zf.write(shot.output_image, f"outputs/shot_{shot.shot_number:02d}.png")

                for char in self.project.characters:
                    for i, img_path in enumerate(char.ref_images):
                        if os.path.exists(img_path):
                            zf.write(img_path, f"references/characters/{char.name}_{i}.png")

            return {"success": True, "message": f"完整备份已导出 {filename}", "filepath": str(filepath)}

        return {"success": False, "message": "未知格式"}

    def _generate_script_text(self) -> List[str]:
        """生成分镜脚本文本"""
        lines = [
            f"分镜脚本: {self.project.name}",
            f"画面比例: {self.project.aspect_ratio}",
            "",
            "=" * 50,
            "角色列表:",
            "=" * 50,
        ]

        for char in self.project.characters:
            lines.append(f"  - {char.name}: {char.description}")

        lines.extend(["", "=" * 50, "场景列表:", "=" * 50])

        for scene in self.project.scenes:
            lines.append(f"  - {scene.name}: {scene.description}")

        lines.extend(["", "=" * 50, "分镜列表:", "=" * 50, ""])

        for shot in self.project.shots:
            template = get_template(shot.template)
            char_names = [c.name for c in self.project.characters if c.id in shot.characters_in_shot]
            scene_name = next((s.name for s in self.project.scenes if s.id == shot.scene_id), "")

            lines.extend([
                f"镜头 {shot.shot_number}",
                f"  类型: {template.name_cn if template else '标准'}",
                f"  场景: {scene_name}",
                f"  角色: {', '.join(char_names) if char_names else '无'}",
                f"  描述: {shot.description}",
                ""
            ])

        return lines


# ========================================
# AI 创意服务
# ========================================

class AICreativeService:
    """AI创意生成服务 - 调用Claude CLI和ComfyUI"""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service
        self.comfyui_settings = None
        self.comfyui_client = None
        self.ai_generator = None
        self.quality_reviewer = None
        self.generated_assets = []

    @property
    def project(self):
        return self.project_service.current_project

    def initialize_comfyui(self, host: str = None, port: int = None) -> Dict[str, Any]:
        """
        Initialize ComfyUI connection

        Args:
            host: ComfyUI host (uses settings if not provided)
            port: ComfyUI port (uses settings if not provided)
        """
        try:
            from comfyui_client import ComfyUIClient, ComfyUIConfig, create_comfyui_client_from_settings
            from models import ComfyUISettings

            # Use settings if host/port not provided
            if host is None or port is None:
                # Use settings-based client
                self.comfyui_client = create_comfyui_client_from_settings()
                config = self.comfyui_client.config
                self.comfyui_settings = ComfyUISettings(
                    host=config.host,
                    port=config.port
                )
            else:
                # Use provided host/port
                self.comfyui_settings = ComfyUISettings(host=host, port=port)
                workflow_dir = str(settings.comfyui_workflows_dir) if settings.comfyui_workflows_dir else None
                config = ComfyUIConfig(host=host, port=port, workflow_dir=workflow_dir)
                self.comfyui_client = ComfyUIClient(config)

            if not self.comfyui_client.is_enabled():
                return {"success": False, "message": "ComfyUI integration is disabled. Set COMFYUI_ENABLED=true in .env"}

            success, message = self.comfyui_client.test_connection()

            # Include workflow list if available
            if success and self.comfyui_client.config.workflow_dir:
                workflows = self.comfyui_client.list_workflows()
                if workflows:
                    message += f" | Available workflows: {', '.join(workflows)}"

            return {"success": success, "message": message}
        except ImportError as e:
            return {"success": False, "message": f"Missing dependency: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def initialize_ai_generator(self) -> Dict[str, Any]:
        """Initialize AI creative generator"""
        try:
            from ai_creative_generator import AICreativeGenerator, QualityReviewer

            self.ai_generator = AICreativeGenerator()
            self.quality_reviewer = QualityReviewer()
            return {"success": True, "message": "AI generator initialized"}
        except ImportError as e:
            return {"success": False, "message": f"Missing dependency: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Initialization error: {str(e)}"}

    def analyze_story(self, story_text: str) -> Dict[str, Any]:
        """Analyze story and extract characters, scenes, props"""
        if not self.ai_generator:
            init_result = self.initialize_ai_generator()
            if not init_result["success"]:
                return init_result

        try:
            result = self.ai_generator.analyze_story(story_text)
            if result.success:
                return {
                    "success": True,
                    "message": f"分析完成: {len(result.characters)}个角色, {len(result.scenes)}个场景, {len(result.shots)}个镜头",
                    "project_name": result.project_name,
                    "description": result.description,
                    "genre": result.genre,
                    "style": result.style,
                    "characters": [c.to_dict() for c in result.characters],
                    "scenes": [s.to_dict() for s in result.scenes],
                    "props": [p.to_dict() for p in result.props],
                    "shots": [s.to_dict() for s in result.shots]
                }
            else:
                return {"success": False, "message": result.error}
        except Exception as e:
            return {"success": False, "message": f"Analysis error: {str(e)}"}

    def generate_character_prompt(self, character_info: Dict, style: str = "realistic") -> Dict[str, Any]:
        """Generate Chinese prompt for character"""
        if not self.ai_generator:
            init_result = self.initialize_ai_generator()
            if not init_result["success"]:
                return init_result

        try:
            from ai_creative_generator import CharacterInfo, ArtStyle

            char = CharacterInfo(
                name=character_info.get("name", ""),
                age=character_info.get("age", ""),
                gender=character_info.get("gender", ""),
                appearance=character_info.get("appearance", ""),
                clothing=character_info.get("clothing", ""),
                personality=character_info.get("personality", ""),
                role=character_info.get("role", "")
            )

            style_map = {
                "realistic": ArtStyle.REALISTIC,
                "anime": ArtStyle.ANIME,
                "comic": ArtStyle.COMIC,
                "watercolor": ArtStyle.WATERCOLOR
            }
            art_style = style_map.get(style, ArtStyle.REALISTIC)

            prompt = self.ai_generator.generate_character_prompt(char, art_style)
            return {
                "success": True,
                "prompt": prompt,
                "character_name": char.name
            }
        except Exception as e:
            return {"success": False, "message": f"Prompt generation error: {str(e)}"}

    def generate_scene_prompt(self, scene_info: Dict, style: str = "realistic") -> Dict[str, Any]:
        """Generate Chinese prompt for scene"""
        if not self.ai_generator:
            init_result = self.initialize_ai_generator()
            if not init_result["success"]:
                return init_result

        try:
            from ai_creative_generator import SceneInfo, ArtStyle

            scene = SceneInfo(
                name=scene_info.get("name", ""),
                location_type=scene_info.get("location_type", ""),
                description=scene_info.get("description", ""),
                lighting=scene_info.get("lighting", ""),
                atmosphere=scene_info.get("atmosphere", ""),
                time_of_day=scene_info.get("time_of_day", ""),
                weather=scene_info.get("weather", "")
            )

            style_map = {
                "realistic": ArtStyle.REALISTIC,
                "anime": ArtStyle.ANIME,
                "comic": ArtStyle.COMIC,
                "watercolor": ArtStyle.WATERCOLOR
            }
            art_style = style_map.get(style, ArtStyle.REALISTIC)

            prompt = self.ai_generator.generate_scene_prompt(scene, art_style)
            return {
                "success": True,
                "prompt": prompt,
                "scene_name": scene.name
            }
        except Exception as e:
            return {"success": False, "message": f"Prompt generation error: {str(e)}"}

    def generate_image_with_comfyui(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 576,
        ref_image_path: str = "",
        output_dir: str = ""
    ) -> Dict[str, Any]:
        """Generate image using ComfyUI"""
        if not self.comfyui_client:
            return {"success": False, "message": "ComfyUI not connected"}

        try:
            from comfyui_client import GenerationParams

            params = GenerationParams(
                prompt=prompt,
                negative_prompt=negative_prompt or "低质量，模糊，变形，丑陋",
                width=width,
                height=height,
                steps=20,
                cfg_scale=7.0
            )

            if ref_image_path:
                params.ref_image_path = ref_image_path
                params.denoise = 0.75
                result = self.comfyui_client.image_to_image(params, output_dir=output_dir)
            else:
                result = self.comfyui_client.text_to_image(params, output_dir=output_dir)

            if result.success:
                return {
                    "success": True,
                    "images": result.images,
                    "generation_time": result.generation_time
                }
            else:
                return {"success": False, "message": result.error}
        except Exception as e:
            return {"success": False, "message": f"Generation error: {str(e)}"}

    def review_generated_image(self, asset_type: str, spec: Dict, prompt: str) -> Dict[str, Any]:
        """Review generated image quality"""
        if not self.quality_reviewer:
            init_result = self.initialize_ai_generator()
            if not init_result["success"]:
                return init_result

        try:
            from ai_creative_generator import CharacterInfo, SceneInfo, PropInfo

            if asset_type == "character":
                char = CharacterInfo(**spec)
                char.generated_prompt = prompt
                review = self.quality_reviewer.review_character(char)
            elif asset_type == "scene":
                scene = SceneInfo(**spec)
                scene.generated_prompt = prompt
                review = self.quality_reviewer.review_scene(scene)
            else:
                prop = PropInfo(**spec)
                prop.generated_prompt = prompt
                review = self.quality_reviewer.review_prop(prop)

            return {
                "success": True,
                "score": review.score,
                "passed": review.passed,
                "issues": review.issues,
                "suggestions": review.suggestions,
                "summary": review.summary
            }
        except Exception as e:
            return {"success": False, "message": f"Review error: {str(e)}"}

    def auto_generate_character(
        self,
        character_info: Dict,
        style: str = "realistic",
        output_dir: str = "",
        ref_image_path: str = ""
    ) -> Dict[str, Any]:
        """Full automation: analyze -> generate prompt -> generate image -> review"""
        from models import GeneratedAsset, GeneratedAssetType, AssetGenerationStatus

        asset = GeneratedAsset(
            asset_type=GeneratedAssetType.CHARACTER,
            name=character_info.get("name", ""),
            description=character_info.get("appearance", "")
        )

        # Step 1: Generate prompt
        prompt_result = self.generate_character_prompt(character_info, style)
        if not prompt_result["success"]:
            asset.status = AssetGenerationStatus.FAILED
            return {"success": False, "message": prompt_result.get("message", "Prompt generation failed"), "asset": asset.to_dict()}

        asset.prompt = prompt_result["prompt"]
        asset.status = AssetGenerationStatus.GENERATING

        # Step 2: Generate image
        gen_result = self.generate_image_with_comfyui(
            prompt=asset.prompt,
            width=768,
            height=1024,  # Portrait for character
            ref_image_path=ref_image_path,
            output_dir=output_dir
        )

        if not gen_result["success"]:
            asset.status = AssetGenerationStatus.FAILED
            return {"success": False, "message": gen_result.get("message", "Image generation failed"), "asset": asset.to_dict()}

        asset.image_path = gen_result["images"][0] if gen_result["images"] else ""
        asset.generation_time = gen_result.get("generation_time", 0)
        asset.status = AssetGenerationStatus.REVIEW_PENDING

        # Step 3: Review quality
        review_result = self.review_generated_image("character", character_info, asset.prompt)
        if review_result["success"]:
            asset.review_score = review_result["score"]
            asset.review_summary = review_result["summary"]
            asset.review_issues = review_result["issues"]
            asset.review_suggestions = review_result["suggestions"]

        asset.status = AssetGenerationStatus.COMPLETED
        self.generated_assets.append(asset)

        # Auto-save to project if enabled
        if self.project and asset.image_path:
            self._add_asset_to_project(asset)

        return {
            "success": True,
            "message": f"角色「{asset.name}」生成完成，评分: {asset.review_score}/10",
            "asset": asset.to_dict()
        }

    def _add_asset_to_project(self, asset):
        """Add generated asset to current project"""
        from models import GeneratedAssetType

        if asset.asset_type == GeneratedAssetType.CHARACTER:
            # Find and update character with generated image
            for char in self.project.characters:
                if char.name == asset.name:
                    if asset.image_path not in char.ref_images:
                        char.ref_images.append(asset.image_path)
                    break
        elif asset.asset_type == GeneratedAssetType.SCENE:
            # Find and update scene
            for scene in self.project.scenes:
                if scene.name == asset.name:
                    if not scene.space_ref_image:
                        scene.space_ref_image = asset.image_path
                    break

    def get_generated_assets(self) -> List[Dict]:
        """Get all generated assets"""
        return [a.to_dict() for a in self.generated_assets]


# ========================================
# 视频分析服务
# ========================================

class VideoAnalysisService:
    """视频分析服务 - 视频拆解和报告生成"""

    def __init__(self, project_service: ProjectService):
        self.project = project_service
        self._analyzer = None
        self._current_result = None
        self._pdf_generator = None

    def _ensure_analyzer(self, ollama_host: str = "localhost", ollama_port: int = 11434):
        """确保分析器已初始化"""
        if self._analyzer is None:
            from video_analyzer import VideoAnalyzer, PDFReportGenerator
            output_dir = str(OUTPUTS_DIR / "video_analysis")
            self._analyzer = VideoAnalyzer(
                output_dir=output_dir,
                ollama_host=ollama_host,
                ollama_port=ollama_port
            )
            self._pdf_generator = PDFReportGenerator()

    def test_connections(self, ollama_host: str = "localhost", ollama_port: int = 11434) -> Dict[str, Any]:
        """测试所有连接"""
        self._ensure_analyzer(ollama_host, ollama_port)
        results = self._analyzer.test_connections()
        return {
            "ollama": {
                "connected": results["ollama"][0],
                "message": results["ollama"][1]
            },
            "claude": {
                "connected": results["claude"][0],
                "message": results["claude"][1]
            }
        }

    def analyze_video(
        self,
        video_path: str,
        extraction_mode: str = "interval",
        interval_seconds: float = 5.0,
        max_frames: int = 50,
        ollama_host: str = "localhost",
        ollama_port: int = 11434,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        分析视频

        Args:
            video_path: 视频文件路径
            extraction_mode: 抽帧模式 (interval/scene_change/both)
            interval_seconds: 间隔秒数
            max_frames: 最大帧数
            ollama_host: Ollama 主机
            ollama_port: Ollama 端口
            progress_callback: 进度回调

        Returns:
            分析结果
        """
        self._ensure_analyzer(ollama_host, ollama_port)

        try:
            result = self._analyzer.analyze_video(
                video_path,
                extraction_mode=extraction_mode,
                interval_seconds=interval_seconds,
                max_frames=max_frames,
                progress_callback=progress_callback
            )
            self._current_result = result
            return {
                "success": True,
                "result": result.to_dict(),
                "message": "分析完成"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"分析失败: {e}"
            }

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        self._ensure_analyzer()
        info = self._analyzer.frame_extractor.get_video_info(video_path)
        return info

    def get_current_result(self) -> Optional[Dict]:
        """获取当前分析结果"""
        if self._current_result:
            return self._current_result.to_dict()
        return None

    def update_item(self, item_type: str, item_id: str, updates: Dict) -> Dict[str, Any]:
        """
        更新分析结果中的某一项

        Args:
            item_type: 项目类型 (story_point, character, scene, shot, frame)
            item_id: 项目ID
            updates: 更新内容

        Returns:
            操作结果
        """
        if not self._current_result:
            return {"success": False, "message": "没有当前分析结果"}

        if not self._analyzer:
            return {"success": False, "message": "分析器未初始化"}

        success = self._analyzer.update_item(
            self._current_result.id,
            item_type,
            item_id,
            updates
        )

        if success:
            return {"success": True, "message": "更新成功"}
        return {"success": False, "message": "更新失败，未找到项目"}

    def generate_pdf_report(self, output_filename: str = None) -> Dict[str, Any]:
        """生成PDF报告"""
        if not self._current_result:
            return {"success": False, "message": "没有分析结果，请先分析视频"}

        if not self._pdf_generator:
            from video_analyzer import PDFReportGenerator
            self._pdf_generator = PDFReportGenerator()

        try:
            output_dir = str(OUTPUTS_DIR / "video_analysis" / "reports")
            os.makedirs(output_dir, exist_ok=True)

            if not output_filename:
                output_filename = f"report_{self._current_result.id}.pdf"

            output_path = os.path.join(output_dir, output_filename)
            report_path = self._pdf_generator.generate_report(self._current_result, output_path)

            return {
                "success": True,
                "path": report_path,
                "message": f"报告已生成: {report_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"生成报告失败: {e}"
            }

    def save_result(self, filename: str = None) -> Dict[str, Any]:
        """保存分析结果"""
        if not self._current_result or not self._analyzer:
            return {"success": False, "message": "没有分析结果"}

        try:
            filepath = self._analyzer.save_result(self._current_result, filename)
            return {
                "success": True,
                "path": filepath,
                "message": f"结果已保存: {filepath}"
            }
        except Exception as e:
            return {"success": False, "message": f"保存失败: {e}"}

    def load_result(self, filepath: str) -> Dict[str, Any]:
        """加载分析结果"""
        self._ensure_analyzer()
        try:
            self._current_result = self._analyzer.load_result(filepath)
            return {
                "success": True,
                "result": self._current_result.to_dict(),
                "message": "加载成功"
            }
        except Exception as e:
            return {"success": False, "message": f"加载失败: {e}"}

    def get_frame_by_timestamp(self, timestamp: float) -> Optional[Dict]:
        """根据时间戳获取最近的帧"""
        if not self._current_result:
            return None

        if not self._current_result.frames:
            return None

        closest_frame = min(
            self._current_result.frames,
            key=lambda f: abs(f.timestamp - timestamp)
        )
        return closest_frame.to_dict()

    def get_timeline_data(self) -> Dict[str, Any]:
        """获取时间轴数据用于可视化"""
        if not self._current_result:
            return {"success": False, "message": "没有分析结果"}

        timeline = {
            "duration": self._current_result.duration,
            "frames": [],
            "story_points": [],
            "scenes": [],
            "shots": []
        }

        # 帧数据
        for frame in self._current_result.frames:
            timeline["frames"].append({
                "id": frame.id,
                "timestamp": frame.timestamp,
                "timestamp_formatted": frame.format_timestamp(),
                "tags": frame.tags,
                "image_path": frame.image_path
            })

        # 故事节点
        for sp in self._current_result.story_points:
            timeline["story_points"].append({
                "id": sp.id,
                "timestamp": sp.timestamp,
                "title": sp.title,
                "point_type": sp.point_type
            })

        # 场景
        for scene in self._current_result.scenes:
            timeline["scenes"].append({
                "id": scene.id,
                "start_time": scene.start_time,
                "end_time": scene.end_time,
                "scene_name": scene.scene_name
            })

        # 分镜
        for shot in self._current_result.shots:
            timeline["shots"].append({
                "id": shot.id,
                "timestamp": shot.timestamp,
                "shot_type": shot.shot_type
            })

        return {"success": True, "timeline": timeline}

    def get_cleanup_info(self, days_to_keep: int = 1) -> Dict[str, Any]:
        """获取可清理的历史数据信息"""
        self._ensure_analyzer()
        return self._analyzer.get_cleanup_info(days_to_keep)

    def cleanup_old_runs(self, days_to_keep: int = 1) -> Dict[str, Any]:
        """清理旧的运行数据（需要手动确认）"""
        self._ensure_analyzer()
        return self._analyzer.cleanup_old_runs(days_to_keep, confirm=True)


# ========================================
# 服务容器
# ========================================

class ServiceContainer:
    """服务容器 - 管理所有服务实例"""

    def __init__(self):
        self.project = ProjectService()
        self.character = CharacterService(self.project)
        self.scene = SceneService(self.project)
        self.shot = ShotService(self.project)
        self.generation = GenerationService(self.project)
        self.import_export = ImportExportService(self.project)
        self.ai_creative = AICreativeService(self.project)
        self.video_analysis = VideoAnalysisService(self.project)

    def get_example_stories(self) -> List[Dict[str, Any]]:
        """获取示例故事列表"""
        return [
            {
                "name": name,
                "description": story["description"],
                "character_count": len(story["characters"]),
                "scene_count": len(story["scenes"]),
                "shot_count": len(story["shots"])
            }
            for name, story in EXAMPLE_STORIES.items()
        ]


# 全局服务实例
services = ServiceContainer()
