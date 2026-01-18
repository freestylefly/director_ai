"""
AI 智能分镜 Pro v2.1 - 专业分镜制作系统
完整功能版本 - 支持多格式导入导出、批量上传、故事范例

电影剧组专业审核版本:
- 编剧: 剧情逻辑和叙事结构
- 导演: 镜头语言和节奏把控
- 场景设计: 环境一致性和氛围
- 人物设计: 角色形象一致性
- 摄影: 构图和光影效果
- 后期: 整体视觉统一性
- 观众视角: 用户体验和易用性
"""

import os
import json
import shutil
import time
import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import uuid
import zipfile
import base64
from io import BytesIO

from models import (
    Character, Scene, Prop, StyleConfig, StyleMode,
    Shot, StoryboardProject, ShotTemplate, SlotWeights,
    CameraSettings, CompositionSettings, StandardShotPrompt
)
from templates import (
    SHOT_TEMPLATES, get_template, get_template_choices_cn,
    get_template_summary, TEMPLATE_QUICK_REF
)
from prompt_generator import generate_shot_prompt, suggest_next_shot_template, generate_standard_shot_prompt, generate_standard_prompt_text
from image_generator import create_generator, GenerationResult
from smart_import import SmartImporter, FileParser, validate_and_fix_json
from settings import settings, needs_setup
from setup_wizard import run_wizard


# 配置 - 从统一设置加载
API_KEY = settings.api_key

# 使用脚本所在目录作为基础路径，确保路径一致
BASE_DIR = settings.base_dir
ASSETS_DIR = settings.assets_dir
PROJECTS_DIR = settings.projects_dir
OUTPUTS_DIR = settings.outputs_dir
EXPORTS_DIR = settings.exports_dir
EXAMPLES_DIR = settings.examples_dir

# 确保目录存在
settings.ensure_directories()

# 视频尺寸映射（与图片比例一致，但尺寸适合视频生成）
VIDEO_ASPECT_RATIOS = {
    "16:9": (832, 480),     # 宽屏视频
    "9:16": (480, 832),     # 竖屏视频
    "1:1": (640, 640),      # 正方形
    "4:3": (768, 576),      # 经典比例
    "3:4": (576, 768),      # 竖屏
    "21:9": (896, 384)      # 超宽屏
}

# 全局状态
current_project: Optional[StoryboardProject] = None

# 自动保存文件路径
AUTO_SAVE_FILE = os.path.join(PROJECTS_DIR, "_autosave.json")


def auto_save_project() -> bool:
    """自动保存当前项目状态"""
    global current_project
    if current_project is None:
        return False

    try:
        project_data = current_project.to_dict()
        with open(AUTO_SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        print(f"[自动保存] 项目已保存: {current_project.name}")
        return True
    except Exception as e:
        print(f"[自动保存] 保存失败: {e}")
        return False


def manual_save_project() -> str:
    """手动保存项目，返回状态消息"""
    global current_project
    if current_project is None:
        return "❌ 没有项目可保存"

    try:
        project_data = current_project.to_dict()
        with open(AUTO_SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        # 统计信息
        total_shots = len(current_project.shots)
        shots_with_images = sum(1 for s in current_project.shots if s.output_image and os.path.exists(s.output_image))
        shots_with_videos = sum(1 for s in current_project.shots if s.output_video and os.path.exists(s.output_video))

        return f"✅ 已保存: {current_project.name} | 镜头: {total_shots} | 图片: {shots_with_images} | 视频: {shots_with_videos}"
    except Exception as e:
        return f"❌ 保存失败: {e}"


def manual_load_project():
    """手动加载项目，返回状态消息和更新后的卡片"""
    global current_project

    if not os.path.exists(AUTO_SAVE_FILE):
        return "❌ 未找到保存的项目", get_video_cards_html(), get_video_stats_html()

    try:
        with open(AUTO_SAVE_FILE, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        current_project = StoryboardProject.from_dict(project_data)

        # 统计信息
        total_shots = len(current_project.shots)
        shots_with_images = sum(1 for s in current_project.shots if s.output_image and os.path.exists(s.output_image))
        shots_with_videos = sum(1 for s in current_project.shots if s.output_video and os.path.exists(s.output_video))

        status = f"✅ 已加载: {current_project.name} | 镜头: {total_shots} | 图片: {shots_with_images} | 视频: {shots_with_videos}"
        return status, get_video_cards_html(), get_video_stats_html()
    except Exception as e:
        return f"❌ 加载失败: {e}", get_video_cards_html(), get_video_stats_html()


def get_video_for_preview(shot_num: int) -> str:
    """获取指定镜头的视频路径用于预览"""
    global current_project
    if current_project is None:
        return None

    shot_num = int(shot_num)
    if shot_num < 1 or shot_num > len(current_project.shots):
        return None

    shot = current_project.shots[shot_num - 1]
    if shot.output_video and os.path.exists(shot.output_video):
        return shot.output_video
    return None


def auto_load_project() -> bool:
    """服务启动时自动加载上次保存的项目"""
    global current_project

    if not os.path.exists(AUTO_SAVE_FILE):
        print("[自动加载] 未找到自动保存文件")
        return False

    try:
        with open(AUTO_SAVE_FILE, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        current_project = StoryboardProject.from_dict(project_data)

        # 验证图片文件是否存在
        valid_shots = 0
        missing_shots = []
        for shot in current_project.shots:
            if shot.output_image and os.path.exists(shot.output_image):
                valid_shots += 1
            elif shot.output_image:
                print(f"[自动加载] 警告: 镜头 {shot.shot_number} 的图片不存在: {shot.output_image}")
                missing_shots.append(shot)
            else:
                missing_shots.append(shot)

        # 如果有镜头缺少图片，尝试从 outputs 目录扫描关联
        if missing_shots and current_project.name:
            scan_and_link_images(current_project)
            # 重新统计
            valid_shots = sum(1 for s in current_project.shots if s.output_image and os.path.exists(s.output_image))

        print(f"[自动加载] 已加载项目: {current_project.name}")
        print(f"[自动加载] 角色: {len(current_project.characters)}, 场景: {len(current_project.scenes)}, 镜头: {len(current_project.shots)} (有效图片: {valid_shots})")
        return True
    except Exception as e:
        print(f"[自动加载] 加载失败: {e}")
        return False


def scan_and_link_images(project: StoryboardProject) -> int:
    """扫描项目输出目录，尝试将图片与镜头关联"""
    project_output = OUTPUTS_DIR / project.name
    if not project_output.exists():
        print(f"[扫描] 项目输出目录不存在: {project_output}")
        return 0

    # 获取所有图片文件，按修改时间排序
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
        image_files.extend(project_output.glob(ext))

    if not image_files:
        print(f"[扫描] 项目目录中没有图片文件")
        return 0

    # 按修改时间排序（最新的在后面）
    image_files.sort(key=lambda f: f.stat().st_mtime)

    # 统计需要关联的镜头
    shots_need_images = [s for s in project.shots if not s.output_image or not os.path.exists(s.output_image)]
    total_shots = len(project.shots)

    print(f"[扫描] 找到 {len(image_files)} 个图片文件，{len(shots_need_images)} 个镜头需要图片")

    # 策略1: 如果最近的图片数量与镜头数量匹配，按顺序关联
    if len(image_files) >= total_shots:
        # 取最新的 N 个图片（N = 镜头数量）
        recent_images = image_files[-total_shots:]
        linked = 0
        for i, shot in enumerate(project.shots):
            if not shot.output_image or not os.path.exists(shot.output_image):
                shot.output_image = str(recent_images[i])
                # 检查是否有对应的视频
                video_path = recent_images[i].with_suffix('.mp4')
                if video_path.exists():
                    shot.output_video = str(video_path)
                linked += 1
                print(f"[扫描] 镜头 {shot.shot_number} 关联图片: {recent_images[i].name}")

        if linked > 0:
            auto_save_project()
            print(f"[扫描] 已关联 {linked} 个镜头的图片")
        return linked

    # 策略2: 图片数量不足，尝试按时间分组关联最新一批
    print(f"[扫描] 图片数量不足，无法自动关联")
    return 0


def get_image_batches(project_name: str = None) -> List[Dict]:
    """
    扫描项目输出目录，按时间分组图片批次

    Returns:
        批次列表，每个批次包含: {
            'id': 批次ID,
            'time': 生成时间字符串,
            'timestamp': 时间戳,
            'count': 图片数量,
            'files': 文件列表,
            'has_videos': 是否有视频
        }
    """
    global current_project

    if project_name:
        project_output = OUTPUTS_DIR / project_name
    elif current_project:
        project_output = OUTPUTS_DIR / current_project.name
    else:
        return []

    if not project_output.exists():
        return []

    # 获取所有图片文件
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
        image_files.extend(project_output.glob(ext))

    if not image_files:
        return []

    # 按修改时间排序
    image_files.sort(key=lambda f: f.stat().st_mtime)

    # 按时间分组（5分钟内的图片算同一批次）
    batches = []
    current_batch = []
    last_time = None
    batch_threshold = 300  # 5分钟

    for img_file in image_files:
        mtime = img_file.stat().st_mtime
        if last_time is None or (mtime - last_time) < batch_threshold:
            current_batch.append(img_file)
        else:
            if current_batch:
                batches.append(current_batch)
            current_batch = [img_file]
        last_time = mtime

    if current_batch:
        batches.append(current_batch)

    # 转换为结果格式
    result = []
    for i, batch in enumerate(batches):
        first_file = batch[0]
        mtime = first_file.stat().st_mtime
        time_str = datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")

        # 检查是否有视频
        has_videos = any(f.with_suffix('.mp4').exists() for f in batch)

        result.append({
            'id': i,
            'time': time_str,
            'timestamp': mtime,
            'count': len(batch),
            'files': [str(f) for f in batch],
            'has_videos': has_videos
        })

    return result


def get_image_history_choices() -> List[str]:
    """获取图片历史批次选项列表"""
    batches = get_image_batches()
    if not batches:
        return ["无历史记录"]

    choices = []
    for batch in reversed(batches):  # 最新的在前面
        video_mark = " +视频" if batch['has_videos'] else ""
        choices.append(f"[{batch['time']}] {batch['count']}张图片{video_mark}")

    return choices


def _get_batch_from_choice(batch_choice: str):
    """从选择项获取批次数据"""
    if not current_project:
        return None, "请先加载项目"

    if batch_choice == "无历史记录" or not batch_choice:
        return None, "请选择一个历史批次"

    batches = get_image_batches()
    if not batches:
        return None, "没有找到图片历史"

    choices = get_image_history_choices()
    try:
        choice_idx = choices.index(batch_choice)
        batch_idx = len(batches) - 1 - choice_idx
        return batches[batch_idx], None
    except (ValueError, IndexError):
        return None, "无效的批次选择"


def load_images_only(batch_choice: str) -> Tuple[str, str]:
    """只加载图片（不加载视频）"""
    global current_project

    print(f"[加载图片] 开始, 选择: {batch_choice}")

    batch, error = _get_batch_from_choice(batch_choice)
    if error:
        return error, get_shot_cards_html()

    total_shots = len(current_project.shots)
    batch_files = batch['files']

    if len(batch_files) < total_shots:
        return f"该批次只有 {len(batch_files)} 张图片，但项目有 {total_shots} 个镜头", get_shot_cards_html()

    if len(batch_files) > total_shots:
        batch_files = batch_files[-total_shots:]

    linked = 0
    for i, shot in enumerate(current_project.shots):
        img_path = batch_files[i]
        if os.path.exists(img_path):
            shot.output_image = img_path
            shot.output_video = ""  # 清空视频路径
            linked += 1
            print(f"[加载图片] 镜头 {i+1}: {Path(img_path).name}")

    auto_save_project()

    result_msg = f"[OK] 已加载 {linked} 张图片 (视频未加载)"
    print(f"[加载图片] 完成: {linked} 张")
    return result_msg, get_shot_cards_html()


def load_videos_only(batch_choice: str) -> Tuple[str, str]:
    """只加载视频（基于当前图片路径）"""
    global current_project

    print(f"[加载视频] 开始, 选择: {batch_choice}")

    if not current_project:
        return "请先加载项目", get_shot_cards_html()

    # 检查是否有图片
    shots_with_images = [s for s in current_project.shots if s.output_image and os.path.exists(s.output_image)]
    if not shots_with_images:
        return "请先加载图片", get_shot_cards_html()

    linked_videos = 0
    for shot in current_project.shots:
        if shot.output_image and os.path.exists(shot.output_image):
            video_path = Path(shot.output_image).with_suffix('.mp4')
            if video_path.exists():
                shot.output_video = str(video_path)
                linked_videos += 1
                print(f"[加载视频] 镜头 {shot.shot_number}: {video_path.name}")
            else:
                shot.output_video = ""

    auto_save_project()

    if linked_videos > 0:
        result_msg = f"[OK] 已加载 {linked_videos} 个视频"
    else:
        result_msg = "未找到对应的视频文件"
    print(f"[加载视频] 完成: {linked_videos} 个")
    return result_msg, get_shot_cards_html()


def load_image_batch(batch_choice: str) -> Tuple[str, str]:
    """加载选中的图片批次（同时加载图片和视频）"""
    global current_project

    print(f"[加载历史] 开始加载, 选择: {batch_choice}")

    batch, error = _get_batch_from_choice(batch_choice)
    if error:
        return error, get_shot_cards_html()

    total_shots = len(current_project.shots)
    batch_files = batch['files']
    print(f"[加载历史] 批次文件数: {len(batch_files)}, 镜头数: {total_shots}")

    if len(batch_files) < total_shots:
        return f"该批次只有 {len(batch_files)} 张图片，但项目有 {total_shots} 个镜头", get_shot_cards_html()

    if len(batch_files) > total_shots:
        batch_files = batch_files[-total_shots:]

    linked = 0
    linked_videos = 0
    for i, shot in enumerate(current_project.shots):
        img_path = batch_files[i]
        if os.path.exists(img_path):
            shot.output_image = img_path
            video_path = Path(img_path).with_suffix('.mp4')
            if video_path.exists():
                shot.output_video = str(video_path)
                linked_videos += 1
            else:
                shot.output_video = ""
            linked += 1
            print(f"[加载历史] 镜头 {i+1}: {Path(img_path).name}")

    auto_save_project()

    video_info = f", {linked_videos} 个视频" if linked_videos > 0 else ""
    result_msg = f"[OK] 已加载 {linked} 张图片{video_info}"
    print(f"[加载历史] 完成: {linked} 张图片{video_info}")
    return result_msg, get_shot_cards_html()


# 服务启动时自动加载
auto_load_project()


def auto_connect_comfyui() -> bool:
    """服务启动时自动连接 ComfyUI"""
    try:
        import requests
        host = settings.comfyui_host
        port = settings.comfyui_port

        # 检查 ComfyUI 是否可用
        resp = requests.get(f"http://{host}:{port}/system_stats", timeout=3)
        if resp.status_code == 200:
            # ComfyUI 可用，尝试连接
            service = get_ai_service()
            result = service.initialize_comfyui(host, int(port))
            if result["success"]:
                print(f"[自动连接] ComfyUI 已连接: {host}:{port}")
                return True
            else:
                print(f"[自动连接] ComfyUI 连接失败: {result['message']}")
                return False
        else:
            print(f"[自动连接] ComfyUI 不可用 (状态码: {resp.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[自动连接] ComfyUI 未运行或无法访问: {e}")
        return False
    except Exception as e:
        print(f"[自动连接] 连接错误: {e}")
        return False


# 注意: auto_connect_comfyui() 在 main 中调用，避免模块加载时的函数定义顺序问题


# ========================================
# 故事范例数据
# ========================================
EXAMPLE_STORIES = {
    "马到成功送祝福": {
        "name": "马到成功送祝福",
        "description": "Q萌小胖马送福上门的欢乐故事",
        "aspect_ratio": "16:9",
        "style": "2D卡通",
        "characters": [
            {"name": "福宝马", "description": "超级Q萌的胖胖小马吉祥物，圆滚滚的身体，大大的眼睛闪闪发光，粉嫩的脸蛋，穿着红色小马甲，背着金色福袋，走路一颠一颠超可爱，2D卡通风格"},
            {"name": "乐乐", "description": "8岁Q萌小男孩，圆脸大眼睛，穿红色马图案新衣，戴可爱的马头帽，手拿小马灯笼，2D卡通风格"},
            {"name": "李爷爷", "description": "Q版70岁老爷爷，圆圆的脸，笑眯眯的眼睛，穿红色唐装，胸前绣着骏马图案，慈祥可爱，2D卡通风格"}
        ],
        "scenes": [
            {"name": "马年装饰街道", "description": "2D卡通风格的喜庆街道，Q萌马形灯笼高挂，红色横幅飘扬，到处是可爱的马年装饰"},
            {"name": "福气满堂客厅", "description": "2D卡通风格的温馨客厅，墙上挂着Q版骏马图，窗花是萌萌的马剪纸，茶几上摆着马形糖果盒"}
        ],
        "shots": [
            {"template": "全景", "description": "2D卡通风格的马年气氛街道，Q萌马形灯笼成排挂起，红色横幅写着马到成功", "characters": [], "scene": "马年装饰街道"},
            {"template": "中景", "description": "Q萌福宝马蹦蹦跳跳走在街上，胖胖的身体一颠一颠，背上的福袋晃来晃去，超级可爱", "characters": ["福宝马"], "scene": "马年装饰街道"},
            {"template": "中景", "description": "乐乐看到福宝马，兴奋地跑过去：哇！是马年福星！福宝马眨眨大眼睛", "characters": ["乐乐", "福宝马"], "scene": "马年装饰街道"},
            {"template": "特写", "description": "福宝马用小蹄子从福袋里掏出金色马蹄铁挂件，眼睛弯成月牙：送你马到成功！", "characters": ["福宝马"], "scene": "马年装饰街道"},
            {"template": "中景", "description": "乐乐牵着福宝马的小蹄子来到李爷爷家，爷爷开门看到惊喜万分", "characters": ["乐乐", "福宝马", "李爷爷"], "scene": "福气满堂客厅"},
            {"template": "特写", "description": "李爷爷笑眯眯地摸摸福宝马的头：马年来了福马，今年一定龙马精神！", "characters": ["李爷爷", "福宝马"], "scene": "福气满堂客厅"},
            {"template": "全景", "description": "大家围坐一起，福宝马跳着萌萌的马蹄舞，胖胖的身体扭来扭去，欢声笑语", "characters": ["福宝马", "乐乐", "李爷爷"], "scene": "福气满堂客厅"}
        ]
    },
    "骏马奔腾迎新年": {
        "name": "骏马奔腾迎新年",
        "description": "Q萌福宝马和马家团圆的温馨故事",
        "aspect_ratio": "16:9",
        "style": "2D卡通",
        "characters": [
            {"name": "福宝马", "description": "超级Q萌的胖胖小马吉祥物，圆滚滚的身体，大大的眼睛闪闪发光，粉嫩的脸蛋，穿着红色小马甲，背着金色福袋，走路一颠一颠超可爱，2D卡通风格"},
            {"name": "马爷爷", "description": "Q版75岁老爷爷，圆脸白胡子，穿红色马褂绣金马，笑呵呵的样子很慈祥，2D卡通风格"},
            {"name": "马奶奶", "description": "Q版72岁老奶奶，圆脸盘发，穿红旗袍绣骏马，温柔可爱，2D卡通风格"},
            {"name": "马叔叔", "description": "Q版中年人，圆脸微胖，穿红毛衣印奔马图，憨厚可爱，2D卡通风格"},
            {"name": "小马驹", "description": "Q萌8岁小男孩，大眼睛圆脸蛋，穿马宝宝连体衣，活泼好动像小马驹，2D卡通风格"}
        ],
        "scenes": [
            {"name": "马家大院", "description": "2D卡通风格的喜庆四合院，门口贴着Q版骏马春联，院里摆着萌萌的马形花灯"},
            {"name": "马年厨房", "description": "2D卡通风格的热闹厨房，到处是Q萌马年装饰，案板上摆着马蹄糕材料"}
        ],
        "shots": [
            {"template": "全景", "description": "2D卡通风格的马家大院张灯结彩，福宝马站在门口迎客，Q萌马灯璀璨", "characters": ["福宝马"], "scene": "马家大院"},
            {"template": "中景", "description": "马奶奶在厨房做马蹄糕，福宝马在旁边帮忙递材料，超级可爱", "characters": ["马奶奶", "福宝马"], "scene": "马年厨房"},
            {"template": "中景", "description": "马叔叔端着马蹄形拼盘上桌，福宝马跟在后面一蹦一跳：马到成功！", "characters": ["马叔叔", "福宝马"], "scene": "马家大院"},
            {"template": "全景", "description": "马家人和福宝马围坐圆桌，胖胖的福宝马坐在小凳子上，其乐融融", "characters": ["马爷爷", "马奶奶", "马叔叔", "小马驹", "福宝马"], "scene": "马家大院"},
            {"template": "特写", "description": "马爷爷举杯，福宝马也举起小蹄子：马年要龙马精神，一马当先！", "characters": ["马爷爷", "福宝马"], "scene": "马家大院"},
            {"template": "中景", "description": "小马驹和福宝马一起收红包，两个小家伙开心得蹦蹦跳跳", "characters": ["小马驹", "福宝马", "马爷爷"], "scene": "马家大院"},
            {"template": "特写", "description": "窗外烟花绽放，福宝马眼睛亮晶晶，全家齐喊：马年大吉！", "characters": ["福宝马", "马爷爷", "马奶奶", "小马驹"], "scene": "马家大院"}
        ]
    },
    "马上有美食": {
        "name": "马上有美食",
        "description": "Q萌福宝马带你吃遍马年美食",
        "aspect_ratio": "16:9",
        "style": "2D卡通",
        "characters": [
            {"name": "福宝马", "description": "超级Q萌的胖胖小马吉祥物，圆滚滚的身体，大大的眼睛闪闪发光，粉嫩的脸蛋，穿着红色小马甲，背着金色福袋，走路一颠一颠超可爱，2D卡通风格"},
            {"name": "马厨娘", "description": "Q版中年女士，圆脸红润，穿马图案围裙，手艺精湛，笑容满面，2D卡通风格"},
            {"name": "小马妹", "description": "Q萌7岁小女孩，大眼睛马尾辫，穿小马图案裙子，看到美食眼睛发亮，2D卡通风格"}
        ],
        "scenes": [
            {"name": "马年厨房", "description": "2D卡通风格的热闹厨房，墙上贴着Q萌马年菜谱，案板上摆满马蹄糕材料"},
            {"name": "马年宴席", "description": "2D卡通风格的圆桌上摆满Q萌马年主题美食，中间是马形蛋糕"}
        ],
        "shots": [
            {"template": "全景", "description": "2D卡通风格的马年厨房，福宝马戴着小厨师帽站在案板前，超级可爱", "characters": ["福宝马"], "scene": "马年厨房"},
            {"template": "特写", "description": "晶莹剔透的Q萌马蹄糕出锅，福宝马眼睛发亮，流口水的样子超可爱", "characters": ["福宝马"], "scene": "马年厨房"},
            {"template": "中景", "description": "马厨娘教小马妹和福宝马一起做马卡龙，三个人其乐融融", "characters": ["马厨娘", "小马妹", "福宝马"], "scene": "马年厨房"},
            {"template": "特写", "description": "福宝马用小蹄子捧着金黄的炸马蹄，鼓着腮帮子吹凉", "characters": ["福宝马"], "scene": "马年厨房"},
            {"template": "中景", "description": "福宝马帮忙搅拌马蹄糕，胖胖的身体跟着节奏晃动，超级萌", "characters": ["福宝马", "马厨娘"], "scene": "马年厨房"},
            {"template": "特写", "description": "小马妹和福宝马一起偷吃马蹄糕，两个小家伙甜得眯起眼睛", "characters": ["小马妹", "福宝马"], "scene": "马年厨房"},
            {"template": "全景", "description": "满桌Q萌马年美食，福宝马坐在中间，开心得手舞足蹈", "characters": ["福宝马"], "scene": "马年宴席"},
            {"template": "中景", "description": "大家围桌品尝，福宝马捧着盘子：吃了这桌菜，马上有福气！", "characters": ["马厨娘", "小马妹", "福宝马"], "scene": "马年宴席"}
        ]
    }
}


# ========================================
# 专业CSS样式
# ========================================
CUSTOM_CSS = """
:root {
    --pure-white: #ffffff;
    --soft-white: #fafafa;
    --light-gray: #f5f5f7;
    --medium-gray: #d2d2d7;
    --dark-gray: #86868b;
    --near-black: #1d1d1f;
    --apple-blue: #0071e3;
    --apple-blue-hover: #0077ed;
    --success-green: #34c759;
    --warning-orange: #ff9500;
    --error-red: #ff3b30;
}

* { box-sizing: border-box; }

.gradio-container {
    background: var(--soft-white) !important;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Noto Sans SC', sans-serif !important;
    color: var(--near-black) !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
    padding: 0 24px !important;
}

.app-title {
    text-align: center;
    padding: 40px 0 30px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.app-title h1 {
    font-size: 42px !important;
    font-weight: 700 !important;
    margin: 0 0 8px 0 !important;
}

.app-title p {
    font-size: 18px !important;
    color: var(--dark-gray) !important;
    -webkit-text-fill-color: var(--dark-gray);
}

input[type="text"], textarea {
    background: #111a22 !important;
    border: 1px solid #233648 !important;
    border-radius: 8px !important;
    padding: 12px 14px !important;
    font-size: 15px !important;
    color: #e2e8f0 !important;
}

input[type="text"]::placeholder, textarea::placeholder {
    color: #6b8299 !important;
    opacity: 1 !important;
}

input[type="text"]:focus, textarea:focus {
    background: #16202a !important;
    border-color: #137fec !important;
    box-shadow: 0 0 0 2px rgba(19, 127, 236, 0.2) !important;
    outline: none !important;
}

/* 隐藏 Gradio 默认的 "单选框" 和 "Textbox" 标签 */
.gradio-container span.sr-only,
label.block span:only-child:empty + span,
.wrap span[data-testid="block-label"]:empty {
    display: none !important;
}

/* 隐藏无用的标签文字 */
.block > span:first-child:not([class]) {
    display: none !important;
}

.primary-btn {
    background: var(--apple-blue) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.primary-btn:hover {
    background: var(--apple-blue-hover) !important;
    transform: translateY(-1px) !important;
}

.secondary-btn {
    background: transparent !important;
    color: var(--apple-blue) !important;
    border: 1px solid var(--apple-blue) !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 15px !important;
}

.secondary-btn:hover {
    background: rgba(0, 113, 227, 0.1) !important;
}

.success-btn {
    background: var(--success-green) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 15px !important;
}

.warning-btn {
    background: var(--warning-orange) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
}

.example-card {
    background: white;
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    cursor: pointer;
    transition: all 0.2s;
}

.example-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    transform: translateY(-2px);
}

.stats-panel {
    display: flex;
    justify-content: center;
    gap: 40px;
    padding: 20px;
    background: white;
    border-radius: 12px;
    margin: 16px 0;
}

.stat-item {
    text-align: center;
}

.stat-value {
    font-size: 28px;
    font-weight: 600;
    color: var(--near-black);
}

.stat-label {
    font-size: 12px;
    color: var(--dark-gray);
    margin-top: 4px;
}

footer { display: none !important; }

.gradio-container label:empty { display: none !important; }

/* 隐藏触发器行 (保持在DOM中以供JavaScript访问) */
.hidden-trigger-row {
    position: absolute !important;
    left: -9999px !important;
    height: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}
.hidden-trigger-row * {
    pointer-events: auto !important;
}
"""


# ========================================
# 工具函数
# ========================================

def save_uploaded_image(image, category: str, name: str) -> str:
    """保存上传的图片"""
    if image is None:
        return ""

    save_dir = ASSETS_DIR / category
    save_dir.mkdir(parents=True, exist_ok=True)

    ext = ".png"
    filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = save_dir / filename

    if isinstance(image, str):
        if os.path.exists(image):
            shutil.copy(image, save_path)
    else:
        try:
            from PIL import Image
            if hasattr(image, 'save'):
                image.save(save_path)
            else:
                Image.fromarray(image).save(save_path)
        except:
            return ""

    return str(save_path)


def save_multiple_images(images: List, category: str, name: str) -> List[str]:
    """批量保存图片"""
    paths = []
    if images:
        for i, img in enumerate(images):
            path = save_uploaded_image(img, category, f"{name}_{i}")
            if path:
                paths.append(path)
    return paths


# ========================================
# 核心功能函数
# ========================================

def create_project(name: str, ratio: str) -> Tuple[str, bool]:
    """创建新项目"""
    global current_project

    if not name.strip():
        name = "我的分镜"

    current_project = StoryboardProject(
        name=name,
        aspect_ratio=ratio
    )

    return f"✓ 项目「{name}」已创建", True


def generate_story_from_idea(story_idea: str):
    """
    从一句话创意生成完整的分镜故事
    使用系统配置的 AI 服务分析并生成角色、场景、镜头
    """
    global current_project
    import re

    empty_return = (
        "请输入故事创意",
        "", "", [], [], [],
        gr.update(choices=[]), gr.update(choices=[]),
        gr.update(choices=[]), gr.update(choices=[]),
        "电影感", "", "",
        get_workflow_indicator(0),
        "", "", "",
        '<div class="no-shots">暂无镜头</div>'
    )

    if not story_idea or not story_idea.strip():
        return empty_return

    try:
        # 使用 AI 服务分析故事
        service = get_ai_service()
        result = service.analyze_story(story_idea.strip())

        if not result.get("success"):
            return (
                f"AI 分析失败: {result.get('message', '未知错误')}",
                "", "", [], [], [],
                gr.update(choices=[]), gr.update(choices=[]),
                gr.update(choices=[]), gr.update(choices=[]),
                "电影感", "", "",
                get_workflow_indicator(0),
                "", "", "",
                '<div class="no-shots">暂无镜头</div>'
            )

        # 从分析结果创建项目
        project_name = result.get("project_name", "AI生成的故事")
        current_project = StoryboardProject(
            name=project_name,
            aspect_ratio="16:9"
        )

        # 设置风格
        style_name = "电影感"
        set_style(style_name)

        # 添加角色
        for char_data in result.get("characters", []):
            char = Character(
                name=char_data.get("name", "未命名角色"),
                description=char_data.get("description") or char_data.get("appearance", ""),
                consistency_weight=0.85
            )
            current_project.characters.append(char)

        # 添加场景
        for scene_data in result.get("scenes", []):
            scene = Scene(
                name=scene_data.get("name", "未命名场景"),
                description=scene_data.get("description", ""),
                consistency_weight=0.7
            )
            current_project.scenes.append(scene)

        # 添加镜头 - 优先使用AI生成的镜头数据
        ai_shots = result.get("shots", [])
        template_map = {
            "全景": ShotTemplate.T1_ESTABLISHING_WIDE,
            "中景": ShotTemplate.T4_STANDARD_MEDIUM,
            "特写": ShotTemplate.T6_CLOSEUP,
            "过肩": ShotTemplate.T5_OVER_SHOULDER,
            "低角度": ShotTemplate.T7_LOW_ANGLE,
            "跟随": ShotTemplate.T8_FOLLOWING,
        }

        if ai_shots:
            # 使用AI生成的镜头数据
            for i, shot_data in enumerate(ai_shots):
                template_name = shot_data.get("template", "中景")
                template_type = template_map.get(template_name, ShotTemplate.T4_STANDARD_MEDIUM)
                template_def = get_template(template_type)

                # 查找角色ID
                char_ids = []
                for cname in shot_data.get("characters", []):
                    for c in current_project.characters:
                        if c.name == cname:
                            char_ids.append(c.id)
                            break

                # 查找场景ID
                scene_id = ""
                scene_name = shot_data.get("scene", "")
                for s in current_project.scenes:
                    if s.name == scene_name:
                        scene_id = s.id
                        break
                if not scene_id and current_project.scenes:
                    scene_id = current_project.scenes[i % len(current_project.scenes)].id

                shot = Shot(
                    shot_number=i + 1,
                    template=template_type,
                    description=shot_data.get("description", f"镜头 {i+1}"),
                    characters_in_shot=char_ids if char_ids else [c.id for c in current_project.characters[:2]],
                    scene_id=scene_id,
                    camera=template_def.camera if template_def else CameraSettings(),
                    composition=template_def.composition if template_def else CompositionSettings(),
                    slot_weights=SlotWeights(character=0.85, scene=0.5, props=0.6, style=0.4)
                )
                shot.generated_prompt = generate_shot_prompt(shot, current_project)
                shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)
                current_project.shots.append(shot)
        elif current_project.characters and current_project.scenes:
            # 如果没有AI生成的镜头，使用默认模板
            shot_templates = [
                (ShotTemplate.T1_ESTABLISHING_WIDE, "全景展示场景环境"),
                (ShotTemplate.T4_STANDARD_MEDIUM, "人物中景互动"),
                (ShotTemplate.T6_CLOSEUP, "特写表情细节"),
                (ShotTemplate.T5_OVER_SHOULDER, "过肩对话镜头"),
                (ShotTemplate.T4_STANDARD_MEDIUM, "中景动作场景"),
                (ShotTemplate.T6_CLOSEUP, "特写情感高潮"),
                (ShotTemplate.T1_ESTABLISHING_WIDE, "结尾全景收束"),
            ]

            for i, (template_type, desc_hint) in enumerate(shot_templates):
                template_def = get_template(template_type)
                char_ids = [c.id for c in current_project.characters[:2]]
                scene_id = current_project.scenes[i % len(current_project.scenes)].id

                shot = Shot(
                    shot_number=i + 1,
                    template=template_type,
                    description=f"{desc_hint} - {story_idea[:30]}",
                    characters_in_shot=char_ids,
                    scene_id=scene_id,
                    camera=template_def.camera if template_def else CameraSettings(),
                    composition=template_def.composition if template_def else CompositionSettings(),
                    slot_weights=SlotWeights(character=0.85, scene=0.5, props=0.6, style=0.4)
                )
                shot.generated_prompt = generate_shot_prompt(shot, current_project)
                shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)
                current_project.shots.append(shot)

        # 获取角色和场景名称列表
        char_names = get_character_names()
        scene_names = get_scene_names()

        # 获取第一个镜头的提示语
        first_standard_prompt = ""
        first_generated_prompt = ""
        if current_project.shots:
            first_shot = current_project.shots[0]
            first_standard_prompt = first_shot.standard_prompt or ""
            first_generated_prompt = first_shot.generated_prompt or ""

        char_count = len(current_project.characters)
        scene_count = len(current_project.scenes)
        shot_count = len(current_project.shots)

        # 自动保存
        auto_save_project()

        return (
            f"[OK] 已生成「{project_name}」- {char_count}角色, {scene_count}场景, {shot_count}镜头",
            get_project_summary(),
            result.get("description", ""),
            get_character_list(),
            get_scene_list(),
            get_shot_list(),
            gr.update(choices=char_names, value=char_names[0] if char_names else None),
            gr.update(choices=scene_names, value=scene_names[0] if scene_names else None),
            gr.update(choices=char_names),
            gr.update(choices=scene_names, value=scene_names[0] if scene_names else None),
            style_name,
            first_standard_prompt,
            first_generated_prompt,
            get_workflow_indicator(3),
            get_step_summary(2),
            get_step_summary(3),
            get_step_summary(4),
            get_shot_cards_html()
        )

    except Exception as e:
        print(f"[一句话生成] 错误: {e}")
        return (
            f"生成失败: {str(e)[:100]}",
            "", "", [], [], [],
            gr.update(choices=[]), gr.update(choices=[]),
            gr.update(choices=[]), gr.update(choices=[]),
            "电影感", "", "",
            get_workflow_indicator(0),
            "", "", "",
            '<div class="no-shots">暂无镜头</div>'
        )


def load_example_story(story_name: str):
    """加载故事范例 - 返回所有需要更新的 UI 元素数据"""
    global current_project

    if story_name not in EXAMPLE_STORIES:
        return (
            "范例不存在", "", "", [], [], [],
            gr.update(choices=[]), gr.update(choices=[]),
            gr.update(choices=[]), gr.update(choices=[]),
            "2D卡通", "", "",
            get_workflow_indicator(0),
            "", "", "",  # step summaries
            '<div class="no-shots">暂无镜头</div>'  # shot_cards_html
        )

    example = EXAMPLE_STORIES[story_name]

    # 检查是否已有同名项目（包含已生成的图片）
    if os.path.exists(AUTO_SAVE_FILE):
        try:
            with open(AUTO_SAVE_FILE, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            saved_name = saved_data.get("project_meta", {}).get("name", "")
            if saved_name == example["name"]:
                # 加载已保存的项目（保留图片和视频路径）
                current_project = StoryboardProject.from_dict(saved_data)
                print(f"[加载范例] 恢复已保存的项目: {saved_name}")

                # 检查是否有镜头缺少图片，尝试扫描关联
                missing_images = sum(1 for s in current_project.shots if not s.output_image or not os.path.exists(s.output_image))
                if missing_images > 0:
                    print(f"[加载范例] 发现 {missing_images} 个镜头缺少图片，尝试扫描关联...")
                    scan_and_link_images(current_project)

                # 验证并统计有效资源
                valid_images = 0
                valid_videos = 0
                for shot in current_project.shots:
                    if shot.output_image and os.path.exists(shot.output_image):
                        valid_images += 1
                    if shot.output_video and os.path.exists(shot.output_video):
                        valid_videos += 1

                # 重新生成所有提示词（确保包含最新风格）
                for shot in current_project.shots:
                    shot.generated_prompt = generate_shot_prompt(shot, current_project)
                print(f"[加载范例] 已重新生成 {len(current_project.shots)} 个镜头的提示词")
                auto_save_project()

                # 获取 UI 数据
                char_names = get_character_names()
                scene_names = get_scene_names()
                first_standard_prompt = ""
                first_generated_prompt = ""
                if current_project.shots:
                    first_shot = current_project.shots[0]
                    first_standard_prompt = first_shot.standard_prompt or ""
                    first_generated_prompt = first_shot.generated_prompt or ""

                status_msg = f"✓ 已恢复项目「{saved_name}」- {valid_images} 张图片, {valid_videos} 个视频"
                return (
                    status_msg,
                    get_project_summary(),
                    example["description"],
                    get_character_list(),
                    get_scene_list(),
                    get_shot_list(),
                    gr.update(choices=char_names), gr.update(choices=scene_names),
                    gr.update(choices=char_names), gr.update(choices=scene_names),
                    example["style"], first_standard_prompt, first_generated_prompt,
                    get_workflow_indicator(2 if valid_images > 0 else 1),
                    get_step_summary(2),
                    get_step_summary(3),
                    get_step_summary(4),
                    get_shot_cards_html()
                )
        except Exception as e:
            print(f"[加载范例] 恢复失败，创建新项目: {e}")

    # 创建新项目
    current_project = StoryboardProject(
        name=example["name"],
        aspect_ratio=example["aspect_ratio"]
    )

    # 设置风格
    set_style(example["style"])

    # 添加角色
    for char_data in example["characters"]:
        char = Character(
            name=char_data["name"],
            description=char_data["description"],
            consistency_weight=0.85
        )
        current_project.characters.append(char)

    # 添加场景
    for scene_data in example["scenes"]:
        scene = Scene(
            name=scene_data["name"],
            description=scene_data["description"],
            consistency_weight=0.7
        )
        current_project.scenes.append(scene)

    # 添加镜头
    for shot_data in example["shots"]:
        template_map = {
            "全景": ShotTemplate.T1_ESTABLISHING_WIDE,
            "中景": ShotTemplate.T4_STANDARD_MEDIUM,
            "特写": ShotTemplate.T6_CLOSEUP,
            "过肩": ShotTemplate.T5_OVER_SHOULDER,
            "低角度": ShotTemplate.T7_LOW_ANGLE,
            "跟随": ShotTemplate.T8_FOLLOWING,
        }

        template_type = template_map.get(shot_data["template"], ShotTemplate.T4_STANDARD_MEDIUM)
        template_def = get_template(template_type)

        # 查找角色ID
        char_ids = []
        for cname in shot_data.get("characters", []):
            for c in current_project.characters:
                if c.name == cname:
                    char_ids.append(c.id)
                    break

        # 查找场景ID
        scene_id = ""
        for s in current_project.scenes:
            if s.name == shot_data.get("scene", ""):
                scene_id = s.id
                break

        shot = Shot(
            shot_number=len(current_project.shots) + 1,
            template=template_type,
            description=shot_data["description"],
            characters_in_shot=char_ids,
            scene_id=scene_id,
            camera=template_def.camera if template_def else CameraSettings(),
            composition=template_def.composition if template_def else CompositionSettings(),
            slot_weights=SlotWeights(
                character=0.85,
                scene=0.5,
                props=0.6,
                style=0.4
            )
        )
        shot.generated_prompt = generate_shot_prompt(shot, current_project)
        shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)
        current_project.shots.append(shot)

    # 获取角色和场景名称列表
    char_names = get_character_names()
    scene_names = get_scene_names()

    # 获取第一个镜头的提示语
    first_standard_prompt = ""
    first_generated_prompt = ""
    if current_project.shots:
        first_shot = current_project.shots[0]
        first_standard_prompt = first_shot.standard_prompt or ""
        first_generated_prompt = first_shot.generated_prompt or ""

    # 自动保存
    auto_save_project()

    return (
        f"✓ 已加载范例「{story_name}」- 角色/场景/镜头已自动创建，请进入【③ 生成】生成图像",
        get_project_summary(),
        example["description"],
        get_character_list(),
        get_scene_list(),
        get_shot_list(),
        gr.update(choices=char_names, value=char_names[0] if char_names else None),  # del_char_name
        gr.update(choices=scene_names, value=scene_names[0] if scene_names else None),  # del_scene_name
        gr.update(choices=char_names),  # shot_chars (编排页面的角色选择)
        gr.update(choices=scene_names, value=scene_names[0] if scene_names else None),  # shot_scene (编排页面的场景选择)
        example["style"],  # style_choice
        first_standard_prompt,  # standard_prompt
        first_generated_prompt,  # generated_prompt
        get_workflow_indicator(3),  # workflow_step_indicator - 跳到第3步生成
        get_step_summary(2),  # step2_summary
        get_step_summary(3),  # step3_summary
        get_step_summary(4),  # step4_summary
        get_shot_cards_html()  # shot_cards_html - 镜头卡片
    )


def add_character_with_multi_images(
    name: str, description: str, ref_images: List,
    gender: str = "", age: str = "", ethnicity: str = "",
    hair_color: str = "", hair_style: str = "", eye_color: str = "",
    body_type: str = "", skin_tone: str = "", glasses: str = "",
    other_features: str = "",
    costume_locked: bool = False,
    top: str = "", top_color: str = "",
    bottom: str = "", bottom_color: str = "",
    outerwear: str = "", accessories: str = ""
) -> Tuple[str, List]:
    """添加角色（支持多图和外貌一致性设置）"""
    global current_project
    from models import CharacterAppearance, CharacterOutfit

    if current_project is None:
        return "请先创建项目", []

    if not name.strip():
        return "请输入角色名称", get_character_list()

    # 保存多张图片
    ref_paths = []
    if ref_images:
        for i, img in enumerate(ref_images):
            if img is not None:
                path = save_uploaded_image(img, "characters", f"{name}_{i}")
                if path:
                    ref_paths.append(path)

    # 创建外貌对象
    appearance = CharacterAppearance(
        gender=gender or "",
        age=age or "",
        ethnicity=ethnicity or "",
        skin_tone=skin_tone or "",
        body_type=body_type or "",
        hair_color=hair_color or "",
        hair_style=hair_style or "",
        eye_color=eye_color or "",
        glasses=glasses or "",
        other_features=other_features or ""
    )

    # 创建服装对象
    outfit = CharacterOutfit(
        top=top or "",
        top_color=top_color or "",
        bottom=bottom or "",
        bottom_color=bottom_color or "",
        outerwear=outerwear or "",
        accessories=accessories or ""
    )

    char = Character(
        name=name,
        description=description,
        ref_images=ref_paths,
        consistency_weight=0.85,
        appearance=appearance,
        outfit=outfit,
        costume_locked=costume_locked
    )
    current_project.characters.append(char)

    # 统计填写的外貌字段数量
    appearance_count = sum(1 for v in [gender, age, ethnicity, hair_color, hair_style, eye_color, body_type, skin_tone, glasses, other_features] if v)
    img_count = len(ref_paths)

    status = f"✓ 角色「{name}」已添加 ({img_count}张参考图"
    if appearance_count > 0:
        status += f", {appearance_count}项外貌特征"
    status += ")"

    return status, get_character_list()


def add_scene_with_multi_images(name: str, description: str, ref_images: List) -> Tuple[str, List]:
    """添加场景（支持多图）"""
    global current_project

    if current_project is None:
        return "请先创建项目", []

    if not name.strip():
        return "请输入场景名称", get_scene_list()

    # 保存多张图片
    ref_paths = []
    space_ref = ""
    if ref_images:
        for i, img in enumerate(ref_images):
            if img is not None:
                path = save_uploaded_image(img, "scenes", f"{name}_{i}")
                if path:
                    ref_paths.append(path)
                    if i == 0:
                        space_ref = path

    scene = Scene(
        name=name,
        description=description,
        space_ref_image=space_ref,
        consistency_weight=0.7
    )
    current_project.scenes.append(scene)

    img_count = len(ref_paths)
    return f"✓ 场景「{name}」已添加 ({img_count}张参考图)", get_scene_list()


# 全局风格锁定状态
style_locked = True
locked_style_name = "2D卡通"


def get_style_options(category: str):
    """根据风格类型获取详细选项"""
    if category == "2D":
        return gr.update(choices=["2D卡通", "动漫风", "漫画风", "水彩画"], value="2D卡通")
    else:  # 3D
        return gr.update(choices=["3D写实", "电影感", "游戏CG", "赛博朋克"], value="3D写实")


def toggle_style_lock(locked: bool):
    """切换风格锁定状态"""
    global style_locked
    style_locked = locked
    if locked:
        return gr.update(visible=True, value='<div style="font-size:11px;color:#22c55e;padding:4px 0;">🔒 风格已锁定，所有镜头将使用统一风格</div>')
    else:
        return gr.update(visible=True, value='<div style="font-size:11px;color:#f59e0b;padding:4px 0;">🔓 风格未锁定，每个镜头可单独设置</div>')


def set_style(style_name: str) -> str:
    """设置风格"""
    global current_project, locked_style_name

    if current_project is None:
        return "请先创建项目"

    style_map = {
        # 2D 风格
        "2D卡通": ("Cartoon2D", "cartoon", "soft"),
        "动漫风": ("Anime", "anime", "natural"),
        "漫画风": ("Comic", "comic", "natural"),
        "水彩画": ("Watercolor", "watercolor", "natural"),
        # 3D 风格
        "3D写实": ("Realistic3D", "3d_render", "studio"),
        "电影感": ("Cinematic", "realistic", "cinematic"),
        "游戏CG": ("GameCG", "3d_render", "cinematic"),
        "赛博朋克": ("Cyberpunk", "3d_render", "neon"),
    }

    preset, render, light = style_map.get(style_name, ("Cartoon2D", "cartoon", "soft"))
    locked_style_name = style_name

    current_project.style = StyleConfig(
        mode=StyleMode.PRESET,
        preset_name=preset,
        render_type=render,
        lighting_style=light,
        weight=0.4
    )

    lock_status = "🔒" if style_locked else "🔓"
    return f"✓ 风格已设为「{style_name}」{lock_status}"


def add_shot_simple(
    template_name: str,
    description: str,
    character_names: List[str],
    scene_name: str
) -> Tuple[str, List, str, str]:
    """添加镜头"""
    global current_project

    if current_project is None:
        return "请先创建项目", [], "", ""

    template_map = {
        "全景": ShotTemplate.T1_ESTABLISHING_WIDE,
        "中景": ShotTemplate.T4_STANDARD_MEDIUM,
        "特写": ShotTemplate.T6_CLOSEUP,
        "过肩": ShotTemplate.T5_OVER_SHOULDER,
        "低角度": ShotTemplate.T7_LOW_ANGLE,
        "跟随": ShotTemplate.T8_FOLLOWING,
    }

    template_type = template_map.get(template_name, ShotTemplate.T4_STANDARD_MEDIUM)
    template_def = get_template(template_type)

    char_ids = []
    for cname in (character_names or []):
        for c in current_project.characters:
            if c.name == cname:
                char_ids.append(c.id)
                break

    scene_id = ""
    for s in current_project.scenes:
        if s.name == scene_name:
            scene_id = s.id
            break

    shot = Shot(
        shot_number=len(current_project.shots) + 1,
        template=template_type,
        description=description,
        characters_in_shot=char_ids,
        scene_id=scene_id,
        camera=template_def.camera if template_def else CameraSettings(),
        composition=template_def.composition if template_def else CompositionSettings(),
        slot_weights=SlotWeights(
            character=template_def.slot_weights.character if template_def else 0.85,
            scene=template_def.slot_weights.scene if template_def else 0.5,
            props=0.6,
            style=0.4
        )
    )

    shot.generated_prompt = generate_shot_prompt(shot, current_project)
    # 生成标准提示语
    shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)
    current_project.shots.append(shot)

    standard_prompt_text = shot.standard_prompt.to_formatted_string()
    return f"✓ 镜头 {shot.shot_number} 已添加", get_shot_list(), shot.generated_prompt, standard_prompt_text


def generate_single_shot(shot_num: int, custom_prompt: str = "") -> Tuple[str, Optional[str]]:
    """生成单个镜头"""
    global current_project
    print(f"[生成] generate_single_shot 调用: shot_num={shot_num}")

    if current_project is None:
        print("[生成] 错误: 没有项目")
        return "请先创建项目", None

    idx = int(shot_num) - 1
    if idx < 0 or idx >= len(current_project.shots):
        print(f"[生成] 错误: 无效镜头编号 {shot_num}, 总共 {len(current_project.shots)} 个镜头")
        return "无效的镜头编号", None

    shot = current_project.shots[idx]
    prompt = custom_prompt.strip() if custom_prompt else shot.generated_prompt

    if not prompt:
        prompt = generate_shot_prompt(shot, current_project)
        shot.generated_prompt = prompt

    print(f"[生成] 使用生成器, API_KEY={'有' if API_KEY else '无'}, 输出目录={OUTPUTS_DIR}")
    generator = create_generator(API_KEY, str(OUTPUTS_DIR))
    print(f"[生成] 生成器类型: {type(generator).__name__}")
    result = generator.generate_shot(shot, current_project, prompt)
    print(f"[生成] 结果: success={result.success}, path={result.image_path}, error={result.error_message}")

    if result.success:
        shot.output_image = result.image_path
        shot.consistency_score = result.consistency_score
        auto_save_project()  # 自动保存
        return f"✓ 镜头 {shot_num} 生成完成", result.image_path
    else:
        return f"生成失败: {result.error_message}", None


def generate_all_shots() -> str:
    """批量生成所有镜头 - 优先使用 ComfyUI 工作流"""
    global current_project

    if current_project is None:
        return "请先创建项目"

    if not current_project.shots:
        return "请先添加镜头"

    print(f"[全部生成] 开始生成, 共 {len(current_project.shots)} 个镜头", flush=True)

    # 检查 ComfyUI 是否可用
    service = get_ai_service()
    use_comfyui = service.comfyui_client is not None
    print(f"[全部生成] 使用 ComfyUI 工作流: {use_comfyui}", flush=True)

    success = 0
    total = len(current_project.shots)

    for i, shot in enumerate(current_project.shots):
        # Check if image exists - if path is set but file doesn't exist, regenerate
        image_exists = shot.output_image and os.path.exists(shot.output_image)
        print(f"[全部生成] 处理镜头 {i+1}/{total}, output_image='{shot.output_image}', exists={image_exists}", flush=True)

        if not image_exists:
            # Clear invalid path
            if shot.output_image and not os.path.exists(shot.output_image):
                print(f"[全部生成] 镜头 {i+1} 图片文件不存在，重新生成", flush=True)
                shot.output_image = ""

            if not shot.generated_prompt:
                shot.generated_prompt = generate_shot_prompt(shot, current_project)
            print(f"[全部生成] 生成镜头 {i+1}, prompt长度={len(shot.generated_prompt)}", flush=True)

            if use_comfyui:
                # 使用 ComfyUI 工作流直接生成
                gen_success, image_path, error_msg = generate_image_with_comfyui(
                    shot, current_project, shot.generated_prompt
                )
                print(f"[全部生成] 镜头 {i+1} 结果: success={gen_success}, error={error_msg}", flush=True)
                if gen_success and image_path:
                    shot.output_image = image_path
                    shot.consistency_score = 0.9
                    success += 1
                    print(f"[全部生成] 镜头 {i+1} 保存到: {image_path}", flush=True)
            else:
                # 回退到旧的生成器
                generator = create_generator(API_KEY, str(OUTPUTS_DIR))
                result = generator.generate_shot(shot, current_project, shot.generated_prompt)
                print(f"[全部生成] 镜头 {i+1} 结果: success={result.success}, error={result.error_message}", flush=True)
                if result.success:
                    shot.output_image = result.image_path
                    shot.consistency_score = result.consistency_score
                    success += 1
                    print(f"[全部生成] 镜头 {i+1} 保存到: {result.image_path}", flush=True)
        else:
            print(f"[全部生成] 镜头 {i+1} 已有图片，跳过", flush=True)
            success += 1  # Count existing images as success

    auto_save_project()  # 自动保存
    print(f"[全部生成] 完成, 成功 {success}/{total}", flush=True)
    return f"✓ 已生成 {success}/{total} 个镜头"


def regenerate_all_prompts() -> str:
    """重新生成所有镜头的提示词（包含风格）"""
    global current_project

    if current_project is None:
        return "请先创建项目"

    if not current_project.shots:
        return "暂无镜头"

    count = 0
    for shot in current_project.shots:
        shot.generated_prompt = generate_shot_prompt(shot, current_project)
        count += 1

    auto_save_project()
    return f"✓ 已重新生成 {count} 个镜头的提示词"


def apply_seed_settings(lock_seed: bool, seed_value: int) -> str:
    """应用种子锁定设置"""
    global current_project

    if current_project is None:
        return "请先创建项目"

    current_project.lock_seed = lock_seed
    current_project.generation_seed = int(seed_value) if seed_value else -1

    if lock_seed:
        if current_project.generation_seed > 0:
            return f"✓ 已锁定种子: {current_project.generation_seed}"
        else:
            return "✓ 已启用种子锁定（将在首次生成时自动确定种子）"
    else:
        return "✓ 已禁用种子锁定（每个镜头将使用随机种子）"


def get_seed_settings() -> Tuple[bool, int]:
    """获取当前种子设置"""
    global current_project
    if current_project:
        return current_project.lock_seed, current_project.generation_seed
    return False, -1


# ========================================
# ComfyUI 图片生成功能 (使用工作流文件)
# ========================================
IMAGE_WORKFLOW_FILE = "workflows/img.json"

# 图片尺寸映射
IMAGE_ASPECT_RATIOS = {
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "1:1": (768, 768),
    "4:3": (896, 672),
    "3:4": (672, 896),
    "21:9": (1024, 440),
}

def generate_image_with_comfyui(
    shot: 'Shot',
    project: 'StoryboardProject',
    prompt: str
) -> Tuple[bool, Optional[str], str]:
    """
    使用 ComfyUI 工作流生成图片

    Returns:
        Tuple of (success, image_path, error_message)
    """
    import time

    try:
        service = get_ai_service()

        if not service.comfyui_client:
            return False, None, "ComfyUI 未连接"

        # 加载图片工作流
        workflow_path = Path(__file__).parent / IMAGE_WORKFLOW_FILE
        if not workflow_path.exists():
            return False, None, f"工作流文件不存在: {IMAGE_WORKFLOW_FILE}"

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # 获取种子
        if project.lock_seed and project.generation_seed > 0:
            seed = project.generation_seed
        else:
            seed = int(time.time() * 1000) % (2**32)
            if project.lock_seed:
                project.generation_seed = seed

        # 设置提示词 (节点 111 - PrimitiveStringMultiline)
        if "111" in workflow:
            workflow["111"]["inputs"]["value"] = prompt
            print(f"[ComfyUI图片] 设置提示词: {prompt[:50]}...", flush=True)

        # 设置种子 (节点 60 - KSampler)
        if "60" in workflow:
            workflow["60"]["inputs"]["seed"] = seed
            print(f"[ComfyUI图片] 设置种子: {seed}", flush=True)

        # 设置图片尺寸 (节点 69 - EmptyFlux2LatentImage)
        project_aspect = project.aspect_ratio if project else "16:9"
        width, height = IMAGE_ASPECT_RATIOS.get(project_aspect, (1024, 576))
        if "69" in workflow:
            workflow["69"]["inputs"]["width"] = width
            workflow["69"]["inputs"]["height"] = height
            print(f"[ComfyUI图片] 设置尺寸: {width}x{height}", flush=True)

        # 提交任务
        print(f"[ComfyUI图片] 提交任务...", flush=True)
        success, prompt_id = service.comfyui_client.queue_prompt(workflow)
        if not success:
            return False, None, f"提交任务失败: {prompt_id}"

        print(f"[ComfyUI图片] 任务ID: {prompt_id}, 等待生成...", flush=True)

        # 等待完成
        def progress_cb(current, total):
            pass

        wait_success, outputs = service.comfyui_client.wait_for_completion(prompt_id, progress_cb)

        if not wait_success:
            error_msg = outputs[0] if outputs else "未知错误"
            return False, None, f"生成失败: {error_msg}"

        print(f"[ComfyUI图片] 生成完成, 输出: {outputs}", flush=True)

        # 获取输出图片
        image_path = None
        if outputs:
            for output_file in outputs:
                if output_file.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # 从 ComfyUI 下载图片
                    if '/' in output_file:
                        subfolder, filename = output_file.rsplit('/', 1)
                    else:
                        subfolder, filename = "", output_file

                    print(f"[ComfyUI图片] 下载: subfolder={subfolder}, filename={filename}", flush=True)
                    image_data = service.comfyui_client.get_image(filename, subfolder=subfolder, folder_type="output")

                    if image_data:
                        # 保存到项目目录
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest_filename = f"shot_{shot.shot_number:03d}_{timestamp}.png"
                        dest_dir = OUTPUTS_DIR / project.name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_dir / dest_filename

                        with open(dest_path, 'wb') as f:
                            f.write(image_data)

                        image_path = str(dest_path)
                        print(f"[ComfyUI图片] 保存到: {image_path}", flush=True)
                        break

        if image_path:
            return True, image_path, ""
        else:
            return False, None, "未能获取生成的图片"

    except Exception as e:
        return False, None, f"生成异常: {str(e)}"


# ========================================
# 视频生成功能
# ========================================
VIDEO_WORKFLOW_FILE = "workflows/video.json"

def generate_video_from_shot(
    shot_num: int,
    gen_mode: str,
    style: str,
    duration: str,
    camera: str,
    char_refs,
    prop_refs,
    scene_ref
) -> Tuple[str, Optional[str]]:
    """生成单个镜头的视频片段"""
    global current_project

    log_lines = []
    log_lines.append(f"> [视频生成] 开始处理镜头 {shot_num}")
    log_lines.append(f"> [参数] 模式: {gen_mode} | 风格: {style} | 时长: {duration} | 运镜: {camera}")

    if current_project is None:
        log_lines.append("> [错误] 请先创建项目")
        return "\n".join(log_lines), None

    idx = int(shot_num) - 1
    if idx < 0 or idx >= len(current_project.shots):
        log_lines.append(f"> [错误] 无效的镜头编号: {shot_num}")
        return "\n".join(log_lines), None

    shot = current_project.shots[idx]
    log_lines.append(f"> [镜头信息] 类型: {shot.template.value if hasattr(shot.template, 'value') else shot.template} | 场景: {shot.scene_id or '无'}")
    log_lines.append(f"> [镜头信息] 角色: {', '.join(shot.characters_in_shot) if shot.characters_in_shot else '无'}")

    # 检查图生视频模式需要有图片
    if gen_mode == "图生视频" and not shot.output_image:
        log_lines.append(f"> [错误] 镜头 {shot_num} 还没有生成图片，请先生成图片")
        return "\n".join(log_lines), None

    try:
        # 获取服务实例
        service = get_ai_service()

        # 加载视频工作流
        log_lines.append(f"> [工作流] 加载: {VIDEO_WORKFLOW_FILE}")
        workflow_path = Path(__file__).parent / VIDEO_WORKFLOW_FILE
        if not workflow_path.exists():
            log_lines.append(f"> [错误] 工作流文件不存在")
            return "\n".join(log_lines), None

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        log_lines.append(f"> [工作流] 加载成功，共 {len(workflow)} 个节点")

        # 获取锁定的种子
        if current_project.lock_seed and current_project.generation_seed > 0:
            seed = current_project.generation_seed
            log_lines.append(f"> [种子] 使用锁定种子: {seed}")
        else:
            seed = int(time.time() * 1000) % (2**32)
            if current_project.lock_seed:
                current_project.generation_seed = seed
                log_lines.append(f"> [种子] 生成并锁定新种子: {seed}")
            else:
                log_lines.append(f"> [种子] 使用随机种子: {seed}")

        # 设置种子 (节点 85 和 86)
        if "85" in workflow:
            workflow["85"]["inputs"]["noise_seed"] = seed
            log_lines.append(f"> [节点85] 设置 noise_seed = {seed}")
        if "86" in workflow:
            workflow["86"]["inputs"]["noise_seed"] = seed
            log_lines.append(f"> [节点86] 设置 noise_seed = {seed}")

        # 设置输入图片 (节点 97 - LoadImage)
        if gen_mode == "图生视频" and shot.output_image:
            log_lines.append(f"> [图片] 源文件: {shot.output_image}")
            # 上传图片到 ComfyUI
            if service.comfyui_client:
                log_lines.append(f"> [图片] 正在上传到 ComfyUI...")
                success, result = service.comfyui_client.upload_image(shot.output_image)
                if success:
                    workflow["97"]["inputs"]["image"] = result
                    log_lines.append(f"> [节点97] 设置 image = {result}")
                else:
                    log_lines.append(f"> [错误] 上传图片失败: {result}")
                    return "\n".join(log_lines), None
            else:
                log_lines.append("> [错误] ComfyUI 未连接")
                return "\n".join(log_lines), None

        # 设置正向提示词 (节点 93)
        prompt_text = shot.generated_prompt or shot.description or ""
        log_lines.append(f"> [提示词] 原始: {prompt_text[:50]}..." if len(prompt_text) > 50 else f"> [提示词] 原始: {prompt_text}")

        # 获取项目锁定的风格名称
        project_style = locked_style_name if style_locked else ""
        log_lines.append(f"> [项目风格] {project_style or '未设置'}")

        # 风格关键字映射（中文 -> 英文提示词）
        style_keyword_map = {
            "2D卡通": "2D cartoon style, flat colors, clean lines, cel shading",
            "3D卡通": "3D cartoon style, stylized 3D render, Pixar style",
            "动漫风": "anime style, vibrant colors, cel shading, Japanese animation",
            "漫画风": "comic book style, bold outlines, halftone dots",
            "水彩画": "watercolor painting style, soft edges, flowing colors",
            "3D写实": "3D realistic render, photorealistic 3D, high detail",
            "电影感": "cinematic style, film grain, dramatic lighting, movie quality",
            "游戏CG": "game CG style, high quality 3D render, video game graphics",
            "赛博朋克": "cyberpunk style, neon lights, futuristic, sci-fi atmosphere",
            "真人摄影": "photorealistic, professional photography, real life, natural lighting"
        }

        # 添加风格和运镜描述
        style_prompts = {
            "电影感": "cinematic lighting, film grain, dramatic atmosphere",
            "动漫风": "anime style, vibrant colors, cel shading",
            "写实风": "photorealistic, natural lighting, high detail",
            "赛博朋克": "cyberpunk, neon lights, futuristic, sci-fi"
        }
        camera_prompts = {
            "静止": "static shot",
            "缓慢推进": "slow zoom in, dolly in",
            "缓慢拉远": "slow zoom out, dolly out",
            "左右平移": "horizontal pan, tracking shot",
            "跟随主体": "follow shot, tracking the subject"
        }

        # 获取项目风格关键字
        project_style_keywords = style_keyword_map.get(project_style, '')
        style_addition = style_prompts.get(style, '')
        camera_addition = camera_prompts.get(camera, '')

        log_lines.append(f"> [提示词] 项目风格: {project_style_keywords or '无'}")
        log_lines.append(f"> [提示词] 视频风格: {style_addition}")
        log_lines.append(f"> [提示词] 运镜增强: {camera_addition}")

        # 组合完整提示词（项目风格优先）
        prompt_parts = [prompt_text]
        if project_style_keywords:
            prompt_parts.append(project_style_keywords)
        if style_addition:
            prompt_parts.append(style_addition)
        if camera_addition:
            prompt_parts.append(camera_addition)
        full_prompt = ", ".join(filter(None, prompt_parts))
        if "93" in workflow:
            workflow["93"]["inputs"]["text"] = full_prompt
            log_lines.append(f"> [节点93] 设置正向提示词完成")

        # 设置视频长度和尺寸 (节点 98 - WanImageToVideo)
        duration_frames = {"3秒": 33, "5秒": 81, "10秒": 161}
        frames = duration_frames.get(duration, 81)

        # 根据项目比例设置视频尺寸
        project_aspect = current_project.aspect_ratio if current_project else "16:9"
        video_width, video_height = VIDEO_ASPECT_RATIOS.get(project_aspect, (832, 480))
        log_lines.append(f"> [视频尺寸] 项目比例 {project_aspect} -> {video_width}x{video_height}")

        if "98" in workflow:
            workflow["98"]["inputs"]["length"] = frames
            workflow["98"]["inputs"]["width"] = video_width
            workflow["98"]["inputs"]["height"] = video_height
            log_lines.append(f"> [节点98] 视频参数: {video_width}x{video_height}, {frames}帧 ({duration})")

        # 一致性参考图信息
        if char_refs:
            log_lines.append(f"> [一致性] 人物参考图: {len(char_refs) if isinstance(char_refs, list) else 1} 张")
        if prop_refs:
            log_lines.append(f"> [一致性] 道具参考图: {len(prop_refs) if isinstance(prop_refs, list) else 1} 张")
        if scene_ref:
            log_lines.append(f"> [一致性] 场景参考图: 1 张")

        # 调用 ComfyUI 生成
        if not service.comfyui_client:
            log_lines.append("> [错误] ComfyUI 未连接，请先连接 ComfyUI")
            return "\n".join(log_lines), None

        log_lines.append("> [ComfyUI] 正在提交任务...")
        success, prompt_id = service.comfyui_client.queue_prompt(workflow)
        if not success:
            log_lines.append(f"> [错误] 提交任务失败: {prompt_id}")
            return "\n".join(log_lines), None

        log_lines.append(f"> [ComfyUI] ✓ 任务提交成功")
        log_lines.append(f"> [任务ID] {prompt_id}")
        log_lines.append(f"> [状态] 等待 ComfyUI 处理中...")

        # 等待任务完成
        def progress_cb(current, total):
            pass  # 进度回调（可扩展为实时更新UI）

        log_lines.append(f"> [ComfyUI] 正在生成视频，请稍候...")
        wait_success, outputs = service.comfyui_client.wait_for_completion(prompt_id, progress_cb)

        if not wait_success:
            error_msg = outputs[0] if outputs else "未知错误"
            log_lines.append(f"> [错误] 视频生成失败: {error_msg}")
            return "\n".join(log_lines), None

        log_lines.append(f"> [ComfyUI] ✓ 视频生成完成")
        log_lines.append(f"> [输出文件] {outputs}")

        # 获取输出视频路径
        video_path = None
        if outputs:
            log_lines.append(f"> [输出列表] {outputs}")
            for output_file in outputs:
                if output_file.endswith(('.mp4', '.webm', '.avi', '.gif')):
                    log_lines.append(f"> [找到视频] {output_file}")
                    # 从 ComfyUI 下载视频
                    # 检查文件名是否包含子目录（如 "video/ComfyUI_00001.mp4"）
                    if '/' in output_file:
                        subfolder, filename = output_file.rsplit('/', 1)
                    else:
                        subfolder, filename = "video", output_file

                    log_lines.append(f"> [下载] 从 ComfyUI 下载: subfolder={subfolder}, filename={filename}")
                    video_data = service.comfyui_client.get_image(filename, subfolder=subfolder, folder_type="output")

                    if video_data and shot.output_image:
                        dest_path = os.path.splitext(shot.output_image)[0] + ".mp4"
                        try:
                            with open(dest_path, 'wb') as f:
                                f.write(video_data)
                            log_lines.append(f"> [保存] 视频已保存到: {dest_path}")
                            video_path = dest_path
                            # 保存视频路径到 shot 并自动保存项目
                            shot.output_video = dest_path
                            auto_save_project()
                            log_lines.append(f"> [自动保存] 项目已保存")
                            break
                        except Exception as save_err:
                            log_lines.append(f"> [警告] 保存视频失败: {save_err}")
                    else:
                        log_lines.append(f"> [警告] 无法从 ComfyUI 下载视频或无输出图片路径")

        log_lines.append(f"")
        log_lines.append(f"========================================")
        log_lines.append(f"✓ 视频生成完成")
        log_lines.append(f"  镜头: {shot_num} | 种子: {seed}")
        log_lines.append(f"  风格: {style} | 时长: {duration} | 运镜: {camera}")
        log_lines.append(f"========================================")

        return "\n".join(log_lines), video_path

    except Exception as e:
        log_lines.append(f"> [错误] 生成失败: {str(e)}")
        return "\n".join(log_lines), None


def generate_single_video_simple(shot_num: int) -> Tuple[str, str]:
    """从镜头卡片按钮触发的简化视频生成（使用默认参数）"""
    status, video_path = generate_video_from_shot(
        shot_num=shot_num,
        gen_mode="图生视频",
        style="电影感",
        duration="5秒",
        camera="静止",
        char_refs=None,
        prop_refs=None,
        scene_ref=None
    )
    # 返回状态和更新后的视频卡片HTML
    return status, get_video_cards_html()


def generate_all_videos(
    gen_mode: str,
    style: str,
    duration: str,
    camera: str,
    char_refs,
    prop_refs,
    scene_ref
) -> Tuple[str, List]:
    """批量生成所有镜头的视频"""
    global current_project

    log_lines = []
    log_lines.append("=" * 50)
    log_lines.append("> [批量视频生成] 开始处理")
    log_lines.append("=" * 50)
    log_lines.append(f"> [参数] 模式: {gen_mode}")
    log_lines.append(f"> [参数] 风格: {style}")
    log_lines.append(f"> [参数] 时长: {duration}")
    log_lines.append(f"> [参数] 运镜: {camera}")

    # 检查 ComfyUI 连接
    service = get_ai_service()
    if service.comfyui_client is None:
        log_lines.append("> [错误] ComfyUI 未连接")
        log_lines.append("> [提示] 请先点击「连接 ComfyUI」按钮")
        return "\n".join(log_lines), []
    else:
        log_lines.append(f"> [ComfyUI] 已连接: {settings.comfyui_host}:{settings.comfyui_port}")

    if current_project is None:
        log_lines.append("> [错误] 请先创建项目")
        return "\n".join(log_lines), []

    if not current_project.shots:
        log_lines.append("> [错误] 请先添加镜头")
        return "\n".join(log_lines), []

    total = len(current_project.shots)
    log_lines.append(f"> [统计] 共 {total} 个镜头待处理")

    # 检查图生视频模式下是否所有镜头都有图片
    if gen_mode == "图生视频":
        with_image = [s.shot_number for s in current_project.shots if s.output_image]
        missing = [s.shot_number for s in current_project.shots if not s.output_image]
        log_lines.append(f"> [检查] 已有图片的镜头: {with_image}")
        if missing:
            log_lines.append(f"> [错误] 以下镜头还没有生成图片: {missing}")
            log_lines.append("> [提示] 请先在「③ 生成」中生成这些镜头的图片")
            return "\n".join(log_lines), []

    # 种子信息
    if current_project.lock_seed:
        if current_project.generation_seed > 0:
            log_lines.append(f"> [种子] 已锁定: {current_project.generation_seed} (所有镜头使用相同种子)")
        else:
            log_lines.append(f"> [种子] 已启用锁定，将在首个镜头生成时确定")
    else:
        log_lines.append(f"> [种子] 未锁定，每个镜头将使用随机种子")

    # 一致性参考图
    log_lines.append("> [一致性参考图]")
    if char_refs:
        count = len(char_refs) if isinstance(char_refs, list) else 1
        log_lines.append(f">   人物参考: {count} 张")
    else:
        log_lines.append(">   人物参考: 无")
    if prop_refs:
        count = len(prop_refs) if isinstance(prop_refs, list) else 1
        log_lines.append(f">   道具参考: {count} 张")
    else:
        log_lines.append(">   道具参考: 无")
    if scene_ref:
        log_lines.append(">   场景参考: 1 张")
    else:
        log_lines.append(">   场景参考: 无")

    log_lines.append("")
    log_lines.append("> [开始批量提交任务]")
    log_lines.append("-" * 50)

    success_count = 0
    fail_count = 0

    for i, shot in enumerate(current_project.shots):
        log_lines.append(f"> [{i+1}/{total}] 处理镜头 {shot.shot_number}...")
        log_lines.append("")

        # 调用视频生成并获取详细日志
        status, video_path = generate_video_from_shot(
            shot.shot_number, gen_mode, style, duration, camera,
            char_refs, prop_refs, scene_ref
        )

        # 将详细日志添加到输出（缩进显示）
        for line in status.split('\n'):
            if line.strip():
                log_lines.append(f"    {line}")

        log_lines.append("")

        # 检查是否成功
        if "✓ 视频生成完成" in status or video_path:
            success_count += 1
            log_lines.append(f">   ✓ 镜头 {shot.shot_number} 生成完成")
            if video_path:
                log_lines.append(f">   📹 视频: {video_path}")
        else:
            fail_count += 1
            log_lines.append(f">   ✗ 镜头 {shot.shot_number} 生成失败")

        log_lines.append("")

    log_lines.append("-" * 50)
    log_lines.append("")
    log_lines.append("=" * 50)
    log_lines.append(f"> [批量生成完成]")
    log_lines.append(f">   总计: {total} 个镜头")
    log_lines.append(f">   成功: {success_count} 个")
    log_lines.append(f">   失败: {fail_count} 个")
    log_lines.append(f">   种子: {current_project.generation_seed if current_project.lock_seed else '随机'}")
    log_lines.append("=" * 50)

    return "\n".join(log_lines), []


def generate_all_videos_with_cli(
    gen_mode: str,
    style: str,
    duration: str,
    camera: str,
    char_refs,
    prop_refs,
    scene_ref
) -> Tuple[str, str, List]:
    """批量生成视频（带CLI输出）"""
    print(f"[DEBUG] generate_all_videos_with_cli called with: gen_mode={gen_mode}, style={style}")

    # 先检查各项服务状态
    cli_lines = []
    cli_lines.append("=" * 50)
    cli_lines.append("> [系统检查] 开始...")
    cli_lines.append("=" * 50)

    # 检查 ComfyUI 连接
    service = get_ai_service()
    if service.comfyui_client:
        cli_lines.append(f"> [ComfyUI] ✓ 已连接 ({settings.comfyui_host}:{settings.comfyui_port})")
    else:
        cli_lines.append(f"> [ComfyUI] ✗ 未连接")
        cli_lines.append(f"> [提示] 请先点击「连接 ComfyUI」按钮")
        return "ComfyUI 未连接", "\n".join(cli_lines), []

    # 检查项目状态
    if current_project:
        cli_lines.append(f"> [项目] ✓ {current_project.name}")
        cli_lines.append(f"> [镜头] 共 {len(current_project.shots)} 个")
        with_image = sum(1 for s in current_project.shots if s.output_image)
        cli_lines.append(f"> [图片] 已生成 {with_image} 个")
    else:
        cli_lines.append(f"> [项目] ✗ 未创建")
        return "请先创建项目", "\n".join(cli_lines), []

    cli_lines.append("")

    # 调用实际生成函数
    log_output, gallery = generate_all_videos(
        gen_mode, style, duration, camera, char_refs, prop_refs, scene_ref
    )

    # 合并日志
    full_log = "\n".join(cli_lines) + "\n" + log_output

    # 提取简短状态
    lines = log_output.split('\n')
    status = "就绪"
    for line in reversed(lines):
        if "成功:" in line or "完成" in line:
            status = line.strip().lstrip('> ')
            break
        elif "错误" in line:
            status = "生成失败"
            break

    print(f"[DEBUG] generate_all_videos_with_cli finished with status: {status}")
    return status, full_log, gallery


def generate_single_video_with_cli(shot_num: int) -> Tuple[str, str, str, str]:
    """生成单个视频（带CLI输出）"""
    status, video_path = generate_video_from_shot(
        shot_num=shot_num,
        gen_mode="图生视频",
        style="电影感",
        duration="5秒",
        camera="静止",
        char_refs=None,
        prop_refs=None,
        scene_ref=None
    )
    # status 已经包含详细日志
    short_status = f"镜头 {shot_num} " + ("✓ 完成" if "✓" in status or "成功" in status else "✗ 失败")
    return short_status, status, get_video_cards_html(), get_video_stats_html()


def delete_shot(shot_num: int) -> Tuple[str, List]:
    """删除镜头"""
    global current_project

    if current_project is None:
        return "请先创建项目", []

    idx = int(shot_num) - 1
    if 0 <= idx < len(current_project.shots):
        current_project.shots.pop(idx)
        for i, s in enumerate(current_project.shots):
            s.shot_number = i + 1
        return f"✓ 镜头已删除", get_shot_list()

    return "无效的镜头编号", get_shot_list()


def delete_character(char_name: str) -> Tuple[str, List]:
    """删除角色"""
    global current_project

    if current_project is None:
        return "请先创建项目", []

    for i, c in enumerate(current_project.characters):
        if c.name == char_name:
            current_project.characters.pop(i)
            return f"✓ 角色「{char_name}」已删除", get_character_list()

    return "未找到该角色", get_character_list()


def delete_scene(scene_name: str) -> Tuple[str, List]:
    """删除场景"""
    global current_project

    if current_project is None:
        return "请先创建项目", []

    for i, s in enumerate(current_project.scenes):
        if s.name == scene_name:
            current_project.scenes.pop(i)
            return f"✓ 场景「{scene_name}」已删除", get_scene_list()

    return "未找到该场景", get_scene_list()


def move_shot(shot_num: int, direction: str) -> Tuple[str, List]:
    """移动镜头顺序"""
    global current_project

    if current_project is None:
        return "请先创建项目", []

    idx = int(shot_num) - 1
    if idx < 0 or idx >= len(current_project.shots):
        return "无效的镜头编号", get_shot_list()

    if direction == "上移" and idx > 0:
        current_project.shots[idx], current_project.shots[idx-1] = \
            current_project.shots[idx-1], current_project.shots[idx]
    elif direction == "下移" and idx < len(current_project.shots) - 1:
        current_project.shots[idx], current_project.shots[idx+1] = \
            current_project.shots[idx+1], current_project.shots[idx]
    else:
        return "无法移动", get_shot_list()

    # 重新编号
    for i, s in enumerate(current_project.shots):
        s.shot_number = i + 1

    return f"✓ 镜头已{direction}", get_shot_list()


# ========================================
# 导入导出功能
# ========================================

def export_project_multi_format(format_type: str) -> Tuple[str, Optional[str]]:
    """多格式导出"""
    global current_project

    if current_project is None:
        return "请先创建项目", None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == "图片包 (ZIP)":
        zip_name = f"{current_project.name}_{timestamp}.zip"
        zip_path = EXPORTS_DIR / zip_name

        with zipfile.ZipFile(zip_path, 'w') as zf:
            # 添加图片
            for shot in current_project.shots:
                if shot.output_image and os.path.exists(shot.output_image):
                    zf.write(shot.output_image, f"shots/shot_{shot.shot_number:02d}.png")

            # 添加项目信息
            info = {
                "project_name": current_project.name,
                "created_at": timestamp,
                "total_shots": len(current_project.shots),
                "characters": [c.name for c in current_project.characters],
                "scenes": [s.name for s in current_project.scenes]
            }
            zf.writestr("project_info.json", json.dumps(info, ensure_ascii=False, indent=2))

        return f"✓ 已导出: {zip_path}", str(zip_path)

    elif format_type == "项目文件 (JSON)":
        json_name = f"{current_project.name}_{timestamp}.json"
        json_path = EXPORTS_DIR / json_name

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(current_project.to_dict(), f, ensure_ascii=False, indent=2)

        return f"✓ 已导出: {json_path}", str(json_path)

    elif format_type == "分镜脚本 (TXT)":
        txt_name = f"{current_project.name}_script_{timestamp}.txt"
        txt_path = EXPORTS_DIR / txt_name

        lines = [
            f"分镜脚本: {current_project.name}",
            f"创建时间: {timestamp}",
            f"画面比例: {current_project.aspect_ratio}",
            "",
            "=" * 50,
            "角色列表:",
            "=" * 50,
        ]

        for char in current_project.characters:
            lines.append(f"  - {char.name}: {char.description}")

        lines.extend([
            "",
            "=" * 50,
            "场景列表:",
            "=" * 50,
        ])

        for scene in current_project.scenes:
            lines.append(f"  - {scene.name}: {scene.description}")

        lines.extend([
            "",
            "=" * 50,
            "分镜列表:",
            "=" * 50,
            ""
        ])

        for shot in current_project.shots:
            template = get_template(shot.template)
            char_names = []
            for cid in shot.characters_in_shot:
                for c in current_project.characters:
                    if c.id == cid:
                        char_names.append(c.name)

            scene_name = ""
            for s in current_project.scenes:
                if s.id == shot.scene_id:
                    scene_name = s.name

            # 获取标准提示语
            std_prompt = shot.standard_prompt
            if not std_prompt.shot_type:
                std_prompt = generate_standard_shot_prompt(shot, current_project)

            lines.extend([
                f"镜头 {shot.shot_number}",
                f"  类型: {template.name_cn if template else '标准'}",
                f"  场景: {scene_name}",
                f"  角色: {', '.join(char_names) if char_names else '无'}",
                f"  描述: {shot.description}",
                f"  状态: {'已生成' if shot.output_image else '待生成'}",
                "",
                "  --- 标准提示语 ---",
                f"  主体: {std_prompt.subject}",
                f"  景别: {std_prompt.shot_type}",
                f"  氛围: {std_prompt.atmosphere}",
                f"  环境: {std_prompt.environment}",
                f"  运镜: {std_prompt.camera_movement}",
                f"  视角: {std_prompt.angle}",
                f"  特殊拍摄手法: {std_prompt.special_technique}",
                f"  构图: {std_prompt.composition}",
                f"  风格统一: {std_prompt.style_consistency}",
                f"  动态控制: {std_prompt.dynamic_control}",
                "",
                "-" * 40,
                ""
            ])

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return f"✓ 已导出: {txt_path}", str(txt_path)

    elif format_type == "完整备份 (ZIP+JSON+图片)":
        backup_name = f"{current_project.name}_backup_{timestamp}.zip"
        backup_path = EXPORTS_DIR / backup_name

        with zipfile.ZipFile(backup_path, 'w') as zf:
            # 项目文件
            zf.writestr("project.json", json.dumps(current_project.to_dict(), ensure_ascii=False, indent=2))

            # 输出图片
            for shot in current_project.shots:
                if shot.output_image and os.path.exists(shot.output_image):
                    zf.write(shot.output_image, f"outputs/shot_{shot.shot_number:02d}.png")

            # 参考图片
            for char in current_project.characters:
                for i, img_path in enumerate(char.ref_images):
                    if os.path.exists(img_path):
                        zf.write(img_path, f"references/characters/{char.name}_{i}.png")

            for scene in current_project.scenes:
                if scene.space_ref_image and os.path.exists(scene.space_ref_image):
                    zf.write(scene.space_ref_image, f"references/scenes/{scene.name}.png")

        return f"✓ 完整备份已导出: {backup_path}", str(backup_path)

    return "未知格式", None


def import_project_file(file) -> Tuple[str, str, List, List, List]:
    """导入项目文件"""
    global current_project

    if file is None:
        return "请选择文件", "", [], [], []

    try:
        filepath = file.name if hasattr(file, 'name') else file

        # 判断文件类型
        if filepath.endswith('.json'):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            current_project = StoryboardProject.from_dict(data)

        elif filepath.endswith('.zip'):
            # 解压并读取
            with zipfile.ZipFile(filepath, 'r') as zf:
                if 'project.json' in zf.namelist():
                    with zf.open('project.json') as f:
                        data = json.load(f)
                    current_project = StoryboardProject.from_dict(data)
                else:
                    return "ZIP文件中未找到project.json", "", [], [], []
        else:
            return "不支持的文件格式", "", [], [], []

        return (
            f"✓ 已导入「{current_project.name}」",
            get_project_summary(),
            get_character_list(),
            get_scene_list(),
            get_shot_list()
        )
    except Exception as e:
        return f"导入失败: {str(e)}", "", [], [], []


# ========================================
# 智能导入功能
# ========================================

# 全局智能导入器实例
smart_importer = SmartImporter()


def smart_import_analyze(files, use_claude: bool = True) -> Tuple[str, str, str]:
    """
    智能分析上传的文件
    返回: (状态消息, 原始内容, 分析后的JSON)
    """
    if files is None or len(files) == 0:
        return "请选择文件", "", ""

    # 处理单个或多个文件
    filepaths = []
    for f in files:
        if hasattr(f, 'name'):
            filepaths.append(f.name)
        else:
            filepaths.append(str(f))

    if len(filepaths) == 1:
        result = smart_importer.import_file(filepaths[0], use_claude)
    else:
        result = smart_importer.import_multiple_files(filepaths)

    if result['success']:
        return (
            f"✓ {result['message']}",
            result.get('raw_content', '')[:3000] + "..." if len(result.get('raw_content', '')) > 3000 else result.get('raw_content', ''),
            result['analyzed_json']
        )
    else:
        return f"✗ {result['message']}", "", ""


def smart_import_apply(json_str: str) -> Tuple[str, str, List, List, List]:
    """
    应用编辑后的JSON创建项目
    返回: (状态消息, 项目概览, 角色列表, 场景列表, 镜头列表)
    """
    global current_project

    if not json_str.strip():
        return "JSON内容为空", "", [], [], []

    # 验证和修复JSON
    valid, fixed_json, error = validate_and_fix_json(json_str)
    if not valid:
        return f"JSON格式错误: {error}", "", [], [], []

    try:
        data = json.loads(fixed_json)

        # 创建项目
        current_project = StoryboardProject(
            name=data.get('project_name', '导入的项目'),
            aspect_ratio=data.get('aspect_ratio', '16:9')
        )

        # 设置风格
        style_name = data.get('style', '电影感')
        set_style(style_name)

        # 添加角色
        for char_data in data.get('characters', []):
            char = Character(
                name=char_data.get('name', '未命名角色'),
                description=char_data.get('description', ''),
                ref_images=[],
                consistency_weight=0.85
            )
            current_project.characters.append(char)

        # 添加场景
        for scene_data in data.get('scenes', []):
            scene = Scene(
                name=scene_data.get('name', '未命名场景'),
                description=scene_data.get('description', ''),
                space_ref_image='',
                consistency_weight=0.7
            )
            current_project.scenes.append(scene)

        # 添加镜头
        template_map = {
            "全景": ShotTemplate.T1_ESTABLISHING_WIDE,
            "中景": ShotTemplate.T4_STANDARD_MEDIUM,
            "特写": ShotTemplate.T6_CLOSEUP,
            "过肩": ShotTemplate.T5_OVER_SHOULDER,
            "低角度": ShotTemplate.T7_LOW_ANGLE,
            "跟随": ShotTemplate.T8_FOLLOWING,
        }

        for shot_data in data.get('shots', []):
            template_name = shot_data.get('template', '中景')
            template_type = template_map.get(template_name, ShotTemplate.T4_STANDARD_MEDIUM)
            template_def = get_template(template_type)

            # 查找角色ID
            char_ids = []
            for cname in shot_data.get('characters', []):
                for c in current_project.characters:
                    if c.name == cname:
                        char_ids.append(c.id)
                        break

            # 查找场景ID
            scene_id = ""
            for s in current_project.scenes:
                if s.name == shot_data.get('scene', ''):
                    scene_id = s.id
                    break

            shot = Shot(
                shot_number=len(current_project.shots) + 1,
                template=template_type,
                description=shot_data.get('description', ''),
                characters_in_shot=char_ids,
                scene_id=scene_id,
                camera=template_def.camera if template_def else CameraSettings(),
                composition=template_def.composition if template_def else CompositionSettings(),
                slot_weights=SlotWeights(character=0.85, scene=0.5, props=0.6, style=0.4)
            )
            shot.generated_prompt = generate_shot_prompt(shot, current_project)
            shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)
            current_project.shots.append(shot)

        char_count = len(current_project.characters)
        scene_count = len(current_project.scenes)
        shot_count = len(current_project.shots)

        return (
            f"✓ 成功导入项目「{current_project.name}」\n   {char_count}个角色 · {scene_count}个场景 · {shot_count}个镜头",
            get_project_summary(),
            get_character_list(),
            get_scene_list(),
            get_shot_list()
        )

    except Exception as e:
        return f"导入失败: {str(e)}", "", [], [], []


def get_supported_formats_html() -> str:
    """返回支持的文件格式HTML说明"""
    return """
    <div style="background: #f5f5f7; border-radius: 12px; padding: 16px; margin: 10px 0;">
        <div style="font-weight: 600; margin-bottom: 12px;">支持的文件格式</div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-size: 13px;">
            <div>📄 PDF 文档</div>
            <div>📝 Word 文档 (.docx)</div>
            <div>📋 Markdown (.md)</div>
            <div>🖼️ 图片 (JPG/PNG)</div>
            <div>🌐 网页 (HTML)</div>
            <div>📃 纯文本 (.txt)</div>
        </div>
        <div style="margin-top: 12px; font-size: 12px; color: #86868b;">
            上传文件后，系统将自动分析内容并生成分镜规划，您可以在确认前编辑修改。
        </div>
    </div>
    """


# ========================================
# 数据获取函数
# ========================================

def get_character_list() -> List:
    """获取角色列表"""
    if current_project is None:
        return []

    result = []
    for c in current_project.characters:
        # 生成描述，优先显示外貌摘要
        appearance_summary = c.appearance.to_prompt_string() if c.appearance else ""
        if appearance_summary:
            desc = appearance_summary[:40] + "..." if len(appearance_summary) > 40 else appearance_summary
        elif c.description:
            desc = c.description[:30] + "..." if len(c.description) > 30 else c.description
        else:
            desc = "-"
        result.append([c.name, desc, len(c.ref_images)])
    return result


def get_scene_list() -> List:
    """获取场景列表"""
    if current_project is None:
        return []
    return [[s.name, s.description[:30] + "..." if len(s.description) > 30 else s.description] for s in current_project.scenes]


def get_shot_list() -> List:
    """获取镜头列表"""
    if current_project is None:
        return []

    result = []
    for s in current_project.shots:
        template = get_template(s.template)

        # 获取角色名
        char_names = []
        for cid in s.characters_in_shot:
            for c in current_project.characters:
                if c.id == cid:
                    char_names.append(c.name)

        # 获取场景名
        scene_name = ""
        for sc in current_project.scenes:
            if sc.id == s.scene_id:
                scene_name = sc.name

        status = "✓" if s.output_image else "○"
        result.append([
            s.shot_number,
            template.name_cn if template else "标准",
            scene_name,
            ", ".join(char_names) if char_names else "-",
            s.description[:20] + "..." if len(s.description) > 20 else s.description,
            status
        ])
    return result


def get_character_names() -> List[str]:
    if current_project is None:
        return []
    return [c.name for c in current_project.characters]


def get_scene_names() -> List[str]:
    if current_project is None:
        return []
    return [s.name for s in current_project.scenes]


def get_gallery_images() -> List:
    if current_project is None:
        return []

    images = []
    for shot in current_project.shots:
        if shot.output_image and os.path.exists(shot.output_image):
            images.append((shot.output_image, f"镜头 {shot.shot_number}"))
    return images


def get_shot_standard_prompt(shot_num: int) -> Tuple[str, str]:
    """获取指定镜头的提示语"""
    global current_project

    if current_project is None:
        return "", ""

    idx = int(shot_num) - 1
    if idx < 0 or idx >= len(current_project.shots):
        return "", ""

    shot = current_project.shots[idx]

    # 如果标准提示语为空，重新生成
    if not shot.standard_prompt.shot_type:
        shot.standard_prompt = generate_standard_shot_prompt(shot, current_project)

    return shot.generated_prompt, shot.standard_prompt.to_formatted_string()


def refresh_dropdowns():
    char_names = get_character_names()
    scene_names = get_scene_names()
    return (
        gr.update(choices=char_names),
        gr.update(choices=scene_names),
        gr.update(choices=char_names),
        gr.update(choices=scene_names)
    )


def get_project_summary() -> str:
    """项目摘要（已禁用 - 返回空字符串）"""
    return ""


def get_example_stories_html() -> str:
    """生成范例故事HTML"""
    html = '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">'

    for name, story in EXAMPLE_STORIES.items():
        html += f'''
        <div style="background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">🎬 {name}</div>
            <div style="font-size: 13px; color: #86868b; margin-bottom: 12px;">{story["description"]}</div>
            <div style="font-size: 12px; color: #0071e3;">
                {len(story["characters"])}个角色 · {len(story["scenes"])}个场景 · {len(story["shots"])}个镜头
            </div>
        </div>
        '''

    html += '</div>'
    return html


# ========================================
# AI 创作功能
# ========================================

# 全局 AI 服务实例
extracted_data = {"characters": [], "scenes": [], "props": []}


def get_step_summary(step: int) -> str:
    """生成前序步骤内容摘要
    step: 2=编排页, 3=生成页, 4=导出页
    """
    if current_project is None:
        return ""

    chars = [c.name for c in current_project.characters]
    scenes = [s.name for s in current_project.scenes]
    shots_count = len(current_project.shots)
    done_count = sum(1 for s in current_project.shots if s.output_image)

    if step == 2:  # 编排页 - 显示角色和场景
        if not chars and not scenes:
            return ""
        char_tags = ''.join([f'<span class="step-summary-tag char">👤 {c}</span>' for c in chars])
        scene_tags = ''.join([f'<span class="step-summary-tag scene">🎬 {s}</span>' for s in scenes])
        return f'''
        <div class="step-summary">
            <div class="step-summary-header">
                <span class="step-summary-title">✓ 第1步已完成：已创建 {len(chars)} 个角色、{len(scenes)} 个场景</span>
            </div>
            <div class="step-summary-content">
                {char_tags}{scene_tags}
            </div>
        </div>
        '''

    elif step == 3:  # 生成页 - 显示角色、场景、镜头
        if not chars and not scenes and not shots_count:
            return ""
        char_tags = ''.join([f'<span class="step-summary-tag char">👤 {c}</span>' for c in chars[:5]])
        if len(chars) > 5:
            char_tags += f'<span class="step-summary-tag char">+{len(chars)-5}</span>'
        scene_tags = ''.join([f'<span class="step-summary-tag scene">🎬 {s}</span>' for s in scenes[:5]])
        if len(scenes) > 5:
            scene_tags += f'<span class="step-summary-tag scene">+{len(scenes)-5}</span>'
        return f'''
        <div class="step-summary">
            <div class="step-summary-header">
                <span class="step-summary-title">✓ 前序已完成：{len(chars)}角色 · {len(scenes)}场景 · {shots_count}镜头待生成</span>
            </div>
            <div class="step-summary-content">
                {char_tags}{scene_tags}
                <span class="step-summary-tag shot">📷 {shots_count}个镜头</span>
            </div>
        </div>
        '''

    elif step == 4:  # 导出页 - 显示完成进度
        if shots_count == 0:
            return ""
        return f'''
        <div class="step-summary">
            <div class="step-summary-header">
                <span class="step-summary-title">✓ 图像生成进度：{done_count}/{shots_count} 已完成</span>
            </div>
            <div class="step-summary-content">
                <span class="step-summary-tag char">👤 {len(chars)}角色</span>
                <span class="step-summary-tag scene">🎬 {len(scenes)}场景</span>
                <span class="step-summary-tag shot">📷 {done_count}/{shots_count}图像</span>
            </div>
        </div>
        '''

    return ""


def get_video_cards_html() -> str:
    """生成视频镜头卡片HTML，样式与图片镜头一致，底色线框区分"""
    if current_project is None or len(current_project.shots) == 0:
        return '<div class="no-videos">暂无镜头，请先生成图片后再生成视频</div>'

    cards_html = '<div class="video-cards-container">'

    video_count = 0
    videos_data = []  # 收集视频数据用于弹窗
    for i, shot in enumerate(current_project.shots, 1):
        # 检查是否有对应的视频文件（基于图片路径推断）
        video_path = ""
        has_video = False
        if shot.output_image:
            # 视频文件命名：与图片同名但扩展名为 .mp4
            base_path = os.path.splitext(shot.output_image)[0]
            for ext in ['.mp4', '.webm', '.avi']:
                potential_video = base_path + ext
                if os.path.exists(potential_video):
                    video_path = potential_video
                    has_video = True
                    video_count += 1
                    break

        # 收集视频数据（转换路径为URL格式）
        video_url = ""
        if has_video and video_path:
            # 使用Gradio 6.x正确的文件服务端点格式
            video_url = "/gradio_api/file=" + video_path.replace("\\", "/")
        videos_data.append({
            "num": i,
            "video_path": video_url,
            "prompt": shot.generated_prompt or shot.description or "",
            "has_video": has_video
        })

        has_image = shot.output_image and os.path.exists(shot.output_image)
        status_class = "video-completed" if has_video else ("video-pending" if has_image else "video-no-image")

        if has_video:
            status_icon = "🎬"
            status_text = "已生成"
        elif has_image:
            status_icon = "⏳"
            status_text = "待生成"
        else:
            status_icon = "🖼️"
            status_text = "需图片"

        # 缩略图（使用原图作为视频封面）
        if has_image:
            try:
                with open(shot.output_image, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                ext = shot.output_image.lower().split('.')[-1]
                mime_type = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                img_data_uri = f"data:{mime_type};base64,{img_data}"
                thumb_html = f'<img src="{img_data_uri}" class="video-thumb" />'
                if has_video:
                    thumb_html = f'<div class="video-thumb-wrapper">{thumb_html}<div class="video-play-icon">▶</div></div>'
            except:
                thumb_html = '<div class="video-thumb-placeholder">⚠️<br/>加载失败</div>'
        else:
            thumb_html = '<div class="video-thumb-placeholder">🖼️<br/>需先生成图片</div>'

        # 镜头描述（截断）
        desc_short = shot.description[:30] + "..." if len(shot.description) > 30 else shot.description

        # 点击事件（仅当有视频时）- 使用 Gradio 触发机制
        click_handler = f'onclick="window.previewVideoByShot({i})"' if has_video else ''

        cards_html += f'''
        <div class="video-card {status_class}" data-shot-num="{i}" {click_handler}>
            <div class="video-card-header">
                <span class="video-num">视频 {i}</span>
                <span class="video-status" title="{status_text}">{status_icon}</span>
            </div>
            <div class="video-thumb-container">
                {thumb_html}
            </div>
            <div class="video-desc">{desc_short}</div>
        </div>
        '''

    cards_html += '</div>'

    # 添加视频卡片样式（紫色主题区分于蓝色图片卡片）
    cards_html += '''
    <style>
        .video-cards-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
            padding: 10px 0;
        }
        .video-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #7c3aed;
            border-radius: 8px;
            padding: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .video-card:hover {
            border-color: #a78bfa;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        }
        .video-card.video-completed {
            border-color: #22c55e;
            background: linear-gradient(135deg, #0f1a0f 0%, #1a2e1a 100%);
        }
        .video-card.video-pending {
            border-color: #f59e0b;
        }
        .video-card.video-no-image {
            border-color: #6b7280;
            opacity: 0.6;
        }
        .video-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .video-num {
            font-weight: 600;
            font-size: 12px;
            color: #a78bfa;
        }
        .video-card.video-completed .video-num {
            color: #4ade80;
        }
        .video-status { font-size: 14px; }
        .video-thumb-container {
            width: 100%;
            aspect-ratio: 16/9;
            background: #0a0a15;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 6px;
        }
        .video-thumb {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .video-thumb-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
        }
        .video-thumb-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .video-play-icon {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 36px;
            height: 36px;
            background: rgba(34, 197, 94, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .video-thumb-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 11px;
            text-align: center;
        }
        .video-desc {
            font-size: 10px;
            color: #9ca3af;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .video-stats {
            text-align: center;
            padding: 8px;
            font-size: 12px;
            color: #9ca3af;
            border-top: 1px solid #333;
            margin-top: 8px;
        }
        .no-videos {
            text-align: center;
            color: #6b7280;
            padding: 30px;
            font-size: 13px;
        }
        /* 红色危险按钮 */
        .danger-btn {
            background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
        }
        .danger-btn:hover {
            background: linear-gradient(135deg, #ef4444, #dc2626) !important;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4) !important;
        }
    </style>

    <!-- JavaScript: 视频预览弹窗 -->
    <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
         onload="
            /* 视频数据存储 */
            window.globalVideosData = window.globalVideosData || [];
            window.globalVideoIndex = 0;

            /* 打开视频弹窗 */
            window.previewVideoByShot = function(shotNum) {
                console.log('[视频预览] 打开弹窗，镜头:', shotNum);
                var videoData = window.globalVideosData.find(function(v) { return v.num === shotNum; });
                if (!videoData || !videoData.video_path) {
                    console.error('[视频预览] 未找到视频数据');
                    return;
                }
                window.globalVideoIndex = shotNum - 1;
                window.updateVideoModal();
                document.getElementById('globalVideoModal').style.display = 'flex';
            };

            /* 更新视频弹窗内容 */
            window.updateVideoModal = function() {
                var data = window.globalVideosData[window.globalVideoIndex];
                if (!data) return;

                document.getElementById('videoModalTitle').textContent = '视频 ' + data.num + ' 预览';
                document.getElementById('videoModalPrompt').textContent = data.prompt || '无提示词';
                document.getElementById('videoModalNav').textContent = data.num + ' / ' + window.globalVideosData.length;

                var player = document.getElementById('videoModalPlayer');
                player.src = data.video_path;
                player.load();
            };

            /* 关闭视频弹窗 */
            window.closeVideoModal = function() {
                var modal = document.getElementById('globalVideoModal');
                modal.style.display = 'none';
                var player = document.getElementById('videoModalPlayer');
                player.pause();
                player.src = '';
            };

            /* 导航视频 */
            window.navigateVideo = function(delta) {
                var newIndex = window.globalVideoIndex + delta;
                /* 找到下一个有视频的镜头 */
                while (newIndex >= 0 && newIndex < window.globalVideosData.length) {
                    if (window.globalVideosData[newIndex] && window.globalVideosData[newIndex].video_path) {
                        window.globalVideoIndex = newIndex;
                        window.updateVideoModal();
                        return;
                    }
                    newIndex += delta;
                }
            };

            /* ESC 关闭弹窗 */
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    var videoModal = document.getElementById('globalVideoModal');
                    if (videoModal && videoModal.style.display === 'flex') {
                        window.closeVideoModal();
                    }
                }
            });

            console.log('[视频预览] 弹窗已初始化');
         " style="display:none" />
    '''

    # 添加视频数据更新脚本（使用base64编码避免特殊字符问题）
    videos_json = json.dumps(videos_data, ensure_ascii=True)
    videos_b64 = base64.b64encode(videos_json.encode('utf-8')).decode('ascii')
    update_script = f'''
    <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
         onload="try {{ window.globalVideosData = JSON.parse(atob('{videos_b64}')); console.log('[视频卡片] 已更新视频数据，共', window.globalVideosData.length, '个'); }} catch(e) {{ console.error('[视频卡片] 数据解析错误:', e); }}"
         style="display:none" />
    '''
    cards_html += update_script

    return cards_html


def get_video_stats_html() -> str:
    """生成视频统计信息HTML"""
    if current_project is None or len(current_project.shots) == 0:
        return '<div class="video-stats">📊 暂无镜头数据</div>'

    total_shots = len(current_project.shots)
    shots_with_images = sum(1 for s in current_project.shots if s.output_image and os.path.exists(s.output_image))

    # 计算已生成视频数
    video_count = 0
    for shot in current_project.shots:
        if shot.output_image:
            base_path = os.path.splitext(shot.output_image)[0]
            for ext in ['.mp4', '.webm', '.avi']:
                if os.path.exists(base_path + ext):
                    video_count += 1
                    break

    return f'''
    <div class="video-stats">
        📊 共 {total_shots} 个镜头 | 🖼️ {shots_with_images} 个已有图片 | 🎬 {video_count} 个已生成视频
    </div>
    <style>
        .video-stats {{
            text-align: center;
            padding: 10px;
            font-size: 13px;
            color: #9ca3af;
            border-top: 1px solid #333;
            margin-top: 10px;
            background: rgba(124, 58, 237, 0.1);
            border-radius: 6px;
        }}
    </style>
    '''


def get_shot_cards_html() -> str:
    """生成镜头卡片HTML，每个镜头显示缩略图和生成按钮，支持点击弹窗预览"""
    if current_project is None or len(current_project.shots) == 0:
        return '<div class="no-shots">暂无镜头，请先在编排页添加镜头</div>'

    cards_html = '<div class="shot-cards-container">'

    # 存储每个镜头的完整数据用于弹窗
    shots_data = []

    for i, shot in enumerate(current_project.shots, 1):
        has_image = shot.output_image and os.path.exists(shot.output_image)
        status_class = "completed" if has_image else "pending"
        status_icon = "✅" if has_image else "⏳"

        # 缩略图或占位符
        img_data_uri = ""
        if has_image:
            try:
                with open(shot.output_image, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                ext = shot.output_image.lower().split('.')[-1]
                mime_type = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                img_data_uri = f"data:{mime_type};base64,{img_data}"
                thumb_html = f'<img src="{img_data_uri}" class="shot-thumb" />'
            except Exception as e:
                thumb_html = '<div class="shot-thumb-placeholder">⚠️<br/>加载失败</div>'
        else:
            thumb_html = '<div class="shot-thumb-placeholder">🖼️<br/>待生成</div>'

        # 镜头描述（截断用于卡片）
        desc_short = shot.description[:40] + "..." if len(shot.description) > 40 else shot.description

        # 收集完整数据用于弹窗
        # 获取角色名称列表
        char_names = []
        if current_project and shot.characters_in_shot:
            for cid in shot.characters_in_shot:
                char = current_project.get_character_by_id(cid)
                if char:
                    char_names.append(char.name)

        # 获取场景名称
        scene_name = "未设置"
        if current_project and shot.scene_id:
            scene = current_project.get_scene_by_id(shot.scene_id)
            if scene:
                scene_name = scene.name

        # 获取景别
        shot_type = shot.template.value if shot.template else "未设置"

        # 清理文本中的特殊字符，防止 JavaScript 解析错误
        def clean_text(text):
            if not text:
                return ""
            # 移除或替换可能导致问题的字符
            return str(text).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

        shot_info = {
            "num": i,
            "description": clean_text(shot.description),
            "characters": ", ".join(char_names) if char_names else "无",
            "scene": clean_text(scene_name),
            "shot_type": shot_type,
            "camera_angle": shot.camera.distance if shot.camera else "未设置",
            "prompt": clean_text(shot.generated_prompt) or "未生成",
            "has_image": has_image,
            "img_uri": img_data_uri
        }
        shots_data.append(shot_info)

        # 视频生成按钮（仅当已生成图片时显示）
        video_btn_html = ""
        if has_image:
            video_btn_html = f'''
            <button class="shot-video-btn" data-shot-num="{i}" onclick="event.stopPropagation(); window.generateShotVideo({i});">
                🎬 生成视频
            </button>
            '''

        cards_html += f'''
        <div class="shot-card {status_class}" data-shot-num="{i}">
            <div class="shot-card-header">
                <span class="shot-num">镜头 {i}</span>
                <span class="shot-status">{status_icon}</span>
            </div>
            <div class="shot-thumb-container">
                {thumb_html}
            </div>
            <div class="shot-desc">{desc_short}</div>
            {video_btn_html}
        </div>
        '''

    cards_html += '</div>'

    # 将镜头数据传递给全局 JavaScript
    # 使用 ensure_ascii=True 确保中文字符以 \uXXXX 形式转义
    shots_json = json.dumps(shots_data, ensure_ascii=True)

    # 简化的 JavaScript - 只更新数据和确保函数存在
    init_js = f'''
        (function() {{
            console.log('[镜头卡片] 开始初始化...');

            /* 确保全局变量存在 */
            if (typeof window.globalShotsData === 'undefined') {{
                window.globalShotsData = [];
            }}
            if (typeof window.globalCurrentIndex === 'undefined') {{
                window.globalCurrentIndex = 0;
            }}

            /* 定义视频生成函数 */
            window.generateShotVideo = function(shotNum) {{
                console.log('[镜头卡片] 触发视频生成:', shotNum);
                var numInput = document.querySelector('#single_video_shot_num input');
                if (numInput) {{
                    numInput.value = shotNum;
                    numInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                var btn = document.querySelector('.shot-card[data-shot-num="' + shotNum + '"] .shot-video-btn');
                if (btn) {{
                    btn.classList.add('generating');
                    btn.textContent = '⏳ 生成中...';
                }}
                setTimeout(function() {{
                    var triggerBtn = document.querySelector('#single_video_trigger_btn');
                    if (triggerBtn) triggerBtn.click();
                }}, 150);
            }};

            /* 更新镜头数据 */
            window.globalShotsData = {shots_json};
            console.log('[镜头卡片] 数据已更新，共', window.globalShotsData.length, '个镜头');

            /* 如果弹窗正在显示且有数据，更新弹窗内容 */
            var modal = document.getElementById('globalShotModal');
            if (modal && modal.style.display === 'flex' && window.updateGlobalModal) {{
                window.updateGlobalModal();
            }}
        }})();
    '''

    # 使用 <img onload> 来执行 JavaScript
    js_code = init_js.replace('\n', ' ')
    js_base64 = base64.b64encode(js_code.encode('utf-8')).decode('ascii')
    cards_html += f'''
    <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
         onload="eval(atob('{js_base64}'))"
         style="display:none; width:1px; height:1px;" />
    '''

    # 添加样式
    cards_html += '''
    <style>
        .shot-cards-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
            padding: 12px 0;
        }
        .shot-card {
            background: var(--panel-dark, #1a1a2e);
            border: 1px solid var(--border-dark, #333);
            border-radius: 8px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .shot-card:hover {
            border-color: var(--primary, #137fec);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(19, 127, 236, 0.2);
        }
        .shot-card.completed {
            border-color: rgba(34, 197, 94, 0.5);
        }
        .shot-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .shot-num {
            font-weight: 600;
            font-size: 13px;
            color: var(--text-primary, #fff);
        }
        .shot-status { font-size: 14px; }
        .shot-thumb-container {
            width: 100%;
            aspect-ratio: 16/9;
            background: #0a0a15;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        .shot-thumb {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .shot-thumb-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary, #86868b);
            font-size: 12px;
            text-align: center;
        }
        .shot-desc {
            font-size: 11px;
            color: var(--text-secondary, #86868b);
            line-height: 1.4;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .shot-video-btn {
            width: 100%;
            margin-top: 8px;
            padding: 6px 10px;
            background: linear-gradient(135deg, #dc2626, #b91c1c);
            border: none;
            border-radius: 6px;
            color: white;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .shot-video-btn:hover {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            transform: scale(1.02);
            box-shadow: 0 2px 8px rgba(220, 38, 38, 0.4);
        }
        .shot-video-btn:active {
            transform: scale(0.98);
        }
        .shot-video-btn.generating {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            cursor: wait;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .no-shots {
            text-align: center;
            color: var(--text-secondary, #86868b);
            padding: 40px;
        }

        @media (max-width: 768px) {
            .shot-cards-container {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        @media (max-width: 480px) {
            .shot-cards-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
    '''

    return cards_html


def get_workflow_indicator(current_step: int = 0) -> str:
    """生成工作流进度指示器HTML
    current_step: 0=未开始, 1=创建, 2=编排, 3=生成, 4=导出完成
    """
    steps = [
        {"num": "1", "title": "创建", "desc": "添加角色和场景", "action": "去创建"},
        {"num": "2", "title": "编排", "desc": "设计镜头顺序", "action": "去编排"},
        {"num": "3", "title": "生成", "desc": "AI生成图像", "action": "去生成"},
        {"num": "4", "title": "导出", "desc": "下载成品", "action": "去导出"},
    ]

    if current_step == 0:
        status_text = "请选择范例或创建项目开始"
        status_class = ""
    elif current_step < 4:
        status_text = f"当前步骤：{steps[current_step-1]['title']} → {steps[current_step-1]['desc']}"
        status_class = "in-progress"
    else:
        status_text = "✓ 全部完成！可导出作品"
        status_class = "completed"

    steps_html = ""
    for i, step in enumerate(steps, 1):
        if i < current_step:
            step_class = "completed"
            icon = "✓"
        elif i == current_step:
            step_class = "current"
            icon = step["num"]
        else:
            step_class = ""
            icon = step["num"]

        steps_html += f'''
        <div class="workflow-step {step_class}" onclick="document.querySelector('[id$=\\'tab-{['create','arrange','generate','export'][i-1]}\\']')?.click()">
            <div class="step-icon">{icon}</div>
            <div class="step-info">
                <h4>{step["title"]}</h4>
                <p>{step["desc"]}</p>
            </div>
        </div>
        '''

    return f'''
    <div class="workflow-progress">
        <div class="workflow-progress-header">
            <span class="workflow-progress-title">📋 工作流程进度</span>
            <span class="workflow-progress-status {status_class}">{status_text}</span>
        </div>
        <div class="workflow-steps">
            {steps_html}
        </div>
    </div>
    '''


# ========================================
# AI 服务 (ComfyUI 集成)
# ========================================

ai_creative_service = None


def get_ai_service():
    """获取 AI 创意服务实例"""
    global ai_creative_service
    if ai_creative_service is None:
        from services import AICreativeService, ProjectService
        project_service = ProjectService()
        ai_creative_service = AICreativeService(project_service)
    return ai_creative_service


def test_comfyui_connection(host: str, port: int) -> str:
    """测试 ComfyUI 连接"""
    service = get_ai_service()
    result = service.initialize_comfyui(host, int(port))
    if result["success"]:
        return f"✓ 连接成功: {result['message']}"
    else:
        return f"✗ 连接失败: {result['message']}"


def get_comfyui_status() -> Tuple[str, str]:
    """获取 ComfyUI 连接状态

    Returns:
        Tuple[状态HTML, 状态文本]
    """
    service = get_ai_service()
    host = settings.comfyui_host
    port = settings.comfyui_port

    if service.comfyui_client is not None:
        # 已连接，尝试ping确认
        try:
            import requests
            resp = requests.get(f"http://{host}:{port}/system_stats", timeout=2)
            if resp.status_code == 200:
                return (
                    f'<div class="comfyui-status connected">🟢 ComfyUI 已连接 ({host}:{port})</div>',
                    "connected"
                )
        except:
            pass

    # 尝试连接
    try:
        import requests
        resp = requests.get(f"http://{host}:{port}/system_stats", timeout=2)
        if resp.status_code == 200:
            return (
                f'<div class="comfyui-status available">🟡 ComfyUI 可用 ({host}:{port}) - 点击连接</div>',
                "available"
            )
    except:
        pass

    return (
        f'<div class="comfyui-status disconnected">🔴 ComfyUI 未连接 ({host}:{port})</div>',
        "disconnected"
    )


def connect_comfyui() -> Tuple[str, str]:
    """连接 ComfyUI 并加载默认工作流

    Returns:
        Tuple[状态HTML, 消息]
    """
    host = settings.comfyui_host
    port = settings.comfyui_port

    # 先测试连接
    result = test_comfyui_connection(host, port)

    if "连接成功" in result:
        # 连接成功，尝试加载默认工作流
        workflow_result = load_default_workflow()
        status_html = f'<div class="comfyui-status connected">🟢 ComfyUI 已连接 ({host}:{port})</div>'
        return status_html, f"{result}\n{workflow_result}"
    else:
        status_html = f'<div class="comfyui-status disconnected">🔴 ComfyUI 未连接 ({host}:{port})</div>'
        return status_html, result


DEFAULT_WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "workflows/img.json")


def load_default_workflow() -> str:
    """加载默认工作流 (image_z_image_turbo.json)"""
    service = get_ai_service()
    if service.comfyui_client is None:
        return "请先连接 ComfyUI"

    if not os.path.exists(DEFAULT_WORKFLOW_PATH):
        return f"✗ 默认工作流文件不存在: {DEFAULT_WORKFLOW_PATH}"

    success, message = service.comfyui_client.load_workflow_from_file(DEFAULT_WORKFLOW_PATH)

    if success:
        return f"✓ 已加载默认工作流: image_z_image_turbo.json"
    else:
        return f"✗ {message}"


def load_workflow_from_file(file) -> str:
    """从上传的文件加载工作流"""
    if file is None:
        return "请选择工作流文件"

    service = get_ai_service()
    if service.comfyui_client is None:
        return "请先连接 ComfyUI"

    filepath = file if isinstance(file, str) else file.name
    if not os.path.exists(filepath):
        return f"✗ 文件不存在: {filepath}"

    success, message = service.comfyui_client.load_workflow_from_file(filepath)

    if success:
        filename = os.path.basename(filepath)
        return f"✓ 已加载工作流: {filename}"
    else:
        return f"✗ {message}"


def get_style_key(style_name: str) -> str:
    """获取风格键值"""
    style_map = {
        "写实风格": "realistic",
        "动漫风格": "anime",
        "漫画风格": "comic",
        "水彩风格": "watercolor"
    }
    return style_map.get(style_name, "realistic")


# ========================================
# 剧本转分镜手册功能
# ========================================

# 全局存储生成的手册内容


# ========================================
# 视频分析功能
# ========================================

# 全局视频分析服务


def get_video_service():
    """获取视频分析服务实例"""
    global video_analysis_service
    if video_analysis_service is None:
        from services import VideoAnalysisService, ProjectService
        project_service = ProjectService()
        video_analysis_service = VideoAnalysisService(project_service)
    return video_analysis_service


def format_loaded_result(data):
    """格式化加载的结果数据"""
    story_summary = data.get("story_summary", "")
    story_structure = data.get("story_structure", "")
    storyboard = data.get("storyboard", "")

    chars_data = []
    for c in data.get("characters", []):
        chars_data.append([
            c.get("id", ""),
            c.get("name", ""),
            c.get("role_type", ""),
            f"{c.get('first_appearance', 0):.1f}s",
            c.get("appearance_description", "")[:50]
        ])

    scenes_data = []
    for s in data.get("scenes", []):
        scenes_data.append([
            s.get("id", ""),
            s.get("scene_name", ""),
            f"{s.get('start_time', 0):.1f}s",
            f"{s.get('end_time', 0):.1f}s",
            s.get("atmosphere", ""),
            s.get("lighting", "")
        ])

    shots_data = []
    for sh in data.get("shots", []):
        shots_data.append([
            sh.get("id", ""),
            f"{sh.get('timestamp', 0):.1f}s",
            sh.get("shot_type", ""),
            sh.get("camera_angle", ""),
            sh.get("camera_movement", ""),
            sh.get("purpose", "")[:30]
        ])

    points_data = []
    for sp in data.get("story_points", []):
        points_data.append([
            sp.get("id", ""),
            f"{sp.get('timestamp', 0):.1f}s",
            sp.get("title", ""),
            sp.get("point_type", ""),
            sp.get("emotional_impact", "")[:30]
        ])

    frame_images = []
    for f in data.get("frames", [])[:50]:
        if f.get("image_path") and os.path.exists(f.get("image_path", "")):
            frame_images.append(f["image_path"])

    return (
        "✓ 加载成功",
        story_summary,
        story_structure,
        storyboard,
        chars_data,
        scenes_data,
        shots_data,
        points_data,
        frame_images
    )


# ========================================
# 时间线可视化函数
# ========================================

# 关键词高亮配置
HIGHLIGHT_KEYWORDS = {
    "plot": {
        "keywords": ["开场", "铺垫", "发展", "高潮", "转折", "结局", "冲突", "紧张", "悬念", "反转"],
        "color": "highlight-red"
    },
    "character": {
        "keywords": ["主角", "配角", "反派", "主人公", "男主", "女主", "boss", "路人"],
        "color": "highlight-green"
    },
    "scene": {
        "keywords": ["室内", "室外", "夜晚", "白天", "黄昏", "黎明", "雨天", "晴天"],
        "color": "highlight-blue"
    },
    "props": {
        "keywords": ["武器", "道具", "信物", "钥匙", "书信", "手机", "电脑", "车辆"],
        "color": "highlight-yellow"
    },
    "shot": {
        "keywords": ["远景", "全景", "中景", "近景", "特写", "俯视", "仰视", "平视", "推", "拉", "摇", "移"],
        "color": "highlight-purple"
    }
}


def highlight_keywords(text: str, category: str) -> str:
    """对文本中的关键词进行高亮"""
    if not text or category not in HIGHLIGHT_KEYWORDS:
        return text

    config = HIGHLIGHT_KEYWORDS[category]
    result = text
    for keyword in config["keywords"]:
        if keyword in result:
            result = result.replace(
                keyword,
                f'<span class="{config["color"]}">{keyword}</span>'
            )
    return result


def format_time_badge(seconds: float) -> str:
    """格式化时间徽章"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# ========================================
# API 配置管理
# ========================================

# 全局 API 配置存储
API_CONFIG = {
    "llm": {"provider": "Claude Code CLI (默认)", "api_key": "", "api_url": ""},
    "image": {"provider": "通义万相 (推荐)", "api_key": "", "api_url": ""},
    "video": {"provider": "智谱 CogVideoX (推荐)", "api_key": "", "api_url": ""}
}

def save_llm_config(provider_cn, api_key_cn, api_url_cn, provider_intl, api_key_intl, api_url_intl):
    """保存大语言模型 API 配置"""
    global API_CONFIG
    # 优先使用国内配置
    if provider_cn and api_key_cn:
        API_CONFIG["llm"] = {
            "provider": provider_cn,
            "api_key": api_key_cn,
            "api_url": api_url_cn or get_default_llm_url(provider_cn),
            "region": "cn"
        }
        return f"✅ 已保存 LLM 配置: {provider_cn}"
    elif provider_intl and api_key_intl:
        API_CONFIG["llm"] = {
            "provider": provider_intl,
            "api_key": api_key_intl,
            "api_url": api_url_intl or get_default_llm_url(provider_intl),
            "region": "intl"
        }
        return f"✅ 已保存 LLM 配置: {provider_intl}"
    return "⚠️ 请选择服务商并填写 API Key"

def save_image_config(provider_cn, api_key_cn, api_url_cn, provider_intl, api_key_intl, api_url_intl):
    """保存图像生成 API 配置"""
    global API_CONFIG
    if provider_cn and api_key_cn:
        API_CONFIG["image"] = {
            "provider": provider_cn,
            "api_key": api_key_cn,
            "api_url": api_url_cn or get_default_image_url(provider_cn),
            "region": "cn"
        }
        return f"✅ 已保存图像生成配置: {provider_cn}"
    elif provider_intl and api_key_intl:
        API_CONFIG["image"] = {
            "provider": provider_intl,
            "api_key": api_key_intl,
            "api_url": api_url_intl or get_default_image_url(provider_intl),
            "region": "intl"
        }
        return f"✅ 已保存图像生成配置: {provider_intl}"
    return "⚠️ 请选择服务商并填写 API Key"

def save_video_config(provider_cn, api_key_cn, api_url_cn, provider_intl, api_key_intl, api_url_intl):
    """保存视频生成 API 配置"""
    global API_CONFIG
    if provider_cn and api_key_cn:
        API_CONFIG["video"] = {
            "provider": provider_cn,
            "api_key": api_key_cn,
            "api_url": api_url_cn or get_default_video_url(provider_cn),
            "region": "cn"
        }
        return f"✅ 已保存视频生成配置: {provider_cn}"
    elif provider_intl and api_key_intl:
        API_CONFIG["video"] = {
            "provider": provider_intl,
            "api_key": api_key_intl,
            "api_url": api_url_intl or get_default_video_url(provider_intl),
            "region": "intl"
        }
        return f"✅ 已保存视频生成配置: {provider_intl}"
    return "⚠️ 请选择服务商并填写 API Key"

def get_default_llm_url(provider):
    """获取 LLM 默认 API 地址"""
    urls = {
        "DeepSeek": "https://api.deepseek.com/chat/completions",
        "智谱 GLM (推荐)": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "智谱 GLM": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "通义千问": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "百度文心": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
        "讯飞星火": "wss://spark-api.xf-yun.com/v3.5/chat",
        "月之暗面 Kimi": "https://api.moonshot.cn/v1/chat/completions",
        "OpenAI GPT": "https://api.openai.com/v1/chat/completions",
        "Anthropic Claude": "https://api.anthropic.com/v1/messages",
        "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    }
    return urls.get(provider, "")

def get_default_image_url(provider):
    """获取图像生成默认 API 地址"""
    urls = {
        "通义万相 (推荐)": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        "百度文心一格": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/text2image",
        "智谱 CogView": "https://open.bigmodel.cn/api/paas/v4/images/generations",
        "LiblibAI": "https://www.liblib.art/api",
        "Stability AI (SD)": "https://api.stability.ai/v1/generation",
        "OpenAI DALL-E": "https://api.openai.com/v1/images/generations",
        "Midjourney": "https://api.mymidjourney.ai/api"
    }
    return urls.get(provider, "")

def get_default_video_url(provider):
    """获取视频生成默认 API 地址"""
    urls = {
        "智谱 CogVideoX (推荐)": "https://open.bigmodel.cn/api/paas/v4/videos/generations",
        "通义视频生成": "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation",
        "可灵 AI": "https://api.kuaishou.com/klingai",
        "Runway Gen-3": "https://api.runwayml.com/v1",
        "Pika Labs": "https://api.pika.art/v1",
        "Luma AI": "https://api.lumalabs.ai/v1"
    }
    return urls.get(provider, "")


# ========================================
# AI 辅助生成功能 (使用 Claude Code CLI)
# ========================================

import requests
import subprocess
import threading
import queue

# 全局 CLI 输出队列
cli_output_queue = queue.Queue()
cli_output_history = []

def call_claude_cli(prompt: str, system_prompt: str = "") -> str:
    """通过 Claude Code CLI 调用 AI（默认方式）"""
    global cli_output_history

    try:
        # 构建完整提示
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # 添加到 CLI 输出
        cli_output_history.append(f"[发送] {prompt[:100]}...")

        # 调用 claude 命令行 (使用 -p 传递提示词，--output-format text 获取纯文本输出)
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            cli_output_history.append(f"[接收] {output[:200]}...")
            return output
        else:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            cli_output_history.append(f"[错误] {error_msg[:100]}")
            return f"⚠️ CLI 调用失败: {error_msg}"

    except subprocess.TimeoutExpired:
        cli_output_history.append("[超时] Claude CLI 响应超时")
        return "⚠️ Claude CLI 响应超时，请稍后重试"
    except FileNotFoundError:
        cli_output_history.append("[错误] 未找到 claude 命令")
        return "⚠️ 未找到 claude 命令，请确保 Claude Code CLI 已安装并在 PATH 中"
    except Exception as e:
        cli_output_history.append(f"[错误] {str(e)[:100]}")
        return f"⚠️ 调用出错: {str(e)}"


def get_cli_output() -> str:
    """获取 CLI 输出历史"""
    global cli_output_history
    # 只保留最近 50 条
    if len(cli_output_history) > 50:
        cli_output_history = cli_output_history[-50:]
    return "\n".join(cli_output_history[-20:]) if cli_output_history else "等待 AI 调用..."


def clear_cli_output() -> str:
    """清空 CLI 输出"""
    global cli_output_history
    cli_output_history = []
    return "已清空"


def call_llm_api(prompt: str, system_prompt: str = "") -> str:
    """调用 LLM API 生成文本 - 默认使用 Claude Code CLI"""
    global API_CONFIG

    llm_config = API_CONFIG.get("llm", {})
    provider = llm_config.get("provider", "Claude Code CLI (默认)")

    # 默认使用 Claude Code CLI
    if "Claude Code CLI" in provider or not llm_config.get("api_key"):
        return call_claude_cli(prompt, system_prompt)

    # 其他 API 调用方式
    api_key = llm_config.get("api_key", "")
    api_url = llm_config.get("api_url", "")

    if not api_key:
        return call_claude_cli(prompt, system_prompt)  # 没有配置 API 时使用 CLI

    if not api_url:
        api_url = get_default_llm_url(provider)

    try:
        # 智谱 GLM API 格式
        if "智谱" in provider or "bigmodel" in api_url:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": "glm-4-flash",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }

            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "生成失败")
            else:
                return f"API 调用失败: {response.status_code} - {response.text[:100]}"

        # 通义千问 API 格式
        elif "通义" in provider or "dashscope" in api_url:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "qwen-turbo",
                "input": {
                    "messages": [
                        {"role": "system", "content": system_prompt} if system_prompt else {"role": "system", "content": "你是一个专业的分镜设计助手。"},
                        {"role": "user", "content": prompt}
                    ]
                }
            }

            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("output", {}).get("text", "生成失败")
            else:
                return f"API 调用失败: {response.status_code}"

        # Anthropic Claude API 格式
        elif "Claude" in provider or "anthropic" in api_url:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            messages = [{"role": "user", "content": prompt}]

            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1024,
                "messages": messages
            }
            if system_prompt:
                data["system"] = system_prompt

            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("content", [{}])[0].get("text", "生成失败")
            else:
                return f"API 调用失败: {response.status_code}"

        # DeepSeek API 格式 (OpenAI 兼容)
        elif "DeepSeek" in provider or "deepseek" in api_url:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048
            }

            response = requests.post(api_url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "生成失败")
            else:
                return f"API 调用失败: {response.status_code} - {response.text[:100]}"

        # OpenAI 兼容格式 (默认)
        else:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }

            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "生成失败")
            else:
                return f"API 调用失败: {response.status_code}"

    except requests.exceptions.Timeout:
        return "⚠️ API 请求超时，请稍后重试"
    except Exception as e:
        return f"⚠️ API 调用出错: {str(e)}"


def ai_generate_character_desc(name: str) -> str:
    """AI 生成角色描述"""
    if not name or not name.strip():
        return "请先输入角色名称"

    system_prompt = """你是一个专业的分镜设计助手，擅长创建生动的角色描述。
请根据角色名称，生成详细的角色外貌描述，包括：
- 性别、年龄范围
- 面部特征（眼睛、头发、表情特点）
- 体型和姿态
- 服装风格
- 独特标识或配饰
描述要具体、视觉化，适合用于图像生成。直接输出描述，不需要任何前缀。"""

    prompt = f"请为角色「{name}」生成详细的外貌描述（100-150字）："

    result = call_llm_api(prompt, system_prompt)
    return result


def ai_generate_scene_desc(name: str) -> str:
    """AI 生成场景描述"""
    if not name or not name.strip():
        return "请先输入场景名称"

    system_prompt = """你是一个专业的分镜设计助手，擅长创建生动的场景描述。
请根据场景名称，生成详细的环境描述，包括：
- 空间布局和规模
- 光线条件（自然光/人工光、方向、强度）
- 色调和氛围
- 关键物品和装饰
- 天气或时间特征（如适用）
描述要具体、视觉化，适合用于图像生成。直接输出描述，不需要任何前缀。"""

    prompt = f"请为场景「{name}」生成详细的环境描述（100-150字）："

    result = call_llm_api(prompt, system_prompt)
    return result


def ai_generate_shot_desc(shot_type: str, characters: List[str], scene: str, context: str = "") -> str:
    """AI 生成镜头描述"""
    if not shot_type:
        return "请先选择镜头类型"

    system_prompt = """你是一个专业的分镜设计助手，擅长创建电影级的镜头描述。
请根据提供的镜头类型、角色和场景信息，生成详细的镜头描述，包括：
- 角色的动作和表情
- 角色之间的互动关系
- 构图要点
- 画面情绪和氛围
描述要具体、动态，能够清晰指导图像生成。直接输出描述，不需要任何前缀。"""

    char_text = "、".join(characters) if characters else "无特定角色"
    scene_text = scene if scene else "未指定场景"

    prompt = f"""镜头类型: {shot_type}
出镜角色: {char_text}
场景: {scene_text}
{f'背景信息: {context}' if context else ''}

请生成这个镜头的详细描述（80-120字）："""

    result = call_llm_api(prompt, system_prompt)
    return result


def ai_optimize_prompt(original_prompt: str, style: str = "电影感") -> str:
    """AI 优化图像生成提示词"""
    if not original_prompt or not original_prompt.strip():
        return "请先输入或生成提示词"

    system_prompt = f"""你是一个专业的 AI 图像生成提示词优化师。
当前风格设定: {style}
请将用户的描述优化为更适合 AI 图像生成的提示词，要求：
1. 添加画面质量关键词（如 masterpiece, high quality, detailed 等）
2. 强化视觉描述（光影、色调、氛围）
3. 添加适合{style}风格的修饰词
4. 保持原意的同时让描述更加精确
5. 输出英文提示词（更适合主流图像生成模型）
直接输出优化后的提示词，不需要任何解释。"""

    prompt = f"请优化以下分镜描述为 AI 图像生成提示词:\n\n{original_prompt}"

    result = call_llm_api(prompt, system_prompt)
    return result


def ai_generate_project_summary() -> str:
    """AI 生成项目摘要"""
    global current_project

    if not current_project or (not current_project.characters and not current_project.shots):
        return "项目为空，无法生成摘要"

    # 收集项目信息
    char_names = [c.name for c in current_project.characters]
    scene_names = [s.name for s in current_project.scenes]
    shot_count = len(current_project.shots)
    shot_types = [s.template.value if hasattr(s.template, 'value') else str(s.template) for s in current_project.shots]

    system_prompt = """你是一个专业的分镜项目分析师。
请根据项目信息生成一份简洁的项目摘要，包括：
1. 项目规模概述
2. 主要角色介绍
3. 场景设定
4. 镜头安排特点
5. 整体风格建议
控制在200字以内，语言专业但易懂。"""

    prompt = f"""项目信息:
- 角色 ({len(char_names)}个): {', '.join(char_names) if char_names else '无'}
- 场景 ({len(scene_names)}个): {', '.join(scene_names) if scene_names else '无'}
- 镜头数量: {shot_count}
- 镜头类型分布: {', '.join(set(shot_types)) if shot_types else '无'}

请生成项目摘要："""

    result = call_llm_api(prompt, system_prompt)
    return result


# ========================================
# 构建界面
# ========================================

def create_ui():
    """创建界面 - PC 全屏优化布局 (深色主题)"""

    # 深色主题配色方案 (参考模板设计)
    dark_theme = gr.themes.Base(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=["Inter", "system-ui", "sans-serif"],
        font_mono=["JetBrains Mono", "Consolas", "monospace"],
    ).set(
        # 背景色
        body_background_fill="#101922",
        body_background_fill_dark="#101922",
        background_fill_primary="#16202a",
        background_fill_primary_dark="#16202a",
        background_fill_secondary="#1c252e",
        background_fill_secondary_dark="#1c252e",
        # 边框
        border_color_primary="#233648",
        border_color_primary_dark="#233648",
        border_color_accent="#137fec",
        # 区块
        block_background_fill="#1c252e",
        block_background_fill_dark="#1c252e",
        block_border_width="1px",
        block_border_color="#233648",
        block_radius="8px",
        block_shadow="0 2px 8px rgba(0,0,0,0.3)",
        # 按钮
        button_primary_background_fill="#137fec",
        button_primary_background_fill_hover="#1a8cff",
        button_primary_text_color="white",
        button_primary_border_color="#137fec",
        button_secondary_background_fill="#233648",
        button_secondary_background_fill_hover="#2d445a",
        button_secondary_text_color="#92adc9",
        button_secondary_border_color="#233648",
        # 输入框
        input_background_fill="#111a22",
        input_background_fill_dark="#111a22",
        input_border_color="#233648",
        input_border_color_dark="#233648",
        input_border_width="1px",
        # 文字颜色
        body_text_color="#e2e8f0",
        body_text_color_dark="#e2e8f0",
        body_text_color_subdued="#92adc9",
        body_text_color_subdued_dark="#92adc9",
        # 表格
        table_border_color="#233648",
        table_even_background_fill="#16202a",
        table_odd_background_fill="#1c252e",
        # 其他
        panel_background_fill="#16202a",
        panel_border_color="#233648",
    )

    with gr.Blocks(
        title="AI 分镜 Pro",
        theme=dark_theme
    ) as demo:

        # ===== 全局样式 =====
        gr.HTML("""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1" rel="stylesheet">
        <style>
            /* ===== 全局深色主题 ===== */
            :root {
                --bg-dark: #101922;
                --surface-dark: #16202a;
                --panel-dark: #1c252e;
                --card-dark: #1e2936;
                --border-dark: #233648;
                --primary: #137fec;
                --text-primary: #e2e8f0;
                --text-secondary: #92adc9;
            }

            body, .gradio-container {
                background: var(--bg-dark) !important;
                font-family: 'Inter', system-ui, sans-serif !important;
            }

            /* 隐藏行不占空间 */
            .gradio-row[style*="display: none"],
            .gradio-column[style*="display: none"],
            .hidden, [hidden] {
                display: none !important;
                margin: 0 !important;
                padding: 0 !important;
                height: 0 !important;
                overflow: hidden !important;
            }

            /* ===== 顶部导航栏 ===== */
            .app-header {
                background: var(--bg-dark);
                padding: 12px 24px;
                border-bottom: 1px solid var(--border-dark);
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: -16px -16px 16px -16px;
            }
            .app-header .logo {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .app-header .logo-icon {
                width: 36px;
                height: 36px;
                background: var(--primary);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 20px;
            }
            .app-header h1 {
                color: white;
                font-size: 18px;
                font-weight: 700;
                margin: 0;
            }
            .status-pill {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                padding: 6px 14px;
                border-radius: 20px;
                color: var(--text-secondary);
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .status-dot {
                width: 8px;
                height: 8px;
                background: #22c55e;
                border-radius: 50%;
                position: relative;
            }
            .status-dot::before {
                content: '';
                position: absolute;
                inset: 0;
                background: #22c55e;
                border-radius: 50%;
                animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
            }
            @keyframes ping {
                75%, 100% { transform: scale(2); opacity: 0; }
            }

            /* ===== 英雄区域 ===== */
            .hero-section {
                background: linear-gradient(135deg, rgba(19, 127, 236, 0.15) 0%, rgba(16, 25, 34, 0.9) 100%),
                            linear-gradient(180deg, #16202a 0%, #101922 100%);
                border: 1px solid var(--border-dark);
                border-radius: 12px;
                padding: 32px;
                margin-bottom: 24px;
                position: relative;
                overflow: hidden;
            }
            .hero-section::before {
                content: '';
                position: absolute;
                top: -50%;
                right: -20%;
                width: 60%;
                height: 200%;
                background: radial-gradient(circle, rgba(19, 127, 236, 0.1) 0%, transparent 60%);
                pointer-events: none;
            }
            .hero-section h2 {
                color: white;
                font-size: 28px;
                font-weight: 700;
                margin: 0 0 8px 0;
            }
            .hero-section p {
                color: var(--text-secondary);
                font-size: 15px;
                margin: 0;
            }
            .hero-actions {
                display: flex;
                gap: 12px;
                margin-top: 24px;
            }
            .hero-btn {
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                border: none;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s;
            }
            .hero-btn-primary {
                background: var(--primary);
                color: white;
            }
            .hero-btn-primary:hover {
                background: #1a8cff;
                box-shadow: 0 4px 12px rgba(19, 127, 236, 0.4);
            }
            .hero-btn-secondary {
                background: rgba(255,255,255,0.1);
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .hero-btn-secondary:hover {
                background: rgba(255,255,255,0.15);
            }

            /* ===== 工作流卡片 ===== */
            .workflow-section {
                margin-bottom: 24px;
            }
            .workflow-section h3 {
                color: white;
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 16px 0;
            }
            .workflow-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
            }
            .workflow-card {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 12px;
                padding: 16px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .workflow-card:hover {
                border-color: rgba(19, 127, 236, 0.5);
                box-shadow: 0 0 20px rgba(19, 127, 236, 0.15);
                transform: translateY(-2px);
            }
            .workflow-card .icon-box {
                width: 100%;
                height: 80px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 12px;
                font-size: 32px;
                border: 1px solid rgba(255,255,255,0.05);
            }
            .workflow-card.create .icon-box { background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, var(--card-dark) 100%); }
            .workflow-card.arrange .icon-box { background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, var(--card-dark) 100%); }
            .workflow-card.generate .icon-box { background: linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, var(--card-dark) 100%); }
            .workflow-card.export .icon-box { background: linear-gradient(135deg, rgba(20, 184, 166, 0.2) 0%, var(--card-dark) 100%); }
            .workflow-card h4 {
                color: white;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 4px 0;
            }
            .workflow-card p {
                color: var(--text-secondary);
                font-size: 12px;
                margin: 0;
            }

            /* ===== 快速开始模板 ===== */
            .templates-section h3 {
                color: white;
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 16px 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .templates-section h3 a {
                color: var(--primary);
                font-size: 13px;
                font-weight: 500;
                text-decoration: none;
            }
            .template-card {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 12px;
                padding: 16px;
                display: flex;
                gap: 16px;
                margin-bottom: 12px;
                transition: all 0.2s;
                position: relative;
                cursor: pointer;
            }
            .template-card:hover {
                border-color: rgba(255,255,255,0.2);
                background: var(--panel-dark);
            }
            .template-card .info { flex: 1; }
            .template-card .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                margin-bottom: 8px;
            }
            .template-card .badge.drama { background: rgba(249, 115, 22, 0.2); color: #fb923c; }
            .template-card .badge.action { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
            .template-card h4 {
                color: white;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 4px 0;
            }
            .template-card p {
                color: var(--text-secondary);
                font-size: 12px;
                margin: 0 0 8px 0;
                line-height: 1.4;
            }
            .template-card .meta {
                color: #64748b;
                font-size: 11px;
                font-family: monospace;
            }
            .template-card .thumb {
                width: 120px;
                height: 80px;
                border-radius: 8px;
                background: var(--border-dark);
                border: 1px solid rgba(255,255,255,0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }

            /* ===== 右侧面板 ===== */
            .section-title {
                font-size: 12px;
                font-weight: 600;
                color: var(--text-secondary);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid var(--border-dark);
                display: flex;
                align-items: center;
                gap: 8px;
            }

            /* ===== CLI 终端样式 ===== */
            .cli-terminal {
                background: #0a0f14;
                border: 1px solid var(--border-dark);
                border-radius: 8px;
                overflow: hidden;
            }
            .cli-terminal-header {
                background: var(--card-dark);
                padding: 8px 12px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .cli-terminal-header span {
                color: var(--text-secondary);
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .cli-terminal-dots {
                display: flex;
                gap: 6px;
            }
            .cli-terminal-dots div {
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }
            .cli-terminal-dots .red { background: rgba(239, 68, 68, 0.5); }
            .cli-terminal-dots .yellow { background: rgba(234, 179, 8, 0.5); }
            .cli-terminal-dots .green { background: rgba(34, 197, 94, 0.5); }
            .cli-terminal-content {
                padding: 12px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: rgba(34, 197, 94, 0.9);
                line-height: 1.6;
                max-height: 200px;
                overflow-y: auto;
            }

            /* ===== 项目摘要卡片 ===== */
            .project-summary-card {
                margin-bottom: 16px;
            }
            .project-summary-card:empty {
                display: none;
            }
            .project-summary-content {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 12px;
                padding: 16px 20px;
            }
            .summary-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid var(--border-dark);
            }
            .project-title {
                color: white;
                font-size: 16px;
                font-weight: 600;
            }
            .project-meta {
                color: var(--text-secondary);
                font-size: 12px;
            }
            .summary-progress {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
            }
            .progress-bar {
                flex: 1;
                height: 6px;
                background: var(--surface-dark);
                border-radius: 3px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #22c55e, #16a34a);
                border-radius: 3px;
                transition: width 0.3s;
            }
            .progress-text {
                color: #22c55e;
                font-size: 11px;
                font-weight: 500;
                white-space: nowrap;
            }
            .summary-section {
                margin-bottom: 12px;
            }
            .summary-section:last-child {
                margin-bottom: 0;
            }
            .section-label {
                color: var(--text-secondary);
                font-size: 11px;
                font-weight: 500;
                margin-bottom: 6px;
            }
            .tags-row {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }
            .tag {
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
            .char-tag {
                background: rgba(59, 130, 246, 0.15);
                color: #60a5fa;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            .scene-tag {
                background: rgba(168, 85, 247, 0.15);
                color: #c084fc;
                border: 1px solid rgba(168, 85, 247, 0.3);
            }
            .shots-preview {
                background: var(--surface-dark);
                border-radius: 8px;
                padding: 8px 12px;
            }
            .shot-item {
                color: var(--text-secondary);
                font-size: 12px;
                padding: 4px 0;
                border-bottom: 1px solid var(--border-dark);
            }
            .shot-item:last-child {
                border-bottom: none;
            }
            .shot-item.more {
                color: var(--primary);
                font-style: italic;
            }
            .empty {
                color: var(--text-secondary);
                font-size: 12px;
                font-style: italic;
            }

            /* ===== ComfyUI 工作流设置 ===== */
            .workflow-label {
                color: var(--text-secondary) !important;
                font-size: 12px !important;
                margin: 8px 0 4px 0 !important;
            }
            .workflow-status {
                font-size: 11px !important;
                color: var(--text-secondary) !important;
                background: transparent !important;
                border: none !important;
                padding: 4px 0 !important;
            }
            .workflow-status textarea {
                background: transparent !important;
                border: none !important;
                color: var(--text-secondary) !important;
                font-size: 11px !important;
                min-height: 20px !important;
            }

            /* ===== 工作区标签页 ===== */
            .work-tabs-header {
                border-top: 1px solid var(--border-dark);
                padding-top: 16px;
                margin-top: 8px;
            }
            .work-tabs-header span {
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 500;
            }

            /* ===== 标签页统一样式 ===== */
            /* 主标签容器 */
            .gradio-container .tabs {
                width: 100% !important;
                max-width: 100% !important;
            }

            /* 标签导航栏 */
            .tabs > .tab-nav {
                display: flex !important;
                justify-content: flex-start !important;
                gap: 4px !important;
                background: var(--surface-dark) !important;
                padding: 6px !important;
                border-radius: 10px !important;
                margin-bottom: 16px !important;
                flex-wrap: wrap !important;
            }

            /* 标签按钮 - 统一宽度 */
            .tabs > .tab-nav > button {
                flex: 1 1 0 !important;
                min-width: 0 !important;
                padding: 10px 12px !important;
                font-size: 13px !important;
                font-weight: 500 !important;
                border-radius: 6px !important;
                background: transparent !important;
                color: var(--text-secondary) !important;
                border: none !important;
                transition: all 0.2s !important;
                text-align: center !important;
                white-space: nowrap !important;
            }

            /* 标签悬停效果 */
            .tabs > .tab-nav > button:hover {
                background: var(--card-dark) !important;
                color: white !important;
            }

            /* 激活标签样式 */
            .tabs > .tab-nav > button.selected {
                background: var(--primary) !important;
                color: white !important;
                box-shadow: 0 2px 8px rgba(19, 127, 236, 0.3) !important;
            }

            /* 标签内容区域 - 统一宽度和排版 */
            .tabs > .tabitem {
                width: 100% !important;
                max-width: 100% !important;
                min-height: 500px !important;
                padding: 20px !important;
                background: var(--panel-dark) !important;
                border: 1px solid var(--border-dark) !important;
                border-radius: 12px !important;
                box-sizing: border-box !important;
            }

            /* 确保所有标签内容等宽 */
            .tabs > .tabitem > * {
                max-width: 100% !important;
            }

            /* 标签内的行元素 */
            .tabs > .tabitem .row {
                width: 100% !important;
                margin: 0 !important;
            }

            /* 标签内的列元素 */
            .tabs > .tabitem .column {
                padding: 0 8px !important;
            }

            /* ===== 前序内容摘要卡片 ===== */
            .step-summary {
                background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, var(--card-dark) 100%);
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 10px;
                padding: 12px 16px;
                margin-bottom: 16px;
            }
            .step-summary-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .step-summary-title {
                color: #22c55e;
                font-size: 12px;
                font-weight: 600;
            }
            .step-summary-edit {
                color: var(--primary);
                font-size: 11px;
                cursor: pointer;
            }
            .step-summary-content {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }
            .step-summary-tag {
                background: var(--surface-dark);
                border: 1px solid var(--border-dark);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: var(--text-secondary);
            }
            .step-summary-tag.char { border-left: 3px solid #60a5fa; }
            .step-summary-tag.scene { border-left: 3px solid #c084fc; }
            .step-summary-tag.shot { border-left: 3px solid #f59e0b; }
            .step-summary-empty {
                color: var(--text-secondary);
                font-size: 11px;
                font-style: italic;
            }

            /* ===== 镜头卡片 ===== */
            .shot-card {
                background: var(--panel-dark);
                border: 1px solid var(--border-dark);
                border-radius: 8px;
                margin-bottom: 12px;
                overflow: hidden;
                transition: all 0.2s;
            }
            .shot-card:hover {
                border-color: #3b526b;
            }
            .shot-card-indicator {
                width: 4px;
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
            }
            .shot-card-indicator.wide { background: #60a5fa; }
            .shot-card-indicator.medium { background: #a78bfa; }
            .shot-card-indicator.close { background: #818cf8; }

            /* ===== Gradio 组件覆盖 ===== */
            .gradio-container .block {
                background: var(--panel-dark) !important;
                border-color: var(--border-dark) !important;
            }
            .gradio-container input, .gradio-container textarea, .gradio-container select {
                background: var(--bg-dark) !important;
                border-color: var(--border-dark) !important;
                color: var(--text-primary) !important;
            }
            .gradio-container input:focus, .gradio-container textarea:focus {
                border-color: var(--primary) !important;
                box-shadow: 0 0 0 2px rgba(19, 127, 236, 0.2) !important;
            }
            .gradio-container label {
                color: var(--text-secondary) !important;
            }
            .gradio-container .prose, .gradio-container .markdown {
                color: var(--text-primary) !important;
            }
            .gradio-container .prose h1, .gradio-container .prose h2, .gradio-container .prose h3 {
                color: white !important;
            }
            .gradio-container .tabs {
                background: transparent !important;
                border-color: var(--border-dark) !important;
            }
            .gradio-container button.selected {
                background: var(--primary) !important;
                color: white !important;
            }

            /* ===== Radio 和 CheckboxGroup 选中状态 ===== */
            /* Radio 组件 - 按钮式样式 */
            .gradio-container .wrap label:has(input[type="radio"]),
            .gradio-container form label:has(input[type="radio"]),
            .gradio-container fieldset label:has(input[type="radio"]) {
                display: inline-flex !important;
                align-items: center !important;
                padding: 10px 18px !important;
                border-radius: 8px !important;
                border: 1.5px solid var(--border-dark) !important;
                background: var(--card-dark) !important;
                color: var(--text-secondary) !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
                margin: 4px !important;
                font-size: 14px !important;
            }
            .gradio-container .wrap label:has(input[type="radio"]):hover,
            .gradio-container form label:has(input[type="radio"]):hover,
            .gradio-container fieldset label:has(input[type="radio"]):hover {
                border-color: var(--primary) !important;
                background: rgba(19, 127, 236, 0.08) !important;
                color: var(--text-primary) !important;
            }
            .gradio-container .wrap label:has(input[type="radio"]:checked),
            .gradio-container form label:has(input[type="radio"]:checked),
            .gradio-container fieldset label:has(input[type="radio"]:checked) {
                background: var(--primary) !important;
                border-color: var(--primary) !important;
                color: white !important;
                font-weight: 500 !important;
                box-shadow: 0 2px 10px rgba(19, 127, 236, 0.35) !important;
            }
            /* 隐藏原生 radio 圆点 */
            .gradio-container input[type="radio"] {
                position: absolute !important;
                opacity: 0 !important;
                width: 0 !important;
                height: 0 !important;
            }

            /* CheckboxGroup 组件 - 按钮式样式 (绿色) */
            .gradio-container .wrap label:has(input[type="checkbox"]),
            .gradio-container form label:has(input[type="checkbox"]),
            .gradio-container fieldset label:has(input[type="checkbox"]) {
                display: inline-flex !important;
                align-items: center !important;
                padding: 10px 18px !important;
                border-radius: 8px !important;
                border: 1.5px solid var(--border-dark) !important;
                background: var(--card-dark) !important;
                color: var(--text-secondary) !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
                margin: 4px !important;
                font-size: 14px !important;
            }
            .gradio-container .wrap label:has(input[type="checkbox"]):hover,
            .gradio-container form label:has(input[type="checkbox"]):hover,
            .gradio-container fieldset label:has(input[type="checkbox"]):hover {
                border-color: #22c55e !important;
                background: rgba(34, 197, 94, 0.08) !important;
                color: var(--text-primary) !important;
            }
            .gradio-container .wrap label:has(input[type="checkbox"]:checked),
            .gradio-container form label:has(input[type="checkbox"]:checked),
            .gradio-container fieldset label:has(input[type="checkbox"]:checked) {
                background: #22c55e !important;
                border-color: #22c55e !important;
                color: white !important;
                font-weight: 500 !important;
                box-shadow: 0 2px 10px rgba(34, 197, 94, 0.35) !important;
            }
            /* 隐藏原生 checkbox */
            .gradio-container .wrap input[type="checkbox"],
            .gradio-container fieldset input[type="checkbox"] {
                position: absolute !important;
                opacity: 0 !important;
                width: 0 !important;
                height: 0 !important;
            }

            /* 单个 Checkbox 开关样式 (保留原生外观) */
            .gradio-container .gr-check-radio label,
            .gradio-container label.flex:has(input[name="checkbox"]) {
                padding: 0 !important;
                border: none !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            /* 响应式 */
            @media (max-width: 1200px) {
                .workflow-grid { grid-template-columns: repeat(2, 1fr); }
            }
            @media (max-width: 768px) {
                .workflow-grid { grid-template-columns: 1fr; }

                /* 移动端优化 */
                .gradio-container {
                    padding: 8px !important;
                }
                .gradio-container .block {
                    padding: 12px !important;
                }
                .app-header {
                    flex-direction: column;
                    gap: 8px;
                    padding: 12px !important;
                }
                .app-header .logo h1 {
                    font-size: 18px !important;
                }

                /* 按钮在移动端更大更易点击 */
                .gradio-container button {
                    min-height: 44px !important;
                    font-size: 14px !important;
                }

                /* Row 在移动端变为纵向 */
                .gradio-row {
                    flex-direction: column !important;
                }
                .gradio-row > .gradio-column {
                    min-width: 100% !important;
                }

                /* 预览图片在移动端全宽 */
                .gradio-container .image-container {
                    max-height: 300px !important;
                }

                /* 快速开始横幅移动端 */
                .quick-start-banner {
                    flex-direction: column;
                    text-align: center;
                    padding: 16px !important;
                }

                /* Tab 标签在移动端更紧凑 */
                .gradio-container .tabs button {
                    padding: 8px 12px !important;
                    font-size: 13px !important;
                }

                /* 表单元素在移动端全宽 */
                .gradio-container input,
                .gradio-container textarea,
                .gradio-container select {
                    width: 100% !important;
                }

                /* Gallery 在移动端显示2列 */
                .gradio-gallery {
                    --columns: 2 !important;
                }
            }

            @media (max-width: 480px) {
                /* 更小屏幕的额外优化 */
                .app-header .logo h1 {
                    font-size: 16px !important;
                }
                .gradio-container h3 {
                    font-size: 16px !important;
                }
                .gradio-container .tabs button {
                    padding: 6px 8px !important;
                    font-size: 12px !important;
                }
                /* Gallery 在小屏幕显示1列 */
                .gradio-gallery {
                    --columns: 1 !important;
                }
            }
        </style>

        <!-- 顶部导航栏 -->
        <div class="app-header">
            <div class="logo">
                <div class="logo-icon">🎬</div>
                <h1>AI 分镜 Pro</h1>
            </div>
            <div class="status-pill">
                <div class="status-dot"></div>
                <span>系统运行中</span>
            </div>
        </div>

        <!-- 全局镜头预览弹窗 -->
        <div id="globalShotModal" class="shot-modal-global" style="display:none;">
            <div class="shot-modal-content">
                <div class="shot-modal-header">
                    <span id="globalModalTitle">镜头预览</span>
                    <button class="shot-modal-close" onclick="window.closeGlobalModal()">&times;</button>
                </div>
                <div class="shot-modal-body">
                    <div class="shot-modal-image-container">
                        <div id="globalModalImage"></div>
                    </div>
                    <div class="shot-modal-info">
                        <div class="info-section">
                            <div class="info-label">镜头描述</div>
                            <div id="globalModalDesc" class="info-value"></div>
                        </div>
                        <div class="info-row">
                            <div class="info-item"><span class="info-label">角色</span><span id="globalModalChars" class="info-value"></span></div>
                            <div class="info-item"><span class="info-label">场景</span><span id="globalModalScene" class="info-value"></span></div>
                        </div>
                        <div class="info-row">
                            <div class="info-item"><span class="info-label">景别</span><span id="globalModalType" class="info-value"></span></div>
                            <div class="info-item"><span class="info-label">镜头角度</span><span id="globalModalAngle" class="info-value"></span></div>
                        </div>
                        <div class="info-section">
                            <div class="info-label">生成提示词</div>
                            <div id="globalModalPrompt" class="info-value prompt-text"></div>
                        </div>
                    </div>
                </div>
                <div class="shot-modal-nav">
                    <button class="nav-btn" onclick="window.navigateGlobalShot(-1)">◀ 上一个</button>
                    <span id="globalModalNav">1 / 7</span>
                    <button class="nav-btn" onclick="window.navigateGlobalShot(1)">下一个 ▶</button>
                </div>
            </div>
        </div>

        <!-- 全局视频预览弹窗 -->
        <div id="globalVideoModal" class="video-modal-global" style="display:none;">
            <div class="video-modal-content">
                <div class="video-modal-header">
                    <span id="videoModalTitle">视频预览</span>
                    <button class="video-modal-close" onclick="window.closeVideoModal()">&times;</button>
                </div>
                <div class="video-modal-body">
                    <div class="video-modal-player">
                        <video id="videoModalPlayer" controls autoplay style="width:100%; max-height:60vh; background:#000;">
                            您的浏览器不支持视频播放
                        </video>
                    </div>
                    <div class="video-modal-info">
                        <div class="info-section">
                            <div class="info-label">生成提示词</div>
                            <div id="videoModalPrompt" class="info-value prompt-text"></div>
                        </div>
                    </div>
                </div>
                <div class="video-modal-nav">
                    <button class="nav-btn" onclick="window.navigateVideo(-1)">◀ 上一个</button>
                    <span id="videoModalNav">1 / 7</span>
                    <button class="nav-btn" onclick="window.navigateVideo(1)">下一个 ▶</button>
                </div>
            </div>
        </div>

        <!-- JavaScript 已移至 gr.Blocks(js=...) 参数中 -->

        <style>
            /* 视频弹窗样式 */
            .video-modal-global {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.95);
                z-index: 99999;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .video-modal-global .video-modal-content {
                background: #1a1a2e;
                border-radius: 12px;
                max-width: 900px;
                width: 100%;
                max-height: 90vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
            .video-modal-global .video-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                border-bottom: 1px solid #333;
            }
            .video-modal-global .video-modal-header span {
                font-size: 18px;
                font-weight: 600;
                color: #a78bfa;
            }
            .video-modal-global .video-modal-close {
                background: none;
                border: none;
                color: #888;
                font-size: 28px;
                cursor: pointer;
            }
            .video-modal-global .video-modal-close:hover { color: #fff; }
            .video-modal-global .video-modal-body {
                display: flex;
                flex-direction: column;
                flex: 1;
                overflow: hidden;
            }
            .video-modal-global .video-modal-player {
                background: #000;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 300px;
            }
            .video-modal-global .video-modal-info {
                padding: 16px 20px;
                background: #16202a;
                max-height: 150px;
                overflow-y: auto;
            }
            .video-modal-global .info-section {
                margin-bottom: 12px;
            }
            .video-modal-global .info-label {
                font-size: 12px;
                color: #a78bfa;
                margin-bottom: 4px;
                font-weight: 600;
            }
            .video-modal-global .info-value {
                font-size: 13px;
                color: #e2e8f0;
                line-height: 1.5;
            }
            .video-modal-global .prompt-text {
                font-family: monospace;
                font-size: 11px;
                color: #9ca3af;
                white-space: pre-wrap;
                word-break: break-all;
            }
            .video-modal-global .video-modal-nav {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 20px;
                padding: 12px 20px;
                border-top: 1px solid #333;
                background: #1a1a2e;
            }
            .video-modal-global .nav-btn {
                background: #7c3aed;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
            }
            .video-modal-global .nav-btn:hover {
                background: #6d28d9;
            }
            .video-modal-global #videoModalNav {
                color: #9ca3af;
                font-size: 13px;
            }

            .shot-modal-global {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                z-index: 99999;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .shot-modal-global .shot-modal-content {
                background: #1a1a2e;
                border-radius: 12px;
                max-width: 900px;
                width: 100%;
                max-height: 90vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
            .shot-modal-global .shot-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                border-bottom: 1px solid #333;
            }
            .shot-modal-global .shot-modal-header span {
                font-size: 18px;
                font-weight: 600;
                color: #fff;
            }
            .shot-modal-global .shot-modal-close {
                background: none;
                border: none;
                color: #888;
                font-size: 28px;
                cursor: pointer;
            }
            .shot-modal-global .shot-modal-close:hover { color: #fff; }
            .shot-modal-global .shot-modal-body {
                display: flex;
                flex: 1;
                overflow: hidden;
            }
            .shot-modal-global .shot-modal-image-container {
                flex: 1;
                background: #0a0a15;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 300px;
            }
            .shot-modal-global .modal-preview-img {
                max-width: 100%;
                max-height: 60vh;
                object-fit: contain;
            }
            .shot-modal-global .modal-no-image {
                color: #666;
                font-size: 24px;
                text-align: center;
            }
            .shot-modal-global .shot-modal-info {
                width: 300px;
                padding: 20px;
                overflow-y: auto;
                border-left: 1px solid #333;
                background: #12121f;
            }
            .shot-modal-global .info-section { margin-bottom: 16px; }
            .shot-modal-global .info-row { display: flex; gap: 16px; margin-bottom: 12px; }
            .shot-modal-global .info-item { flex: 1; }
            .shot-modal-global .info-label { font-size: 11px; color: #666; margin-bottom: 4px; text-transform: uppercase; }
            .shot-modal-global .info-value { font-size: 13px; color: #e0e0e0; line-height: 1.5; }
            .shot-modal-global .prompt-text { font-size: 12px; color: #888; background: #0a0a15; padding: 10px; border-radius: 6px; max-height: 100px; overflow-y: auto; }
            .shot-modal-global .shot-modal-nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 20px;
                border-top: 1px solid #333;
                background: #12121f;
            }
            .shot-modal-global .nav-btn {
                background: #2a2a3e;
                border: none;
                color: #fff;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
            }
            .shot-modal-global .nav-btn:hover { background: #3a3a4e; }
            @media (max-width: 768px) {
                .shot-modal-global .shot-modal-body { flex-direction: column; }
                .shot-modal-global .shot-modal-info { width: 100%; border-left: none; border-top: 1px solid #333; }
            }
        </style>
        """)

        # ===== 主布局：左侧内容 + 右侧面板 =====
        with gr.Row(equal_height=False):

            # ===== 左侧：主工作区 (80%) =====
            with gr.Column(scale=4):

                # 项目状态概览 (可见，显示加载的范例内容)
                project_summary = gr.HTML(value=get_project_summary(), elem_classes="project-summary-card")

                # ===== 新手快速开始区域 =====
                gr.HTML("""
                <div class="quick-start-banner">
                    <div class="qs-icon">🚀</div>
                    <div class="qs-content">
                        <h3>新手？一键开始体验</h3>
                        <p>点击下方任意范例模板，立即加载完整的角色、场景和镜头数据，快速了解系统工作流程。</p>
                    </div>
                </div>
                <style>
                    .quick-start-banner {
                        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(16, 25, 34, 0.95) 100%);
                        border: 1px solid rgba(34, 197, 94, 0.3);
                        border-radius: 12px;
                        padding: 20px 24px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 16px;
                    }
                    .quick-start-banner .qs-icon {
                        font-size: 32px;
                        background: rgba(34, 197, 94, 0.2);
                        padding: 12px;
                        border-radius: 12px;
                    }
                    .quick-start-banner h3 {
                        color: #22c55e;
                        font-size: 16px;
                        font-weight: 600;
                        margin: 0 0 4px 0;
                    }
                    .quick-start-banner p {
                        color: var(--text-secondary);
                        font-size: 13px;
                        margin: 0;
                    }
                </style>
                """)

                # ===== 一句话生成故事 =====
                with gr.Group(elem_classes="ai-story-generator"):
                    gr.HTML("""
                    <div class="ai-gen-header">
                        <span class="ai-icon">✨</span>
                        <div>
                            <h4>一句话生成故事</h4>
                            <p>输入你的创意，AI 自动生成完整的角色、场景和分镜</p>
                        </div>
                    </div>
                    <style>
                        .ai-story-generator {
                            background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(16, 25, 34, 0.95) 100%);
                            border: 1px solid rgba(139, 92, 246, 0.3);
                            border-radius: 12px;
                            padding: 16px;
                            margin-bottom: 20px;
                        }
                        .ai-gen-header {
                            display: flex;
                            align-items: center;
                            gap: 12px;
                            margin-bottom: 12px;
                        }
                        .ai-gen-header .ai-icon {
                            font-size: 28px;
                            background: rgba(139, 92, 246, 0.2);
                            padding: 10px;
                            border-radius: 10px;
                        }
                        .ai-gen-header h4 {
                            color: #a78bfa;
                            font-size: 15px;
                            font-weight: 600;
                            margin: 0 0 2px 0;
                        }
                        .ai-gen-header p {
                            color: var(--text-secondary);
                            font-size: 12px;
                            margin: 0;
                        }
                    </style>
                    """)
                    with gr.Row():
                        story_idea_input = gr.Textbox(
                            label="",
                            placeholder="例如：一个程序员在深夜加班时，意外发现公司的AI系统产生了自我意识...",
                            lines=2,
                            scale=4,
                            container=False
                        )
                        generate_story_btn = gr.Button("🚀 AI 生成", variant="primary", scale=1, min_width=100)
                    story_gen_status = gr.Textbox(label="", show_label=False, interactive=False, container=False, visible=False)

                # ===== 范例模板（推荐新手使用）=====
                gr.HTML('<div class="templates-section"><h3>📦 选择一个范例开始 <span style="font-size:12px;color:#22c55e;font-weight:normal;">推荐新手</span></h3></div>')

                with gr.Row():
                    # 模板卡片 - 马到成功送祝福
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div class="template-card featured" id="template-madao" onclick="document.getElementById('load-madao')?.click()">
                            <div class="info">
                                <span class="badge drama">🐴 送福</span>
                                <h4>🎊 马到成功送祝福</h4>
                                <p>马年吉祥物小骏马送福上门的欢乐故事</p>
                                <span class="meta">3 角色 • 2 场景 • 7 镜头</span>
                            </div>
                        </div>
                        """)
                        load_madao_btn = gr.Button("✨ 加载此范例", size="sm", variant="primary", elem_id="load-madao")

                    # 模板卡片 - 骏马奔腾迎新年
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div class="template-card" id="template-junma" onclick="document.getElementById('load-junma')?.click()">
                            <div class="info">
                                <span class="badge action">🏠 团圆</span>
                                <h4>🎆 骏马奔腾迎新年</h4>
                                <p>马家大院除夕团圆，龙马精神迎新春</p>
                                <span class="meta">5 角色 • 2 场景 • 7 镜头</span>
                            </div>
                        </div>
                        """)
                        load_junma_btn = gr.Button("加载此范例", size="sm", variant="secondary", elem_id="load-junma")

                    # 模板卡片 - 马上有美食
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div class="template-card" id="template-mashang" onclick="document.getElementById('load-mashang')?.click()">
                            <div class="info">
                                <span class="badge drama">🍜 美食</span>
                                <h4>🥟 马上有美食</h4>
                                <p>马蹄糕马卡龙，马年特色美食大展示</p>
                                <span class="meta">3 角色 • 2 场景 • 8 镜头</span>
                            </div>
                        </div>
                        """)
                        load_mashang_btn = gr.Button("加载此范例", size="sm", variant="secondary", elem_id="load-mashang")

                # ===== 工作流程指引（步骤说明）=====
                gr.HTML("""
                <div class="workflow-guide">
                    <h3>📋 工作流程（4个步骤）</h3>
                    <p class="guide-desc">加载范例后，按顺序完成以下步骤即可生成分镜作品</p>
                    <div class="steps-container">
                        <div class="step-item">
                            <div class="step-num">1</div>
                            <div class="step-info">
                                <h4>创建</h4>
                                <p>添加角色和场景</p>
                            </div>
                            <div class="step-arrow">→</div>
                        </div>
                        <div class="step-item">
                            <div class="step-num">2</div>
                            <div class="step-info">
                                <h4>编排</h4>
                                <p>设计镜头顺序</p>
                            </div>
                            <div class="step-arrow">→</div>
                        </div>
                        <div class="step-item">
                            <div class="step-num">3</div>
                            <div class="step-info">
                                <h4>生成</h4>
                                <p>AI 生成图像</p>
                            </div>
                            <div class="step-arrow">→</div>
                        </div>
                        <div class="step-item last">
                            <div class="step-num done">4</div>
                            <div class="step-info">
                                <h4>导出</h4>
                                <p>下载成品</p>
                            </div>
                        </div>
                    </div>
                </div>
                <style>
                    .workflow-guide {
                        background: var(--card-dark);
                        border: 1px solid var(--border-dark);
                        border-radius: 12px;
                        padding: 16px 20px;
                        margin: 12px 0 4px 0;
                    }
                    .workflow-guide h3 {
                        color: white;
                        font-size: 15px;
                        font-weight: 600;
                        margin: 0 0 4px 0;
                    }
                    .workflow-guide .guide-desc {
                        color: var(--text-secondary);
                        font-size: 12px;
                        margin: 0 0 16px 0;
                    }
                    .steps-container {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    .step-item {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        flex: 1;
                        background: var(--surface-dark);
                        padding: 12px 16px;
                        border-radius: 8px;
                        border: 1px solid var(--border-dark);
                    }
                    .step-item.last { flex: 0.8; }
                    .step-num {
                        width: 28px;
                        height: 28px;
                        background: var(--primary);
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-size: 13px;
                        font-weight: 700;
                        flex-shrink: 0;
                    }
                    .step-num.done { background: #22c55e; }
                    .step-info h4 {
                        color: white;
                        font-size: 13px;
                        font-weight: 600;
                        margin: 0;
                    }
                    .step-info p {
                        color: var(--text-secondary);
                        font-size: 11px;
                        margin: 0;
                    }
                    .step-arrow {
                        color: var(--text-secondary);
                        font-size: 16px;
                        margin-left: auto;
                    }
                    .step-item.last .step-arrow { display: none; }

                    /* 工作流导航按钮 */
                    .workflow-nav-buttons {
                        margin: 8px 0 0 0 !important;
                        gap: 8px !important;
                    }
                    .workflow-nav-buttons button {
                        flex: 1;
                        padding: 8px 12px !important;
                        font-size: 12px !important;
                        background: var(--card-dark) !important;
                        border: 1px solid var(--border-dark) !important;
                        color: var(--text-secondary) !important;
                        border-radius: 6px !important;
                    }
                    .workflow-nav-buttons button:hover {
                        background: var(--primary) !important;
                        border-color: var(--primary) !important;
                        color: white !important;
                    }

                    .template-card.featured {
                        border-color: rgba(34, 197, 94, 0.4);
                        box-shadow: 0 0 20px rgba(34, 197, 94, 0.1);
                    }
                    .template-card.selected {
                        border-color: #137fec !important;
                        box-shadow: 0 0 0 2px rgba(19, 127, 236, 0.3), 0 4px 20px rgba(19, 127, 236, 0.2) !important;
                        background: linear-gradient(135deg, rgba(19, 127, 236, 0.1) 0%, var(--card-dark) 100%) !important;
                    }
                    .template-card.selected::after {
                        content: '✓ 已加载';
                        position: absolute;
                        top: 8px;
                        right: 8px;
                        background: #137fec;
                        color: white;
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: 600;
                    }
                </style>
                """)

                # 快速导航按钮
                with gr.Row(elem_classes="workflow-nav-buttons"):
                    nav_create_btn = gr.Button("① 创建角色/场景", size="sm", elem_id="nav-create")
                    nav_arrange_btn = gr.Button("② 编排镜头", size="sm", elem_id="nav-arrange")
                    nav_generate_btn = gr.Button("③ 生成图像", size="sm", elem_id="nav-generate")
                    nav_export_btn = gr.Button("④ 导出作品", size="sm", elem_id="nav-export")

                # 隐藏旧按钮（保留事件绑定）
                with gr.Row(visible=False):
                    new_project_btn = gr.Button("新建项目")
                    load_template_btn = gr.Button("加载范例")

                # 隐藏的范例选择器(保留功能)
                with gr.Row(visible=False):
                    example_choice = gr.Radio(
                        choices=list(EXAMPLE_STORIES.keys()),
                        label="范例故事",
                        value=None
                    )
                    load_example_btn = gr.Button("🚀 加载范例", variant="primary", size="sm", elem_id="load-example-btn")
                    example_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)
                    example_desc = gr.Textbox(label="说明", interactive=False, lines=2)

            # ===== 右侧：设置面板 (20%) =====
            with gr.Column(scale=1, min_width=280):

                # ComfyUI 连接状态
                with gr.Group(elem_classes="comfyui-status-container"):
                    comfyui_status_html = gr.HTML(
                        value='<div class="comfyui-status disconnected">🔴 ComfyUI 状态检测中...</div>'
                    )
                    with gr.Row():
                        comfyui_connect_btn = gr.Button("🔌 连接", size="sm", scale=1, elem_classes="comfyui-connect-btn")
                        comfyui_refresh_btn = gr.Button("🔄", size="sm", scale=0, min_width=40)
                    comfyui_msg = gr.Textbox(label="", show_label=False, interactive=False, container=False, visible=False)

                gr.HTML('<div class="section-title">⚙️ AI 引擎设置</div>')

                # LLM 设置
                with gr.Accordion("🤖 语言模型", open=False):
                    llm_provider_cn = gr.Radio(
                        ["Claude Code CLI (默认)", "DeepSeek", "智谱 GLM", "通义千问", "OpenAI GPT"],
                        label="",
                        value="Claude Code CLI (默认)",
                        container=False
                    )
                    llm_api_key_cn = gr.Textbox(
                        label="API Key (CLI 模式无需填写)",
                        placeholder="使用 CLI 无需 API Key",
                        type="password"
                    )
                    llm_api_url_cn = gr.Textbox(
                        label="API 地址",
                        placeholder="留空使用默认",
                        value="",
                        visible=False
                    )
                    # 隐藏的国际服务商字段
                    llm_provider_intl = gr.Textbox(visible=False, value="")
                    llm_api_key_intl = gr.Textbox(visible=False, value="")
                    llm_api_url_intl = gr.Textbox(visible=False, value="")
                    llm_save_btn = gr.Button("保存配置", elem_classes="primary-btn", size="sm")
                    llm_save_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                # 图像生成配置 - 简化版
                with gr.Accordion("🎨 图像生成", open=False):
                    img_provider_cn = gr.Radio(
                        ["本地 ComfyUI (默认)", "通义万相", "智谱 CogView", "Stability AI"],
                        label="选择引擎",
                        value="本地 ComfyUI (默认)"
                    )
                    img_api_key_cn = gr.Textbox(
                        label="API Key",
                        placeholder="ComfyUI 无需 API Key",
                        type="password"
                    )

                    # ComfyUI 工作流设置
                    gr.Markdown("**ComfyUI 工作流**", elem_classes="workflow-label")
                    with gr.Row():
                        load_default_workflow_btn = gr.Button(
                            "📦 加载默认流",
                            size="sm",
                            variant="primary",
                            scale=1
                        )
                        load_custom_workflow_btn = gr.Button(
                            "📁 加载自定义",
                            size="sm",
                            variant="secondary",
                            scale=1
                        )
                    img_workflow_file = gr.File(
                        label="上传工作流 (JSON)",
                        file_types=[".json"],
                        type="filepath",
                        visible=False
                    )
                    workflow_status = gr.Textbox(
                        label="",
                        show_label=False,
                        interactive=False,
                        container=False,
                        value="未加载工作流",
                        elem_classes="workflow-status"
                    )

                    img_api_url_cn = gr.Textbox(visible=False, value="")
                    img_provider_intl = gr.Textbox(visible=False, value="")
                    img_api_key_intl = gr.Textbox(visible=False, value="")
                    img_api_url_intl = gr.Textbox(visible=False, value="")
                    img_save_btn = gr.Button("保存配置", elem_classes="primary-btn", size="sm")
                    img_save_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                # 视频生成配置 - 简化版
                with gr.Accordion("🎬 视频生成", open=False):
                    video_provider_cn = gr.Radio(
                        ["本地 ComfyUI (默认)", "智谱 CogVideoX", "可灵 AI", "Runway"],
                        label="选择引擎",
                        value="本地 ComfyUI (默认)"
                    )
                    video_api_key_cn = gr.Textbox(
                        label="API Key",
                        placeholder="ComfyUI 无需 API Key",
                        type="password"
                    )
                    video_workflow_file = gr.File(
                        label="ComfyUI 工作流 (JSON)",
                        file_types=[".json"],
                        type="filepath"
                    )
                    video_api_url_cn = gr.Textbox(visible=False, value="")
                    video_provider_intl = gr.Textbox(visible=False, value="")
                    video_api_key_intl = gr.Textbox(visible=False, value="")
                    video_api_url_intl = gr.Textbox(visible=False, value="")
                    video_save_btn = gr.Button("保存配置", elem_classes="primary-btn", size="sm")
                    video_save_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                # ===== CLI 实时反馈窗口 =====
                gr.HTML("""
                <div class="cli-terminal">
                    <div class="cli-terminal-header">
                        <span>CLI 实时反馈</span>
                        <div class="cli-terminal-dots">
                            <div class="red"></div>
                            <div class="yellow"></div>
                            <div class="green"></div>
                        </div>
                    </div>
                </div>
                """)
                cli_output_display = gr.Textbox(
                    value="",
                    lines=4,
                    max_lines=8,
                    interactive=False,
                    show_label=False,
                    container=False,
                    elem_classes="cli-terminal-content",
                    visible=False
                )
                with gr.Row():
                    refresh_cli_btn = gr.Button("🔄 刷新", size="sm", scale=1, variant="secondary")
                    clear_cli_btn = gr.Button("🗑️ 清空", size="sm", scale=1, variant="secondary")

        # ===== 工作流进度指示器样式 =====
        gr.HTML("""
        <style>
            /* ===== 工作流进度指示器 (紧凑版) ===== */
            .workflow-progress {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 12px;
            }
            .workflow-progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }
            .workflow-progress-title {
                color: white;
                font-size: 12px;
                font-weight: 600;
            }
            .workflow-progress-status {
                color: #22c55e;
                font-size: 11px;
                font-weight: 500;
            }
            .workflow-steps {
                display: flex;
                gap: 4px;
            }
            .workflow-step {
                flex: 1;
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 6px 8px;
                background: var(--surface-dark);
                border: 2px solid var(--border-dark);
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .workflow-step:hover {
                border-color: var(--primary);
            }
            .workflow-step.completed {
                border-color: #22c55e;
                background: rgba(34, 197, 94, 0.1);
            }
            .workflow-step.current {
                border-color: var(--primary);
                background: rgba(19, 127, 236, 0.15);
                box-shadow: 0 0 0 3px rgba(19, 127, 236, 0.2);
            }
            .workflow-step.current::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                border-radius: 10px;
                background: linear-gradient(90deg, var(--primary), #60a5fa);
                animation: pulse-border 2s infinite;
                z-index: -1;
            }
            @keyframes pulse-border {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
            }
            .workflow-step .step-icon {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                font-weight: 700;
                background: var(--border-dark);
                color: var(--text-secondary);
                flex-shrink: 0;
            }
            .workflow-step.completed .step-icon {
                background: #22c55e;
                color: white;
            }
            .workflow-step.current .step-icon {
                background: var(--primary);
                color: white;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            .workflow-step .step-info h4 {
                color: white;
                font-size: 11px;
                font-weight: 600;
                margin: 0;
            }
            .workflow-step .step-info p {
                color: var(--text-secondary);
                font-size: 9px;
                margin: 0;
                display: none; /* 隐藏详细描述以节省空间 */
            }
            .workflow-step.current .step-info h4 {
                color: var(--primary);
            }
            .workflow-step.completed .step-info h4 {
                color: #22c55e;
            }

            /* ===== ComfyUI 连接状态 ===== */
            .comfyui-status-container {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 8px;
            }
            .comfyui-status {
                font-size: 12px;
                font-weight: 500;
                padding: 4px 0;
            }
            .comfyui-status.connected {
                color: #22c55e;
            }
            .comfyui-status.available {
                color: #eab308;
            }
            .comfyui-status.disconnected {
                color: #ef4444;
            }
            .comfyui-connect-btn {
                margin-top: 6px;
            }

            /* ===== 生成控制栏样式 ===== */
            .generate-control-bar {
                background: var(--card-dark);
                border: 1px solid var(--border-dark);
                border-radius: 8px;
                padding: 8px 12px;
                margin: 8px 0;
                align-items: center !important;
                gap: 8px !important;
            }
            .generate-control-bar > div {
                min-width: 0;
            }
            .shot-num-input {
                max-width: 80px !important;
            }
            .shot-num-input input[type="number"] {
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                padding: 8px !important;
                background: var(--surface-dark) !important;
                border: 2px solid var(--primary) !important;
                border-radius: 6px !important;
            }
            /* 折叠面板样式优化 */
            .gradio-accordion {
                border: 1px solid var(--border-dark) !important;
                border-radius: 8px !important;
                margin-top: 8px !important;
            }
            .gradio-accordion > .label-wrap {
                padding: 8px 12px !important;
                background: var(--surface-dark) !important;
            }
            .gradio-accordion > .label-wrap span {
                font-size: 13px !important;
            }
            .text-muted {
                color: var(--text-secondary) !important;
                font-size: 12px !important;
                margin: 4px 0 8px 0 !important;
            }

            /* ===== 加载范例后的三栏布局 ===== */
            /* 使用CSS Grid重构布局：左边范例(20%) | 中间工作区(60%) | 右边设置(20%) */

            /* 父容器使用Grid布局 */
            body.layout-active .gradio-container main .wrap .contain > .column {
                display: grid !important;
                grid-template-columns: 20% 60% 20%;
                grid-template-rows: auto auto 1fr auto;
                gap: 16px;
                align-items: start;
            }

            /* 项目摘要卡片横跨全宽 */
            body.layout-active .gradio-container main .wrap .contain > .column > .block:first-child {
                grid-column: 1 / -1;
                grid-row: 1;
            }

            /* 主布局行（包含范例和设置）分解为独立区域 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row {
                display: contents !important;
            }

            /* 左侧范例区 - 第1列 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child {
                grid-column: 1;
                grid-row: 2 / span 2;
                max-height: 80vh;
                overflow-y: auto;
                overflow-x: hidden;
                position: sticky;
                top: 20px;
                word-wrap: break-word;
            }

            /* 右侧设置区 - 第3列 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:last-child {
                grid-column: 3;
                grid-row: 2 / span 2;
                max-height: 80vh;
                overflow-y: auto;
                overflow-x: hidden;
                position: sticky;
                top: 20px;
                word-wrap: break-word;
            }

            /* 确保所有侧边栏内容不超宽 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child *,
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:last-child * {
                max-width: 100%;
                box-sizing: border-box;
            }

            /* 侧边栏内元素纵向排列 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child > .block,
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:last-child > .block {
                width: 100%;
                flex-shrink: 0;
            }

            /* 侧边栏内 Accordion 默认折叠样式 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .accordion {
                width: 100%;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .accordion > .label-wrap {
                padding: 8px 12px;
                font-size: 13px;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .accordion > .label-wrap svg {
                width: 14px;
                height: 14px;
            }

            /* 侧边栏表格和数据框不超宽 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column table {
                width: 100%;
                table-layout: fixed;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column table td,
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column table th {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: 150px;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .dataframe {
                overflow-x: hidden !important;
            }

            /* 侧边栏图片适应宽度 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column img {
                max-width: 100%;
                height: auto;
            }

            /* 侧边栏输入框和按钮 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column input,
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column textarea,
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column select {
                width: 100%;
                max-width: 100%;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column button {
                white-space: normal;
                word-wrap: break-word;
            }

            /* 侧边栏 Row 内元素堆叠 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .row {
                flex-wrap: wrap;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column .row > * {
                flex: 1 1 100%;
                min-width: 0;
            }

            /* 工作流指示器 - 第2列顶部 */
            body.layout-active .workflow-indicator {
                grid-column: 2 !important;
                grid-row: 2 !important;
            }

            /* 主标签页(工作区) - 第2列主体 */
            body.layout-active .gradio-container main .wrap .contain > .column > .tabs {
                grid-column: 2 !important;
                grid-row: 3 !important;
            }

            /* 隐藏不需要的元素 */
            body.layout-active .quick-start-banner {
                display: none !important;
            }
            body.layout-active .workflow-guide {
                display: none !important;
            }
            body.layout-active .workflow-nav-buttons {
                display: none !important;
            }

            /* 隐藏的HTML块不占用网格空间 */
            body.layout-active .gradio-container main .wrap .contain > .column > .block.hide-container:not(.workflow-indicator):not(:first-child) {
                display: none !important;
            }

            /* 左侧列使用flexbox重排内容 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child {
                display: flex !important;
                flex-direction: column !important;
            }

            /* 项目摘要卡片保持顶部 */
            body.layout-active .project-summary-card {
                order: 1 !important;
            }

            /* 范例模板区域移到底部并折叠 */
            body.layout-active .templates-section {
                order: 100 !important;
                margin-top: auto !important;
                padding-top: 16px !important;
                border-top: 1px solid var(--border-dark) !important;
            }
            body.layout-active .templates-section h3 {
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: space-between;
                font-size: 13px !important;
                margin-bottom: 0 !important;
                padding: 8px 0;
            }
            body.layout-active .templates-section h3::after {
                content: '▼';
                font-size: 10px;
                transition: transform 0.3s;
            }
            body.layout-active .templates-section.collapsed h3::after {
                transform: rotate(-90deg);
            }
            body.layout-active .templates-section h3 span {
                display: none !important;
            }

            /* 模板卡片容器 - 默认折叠 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child > .row {
                order: 101 !important;
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.3s ease, opacity 0.3s ease;
                opacity: 0;
            }
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child > .row.templates-expanded {
                max-height: 500px !important;
                opacity: 1 !important;
            }

            /* 范例卡片紧凑显示 */
            body.layout-active .template-card {
                padding: 8px !important;
                margin-bottom: 4px;
            }
            body.layout-active .template-card h4 {
                font-size: 12px !important;
                margin-bottom: 2px;
            }
            body.layout-active .template-card p {
                display: none !important;
            }
            body.layout-active .template-card .meta {
                font-size: 10px !important;
            }
            body.layout-active .template-card .badge {
                font-size: 9px !important;
                padding: 2px 6px !important;
            }

            /* 加载按钮紧凑 */
            body.layout-active .gradio-container main .wrap .contain > .column > .row > .column:first-child > .row button {
                font-size: 11px !important;
                padding: 4px 8px !important;
            }

            /* 页脚横跨全宽 */
            body.layout-active .gradio-container main .wrap .contain > .column > .block:last-child {
                grid-column: 1 / -1;
                grid-row: 4;
            }

            /* 响应式 - 平板 */
            @media (max-width: 1200px) {
                body.layout-active .gradio-container main .wrap .contain > .column {
                    grid-template-columns: 25% 50% 25%;
                }
            }

            /* 响应式 - 手机 */
            @media (max-width: 768px) {
                body.layout-active .gradio-container main .wrap .contain > .column {
                    display: flex !important;
                    flex-direction: column;
                }
                body.layout-active .gradio-container main .wrap .contain > .column > .row {
                    display: flex !important;
                    flex-direction: column;
                }
                body.layout-active .gradio-container main .wrap .contain > .column > .row > .column {
                    max-height: none;
                    position: static;
                }
            }
        </style>
        """)

        # ===== 隐藏的兼容组件 =====
        with gr.Row(visible=False):
            project_name = gr.Textbox(value="我的分镜")
            aspect_ratio = gr.Radio(["16:9"], value="16:9")
            create_btn = gr.Button("创建项目")
            create_status = gr.Textbox()
            import_file = gr.File()
            import_btn = gr.Button("导入")
            import_status = gr.Textbox()
            smart_import_files = gr.File()
            smart_analyze_btn = gr.Button("AI 分析")
            use_claude_check = gr.Checkbox(value=True)
            smart_import_status = gr.Textbox()
            raw_content_preview = gr.Textbox()
            analyzed_json = gr.Textbox()
            smart_apply_btn = gr.Button("应用导入")

        # ===== 工作流进度指示器 =====
        workflow_step_indicator = gr.HTML(value=get_workflow_indicator(0), elem_classes="workflow-indicator")

        with gr.Tabs() as main_tabs:

            # ===== 步骤1: 创建 =====
            with gr.Tab("① 创建", elem_id="tab-create"):

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 添加角色")
                        char_name = gr.Textbox(label="角色名称", placeholder="如：李明")
                        with gr.Row():
                            char_desc = gr.Textbox(label="角色描述", placeholder="详细描述角色外貌、服装、特征", lines=2, scale=4)
                            ai_char_desc_btn = gr.Button("🤖 AI生成", elem_classes="secondary-btn", size="sm", scale=1)

                        # 角色外貌详细设置（确保一致性）
                        with gr.Accordion("🎭 外貌一致性设置（展开填写可保持角色统一）", open=False):
                            gr.Markdown("*填写以下字段可确保该角色在所有镜头中外貌保持一致*")
                            with gr.Row():
                                char_gender = gr.Dropdown(
                                    choices=["", "male", "female"],
                                    label="性别", value=""
                                )
                                char_age = gr.Dropdown(
                                    choices=["", "child", "teen", "young_adult", "adult", "middle_aged", "elderly"],
                                    label="年龄", value=""
                                )
                                char_ethnicity = gr.Textbox(label="种族/民族", placeholder="如：asian, caucasian")
                            with gr.Row():
                                char_hair_color = gr.Textbox(label="发色", placeholder="如：black, brown, blonde")
                                char_hair_style = gr.Textbox(label="发型", placeholder="如：short, long, ponytail")
                                char_eye_color = gr.Textbox(label="眼睛颜色", placeholder="如：brown, blue")
                            with gr.Row():
                                char_body_type = gr.Dropdown(
                                    choices=["", "slim", "average", "athletic", "muscular", "heavy"],
                                    label="体型", value=""
                                )
                                char_skin_tone = gr.Dropdown(
                                    choices=["", "fair", "light", "medium", "tan", "dark"],
                                    label="肤色", value=""
                                )
                                char_glasses = gr.Dropdown(
                                    choices=["", "none", "round", "square", "cat-eye", "rimless"],
                                    label="眼镜", value=""
                                )
                            char_other_features = gr.Textbox(label="其他特征", placeholder="如：freckles, beard, scar on left cheek")

                        # 服装设置
                        with gr.Accordion("👔 服装设置（锁定后每个镜头保持相同）", open=False):
                            char_costume_locked = gr.Checkbox(label="锁定服装（所有镜头使用相同服装）", value=False)
                            with gr.Row():
                                char_top = gr.Textbox(label="上装", placeholder="如：shirt, blouse, t-shirt")
                                char_top_color = gr.Textbox(label="上装颜色", placeholder="如：white, blue")
                            with gr.Row():
                                char_bottom = gr.Textbox(label="下装", placeholder="如：jeans, skirt, pants")
                                char_bottom_color = gr.Textbox(label="下装颜色", placeholder="如：black, navy")
                            with gr.Row():
                                char_outerwear = gr.Textbox(label="外套", placeholder="如：jacket, coat, hoodie")
                                char_accessories = gr.Textbox(label="配饰", placeholder="如：watch, necklace, hat")

                        char_images = gr.File(
                            label="参考图片 (可多选)",
                            file_count="multiple",
                            file_types=["image"]
                        )
                        add_char_btn = gr.Button("添加角色", elem_classes="primary-btn")
                        char_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                    with gr.Column(scale=1):
                        gr.Markdown("### 添加场景")
                        scene_name = gr.Textbox(label="场景名称", placeholder="如：咖啡厅")
                        with gr.Row():
                            scene_desc = gr.Textbox(label="场景描述", placeholder="详细描述环境、光线、氛围", lines=2, scale=4)
                            ai_scene_desc_btn = gr.Button("🤖 AI生成", elem_classes="secondary-btn", size="sm", scale=1)
                        scene_images = gr.File(
                            label="参考图片 (可多选)",
                            file_count="multiple",
                            file_types=["image"]
                        )
                        add_scene_btn = gr.Button("添加场景", elem_classes="primary-btn")
                        scene_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                gr.Markdown("---")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 已添加角色")
                        char_list = gr.Dataframe(
                            headers=["名称", "描述", "参考图数"],
                            value=get_character_list(),
                            show_label=False,
                            interactive=False
                        )
                        with gr.Row():
                            del_char_name = gr.Dropdown(choices=get_character_names(), label="选择角色")
                            del_char_btn = gr.Button("删除角色", elem_classes="warning-btn", size="sm")

                    with gr.Column():
                        gr.Markdown("### 已添加场景")
                        scene_list = gr.Dataframe(
                            headers=["名称", "描述"],
                            value=get_scene_list(),
                            show_label=False,
                            interactive=False
                        )
                        with gr.Row():
                            del_scene_name = gr.Dropdown(choices=get_scene_names(), label="选择场景")
                            del_scene_btn = gr.Button("删除场景", elem_classes="warning-btn", size="sm")

                gr.Markdown("---")
                gr.Markdown("### 视觉风格")
                with gr.Row():
                    style_category = gr.Radio(
                        ["2D", "3D"],
                        label="风格类型",
                        value="2D",
                        scale=2
                    )
                    style_lock = gr.Checkbox(label="🔒 锁定风格", value=True, scale=1)
                style_choice = gr.Radio(
                    ["2D卡通", "动漫风", "漫画风", "水彩画"],
                    label="详细风格",
                    value="2D卡通"
                )
                style_btn = gr.Button("应用风格", elem_classes="secondary-btn")
                style_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)
                style_lock_info = gr.HTML(
                    value='<div style="font-size:11px;color:#888;padding:4px 0;">🔒 风格已锁定，所有镜头将使用统一风格</div>',
                    visible=True
                )

            # ===== 步骤2: 编排 =====
            with gr.Tab("② 编排", elem_id="tab-arrange"):

                # 隐藏摘要 (工作流进度指示器已显示)
                step2_summary = gr.HTML(value=get_step_summary(2), visible=False)

                gr.Markdown("### 添加镜头")
                gr.Markdown("""
                | 镜头类型 | 说明 | 适用场景 |
                |---------|------|---------|
                | 全景 | 展示整体环境，建立空间感 | 开场、转场、环境介绍 |
                | 中景 | 人物膝盖以上，展示动作和表情 | 对话、日常动作 |
                | 特写 | 聚焦面部或细节，强调情感 | 情绪表达、重要细节 |
                | 过肩 | 从一人肩后看另一人，增强对话感 | 双人对话、对峙 |
                | 低角度 | 仰拍，增强气势和压迫感 | 英雄出场、权威表现 |
                | 跟随 | 跟随人物移动，增强动态感 | 追逐、行走、动作场景 |
                """)

                shot_template = gr.Radio(
                    ["全景", "中景", "特写", "过肩", "低角度", "跟随"],
                    label="镜头类型",
                    value="中景"
                )

                with gr.Row():
                    shot_desc = gr.Textbox(
                        label="镜头描述",
                        placeholder="描述这个镜头中发生的动作和情节",
                        lines=2,
                        scale=4
                    )
                    ai_shot_desc_btn = gr.Button("🤖 AI生成", elem_classes="secondary-btn", size="sm", scale=1)

                with gr.Row():
                    shot_chars = gr.CheckboxGroup(choices=[], label="出镜角色")
                    shot_scene = gr.Dropdown(choices=[], label="场景")

                with gr.Row():
                    add_shot_btn = gr.Button("添加镜头", elem_classes="primary-btn")
                    refresh_btn = gr.Button("刷新选项", elem_classes="secondary-btn")

                shot_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)

                gr.Markdown("---")
                gr.Markdown("### 镜头列表")

                shot_list = gr.Dataframe(
                    headers=["#", "类型", "场景", "角色", "描述", "状态"],
                    value=get_shot_list(),
                    show_label=False,
                    interactive=False
                )

                with gr.Row():
                    delete_num = gr.Number(label="镜头编号", value=1, precision=0, minimum=1)
                    delete_btn = gr.Button("删除", elem_classes="warning-btn")
                    move_up_btn = gr.Button("上移", elem_classes="secondary-btn")
                    move_down_btn = gr.Button("下移", elem_classes="secondary-btn")

                gr.Markdown("---")
                gr.Markdown("### 分镜提示语")

                with gr.Row():
                    view_shot_num = gr.Number(label="查看镜头编号", value=1, precision=0, minimum=1)
                    view_prompt_btn = gr.Button("查看提示语", elem_classes="secondary-btn")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**标准提示语 (专业分镜格式)**")
                        standard_prompt = gr.Textbox(
                            label="",
                            show_label=False,
                            lines=12,
                            placeholder="主体:\n景别:\n氛围:\n环境:\n运镜:\n视角:\n特殊拍摄手法:\n构图:\n风格统一:\n动态控制:",
                            interactive=False
                        )

                    with gr.Column():
                        gr.Markdown("**AI 生成提示词 (用于图像生成)**")
                        generated_prompt = gr.Textbox(
                            label="",
                            show_label=False,
                            lines=10,
                            placeholder="添加镜头后自动生成...",
                            interactive=True
                        )

            # ===== 生成 =====
            with gr.Tab("③ 生成", elem_id="tab-generate"):

                # 隐藏的组件 (保留但不显示，用于数据传递)
                step3_summary = gr.HTML(value=get_step_summary(3), visible=False)
                preview_image = gr.Image(visible=False)  # 隐藏预览图，卡片内已有预览

                # ===== 核心区域：镜头卡片 =====
                shot_cards_html = gr.HTML(value=get_shot_cards_html(), elem_classes="shot-cards-panel")

                # ===== 核心区域：生成控制栏 (紧凑一行) =====
                with gr.Row(elem_classes="generate-control-bar"):
                    gen_shot_num = gr.Number(label="", show_label=False, value=1, precision=0, minimum=1, scale=1, container=False, elem_classes="shot-num-input")
                    gen_single_btn = gr.Button("▶ 生成选中", elem_classes="primary-btn", scale=2, min_width=120)
                    gen_all_btn = gr.Button("▶▶ 全部生成", elem_classes="success-btn", scale=2, min_width=120)
                    refresh_cards_btn = gr.Button("🔄", elem_classes="secondary-btn", scale=0, min_width=50)

                # 状态显示
                gen_status = gr.Textbox(label="", show_label=False, interactive=False, container=False, placeholder="就绪")

                # 图片历史加载（放在镜头生成下面）
                gr.Markdown("---")
                gr.Markdown("### 📂 加载图片历史")
                with gr.Row(elem_classes="image-history-bar"):
                    image_history_dropdown = gr.Dropdown(
                        label="",
                        choices=get_image_history_choices(),
                        value=None,
                        scale=4,
                        container=False,
                        allow_custom_value=False
                    )
                    refresh_history_btn = gr.Button("刷新", elem_classes="secondary-btn", scale=0, min_width=50)
                with gr.Row(elem_classes="image-history-bar"):
                    load_images_btn = gr.Button("加载图片", elem_classes="secondary-btn", scale=1, min_width=100)
                    load_all_btn = gr.Button("全部加载", elem_classes="primary-btn", scale=1, min_width=100)
                image_history_status = gr.Textbox(label="", show_label=False, interactive=False, container=False, visible=False)

                # ===== 视频生成区域 =====
                gr.Markdown("---")
                gr.Markdown("### 🎬 视频生成")

                # 视频镜头预览卡片（样式与图片镜头一致）
                video_cards_html = gr.HTML(value=get_video_cards_html(), elem_classes="video-cards-panel")

                # 按钮行
                with gr.Row(elem_classes="video-generate-bar"):
                    batch_video_btn = gr.Button(
                        "🎬 一键生成全部视频",
                        elem_classes="danger-btn",
                        elem_id="batch_video_btn",
                        scale=2
                    )
                    load_videos_btn = gr.Button("加载视频", elem_classes="secondary-btn", scale=1, min_width=80)
                    manual_save_btn = gr.Button("💾 保存", elem_classes="primary-btn", scale=0, min_width=80)
                    manual_load_btn = gr.Button("📂 加载", elem_classes="secondary-btn", scale=0, min_width=80)
                    refresh_video_cards_btn = gr.Button("🔄 刷新", elem_classes="secondary-btn", scale=0, min_width=80)

                # 统计信息
                video_stats_html = gr.HTML(value=get_video_stats_html(), elem_classes="video-stats-panel")

                # 状态显示（取消视频预览播放器，改用弹窗）
                batch_video_status = gr.Textbox(label="生成状态", show_label=True, interactive=False, placeholder="就绪", lines=1)

                # 隐藏的视频预览播放器（保留用于事件绑定）
                video_preview_player = gr.Video(visible=False)

                # CLI输出
                video_cli_output = gr.Textbox(
                    label="ComfyUI 输出",
                    show_label=True,
                    interactive=False,
                    placeholder="ComfyUI 生成过程将在此显示...",
                    lines=4,
                    max_lines=8
                )

                # 隐藏元素：用于单个镜头视频生成触发 (使用CSS隐藏以保持JavaScript可交互)
                with gr.Row(elem_classes="hidden-trigger-row"):
                    single_video_shot_num = gr.Number(value=1, elem_id="single_video_shot_num")
                    single_video_trigger_btn = gr.Button("生成单个视频", elem_id="single_video_trigger_btn")

                # 隐藏元素：用于视频预览触发
                with gr.Row(elem_classes="hidden-trigger-row"):
                    preview_video_shot_num = gr.Number(value=1, elem_id="preview_video_shot_num")
                    preview_video_trigger_btn = gr.Button("预览视频", elem_id="preview_video_trigger_btn")

                # ===== 折叠区域：一致性设置 =====
                with gr.Accordion("🎯 一致性设置（锁定种子保持风格统一）", open=True):
                    gr.Markdown("*锁定种子后，所有镜头将使用相同的随机种子，仅通过提示词变化来区分画面，保持整体风格一致*")
                    with gr.Row():
                        lock_seed_checkbox = gr.Checkbox(
                            label="锁定种子",
                            value=True,
                            info="启用后所有镜头使用相同种子"
                        )
                        seed_input = gr.Number(
                            label="种子值",
                            value=-1,
                            precision=0,
                            info="-1 表示自动生成并锁定，正整数为指定种子",
                            interactive=True
                        )
                        apply_seed_btn = gr.Button("应用", elem_classes="secondary-btn", size="sm")
                    seed_status = gr.Textbox(label="", show_label=False, interactive=False, container=False, visible=False)

                # ===== 折叠区域：视频片段生成 =====
                with gr.Accordion("🎬 视频片段生成", open=False):
                    gr.Markdown("*基于分镜图片生成动态视频片段，保持角色和道具的一致性*")

                    with gr.Row():
                        # 左侧：设置区域
                        with gr.Column(scale=1):
                            # 生成模式
                            video_gen_mode = gr.Radio(
                                ["图生视频", "文生视频"],
                                label="生成模式",
                                value="图生视频",
                                info="图生视频：基于已生成的分镜图片；文生视频：直接从描述生成"
                            )

                            # 视频风格
                            video_style = gr.Radio(
                                ["电影感", "动漫风", "写实风", "赛博朋克"],
                                label="视频风格",
                                value="电影感"
                            )

                            # 视频时长
                            video_duration = gr.Radio(
                                ["3秒", "5秒", "10秒"],
                                label="视频时长",
                                value="5秒"
                            )

                            # 运镜方式
                            video_camera = gr.Radio(
                                ["静止", "缓慢推进", "缓慢拉远", "左右平移", "跟随主体"],
                                label="运镜方式",
                                value="静止"
                            )

                        # 右侧：一致性参考图
                        with gr.Column(scale=1):
                            gr.Markdown("**一致性参考图**")
                            gr.Markdown("*上传参考图以保持视频中角色和道具的一致性*", elem_classes="text-muted")

                            video_char_ref = gr.File(
                                label="👤 人物参考图",
                                file_types=["image"],
                                file_count="multiple"
                            )

                            video_prop_ref = gr.File(
                                label="🎒 道具参考图",
                                file_types=["image"],
                                file_count="multiple"
                            )

                            video_scene_ref = gr.File(
                                label="🏞️ 场景参考图 (可选)",
                                file_types=["image"]
                            )

                    # 生成控制
                    with gr.Row():
                        video_shot_num = gr.Number(label="镜头编号", value=1, precision=0, minimum=1, scale=1, elem_id="video_shot_num")
                        generate_video_btn = gr.Button("🎬 生成视频片段", elem_classes="primary-btn", scale=2, elem_id="generate_video_btn")
                        generate_all_video_btn = gr.Button("🎬 批量生成全部", elem_classes="success-btn", scale=2)

                    video_gen_status = gr.Textbox(label="", show_label=False, interactive=False, container=False, placeholder="就绪")

                    # 视频预览
                    gr.Markdown("**生成预览**")
                    with gr.Row():
                        video_preview = gr.Video(label="视频预览", height=300)
                        with gr.Column():
                            video_gallery = gr.Gallery(label="已生成视频", columns=3, height=200, allow_preview=True)
                            refresh_video_gallery_btn = gr.Button("🔄 刷新", elem_classes="secondary-btn", size="sm")

                # ===== 折叠区域：AI提示词优化 (高级功能) =====
                with gr.Accordion("🤖 AI 提示词优化", open=False):
                    gr.Markdown("优化提示词，使其更适合图像生成模型", elem_classes="text-muted")
                    with gr.Row():
                        with gr.Column(scale=1):
                            original_prompt_input = gr.Textbox(
                                label="原始提示词",
                                placeholder="输入需要优化的提示词...",
                                lines=3
                            )
                            with gr.Row():
                                optimize_style_select = gr.Dropdown(
                                    ["2D卡通", "电影感", "动漫风", "漫画风", "写实风", "水彩画"],
                                    label="风格",
                                    value="电影感",
                                    scale=1
                                )
                                ai_optimize_btn = gr.Button("优化", elem_classes="primary-btn", scale=1)
                        with gr.Column(scale=1):
                            optimized_prompt_output = gr.Textbox(
                                label="优化结果 (英文)",
                                placeholder="优化后的提示词...",
                                lines=4,
                                interactive=True
                            )
                            copy_prompt_btn = gr.Button("📋 复制", elem_classes="secondary-btn", size="sm")

            # ===== 导出 =====
            with gr.Tab("④ 导出", elem_id="tab-export"):

                # 隐藏摘要 (工作流进度指示器已显示)
                step4_summary = gr.HTML(value=get_step_summary(4), visible=False)

                gr.Markdown("### 导出项目")
                gr.Markdown("选择导出格式，下载您的分镜作品")

                export_format = gr.Radio(
                    ["图片包 (ZIP)", "项目文件 (JSON)", "分镜脚本 (TXT)", "完整备份 (ZIP+JSON+图片)"],
                    label="导出格式",
                    value="图片包 (ZIP)"
                )

                export_btn = gr.Button("导出", elem_classes="primary-btn")
                export_status = gr.Textbox(label="", show_label=False, interactive=False, container=False)
                export_file = gr.File(label="下载文件")

                gr.Markdown("---")
                gr.Markdown("### 🤖 AI 项目摘要")
                gr.Markdown("使用 AI 自动生成项目摘要，可用于项目说明或分享")

                with gr.Row():
                    ai_summary_btn = gr.Button("🤖 生成项目摘要", elem_classes="primary-btn")
                ai_project_summary = gr.Textbox(
                    label="项目摘要",
                    placeholder="点击按钮生成项目摘要...",
                    lines=6,
                    interactive=True
                )

                gr.Markdown("---")
                gr.Markdown("### 格式说明")
                gr.Markdown("""
                | 格式 | 说明 | 用途 |
                |------|------|------|
                | 图片包 (ZIP) | 仅包含生成的分镜图片 | 快速分享或导入其他软件 |
                | 项目文件 (JSON) | 完整项目数据，不含图片 | 项目备份或迁移 |
                | 分镜脚本 (TXT) | 文字版分镜脚本 | 打印或文档存档 |
                | 完整备份 | 项目+图片+参考图 | 完整归档保存 |
                """)

        # 页脚
        gr.HTML("""
        <div style="text-align: center; padding: 30px 0; color: #86868b; font-size: 13px;">
            AI 分镜 Pro v2.1 · 专业分镜制作系统
        </div>
        """)

        # ========================================
        # 事件绑定
        # ========================================

        # API 配置保存
        llm_save_btn.click(
            save_llm_config,
            inputs=[llm_provider_cn, llm_api_key_cn, llm_api_url_cn, llm_provider_intl, llm_api_key_intl, llm_api_url_intl],
            outputs=[llm_save_status]
        )

        img_save_btn.click(
            save_image_config,
            inputs=[img_provider_cn, img_api_key_cn, img_api_url_cn, img_provider_intl, img_api_key_intl, img_api_url_intl],
            outputs=[img_save_status]
        )

        # ComfyUI 连接状态
        def refresh_comfyui_status():
            status_html, _ = get_comfyui_status()
            return status_html

        comfyui_refresh_btn.click(
            refresh_comfyui_status,
            outputs=[comfyui_status_html]
        )

        comfyui_connect_btn.click(
            connect_comfyui,
            outputs=[comfyui_status_html, comfyui_msg]
        ).then(
            lambda msg: gr.update(visible=bool(msg), value=msg),
            inputs=[comfyui_msg],
            outputs=[comfyui_msg]
        )

        # ComfyUI 工作流加载
        load_default_workflow_btn.click(
            load_default_workflow,
            outputs=[workflow_status]
        )

        # 点击自定义按钮显示文件上传
        load_custom_workflow_btn.click(
            lambda: gr.update(visible=True),
            outputs=[img_workflow_file]
        )

        # 上传文件后加载工作流
        img_workflow_file.change(
            load_workflow_from_file,
            inputs=[img_workflow_file],
            outputs=[workflow_status]
        ).then(
            lambda: gr.update(visible=False),
            outputs=[img_workflow_file]
        )

        video_save_btn.click(
            save_video_config,
            inputs=[video_provider_cn, video_api_key_cn, video_api_url_cn, video_provider_intl, video_api_key_intl, video_api_url_intl],
            outputs=[video_save_status]
        )

        # 创建项目
        create_btn.click(
            create_project,
            inputs=[project_name, aspect_ratio],
            outputs=[create_status, gr.State()]
        ).then(
            lambda: get_project_summary(),
            outputs=[project_summary]
        )

        # 导入项目
        import_btn.click(
            import_project_file,
            inputs=[import_file],
            outputs=[import_status, project_summary, char_list, scene_list, shot_list]
        )

        # 智能导入 - AI分析
        smart_analyze_btn.click(
            smart_import_analyze,
            inputs=[smart_import_files, use_claude_check],
            outputs=[smart_import_status, raw_content_preview, analyzed_json]
        )

        # 智能导入 - 应用导入
        smart_apply_btn.click(
            smart_import_apply,
            inputs=[analyzed_json],
            outputs=[smart_import_status, project_summary, char_list, scene_list, shot_list]
        )

        # 加载范例 (使用与模板按钮相同的输出列表)
        load_example_btn.click(
            load_example_story,
            inputs=[example_choice],
            outputs=[
                example_status, project_summary, example_desc,
                char_list, scene_list, shot_list,
                del_char_name, del_scene_name,
                shot_chars, shot_scene,
                style_choice, standard_prompt, generated_prompt,
                workflow_step_indicator,
                step2_summary, step3_summary, step4_summary,
                shot_cards_html
            ]
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # ========================================
        # 首页导航按钮事件绑定
        # ========================================

        # 工作流导航按钮 - 点击跳转到对应标签页
        nav_create_btn.click(
            fn=None,
            js="() => { const tabs = document.querySelectorAll('[role=\"tablist\"] button'); if(tabs[0]) tabs[0].click(); }"
        )
        nav_arrange_btn.click(
            fn=None,
            js="() => { const tabs = document.querySelectorAll('[role=\"tablist\"] button'); if(tabs[1]) tabs[1].click(); }"
        )
        nav_generate_btn.click(
            fn=None,
            js="() => { const tabs = document.querySelectorAll('[role=\"tablist\"] button'); if(tabs[2]) tabs[2].click(); }"
        )
        nav_export_btn.click(
            fn=None,
            js="() => { const tabs = document.querySelectorAll('[role=\"tablist\"] button'); if(tabs[3]) tabs[3].click(); }"
        )

        # 快速开始模板按钮 - 加载预设范例
        def load_template_and_navigate(template_name):
            """加载模板并返回状态"""
            result = load_example_story(template_name)
            return result

        # 模板加载按钮 - 更新所有相关 UI 元素
        template_outputs = [
            example_status, project_summary, example_desc,
            char_list, scene_list, shot_list,
            del_char_name, del_scene_name,
            shot_chars, shot_scene,
            style_choice, standard_prompt, generated_prompt,
            workflow_step_indicator,
            step2_summary, step3_summary, step4_summary,
            shot_cards_html  # 镜头卡片
        ]

        # 加载范例后自动跳转到生成页面，激活三栏布局
        load_example_js = """() => {
            document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
            document.getElementById('template-{id}')?.classList.add('selected');
            // 激活三栏布局：左边范例 | 中间工作区 | 右边设置
            document.body.classList.add('layout-active');

            // 折叠范例模板区域并添加点击展开功能
            const templatesSection = document.querySelector('.templates-section');
            if (templatesSection) {
                templatesSection.classList.add('collapsed');
                // 找到模板卡片容器（下一个兄弟Row元素）
                const templateCardsRow = templatesSection.closest('.column')?.querySelector(':scope > .row');
                if (templateCardsRow) {
                    templateCardsRow.classList.remove('templates-expanded');
                }
                // 添加点击展开/折叠功能
                const h3 = templatesSection.querySelector('h3');
                if (h3 && !h3.hasAttribute('data-toggle-bound')) {
                    h3.setAttribute('data-toggle-bound', 'true');
                    h3.addEventListener('click', () => {
                        templatesSection.classList.toggle('collapsed');
                        if (templateCardsRow) {
                            templateCardsRow.classList.toggle('templates-expanded');
                        }
                    });
                }
            }

            // 滚动到工作流指示器
            document.querySelector('.workflow-indicator')?.scrollIntoView({behavior: 'smooth', block: 'start'});
            // 延迟后切换到生成标签
            setTimeout(() => {
                const tabs = document.querySelectorAll('[role=\"tablist\"] button');
                if(tabs[2]) tabs[2].click();  // 点击第3个标签(生成)
            }, 500);
        }"""

        # ===== 一句话生成故事按钮 =====
        generate_story_btn.click(
            generate_story_from_idea,
            inputs=[story_idea_input],
            outputs=template_outputs
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        ).then(
            fn=None,
            js=load_example_js.replace('{id}', 'ai-generated')
        )

        load_madao_btn.click(
            lambda: load_example_story("马到成功送祝福"),
            outputs=template_outputs
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        ).then(
            fn=None,
            js=load_example_js.replace('{id}', 'madao')
        )
        load_junma_btn.click(
            lambda: load_example_story("骏马奔腾迎新年"),
            outputs=template_outputs
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        ).then(
            fn=None,
            js=load_example_js.replace('{id}', 'junma')
        )
        load_mashang_btn.click(
            lambda: load_example_story("马上有美食"),
            outputs=template_outputs
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        ).then(
            fn=None,
            js=load_example_js.replace('{id}', 'mashang')
        )

        # 英雄区按钮
        new_project_btn.click(
            fn=None,
            js="() => { const tabs = document.querySelectorAll('[role=\"tablist\"] button'); if(tabs[0]) tabs[0].click(); }"
        )
        load_template_btn.click(
            fn=None,
            js="() => { document.querySelector('.templates-section')?.scrollIntoView({behavior: 'smooth'}); }"
        )

        # 添加角色
        add_char_btn.click(
            add_character_with_multi_images,
            inputs=[
                char_name, char_desc, char_images,
                char_gender, char_age, char_ethnicity,
                char_hair_color, char_hair_style, char_eye_color,
                char_body_type, char_skin_tone, char_glasses,
                char_other_features,
                char_costume_locked,
                char_top, char_top_color,
                char_bottom, char_bottom_color,
                char_outerwear, char_accessories
            ],
            outputs=[char_status, char_list]
        ).then(
            lambda: get_project_summary(),
            outputs=[project_summary]
        )

        # 添加场景
        add_scene_btn.click(
            add_scene_with_multi_images,
            inputs=[scene_name, scene_desc, scene_images],
            outputs=[scene_status, scene_list]
        ).then(
            lambda: get_project_summary(),
            outputs=[project_summary]
        )

        # ========================================
        # AI 辅助功能事件绑定
        # ========================================

        # AI 生成角色描述
        ai_char_desc_btn.click(
            ai_generate_character_desc,
            inputs=[char_name],
            outputs=[char_desc]
        )

        # AI 生成场景描述
        ai_scene_desc_btn.click(
            ai_generate_scene_desc,
            inputs=[scene_name],
            outputs=[scene_desc]
        )

        # AI 生成镜头描述
        ai_shot_desc_btn.click(
            ai_generate_shot_desc,
            inputs=[shot_template, shot_chars, shot_scene],
            outputs=[shot_desc]
        )

        # AI 优化提示词
        ai_optimize_btn.click(
            ai_optimize_prompt,
            inputs=[original_prompt_input, optimize_style_select],
            outputs=[optimized_prompt_output]
        )

        # AI 生成项目摘要
        ai_summary_btn.click(
            ai_generate_project_summary,
            outputs=[ai_project_summary]
        )

        # CLI 输出刷新和清空
        refresh_cli_btn.click(
            get_cli_output,
            outputs=[cli_output_display]
        )

        clear_cli_btn.click(
            clear_cli_output,
            outputs=[cli_output_display]
        )

        # 设置风格
        style_btn.click(
            set_style,
            inputs=[style_choice],
            outputs=[style_status]
        )

        # 风格类型切换 (2D/3D)
        style_category.change(
            get_style_options,
            inputs=[style_category],
            outputs=[style_choice]
        )

        # 风格锁定切换
        style_lock.change(
            toggle_style_lock,
            inputs=[style_lock],
            outputs=[style_lock_info]
        )

        # 刷新下拉
        refresh_btn.click(
            refresh_dropdowns,
            outputs=[shot_chars, shot_scene, del_char_name, del_scene_name]
        )

        # 添加镜头
        add_shot_btn.click(
            add_shot_simple,
            inputs=[shot_template, shot_desc, shot_chars, shot_scene],
            outputs=[shot_status, shot_list, generated_prompt, standard_prompt]
        ).then(
            lambda: get_project_summary(),
            outputs=[project_summary]
        )

        # 查看镜头提示语
        view_prompt_btn.click(
            get_shot_standard_prompt,
            inputs=[view_shot_num],
            outputs=[generated_prompt, standard_prompt]
        )

        # 删除镜头
        delete_btn.click(
            delete_shot,
            inputs=[delete_num],
            outputs=[shot_status, shot_list]
        ).then(
            lambda: get_project_summary(),
            outputs=[project_summary]
        )

        # 镜头上移
        move_up_btn.click(
            lambda n: move_shot(n, "上移"),
            inputs=[delete_num],
            outputs=[shot_status, shot_list]
        )

        # 镜头下移
        move_down_btn.click(
            lambda n: move_shot(n, "下移"),
            inputs=[delete_num],
            outputs=[shot_status, shot_list]
        )

        # 删除角色
        del_char_btn.click(
            delete_character,
            inputs=[del_char_name],
            outputs=[char_status, char_list]
        ).then(
            lambda: (get_project_summary(), gr.update(choices=get_character_names())),
            outputs=[project_summary, del_char_name]
        )

        # 删除场景
        del_scene_btn.click(
            delete_scene,
            inputs=[del_scene_name],
            outputs=[scene_status, scene_list]
        ).then(
            lambda: (get_project_summary(), gr.update(choices=get_scene_names())),
            outputs=[project_summary, del_scene_name]
        )

        # 生成单个
        gen_single_btn.click(
            generate_single_shot,
            inputs=[gen_shot_num, generated_prompt],
            outputs=[gen_status, preview_image]
        ).then(
            lambda: (get_project_summary(), get_shot_list(), get_shot_cards_html()),
            outputs=[project_summary, shot_list, shot_cards_html]
        )

        # 生成全部
        gen_all_btn.click(
            generate_all_shots,
            outputs=[gen_status]
        ).then(
            lambda: (get_project_summary(), get_shot_list(), get_shot_cards_html()),
            outputs=[project_summary, shot_list, shot_cards_html]
        )

        # 种子锁定设置
        apply_seed_btn.click(
            apply_seed_settings,
            inputs=[lock_seed_checkbox, seed_input],
            outputs=[gen_status]
        )

        # 刷新镜头卡片
        refresh_cards_btn.click(
            get_shot_cards_html,
            outputs=[shot_cards_html]
        )

        # ========================================
        # 视频生成事件绑定
        # ========================================

        # 生成单个视频
        generate_video_btn.click(
            generate_video_from_shot,
            inputs=[
                video_shot_num, video_gen_mode, video_style,
                video_duration, video_camera,
                video_char_ref, video_prop_ref, video_scene_ref
            ],
            outputs=[video_gen_status, video_preview]
        )

        # 批量生成全部视频
        generate_all_video_btn.click(
            generate_all_videos,
            inputs=[
                video_gen_mode, video_style,
                video_duration, video_camera,
                video_char_ref, video_prop_ref, video_scene_ref
            ],
            outputs=[video_gen_status, video_gallery]
        )

        # 刷新视频画廊
        refresh_video_gallery_btn.click(
            lambda: [],  # TODO: 实现获取已生成视频列表
            outputs=[video_gallery]
        )

        # 一键生成全部视频（主按钮）
        batch_video_btn.click(
            generate_all_videos_with_cli,
            inputs=[
                video_gen_mode, video_style,
                video_duration, video_camera,
                video_char_ref, video_prop_ref, video_scene_ref
            ],
            outputs=[batch_video_status, video_cli_output, video_gallery]
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # 刷新视频卡片
        refresh_video_cards_btn.click(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # 手动保存项目
        manual_save_btn.click(
            manual_save_project,
            outputs=[batch_video_status]
        )

        # 手动加载项目
        manual_load_btn.click(
            manual_load_project,
            outputs=[batch_video_status, video_cards_html, video_stats_html]
        )

        # 图片历史加载 - 只加载图片
        load_images_btn.click(
            load_images_only,
            inputs=[image_history_dropdown],
            outputs=[batch_video_status, shot_cards_html]
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # 图片历史加载 - 只加载视频
        load_videos_btn.click(
            load_videos_only,
            inputs=[image_history_dropdown],
            outputs=[batch_video_status, shot_cards_html]
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # 图片历史加载 - 全部加载（图片+视频）
        load_all_btn.click(
            load_image_batch,
            inputs=[image_history_dropdown],
            outputs=[batch_video_status, shot_cards_html]
        ).then(
            lambda: (get_video_cards_html(), get_video_stats_html()),
            outputs=[video_cards_html, video_stats_html]
        )

        # 刷新图片历史下拉列表
        refresh_history_btn.click(
            lambda: gr.update(choices=get_image_history_choices()),
            outputs=[image_history_dropdown]
        )

        # 视频预览触发（从镜头卡片点击触发）
        preview_video_trigger_btn.click(
            get_video_for_preview,
            inputs=[preview_video_shot_num],
            outputs=[video_preview_player]
        )

        # 单个镜头视频生成（从镜头卡片按钮触发）
        single_video_trigger_btn.click(
            generate_single_video_with_cli,
            inputs=[single_video_shot_num],
            outputs=[batch_video_status, video_cli_output, video_cards_html, video_stats_html]
        )

        # 导出
        export_btn.click(
            export_project_multi_format,
            inputs=[export_format],
            outputs=[export_status, export_file]
        )

        # ========================================
        # 页面加载时检测 ComfyUI 状态
        def on_page_load():
            status_html, _ = get_comfyui_status()
            return status_html

        # 镜头预览弹窗初始化 JavaScript
        shot_modal_init_js = """
        () => {
            if (window._shotModalInitialized) return;
            window._shotModalInitialized = true;
            window.globalShotsData = [];
            window.globalCurrentIndex = 0;

            document.addEventListener('click', function(e) {
                var card = e.target.closest('.shot-card');
                if (card) {
                    var shotNum = parseInt(card.getAttribute('data-shot-num'));
                    console.log('[镜头预览] 点击镜头卡片:', shotNum, '数据长度:', window.globalShotsData.length);
                    if (shotNum) {
                        window.globalCurrentIndex = shotNum - 1;
                        var modal = document.getElementById('globalShotModal');
                        if (modal) {
                            if (window.globalShotsData.length >= shotNum) {
                                window.updateGlobalModal();
                            } else {
                                console.log('[镜头预览] 数据未加载，尝试从页面获取');
                                document.getElementById('globalModalTitle').textContent = '镜头 ' + shotNum + ' 预览';
                                document.getElementById('globalModalDesc').textContent = '数据加载中...';
                                document.getElementById('globalModalImage').innerHTML = '<div class="modal-no-image">⏳<br/>加载中...</div>';
                            }
                            modal.style.display = 'flex';
                            document.body.style.overflow = 'hidden';
                        } else {
                            console.error('[镜头预览] 未找到弹窗元素 #globalShotModal');
                        }
                    }
                }
            });

            document.addEventListener('keydown', function(e) {
                var modal = document.getElementById('globalShotModal');
                if (modal && modal.style.display === 'flex') {
                    if (e.key === 'Escape') window.closeGlobalModal();
                    if (e.key === 'ArrowLeft') window.navigateGlobalShot(-1);
                    if (e.key === 'ArrowRight') window.navigateGlobalShot(1);
                }
            });

            window.closeGlobalModal = function() {
                document.getElementById('globalShotModal').style.display = 'none';
                document.body.style.overflow = '';
            };

            window.navigateGlobalShot = function(dir) {
                window.globalCurrentIndex += dir;
                if (window.globalCurrentIndex < 0) window.globalCurrentIndex = window.globalShotsData.length - 1;
                if (window.globalCurrentIndex >= window.globalShotsData.length) window.globalCurrentIndex = 0;
                window.updateGlobalModal();
            };

            window.updateGlobalModal = function() {
                var shot = window.globalShotsData[window.globalCurrentIndex];
                if (!shot) {
                    console.log('[镜头预览] 未找到镜头数据，索引:', window.globalCurrentIndex);
                    return;
                }
                document.getElementById('globalModalTitle').textContent = '镜头 ' + shot.num + ' 预览';
                document.getElementById('globalModalDesc').textContent = shot.description || '-';
                document.getElementById('globalModalChars').textContent = shot.characters || '无';
                document.getElementById('globalModalScene').textContent = shot.scene || '-';
                document.getElementById('globalModalType').textContent = shot.shot_type || '-';
                document.getElementById('globalModalAngle').textContent = shot.camera_angle || '-';
                document.getElementById('globalModalPrompt').textContent = shot.prompt || '未生成';
                document.getElementById('globalModalNav').textContent = (window.globalCurrentIndex + 1) + ' / ' + window.globalShotsData.length;
                var imgArea = document.getElementById('globalModalImage');
                if (shot.has_image && shot.img_uri) {
                    imgArea.innerHTML = '<img src="' + shot.img_uri + '" class="modal-preview-img" />';
                } else {
                    imgArea.innerHTML = '<div class="modal-no-image">🖼️<br/>图片待生成</div>';
                }
            };

            window.updateShotsData = function(data) {
                console.log('[镜头预览] 更新数据，共', data.length, '个镜头');
                window.globalShotsData = data;
            };

            console.log('[AI分镜Pro] 镜头预览弹窗已初始化');
        }
        """

        demo.load(
            on_page_load,
            outputs=[comfyui_status_html],
            js=shot_modal_init_js
        )

    return demo


# ========================================
# 启动
# ========================================

if __name__ == "__main__":
    # Check if setup is needed
    if needs_setup():
        print("\n" + "=" * 50)
        print("  First-time setup required")
        print("=" * 50)
        print("\nNo configuration found. Running setup wizard...\n")

        if not run_wizard():
            print("\nSetup was not completed. Please run setup_wizard.py")
            print("or create a .env file from .env.example")
            exit(1)

        # Reload settings after wizard completes
        from settings import reload_settings
        reload_settings()
        API_KEY = settings.api_key

    # Validate configuration (warnings only, don't block startup)
    errors = settings.validate()
    if errors:
        print("\n" + "=" * 50)
        print("  Configuration Warning")
        print("=" * 50)
        for error in errors:
            print(f"  - {error}")
        print("\nSome features may not work. Run 'python setup_wizard.py' to configure.")
        print("Continuing startup...\n")

    # 设置静态文件路径（Gradio 6.x文件服务）
    static_paths = [
        str(OUTPUTS_DIR),
        str(ASSETS_DIR),
        str(BASE_DIR / "projects"),
    ]
    gr.set_static_paths(paths=static_paths)

    # 自动连接 ComfyUI
    auto_connect_comfyui()

    demo = create_ui()

    # 允许 Gradio 访问输出目录的文件（用于视频预览）
    allowed_paths = [
        str(OUTPUTS_DIR),
        str(ASSETS_DIR),
        str(BASE_DIR / "projects"),
    ]

    demo.launch(
        server_name=settings.gradio_host,
        server_port=settings.gradio_port,
        share=False,
        inbrowser=True,
        css=CUSTOM_CSS,
        allowed_paths=allowed_paths
    )
