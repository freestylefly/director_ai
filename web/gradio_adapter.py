"""
Gradio 适配层 - 连接 Gradio UI 与服务层
支持未来迁移到其他前端框架
"""

from typing import List, Tuple, Dict, Any, Optional
from services import services, Config, EXAMPLE_STORIES
from templates import get_template_choices_cn, TEMPLATE_QUICK_REF


# ========================================
# 项目管理适配
# ========================================

def create_project(name: str, ratio: str) -> Tuple[str, bool]:
    """创建新项目"""
    if not name.strip():
        name = "我的分镜"

    result = services.project.create_project(name, ratio)
    return f"✓ {result['message']}", result['success']


def get_project_summary() -> str:
    """获取项目摘要"""
    info = services.project.get_project_info()
    if not info:
        return "尚未创建项目"

    stats = info['stats']
    return f"""
### {info['name']}

**角色**: {stats['character_count']} 个  |  **场景**: {stats['scene_count']} 个  |  **镜头**: {stats['shot_count']} 个

**已生成**: {stats['completed_count']}/{stats['shot_count']} 个镜头
"""


def set_style(style_name: str) -> str:
    """设置项目风格"""
    result = services.project.set_style(style_name)
    return result['message']


# ========================================
# 角色管理适配
# ========================================

def add_character(name: str, description: str, ref_images: List = None) -> Tuple[str, str, str, str]:
    """添加角色"""
    # 保存上传的图片
    ref_paths = []
    if ref_images:
        from app import save_multiple_images
        ref_paths = save_multiple_images(ref_images, "characters", name)

    result = services.character.add_character(name, description, ref_paths)

    # 返回: 消息, 更新后的列表HTML, 清空名称, 清空描述
    char_list = format_character_list()
    return result['message'], char_list, "", ""


def delete_character(character_id: str) -> Tuple[str, str]:
    """删除角色"""
    result = services.character.delete_character(character_id)
    char_list = format_character_list()
    return result['message'], char_list


def format_character_list() -> str:
    """格式化角色列表为HTML"""
    chars = services.character.list_characters()
    if not chars:
        return "<p style='color: #666;'>暂无角色</p>"

    html = ""
    for c in chars:
        html += f"""
        <div style='background: #f5f5f7; padding: 12px; border-radius: 8px; margin: 8px 0;'>
            <strong>{c['name']}</strong>
            <p style='color: #666; margin: 4px 0; font-size: 13px;'>{c['description'][:50]}...</p>
            <button onclick='delete_char("{c["id"]}")' style='font-size: 12px; color: #ff3b30;'>删除</button>
        </div>
        """
    return html


def get_character_choices() -> List[Tuple[str, str]]:
    """获取角色选择列表"""
    chars = services.character.list_characters()
    return [(c['name'], c['id']) for c in chars]


# ========================================
# 场景管理适配
# ========================================

def add_scene(name: str, description: str, ref_image=None) -> Tuple[str, str, str, str]:
    """添加场景"""
    ref_path = ""
    if ref_image:
        from app import save_uploaded_image
        ref_path = save_uploaded_image(ref_image, "scenes", name)

    result = services.scene.add_scene(name, description, ref_path)

    scene_list = format_scene_list()
    return result['message'], scene_list, "", ""


def delete_scene(scene_id: str) -> Tuple[str, str]:
    """删除场景"""
    result = services.scene.delete_scene(scene_id)
    scene_list = format_scene_list()
    return result['message'], scene_list


def format_scene_list() -> str:
    """格式化场景列表为HTML"""
    scenes = services.scene.list_scenes()
    if not scenes:
        return "<p style='color: #666;'>暂无场景</p>"

    html = ""
    for s in scenes:
        html += f"""
        <div style='background: #f5f5f7; padding: 12px; border-radius: 8px; margin: 8px 0;'>
            <strong>{s['name']}</strong>
            <p style='color: #666; margin: 4px 0; font-size: 13px;'>{s['description'][:50]}...</p>
            <button onclick='delete_scene("{s["id"]}")' style='font-size: 12px; color: #ff3b30;'>删除</button>
        </div>
        """
    return html


def get_scene_choices() -> List[Tuple[str, str]]:
    """获取场景选择列表"""
    scenes = services.scene.list_scenes()
    return [(s['name'], s['id']) for s in scenes]


# ========================================
# 镜头管理适配
# ========================================

def add_shot(template_name: str, description: str,
             character_ids: List[str] = None, scene_id: str = "") -> Tuple[str, str]:
    """添加镜头"""
    result = services.shot.add_shot(template_name, description, character_ids or [], scene_id)

    shot_list = format_shot_list()
    return result['message'], shot_list


def delete_shot(shot_number: int) -> Tuple[str, str]:
    """删除镜头"""
    result = services.shot.delete_shot(shot_number)
    shot_list = format_shot_list()
    return result['message'], shot_list


def move_shot(shot_number: int, direction: str) -> Tuple[str, str]:
    """移动镜头"""
    result = services.shot.move_shot(shot_number, direction)
    shot_list = format_shot_list()
    return result['message'], shot_list


def format_shot_list() -> str:
    """格式化镜头列表为HTML"""
    shots = services.shot.list_shots()
    if not shots:
        return "<p style='color: #666;'>暂无镜头</p>"

    html = '<div style="display: flex; flex-direction: column; gap: 12px;">'
    for s in shots:
        status_color = "#34c759" if s['status'] == 'completed' else "#ff9500"
        status_text = "已生成" if s['status'] == 'completed' else "待生成"

        char_str = ", ".join(s['characters']) if s['characters'] else "无角色"

        html += f"""
        <div style='background: white; padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <span style='font-size: 18px; font-weight: 600;'>镜头 {s['shot_number']}</span>
                    <span style='background: #e8e8ed; padding: 4px 12px; border-radius: 4px; margin-left: 8px; font-size: 12px;'>{s['template']}</span>
                    <span style='color: {status_color}; font-size: 12px; margin-left: 8px;'>● {status_text}</span>
                </div>
                <div>
                    <button onclick='move_shot_up({s["shot_number"]})' style='padding: 4px 8px;'>↑</button>
                    <button onclick='move_shot_down({s["shot_number"]})' style='padding: 4px 8px;'>↓</button>
                    <button onclick='delete_shot({s["shot_number"]})' style='padding: 4px 8px; color: #ff3b30;'>×</button>
                </div>
            </div>
            <p style='color: #666; margin: 8px 0; font-size: 14px;'>{s['description']}</p>
            <div style='font-size: 12px; color: #888;'>
                场景: {s['scene']} | 角色: {char_str}
            </div>
        </div>
        """
    html += '</div>'
    return html


# ========================================
# 图片生成适配
# ========================================

def generate_shot(shot_number: int, custom_prompt: str = "") -> Tuple[str, Optional[str]]:
    """生成单个镜头"""
    result = services.generation.generate_shot(shot_number, custom_prompt)

    if result['success']:
        return result['message'], result.get('image_path')
    else:
        return result['message'], None


def generate_all_shots() -> Tuple[str, str]:
    """批量生成所有镜头"""
    result = services.generation.generate_all()

    # 刷新镜头列表
    shot_list = format_shot_list()
    return result['message'], shot_list


# ========================================
# 导入导出适配
# ========================================

def smart_import_file(filepath: str, use_claude: bool = True) -> Tuple[str, str, str]:
    """智能导入文件"""
    result = services.import_export.smart_import(filepath, use_claude)

    return (
        result['message'],
        result.get('raw_content', ''),
        result.get('analyzed_json', '')
    )


def apply_import_json(json_str: str) -> Tuple[str, str, str, str, str]:
    """应用导入的JSON"""
    result = services.import_export.apply_import(json_str)

    if result['success']:
        # 返回更新后的各列表
        return (
            result['message'],
            get_project_summary(),
            format_character_list(),
            format_scene_list(),
            format_shot_list()
        )
    else:
        return result['message'], "", "", "", ""


def export_project(format_type: str) -> Tuple[str, Optional[str]]:
    """导出项目"""
    result = services.import_export.export_project(format_type)

    if result['success']:
        return result['message'], result.get('filepath')
    else:
        return result['message'], None


# ========================================
# 示例故事适配
# ========================================

def get_example_stories_html() -> str:
    """获取示例故事HTML卡片"""
    examples = services.get_example_stories()

    html = '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">'
    for e in examples:
        html += f"""
        <div class='example-card' onclick='load_example("{e["name"]}")'>
            <h4 style='margin: 0 0 8px 0;'>{e['name']}</h4>
            <p style='color: #666; font-size: 13px; margin: 0;'>{e['description']}</p>
            <div style='margin-top: 12px; font-size: 12px; color: #888;'>
                角色: {e['character_count']} | 场景: {e['scene_count']} | 镜头: {e['shot_count']}
            </div>
        </div>
        """
    html += '</div>'
    return html


def load_example_story(story_name: str) -> Tuple[str, str, str, str, str]:
    """加载示例故事"""
    result = services.project.load_example(story_name)

    if result['success']:
        return (
            result['message'],
            get_project_summary(),
            format_character_list(),
            format_scene_list(),
            format_shot_list()
        )
    else:
        return result['message'], "", "", "", ""


# ========================================
# UI 数据刷新适配
# ========================================

def refresh_all_ui() -> Tuple[str, str, str, str]:
    """刷新所有UI组件"""
    return (
        get_project_summary(),
        format_character_list(),
        format_scene_list(),
        format_shot_list()
    )


def get_template_guide() -> str:
    """获取镜头类型指南HTML"""
    html = '<div style="background: #f5f5f7; padding: 16px; border-radius: 12px;">'
    html += '<h4 style="margin: 0 0 12px 0;">镜头类型参考</h4>'

    for template_cn, info in TEMPLATE_QUICK_REF.items():
        html += f"""
        <div style='margin: 8px 0; padding: 8px; background: white; border-radius: 8px;'>
            <strong>{template_cn}</strong>
            <span style='color: #666; font-size: 13px; margin-left: 8px;'>{info['use']}</span>
        </div>
        """

    html += '</div>'
    return html


# ========================================
# API 客户端适配 (用于未来前端)
# ========================================

class APIClient:
    """
    API 客户端 - 用于前端调用后端 API
    可被 React/Flutter/Mobile 等前端使用
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def create_project(self, name: str, aspect_ratio: str = "16:9") -> Dict:
        """创建项目 - 调用 POST /api/project"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/project",
                json={"name": name, "aspect_ratio": aspect_ratio}
            )
            return response.json()

    async def get_project(self) -> Dict:
        """获取项目 - 调用 GET /api/project"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/project")
            return response.json()

    async def add_character(self, name: str, description: str) -> Dict:
        """添加角色 - 调用 POST /api/characters"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/characters",
                json={"name": name, "description": description}
            )
            return response.json()

    async def add_scene(self, name: str, description: str) -> Dict:
        """添加场景 - 调用 POST /api/scenes"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/scenes",
                json={"name": name, "description": description}
            )
            return response.json()

    async def add_shot(self, template: str, description: str,
                       character_ids: List[str] = None, scene_id: str = "") -> Dict:
        """添加镜头 - 调用 POST /api/shots"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/shots",
                json={
                    "template": template,
                    "description": description,
                    "character_ids": character_ids or [],
                    "scene_id": scene_id
                }
            )
            return response.json()

    async def generate_shot(self, shot_number: int, custom_prompt: str = "") -> Dict:
        """生成镜头 - 调用 POST /api/generate/shot"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate/shot",
                json={"shot_number": shot_number, "custom_prompt": custom_prompt}
            )
            return response.json()

    async def export_project(self, format_type: str = "json") -> Dict:
        """导出项目 - 调用 POST /api/export"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/export",
                json={"format": format_type}
            )
            return response.json()

    async def load_example(self, story_name: str) -> Dict:
        """加载示例 - 调用 POST /api/examples/load"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/examples/load",
                json={"story_name": story_name}
            )
            return response.json()


# 用于快速测试
if __name__ == "__main__":
    # 测试服务层调用
    print("测试服务层适配...")

    # 创建项目
    msg, success = create_project("测试项目", "16:9")
    print(f"创建项目: {msg}")

    # 添加角色
    msg, html, _, _ = add_character("测试角色", "这是一个测试角色描述")
    print(f"添加角色: {msg}")

    # 添加场景
    msg, html, _, _ = add_scene("测试场景", "这是一个测试场景描述")
    print(f"添加场景: {msg}")

    # 获取项目摘要
    summary = get_project_summary()
    print(f"项目摘要:\n{summary}")

    print("\n适配层测试完成!")
