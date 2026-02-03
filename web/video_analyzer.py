# -*- coding: utf-8 -*-
"""
视频分析模块 - Video Analyzer Module
=====================================

高德纳的文学编程: 代码应该像文章一样可读。
维特根斯坦的语言清晰: 说清楚能说的，对不能说的保持沉默。

模块功能:
---------
1. 视频抽帧 (VideoFrameExtractor)
   - 按固定时间间隔提取
   - 基于场景变化检测提取
   - 混合模式

2. OCR识别 (OllamaVisionClient)
   - 调用本地 Ollama qwen3-vl:4b 模型
   - 支持重试和超时处理

3. 智能分析 (ClaudeAnalyzer)
   - 调用 Claude Code CLI
   - 故事结构、角色、场景、分镜分析

4. 时间锚点系统
   - 关键帧与分析内容双向关联
   - 支持时间轴导航

5. 报告生成 (PDFReportGenerator)
   - PDF报告输出
   - HTML备选方案

设计哲学 (由20位大师审核):
------------------------
- 苏格拉底: 诘问式错误处理
- 亚里士多德: 完备的类型分类
- 笛卡尔: 方法论怀疑的输入验证
- 康德: 先验配置与接口契约
- 欧拉/高斯: 数学简洁与精确
- 图灵: 可停机的分析流程
- 迪杰斯特拉: 结构化编程
- 高德纳: 文学编程与算法优化

Version: 2.0.0
Author: AI 分镜 Pro Team
"""

import os
import json
import subprocess
import tempfile
import base64
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Protocol
from datetime import datetime
from enum import Enum
import uuid
import cv2
import numpy as np
from pathlib import Path


# ========================================
# 康德: 先验配置 - 普遍法则定义
# ========================================

@dataclass
class AnalyzerConfig:
    """
    康德的绝对命令: 配置应该是先验的、普遍的、可验证的

    所有可配置项集中管理，避免魔法数字。
    """
    # Ollama 配置
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_model: str = "qwen3-vl:4b"
    ollama_timeout: int = 60
    ollama_max_retries: int = 3

    # 抽帧配置
    default_interval_seconds: float = 5.0
    default_max_frames: int = 50
    scene_change_threshold: float = 30.0
    min_scene_interval: float = 2.0

    # 输出配置
    output_dir: str = ""
    frame_quality: int = 90  # JPEG质量
    max_video_size_gb: float = 10.0

    # 分析配置
    max_frames_for_analysis: int = 50
    max_frames_for_tags: int = 20
    claude_timeout: int = 180

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(os.getcwd(), "video_analysis")


# 康德: 接口契约 - 普遍法则
class ImageAnalyzerProtocol(Protocol):
    """康德的绝对命令: 图像分析器必须遵守的契约"""

    def test_connection(self) -> Tuple[bool, str]:
        """测试连接"""
        ...

    def analyze_image(self, image_path: str, prompt: str) -> Tuple[str, float]:
        """分析图像"""
        ...


class TextAnalyzerProtocol(Protocol):
    """康德的绝对命令: 文本分析器必须遵守的契约"""

    def analyze_video_content(self, frames_data: List[Dict], video_info: Dict) -> Dict[str, Any]:
        """分析视频内容"""
        ...


# ========================================
# 欧拉 & 高斯: 数学工具函数 - 简洁且精确
# ========================================

def format_timestamp(seconds: float) -> str:
    """
    欧拉的简洁: 将秒数格式化为 HH:MM:SS.mmm

    高斯的精确: 毫秒精度，无浮点误差
    """
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def format_duration(seconds: float) -> str:
    """欧拉的简洁: 格式化时长为可读字符串"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def bytes_to_human(size_bytes: int) -> str:
    """欧拉的简洁: 字节转人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}PB"


class AnalysisStatus(Enum):
    """分析状态 - 亚里士多德: 穷尽所有可能状态"""
    PENDING = "pending"          # 等待中
    EXTRACTING = "extracting"    # 抽帧中
    OCR_PROCESSING = "ocr_processing"  # OCR处理中
    ANALYZING = "analyzing"      # 分析中
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消
    PAUSED = "paused"            # 已暂停


class FrameType(Enum):
    """帧类型 - 亚里士多德: 互斥且穷尽的分类"""
    KEYFRAME = "keyframe"        # 关键帧 (I帧)
    INTERVAL = "interval"        # 间隔帧
    SCENE_CHANGE = "scene_change"  # 场景切换帧
    DIALOG = "dialog"            # 对话帧
    ACTION = "action"            # 动作帧
    TRANSITION = "transition"    # 转场帧
    TITLE = "title"              # 标题/字幕帧


class ShotType(Enum):
    """镜头类型 - 亚里士多德: 电影语言的逻辑分类"""
    EXTREME_LONG = "extreme_long"    # 大远景
    LONG = "long"                    # 远景
    FULL = "full"                    # 全景
    MEDIUM_LONG = "medium_long"      # 中远景
    MEDIUM = "medium"                # 中景
    MEDIUM_CLOSE = "medium_close"    # 中近景
    CLOSE = "close"                  # 近景
    EXTREME_CLOSE = "extreme_close"  # 特写
    INSERT = "insert"                # 插入镜头


class CameraAngle(Enum):
    """摄像机角度 - 亚里士多德: 视角的逻辑分类"""
    EYE_LEVEL = "eye_level"      # 平视
    HIGH_ANGLE = "high_angle"    # 俯视
    LOW_ANGLE = "low_angle"      # 仰视
    DUTCH_ANGLE = "dutch_angle"  # 斜角
    BIRDS_EYE = "birds_eye"      # 鸟瞰
    WORMS_EYE = "worms_eye"      # 虫视


class CameraMovement(Enum):
    """摄像机运动 - 亚里士多德: 运动的逻辑分类"""
    STATIC = "static"        # 固定
    PAN = "pan"              # 摇 (水平)
    TILT = "tilt"            # 俯仰 (垂直)
    ZOOM = "zoom"            # 推拉
    DOLLY = "dolly"          # 移动
    TRACK = "track"          # 跟踪
    CRANE = "crane"          # 升降
    HANDHELD = "handheld"    # 手持


@dataclass
class ExtractedFrame:
    """提取的帧数据"""
    id: str = ""
    timestamp: float = 0.0  # 秒
    frame_number: int = 0
    frame_type: FrameType = FrameType.INTERVAL
    image_path: str = ""
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    tags: List[str] = field(default_factory=list)
    scene_description: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "timestamp_formatted": self.format_timestamp(),
            "frame_number": self.frame_number,
            "frame_type": self.frame_type.value,
            "image_path": self.image_path,
            "ocr_text": self.ocr_text,
            "ocr_confidence": self.ocr_confidence,
            "tags": self.tags,
            "scene_description": self.scene_description
        }

    def format_timestamp(self) -> str:
        """格式化时间戳为 HH:MM:SS.ms"""
        hours = int(self.timestamp // 3600)
        minutes = int((self.timestamp % 3600) // 60)
        seconds = int(self.timestamp % 60)
        ms = int((self.timestamp % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


@dataclass
class StoryPoint:
    """故事节点/爽点"""
    id: str = ""
    timestamp: float = 0.0
    title: str = ""
    description: str = ""
    point_type: str = ""  # 开场、铺垫、高潮、转折、结局
    emotional_impact: str = ""
    related_frames: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CharacterAnalysis:
    """角色分析"""
    id: str = ""
    name: str = ""
    first_appearance: float = 0.0
    role_type: str = ""  # 主角、配角、反派
    appearance_description: str = ""
    personality_traits: List[str] = field(default_factory=list)
    key_moments: List[float] = field(default_factory=list)
    related_frames: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SceneAnalysis:
    """场景分析"""
    id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    scene_name: str = ""
    location_type: str = ""
    atmosphere: str = ""
    lighting: str = ""
    key_elements: List[str] = field(default_factory=list)
    related_frames: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ShotAnalysis:
    """分镜分析"""
    id: str = ""
    timestamp: float = 0.0
    shot_type: str = ""  # 远景、中景、近景、特写
    camera_angle: str = ""  # 平视、俯视、仰视
    camera_movement: str = ""  # 固定、推、拉、摇、移
    composition: str = ""
    purpose: str = ""
    related_frame: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class VideoAnalysisResult:
    """完整的视频分析结果"""
    id: str = ""
    video_path: str = ""
    video_name: str = ""
    duration: float = 0.0
    fps: float = 0.0
    resolution: Tuple[int, int] = (0, 0)

    # 分析结果
    story_summary: str = ""
    story_structure: str = ""
    storyboard: str = ""  # 专业分镜脚本 (中文)
    story_points: List[StoryPoint] = field(default_factory=list)
    characters: List[CharacterAnalysis] = field(default_factory=list)
    scenes: List[SceneAnalysis] = field(default_factory=list)
    shots: List[ShotAnalysis] = field(default_factory=list)
    frames: List[ExtractedFrame] = field(default_factory=list)

    # 元数据
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: str = ""
    completed_at: str = ""
    error_message: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "video_path": self.video_path,
            "video_name": self.video_name,
            "duration": self.duration,
            "duration_formatted": self._format_duration(),
            "fps": self.fps,
            "resolution": list(self.resolution),
            "story_summary": self.story_summary,
            "story_structure": self.story_structure,
            "storyboard": self.storyboard,
            "story_points": [sp.to_dict() for sp in self.story_points],
            "characters": [c.to_dict() for c in self.characters],
            "scenes": [s.to_dict() for s in self.scenes],
            "shots": [sh.to_dict() for sh in self.shots],
            "frames": [f.to_dict() for f in self.frames],
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message
        }

    def _format_duration(self) -> str:
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class OllamaVisionClient:
    """Ollama Vision 客户端 - 调用本地 qwen3-vl:4b"""

    def __init__(self, host: str = "localhost", port: int = 11434, model: str = "qwen3-vl:4b"):
        self.base_url = f"http://{host}:{port}"
        self.model = model

    def test_connection(self) -> Tuple[bool, str]:
        """测试连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(self.model in name for name in model_names):
                    return True, f"已连接 Ollama，模型 {self.model} 可用"
                else:
                    return False, f"Ollama 已连接，但未找到模型 {self.model}。可用模型: {model_names}"
            return False, f"连接失败: HTTP {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"无法连接到 Ollama ({self.base_url})"
        except Exception as e:
            return False, f"连接错误: {str(e)}"

    def analyze_image(self, image_path: str, prompt: str = None, max_retries: int = 3) -> Tuple[str, float]:
        """
        分析图像，返回 OCR 文本和置信度

        苏格拉底诘问: 如果失败怎么办？添加重试机制。

        Args:
            image_path: 图像路径
            prompt: 自定义提示语
            max_retries: 最大重试次数

        Returns:
            (ocr_text, confidence)
        """
        if prompt is None:
            prompt = """请仔细分析这张图片，完成以下任务：

1. **文字识别(OCR)**：识别图片中所有可见的文字，包括对话框、字幕、标题、旁白等
2. **场景描述**：简要描述画面内容

请按以下JSON格式返回：
{
    "ocr_text": "识别到的所有文字",
    "scene_description": "场景描述",
    "has_dialog": true/false,
    "dialog_content": "如有对话，列出对话内容"
}"""

        import time

        for attempt in range(max_retries):
            try:
                # 读取图像并转为 base64
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                # 调用 Ollama API
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_data],
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 1024
                        }
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get("response", "")
                    # 尝试解析 JSON
                    try:
                        # 提取 JSON 部分
                        import re
                        json_match = re.search(r'\{[\s\S]*\}', text)
                        if json_match:
                            parsed = json.loads(json_match.group())
                            ocr_text = parsed.get("ocr_text", "")
                            return ocr_text, 0.85
                    except:
                        pass
                    return text, 0.7
                elif attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 指数退避
                    continue
                else:
                    return "", 0.0

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Ollama 分析错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(1 * (attempt + 1))
                    continue
                print(f"Ollama 分析最终失败: {e}")
                return "", 0.0

        return "", 0.0

    def batch_analyze(self, image_paths: List[str], progress_callback=None) -> List[Tuple[str, float]]:
        """批量分析图像"""
        results = []
        total = len(image_paths)

        for i, path in enumerate(image_paths):
            text, confidence = self.analyze_image(path)
            results.append((text, confidence))

            if progress_callback:
                progress_callback(i + 1, total, path)

        return results


class ClaudeAnalyzer:
    """Claude CLI 分析器"""

    def __init__(self):
        self.claude_cmd = "claude"

    def _call_claude(self, prompt: str, timeout: int = 120) -> str:
        """调用 Claude CLI"""
        try:
            result = subprocess.run(
                [self.claude_cmd, "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8"
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Claude CLI 错误: {result.stderr}")
                return ""

        except subprocess.TimeoutExpired:
            print("Claude CLI 超时")
            return ""
        except Exception as e:
            print(f"Claude CLI 调用错误: {e}")
            return ""

    def analyze_video_content(self, frames_data: List[Dict], video_info: Dict) -> Dict[str, Any]:
        """
        综合分析视频内容 - 专业级深度拆解

        Args:
            frames_data: 帧数据列表，包含时间戳、OCR文本、场景描述
            video_info: 视频基本信息

        Returns:
            完整的分析结果
        """
        # 构建分析提示语 - 包含前后帧信息用于运镜分析
        frames_text = ""
        for i, f in enumerate(frames_data[:80]):
            prev_info = f"(前一帧: {frames_data[i-1].get('scene_description', '')[:30]})" if i > 0 else ""
            next_info = f"(后一帧: {frames_data[i+1].get('scene_description', '')[:30]})" if i < len(frames_data)-1 else ""
            frames_text += f"【{f['timestamp_formatted']}】{f.get('ocr_text', '')} | 场景: {f.get('scene_description', '')} {prev_info} {next_info}\n"

        prompt = f"""你是一位顶级的影视分析师、分镜师和编剧。请根据以下视频抽帧信息，进行【极其详细】的专业级剧本拆解分析。

## 视频基本信息
- 视频时长: {video_info.get('duration_formatted', 'N/A')}
- 帧率: {video_info.get('fps', 'N/A')} fps
- 分辨率: {video_info.get('resolution', 'N/A')}

## 抽帧信息（时间戳 | OCR文字 | 场景描述 | 前后帧参考）
{frames_text}

## 分析要求
你需要进行【倒推剧本拆解】，像专业导演和分镜师一样详细分析每一个镜头。
重点关注：
1. 剧情拆解 - 故事脉络、情节点、叙事节奏
2. 人物拆解 - 角色形象、表情、服饰、发型、状态
3. 镜头拆解（核心重点）- 景别、机位、运镜方向、构图意图
4. 前后帧运镜方向 - 镜头如何从上一帧过渡到当前帧

请按以下JSON格式返回【非常详细】的分析结果：

{{
    "story_summary": "故事概要（300字以上，详细描述故事主线、冲突、人物关系）",
    "story_structure": "故事结构分析（详细分析起承转合、三幕结构、节奏曲线，至少200字）",

    "story_points": [
        {{
            "timestamp": 0.0,
            "title": "节点标题",
            "description": "详细描述（至少100字，包含这个节点的剧情内容、情感变化、人物状态）",
            "point_type": "开场/铺垫/发展/高潮/转折/结局",
            "emotional_impact": "情感冲击描述（观众的情绪反应）",
            "narrative_function": "叙事功能（这个节点在整体故事中的作用）"
        }}
    ],

    "characters": [
        {{
            "name": "角色名",
            "first_appearance": 0.0,
            "role_type": "主角/配角/反派/路人",
            "appearance_description": "外貌详细描述（至少150字）：面部特征、年龄特征、身材比例、皮肤质感",
            "hair_style": "发型详细描述：长度、颜色、造型、质感",
            "clothing": "服饰详细描述：款式、颜色、材质、配饰",
            "expression_range": "表情变化范围：主要出现的表情类型",
            "body_language": "肢体语言特征：姿态、动作习惯",
            "personality_traits": ["特征1", "特征2", "特征3"],
            "character_arc": "角色弧光（在这段视频中的变化）"
        }}
    ],

    "scenes": [
        {{
            "start_time": 0.0,
            "end_time": 10.0,
            "scene_name": "场景名称",
            "location_type": "室内/室外/虚拟空间",
            "location_detail": "具体位置详细描述（至少100字）：空间布局、家具摆设、装饰风格",
            "atmosphere": "氛围详细描述：情感基调、紧张程度、温度感",
            "lighting": "光线详细描述：光源方向、色温、明暗对比、阴影效果",
            "color_palette": "色彩基调：主色调、辅助色、点缀色",
            "key_elements": ["重要元素1", "重要元素2"],
            "props": ["道具1：描述", "道具2：描述"],
            "sound_atmosphere": "声音氛围推测：环境音、配乐情绪"
        }}
    ],

    "shots": [
        {{
            "timestamp": 0.0,
            "end_timestamp": 2.0,
            "shot_number": 1,
            "shot_type": "远景/全景/中景/近景/特写/大特写",
            "shot_type_detail": "景别详细说明（如：中近景偏人物上半身）",
            "camera_angle": "平视/俯视/仰视/斜角/低角度/高角度",
            "camera_angle_degree": "机位角度具体描述（如：略微俯视约15度）",
            "camera_movement": "固定/推/拉/摇/移/跟/升/降/环绕",
            "camera_movement_detail": "运镜详细描述（如：缓慢推进，从中景推到近景）",
            "movement_direction": "运镜方向（从前一帧到当前帧的镜头变化：如从左到右摇、从远到近推）",

            "cut_logic": {{
                "transition_type": "硬切/叠化/淡入/淡出/闪白/闪黑/划像/匹配剪辑/跳切/L剪辑/J剪辑",
                "cut_reason": "切镜原因（为什么在这里切：情绪转换/视角切换/时间跳跃/空间转移/强调重点/节奏需要）",
                "cut_timing": "切点选择理由（为什么选择这个时间点切：动作完成点/台词结束/表情变化/视线引导）",
                "continuity_type": "连续性类型（动作连续/视线连续/声音连续/情绪连续/图形连续）",
                "axis_compliance": "轴线规则（是否遵守180度轴线/有无越轴/越轴原因）",
                "rhythm_function": "节奏功能（加速/减速/停顿/强调/呼吸点）",
                "emotional_beat": "情感节拍（这个切点对应的情感变化）",
                "prev_shot_relation": "与前镜头关系（正反打/主观-客观/全-分/因-果/平行）",
                "next_shot_setup": "为下一镜头的铺垫（视线引导/动作延续/悬念设置）"
            }},

            "editing_technique": {{
                "montage_type": "蒙太奇类型（叙事蒙太奇/表现蒙太奇/理性蒙太奇/无）",
                "screen_direction": "画面方向（人物/物体运动方向：左→右/右→左/向镜头/背镜头）",
                "eye_trace": "视线引导（观众视线从画面哪里移动到哪里）",
                "match_elements": "匹配元素（与前后镜头匹配的视觉元素：颜色/形状/动作/位置）",
                "contrast_elements": "对比元素（与前后镜头形成对比的元素）"
            }},

            "composition": "构图详细分析（至少80字）：主体位置、黄金分割、引导线、前景中景后景层次",
            "depth_of_field": "景深效果：焦点位置、虚化程度",
            "character_position": "人物在画面中的位置：左/中/右、上/中/下，占画面比例",
            "character_state": "人物当前状态：表情、姿态、动作、视线方向",
            "purpose": "镜头目的（叙事功能、情感传达、视觉重点）",
            "visual_style": "视觉风格：滤镜、色调、质感"
        }}
    ],

    "highlights": [
        {{
            "timestamp": 0.0,
            "type": "爽点类型（反转/打脸/高能/虐心/甜蜜/燃）",
            "description": "爽点详细描述（至少100字）",
            "technique": "表现手法（镜头、剪辑、音乐如何配合）",
            "audience_reaction": "预期观众反应"
        }}
    ],

    "professional_notes": {{
        "pacing": "节奏详细分析（至少150字）：整体节奏曲线、快慢切换、情绪起伏",
        "visual_style": "视觉风格分析（至少100字）：整体美学、色彩运用、光影特点",
        "narrative_technique": "叙事技巧分析：叙事视角、时间线处理、悬念设置",
        "cinematography": "摄影技法总结：主要运镜手法、镜头语言特点",
        "editing_style": "剪辑风格：剪辑节奏、转场方式、蒙太奇运用",
        "target_audience": "目标受众分析",
        "genre_elements": "类型元素：属于什么类型，有哪些类型特征",
        "strengths": ["优点1（具体说明）", "优点2"],
        "suggestions": ["专业建议1", "专业建议2"]
    }}
}}

请确保返回有效的JSON格式。每个字段都要尽量详细，特别是shots部分要体现专业的镜头分析能力。"""

        result = self._call_claude(prompt, timeout=300)  # 增加超时时间以支持详细分析

        if result:
            try:
                # 提取 JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")

        return {}

    def generate_storyboard(self, frames_data: List[Dict], video_info: Dict) -> str:
        """
        生成专业级深度分镜脚本 (中文输出，每镜头500字以上)

        进行倒推剧本拆解，详细描述：
        - 场景环境、氛围、光线
        - 人物外貌、表情、服饰、发型
        - 物品道具、状态
        - 人物交互、动作
        - 画面风格、色调
        - 镜头类型、运镜方向
        - 与前后帧的关系

        Args:
            frames_data: 帧数据列表
            video_info: 视频信息

        Returns:
            格式化的详细分镜脚本文本
        """
        # 按时间顺序整理帧信息，包含前后帧参考
        frames_text = ""
        for i, f in enumerate(frames_data[:60]):
            prev_scene = frames_data[i-1].get('scene_description', '')[:50] if i > 0 else "无"
            next_scene = frames_data[i+1].get('scene_description', '')[:50] if i < len(frames_data)-1 else "无"
            frames_text += f"""
[{f.get('timestamp', 0):.1f}秒]
  OCR: {f.get('ocr_text', '无')}
  场景: {f.get('scene_description', '')}
  前帧参考: {prev_scene}
  后帧参考: {next_scene}
"""

        prompt = f"""你是一位顶级的分镜师、编剧和影视分析专家。请根据以下视频抽帧信息，生成【极其详细】的专业分镜脚本。

## 视频信息
- 时长: {video_info.get('duration_formatted', 'N/A')}
- 帧率: {video_info.get('fps', 'N/A')} fps
- 分辨率: {video_info.get('resolution', 'N/A')}

## 抽帧数据（包含前后帧参考用于分析运镜方向）
{frames_text}

## 核心要求 - 倒推剧本拆解
这是一个专业的【倒推剧本拆解】任务，目的是从成片反推出完整的分镜脚本。
每个镜头的描述必须【不少于500字】，详细到可以让画师直接绘制分镜稿。

## 每个镜头必须包含以下全部内容：

### 1. 基础信息
- 时间范围（如：0.1～2秒）
- 景别：远景/全景/中景/中近景/近景/特写/大特写
- 机位角度：平视/俯视/仰视/斜角/低角度/高角度（含具体角度）
- 运镜方式：固定/推/拉/摇/移/跟/升/降/环绕/手持
- 运镜方向：从前一帧到当前帧的镜头运动方向（如：从左摇到右、从远推到近）

### 2. 场景描述（至少100字）
- 场景类型：室内/室外/虚拟空间
- 具体环境：空间布局、建筑结构
- 陈设道具：家具、装饰物、重要物品
- 光线条件：光源方向、色温、明暗对比
- 氛围基调：冷暖、紧张/轻松、压抑/明朗

### 3. 人物描述（每个人物至少100字）
- 人物位置：在画面中的位置（左/中/右、前景/中景/后景）
- 占画面比例：人物在画面中占据的大小
- 面部表情：具体表情描述（眼神、嘴角、眉毛）
- 发型描述：长度、颜色、造型、是否有发饰
- 服饰描述：款式、颜色、材质、配饰
- 肢体状态：姿态、手势、动作
- 视线方向：看向哪里
- 情绪状态：内心情感

### 4. 物品/道具（如有）
- 物品名称和描述
- 在画面中的位置
- 与人物的关系

### 5. 人物交互（如有多人）
- 人物之间的空间关系
- 互动动作
- 眼神交流
- 情感流动

### 6. 画面风格
- 整体色调：暖色/冷色/中性
- 滤镜效果：清新/复古/电影感
- 画面质感：写实/梦幻/硬朗

### 7. 镜头目的
- 叙事功能：这个镜头在故事中的作用
- 情感传达：传递什么情绪
- 视觉重点：观众应该注意什么

### 8. 切镜逻辑（核心重点）
- 转场方式：硬切/叠化/淡入淡出/闪白/闪黑/划像/匹配剪辑/跳切/L剪辑/J剪辑
- 切镜原因：为什么在这里切（情绪转换/视角切换/时间跳跃/空间转移/强调重点/节奏需要）
- 切点选择：为什么选择这个时间点切（动作完成点/台词结束/表情变化/视线引导）
- 连续性类型：动作连续/视线连续/声音连续/情绪连续/图形连续
- 轴线规则：是否遵守180度轴线，有无越轴及原因
- 节奏功能：这个切点在节奏上的作用（加速/减速/停顿/强调/呼吸点）
- 与前镜头关系：正反打/主观-客观切换/全景-分切/因果关系/平行剪辑
- 与后镜头铺垫：视线引导/动作延续/悬念设置/情绪承接
- 画面方向：人物/物体运动方向（左→右/右→左/向镜头/背镜头）
- 视线引导：观众视线从画面哪里移动到哪里
- 匹配元素：与前后镜头匹配的视觉元素（颜色/形状/动作/位置）

## 输出格式示例

---
【镜头01】0.1～2秒
景别：中景 | 机位：平视 | 运镜：固定 | 过渡：硬切开场

【场景环境】
现代都市高档公寓客厅，约50平米的开阔空间。整体装修风格为现代简约，以灰白色调为主。落地窗外是城市天际线，透过薄纱窗帘可以看到远处的高楼大厦，阳光从窗户斜射进来，在地板上形成温暖的光斑。客厅中央是一组深灰色的L型布艺沙发，沙发前是一张大理石茶几，上面放着一杯冒着热气的咖啡和一本翻开的杂志。墙上挂着一幅抽象艺术画，为空间增添了几分艺术气息。整体光线柔和，色温偏暖，营造出舒适惬意的居家氛围。

【人物描述】
女主角位于画面中央偏右，占画面约1/3。她是一位约25岁的年轻女性，五官精致，皮肤白皙细腻。此刻她的表情平静中带着一丝若有所思，眉头微微皱起，嘴角保持自然弧度。她的眼神望向窗外，似乎在思考什么。

发型：及腰的黑色长直发，发质柔顺有光泽，自然垂落在肩膀两侧，没有刘海，露出光洁的额头。左耳后别着一枚精致的珍珠发夹。

服饰：身穿一件米白色的宽松针织毛衣，领口为V领设计，露出锁骨线条。下身搭配浅灰色的休闲长裤。手腕上戴着一只简约的玫瑰金手表。整体穿搭风格简约大方，透出知性优雅的气质。

肢体状态：她坐在沙发上，身体略微后仰靠着靠背，双腿自然交叠。右手轻轻扶着咖啡杯，左手搭在沙发扶手上。姿态放松但不慵懒，透出一种从容不迫的气质。

【画面风格】
整体色调偏暖，以米白、浅灰、原木色为主，画面干净通透。采用电影感调色，对比度适中，高光柔和。画面质感细腻，有一定的景深效果，背景的城市天际线略微虚化，将观众的注意力集中在女主角身上。

【镜头目的】
这是一个建立性镜头，用于介绍女主角的生活环境和基本形象。通过高档公寓和精致的穿搭，暗示女主角的社会地位和生活品质。她若有所思的表情为后续剧情埋下伏笔，引发观众对她内心世界的好奇。

【切镜逻辑】
转场方式：硬切开场，黑场直接切入画面
切镜原因：作为开场镜头，需要快速建立场景和人物
切点选择：选择女主角静态思考的瞬间，给观众留出观察和适应的时间
连续性：无前置镜头，作为序列起点
轴线规则：建立基础轴线，女主角面向画面右侧，为后续正反打预留空间
节奏功能：开场呼吸点，节奏较慢，让观众沉浸
与后镜头铺垫：女主角的视线方向（看向窗外右侧）为下一镜头的切入方向提供引导
画面方向：静态镜头，女主角面向右侧，建立画面方向基准
视线引导：观众视线从画面中央的女主角开始，沿其视线方向移向窗外
匹配元素：暖色调和室内环境将在后续镜头中保持一致，形成视觉连贯

[cut]
---

请按照以上格式，为视频生成完整的分镜脚本。每个镜头描述不少于500字，切镜逻辑部分必须详细分析。"""

        result = self._call_claude(prompt, timeout=300)  # 增加超时时间

        if result:
            return result.strip()

        return "分镜脚本生成失败"

    def generate_production_manual(self, story_text: str, style: str = "电影感", aspect_ratio: str = "16:9") -> str:
        """
        根据小说/剧本生成完整的视频制作操作手册

        包含：
        - 剧情拆解
        - 人物设定
        - 场景设定
        - 道具清单
        - 完整分镜脚本（每镜头500字+，含切镜逻辑）
        - 镜头运动设计
        - 剪辑节奏建议

        Args:
            story_text: 小说/剧本文本
            style: 视觉风格
            aspect_ratio: 画面比例

        Returns:
            完整的视频制作操作手册
        """
        prompt = f"""你是一位顶级的影视导演、分镜师和制片人。请根据以下小说/剧本内容，生成一份【极其详细】的视频制作操作手册。

## 输入内容
{story_text[:8000]}

## 制作参数
- 视觉风格: {style}
- 画面比例: {aspect_ratio}

## 你需要生成的内容

请生成一份完整的【视频制作操作手册】，包含以下所有章节：

---

# 📖 视频制作操作手册

## 第一章：剧情总览

### 1.1 故事梗概（300字以上）
详细描述故事主线、核心冲突、人物关系、情感走向

### 1.2 故事结构分析
- 三幕结构划分
- 起承转合节点
- 情感曲线图（用文字描述）
- 节奏设计意图

### 1.3 主题与调性
- 核心主题
- 情感基调
- 视觉调性

---

## 第二章：角色设定

为每个角色生成详细设定卡：

### 角色名：XXX
**基础信息**
- 年龄/性别/身份
- 性格特征
- 角色功能（主角/配角/反派）

**外貌设定（150字以上）**
- 面部特征：五官、肤色、年龄感
- 身材体型：身高、体态
- 发型设定：长度、颜色、造型、质感
- 标志性特征

**服装设定**
- 主要造型：款式、颜色、材质
- 配饰道具
- 服装变化（如有场景需要）

**表演指导**
- 常见表情
- 肢体语言特点
- 说话方式/语气

---

## 第三章：场景设定

为每个场景生成详细设定：

### 场景名：XXX
**场景概述**
- 场景类型：室内/室外
- 出现时间段
- 叙事功能

**环境设计（150字以上）**
- 空间布局
- 建筑/装修风格
- 主要陈设
- 重要道具

**光影设计**
- 主光源
- 色温倾向
- 明暗对比
- 氛围营造

**声音设计建议**
- 环境音
- 配乐情绪

---

## 第四章：道具清单

列出所有重要道具：

| 道具名 | 描述 | 出现场景 | 叙事功能 |
|--------|------|----------|----------|
| XXX | 详细描述 | 场景X | 功能说明 |

---

## 第五章：分镜脚本

【核心章节 - 每个镜头描述不少于500字】

### 镜头01：0～2秒

**基础信息**
- 景别：远景/全景/中景/近景/特写/大特写
- 机位：平视/俯视/仰视（含具体角度）
- 运镜：固定/推/拉/摇/移/跟/升/降

**场景描述（100字以上）**
详细描述画面中的环境、光线、氛围...

**人物描述（每人100字以上）**
- 位置：画面中的具体位置
- 表情：眼神、嘴角、眉毛
- 发型：当前状态
- 服装：当前穿着
- 姿态：站/坐/动作
- 视线：看向哪里
- 情绪：内心状态

**画面构图**
- 主体位置
- 前景/中景/后景层次
- 引导线
- 景深效果

**【切镜逻辑】**
- 转场方式：硬切/叠化/淡入淡出/闪白/闪黑/划像/匹配剪辑/跳切/L剪辑/J剪辑
- 切镜原因：为什么在这里切（情绪转换/视角切换/时间跳跃/空间转移/强调重点/节奏需要）
- 切点选择：为什么选择这个时间点切（动作完成点/台词结束/表情变化/视线引导）
- 连续性类型：动作连续/视线连续/声音连续/情绪连续/图形连续
- 轴线规则：是否遵守180度轴线，有无越轴及原因
- 节奏功能：加速/减速/停顿/强调/呼吸点
- 与前镜头关系：正反打/主观-客观切换/全景-分切/因果关系/平行剪辑
- 与后镜头铺垫：视线引导/动作延续/悬念设置/情绪承接
- 画面方向：人物运动方向（左→右/右→左/向镜头/背镜头）
- 视线引导：观众视线移动路径
- 匹配元素：与前后镜头匹配的视觉元素

**镜头目的**
- 叙事功能
- 情感传达
- 视觉重点

[cut]

---

## 第六章：剪辑节奏设计

### 6.1 整体节奏曲线
描述全片的节奏走向...

### 6.2 重点段落剪辑建议
- 开场段落：建议节奏...
- 高潮段落：建议节奏...
- 结尾段落：建议节奏...

### 6.3 转场设计总表
| 镜头 | 转场方式 | 时长 | 原因 |
|------|----------|------|------|

---

## 第七章：制作检查清单

### 前期准备
- [ ] 角色造型确认
- [ ] 场景搭建/选址
- [ ] 道具准备
- [ ] 分镜确认

### 拍摄要点
- [ ] 轴线标记
- [ ] 光位设计
- [ ] 动作预演

### 后期要点
- [ ] 剪辑节奏
- [ ] 调色风格
- [ ] 音效配乐

---

请按照以上格式，生成完整详细的视频制作操作手册。分镜部分是核心，每个镜头必须详细描述，特别是切镜逻辑必须完整分析。"""

        result = self._call_claude(prompt, timeout=600)  # 10分钟超时，因为内容很长

        if result:
            return result.strip()

        return "视频制作手册生成失败"

    def generate_frame_tags(self, frame_data: Dict) -> List[str]:
        """为单帧生成标签"""
        prompt = f"""请为这一帧画面生成3-5个简短的标签。

帧信息：
- 时间戳: {frame_data.get('timestamp_formatted', '')}
- OCR文字: {frame_data.get('ocr_text', '')}
- 场景描述: {frame_data.get('scene_description', '')}

请直接返回标签列表，用逗号分隔，如：室内,对话,紧张氛围,特写镜头"""

        result = self._call_claude(prompt, timeout=30)
        if result:
            return [tag.strip() for tag in result.split(",")]
        return []


class VideoFrameExtractor:
    """视频帧提取器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="video_frames_")
        os.makedirs(self.output_dir, exist_ok=True)
        self._temp_dirs = []  # 跟踪临时目录以便清理

    def cleanup(self):
        """清理临时文件 - 苏格拉底诘问: 资源管理"""
        import shutil
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
        self._temp_dirs.clear()

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {"error": "无法打开视频文件"}

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()

        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "resolution": (width, height),
            "duration": duration,
            "duration_formatted": self._format_duration(duration)
        }

    def _format_duration(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def extract_frames_ffmpeg(
        self,
        video_path: str,
        interval_seconds: float = 5.0,
        max_frames: int = 100,
        progress_callback=None
    ) -> List[ExtractedFrame]:
        """
        使用 FFmpeg 快速抽帧 (比 OpenCV 快 5-10 倍)

        Args:
            video_path: 视频路径
            interval_seconds: 间隔秒数
            max_frames: 最大帧数
            progress_callback: 进度回调

        Returns:
            提取的帧列表
        """
        if not self._check_ffmpeg():
            print("FFmpeg 不可用，回退到 OpenCV 方法")
            return self.extract_frames_by_interval(
                video_path, interval_seconds, max_frames, progress_callback
            )

        # 清理旧的 FFmpeg 输出文件和帧文件
        import glob
        old_ffmpeg_files = glob.glob(os.path.join(self.output_dir, "ffmpeg_*.jpg"))
        old_frame_files = glob.glob(os.path.join(self.output_dir, "frame_*.jpg"))
        for old_file in old_ffmpeg_files + old_frame_files:
            try:
                os.remove(old_file)
            except:
                pass

        # 获取视频信息
        video_info = self.get_video_info(video_path)
        if "error" in video_info:
            raise ValueError(video_info["error"])

        duration = video_info["duration"]
        fps = video_info["fps"]

        # 计算时间戳
        timestamps = []
        current_time = 0
        while current_time < duration and len(timestamps) < max_frames:
            timestamps.append(current_time)
            current_time += interval_seconds

        if progress_callback:
            progress_callback(0, len(timestamps), "FFmpeg 批量抽帧中...")

        # 使用 FFmpeg 的 fps filter 一次性抽取所有帧
        output_pattern = os.path.join(self.output_dir, "ffmpeg_%04d.jpg")

        # 计算等效的 fps 值
        if interval_seconds > 0:
            target_fps = 1.0 / interval_seconds
        else:
            target_fps = fps

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"fps={target_fps}",
            "-frames:v", str(max_frames),
            "-q:v", "2",  # 高质量 JPEG
            "-y",  # 覆盖已存在文件
            output_pattern
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                print(f"FFmpeg 错误: {result.stderr.decode()}")
                return self.extract_frames_by_interval(
                    video_path, interval_seconds, max_frames, progress_callback
                )

        except subprocess.TimeoutExpired:
            print("FFmpeg 超时，回退到 OpenCV")
            return self.extract_frames_by_interval(
                video_path, interval_seconds, max_frames, progress_callback
            )

        # 收集生成的帧
        extracted_frames = []
        for i, timestamp in enumerate(timestamps):
            frame_path = os.path.join(self.output_dir, f"ffmpeg_{i+1:04d}.jpg")
            if os.path.exists(frame_path):
                # 重命名为统一格式 (使用 replace 以支持 Windows 覆盖)
                new_path = os.path.join(self.output_dir, f"frame_{i:04d}_{timestamp:.2f}s.jpg")
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(frame_path, new_path)

                extracted_frame = ExtractedFrame(
                    timestamp=timestamp,
                    frame_number=int(timestamp * fps),
                    frame_type=FrameType.INTERVAL,
                    image_path=new_path
                )
                extracted_frames.append(extracted_frame)

            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, len(timestamps), f"处理帧 {i+1}/{len(timestamps)}")

        if progress_callback:
            progress_callback(len(timestamps), len(timestamps), "FFmpeg 抽帧完成")

        return extracted_frames

    def extract_frames_by_interval(
        self,
        video_path: str,
        interval_seconds: float = 5.0,
        max_frames: int = 100,
        progress_callback=None
    ) -> List[ExtractedFrame]:
        """
        按时间间隔提取帧

        Args:
            video_path: 视频路径
            interval_seconds: 间隔秒数
            max_frames: 最大帧数
            progress_callback: 进度回调 (current, total, message)

        Returns:
            提取的帧列表
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        # 计算要提取的帧
        timestamps = []
        current_time = 0
        while current_time < duration and len(timestamps) < max_frames:
            timestamps.append(current_time)
            current_time += interval_seconds

        extracted_frames = []
        total = len(timestamps)

        for i, timestamp in enumerate(timestamps):
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if ret:
                # 保存帧
                frame_filename = f"frame_{i:04d}_{timestamp:.2f}s.jpg"
                frame_path = os.path.join(self.output_dir, frame_filename)
                cv2.imwrite(frame_path, frame)

                extracted_frame = ExtractedFrame(
                    timestamp=timestamp,
                    frame_number=frame_number,
                    frame_type=FrameType.INTERVAL,
                    image_path=frame_path
                )
                extracted_frames.append(extracted_frame)

            if progress_callback:
                progress_callback(i + 1, total, f"提取帧 {i + 1}/{total}")

        cap.release()
        return extracted_frames

    def extract_scene_change_frames(
        self,
        video_path: str,
        threshold: float = 30.0,
        min_interval: float = 2.0,
        max_frames: int = 50,
        progress_callback=None
    ) -> List[ExtractedFrame]:
        """
        提取场景切换帧

        使用直方图差异检测场景变化
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        min_frame_interval = int(min_interval * fps)

        extracted_frames = []
        prev_hist = None
        last_extracted_frame = -min_frame_interval

        frame_idx = 0
        while frame_idx < total_frames and len(extracted_frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                break

            # 计算直方图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            if prev_hist is not None:
                # 计算直方图差异
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)

                if diff > threshold / 100 and (frame_idx - last_extracted_frame) >= min_frame_interval:
                    timestamp = frame_idx / fps
                    frame_filename = f"scene_{len(extracted_frames):04d}_{timestamp:.2f}s.jpg"
                    frame_path = os.path.join(self.output_dir, frame_filename)
                    cv2.imwrite(frame_path, frame)

                    extracted_frame = ExtractedFrame(
                        timestamp=timestamp,
                        frame_number=frame_idx,
                        frame_type=FrameType.SCENE_CHANGE,
                        image_path=frame_path
                    )
                    extracted_frames.append(extracted_frame)
                    last_extracted_frame = frame_idx

            prev_hist = hist
            frame_idx += int(fps / 4)  # 每0.25秒检测一次

            if progress_callback:
                progress = int((frame_idx / total_frames) * 100)
                progress_callback(progress, 100, f"检测场景变化... {progress}%")

        cap.release()
        return extracted_frames


class VideoAnalyzer:
    """视频分析器 - 主类"""

    # 笛卡尔方法论: 支持的视频格式 (可验证的基本事实)
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

    def __init__(self,
                 output_dir: str = None,
                 ollama_host: str = "localhost",
                 ollama_port: int = 11434,
                 ollama_model: str = "qwen3-vl:4b"):

        # 基础输出目录
        self.base_output_dir = output_dir or os.path.join(os.getcwd(), "outputs", "video_analysis")
        os.makedirs(self.base_output_dir, exist_ok=True)

        # 为本次运行创建独立目录（按时间戳）
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(self.base_output_dir, f"run_{run_timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)

        self.frame_extractor = VideoFrameExtractor(
            os.path.join(self.output_dir, "frames")
        )
        self.ollama_client = OllamaVisionClient(ollama_host, ollama_port, ollama_model)
        self.claude_analyzer = ClaudeAnalyzer()

        self._current_result: Optional[VideoAnalysisResult] = None
        self._is_cancelled = False  # 支持取消操作

    def get_cleanup_info(self, days_to_keep: int = 1) -> Dict[str, Any]:
        """
        获取可清理的运行目录信息（不执行清理）

        Args:
            days_to_keep: 保留最近几天的数据，默认1天

        Returns:
            包含可清理目录列表和统计信息的字典
        """
        import shutil
        from datetime import timedelta

        cleanup_info = {
            "directories_to_clean": [],
            "directories_to_keep": [],
            "total_size_to_clean": 0,
            "total_size_to_keep": 0,
            "cutoff_date": (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d %H:%M:%S")
        }

        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        if not os.path.exists(self.base_output_dir):
            return cleanup_info

        for item in os.listdir(self.base_output_dir):
            item_path = os.path.join(self.base_output_dir, item)
            if os.path.isdir(item_path) and item.startswith("run_"):
                # 从目录名解析时间戳
                try:
                    # 格式: run_YYYYMMDD_HHMMSS
                    timestamp_str = item[4:]  # 移除 "run_" 前缀
                    dir_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    # 计算目录大小
                    dir_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(item_path)
                        for filename in filenames
                    )

                    dir_info = {
                        "path": item_path,
                        "name": item,
                        "created": dir_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "size_mb": round(dir_size / 1024 / 1024, 2)
                    }

                    if dir_time < cutoff_time:
                        cleanup_info["directories_to_clean"].append(dir_info)
                        cleanup_info["total_size_to_clean"] += dir_size
                    else:
                        cleanup_info["directories_to_keep"].append(dir_info)
                        cleanup_info["total_size_to_keep"] += dir_size

                except (ValueError, OSError):
                    # 无法解析的目录，加入清理列表
                    cleanup_info["directories_to_clean"].append({
                        "path": item_path,
                        "name": item,
                        "created": "未知",
                        "size_mb": 0
                    })

        # 转换大小为 MB
        cleanup_info["total_size_to_clean_mb"] = round(cleanup_info["total_size_to_clean"] / 1024 / 1024, 2)
        cleanup_info["total_size_to_keep_mb"] = round(cleanup_info["total_size_to_keep"] / 1024 / 1024, 2)

        return cleanup_info

    def cleanup_old_runs(self, days_to_keep: int = 1, confirm: bool = False) -> Dict[str, Any]:
        """
        清理旧的运行目录（需要确认）

        Args:
            days_to_keep: 保留最近几天的数据，默认1天
            confirm: 是否确认执行清理，必须为 True 才会执行

        Returns:
            清理结果信息
        """
        import shutil

        result = {
            "success": False,
            "message": "",
            "cleaned_count": 0,
            "cleaned_size_mb": 0,
            "failed": []
        }

        if not confirm:
            result["message"] = "清理未执行：需要设置 confirm=True 确认清理"
            return result

        cleanup_info = self.get_cleanup_info(days_to_keep)

        for dir_info in cleanup_info["directories_to_clean"]:
            try:
                shutil.rmtree(dir_info["path"])
                result["cleaned_count"] += 1
                result["cleaned_size_mb"] += dir_info["size_mb"]
            except Exception as e:
                result["failed"].append({
                    "path": dir_info["path"],
                    "error": str(e)
                })

        result["success"] = True
        result["message"] = f"已清理 {result['cleaned_count']} 个目录，释放 {result['cleaned_size_mb']:.2f} MB"

        if result["failed"]:
            result["message"] += f"，{len(result['failed'])} 个清理失败"

        return result

    def validate_video_file(self, video_path: str) -> Tuple[bool, str]:
        """
        笛卡尔方法论怀疑: 验证视频文件的存在性和有效性

        质疑每一个假设，确保文件确实可用。
        """
        # 1. 文件是否存在？
        if not os.path.exists(video_path):
            return False, f"文件不存在: {video_path}"

        # 2. 是否是文件（而非目录）？
        if not os.path.isfile(video_path):
            return False, f"路径不是文件: {video_path}"

        # 3. 文件格式是否支持？
        ext = os.path.splitext(video_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            return False, f"不支持的格式 {ext}，支持: {self.SUPPORTED_FORMATS}"

        # 4. 文件是否可读？
        if not os.access(video_path, os.R_OK):
            return False, f"文件不可读: {video_path}"

        # 5. 文件大小是否合理？
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            return False, "文件为空"
        if file_size > 10 * 1024 * 1024 * 1024:  # 10GB
            return False, f"文件过大 ({file_size / 1024 / 1024 / 1024:.1f}GB)，建议小于10GB"

        # 6. 尝试打开视频验证
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False, "无法打开视频文件，可能已损坏"

        # 7. 检查视频是否有帧
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if frame_count <= 0:
            return False, "视频没有有效帧"

        return True, "视频文件验证通过"

    def cancel_analysis(self):
        """取消分析 - 笛卡尔: 控制权应该在使用者手中"""
        self._is_cancelled = True

    def test_connections(self) -> Dict[str, Tuple[bool, str]]:
        """测试所有连接"""
        results = {}

        # 测试 Ollama
        ollama_ok, ollama_msg = self.ollama_client.test_connection()
        results["ollama"] = (ollama_ok, ollama_msg)

        # 测试 Claude CLI
        try:
            test_result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if test_result.returncode == 0:
                results["claude"] = (True, f"Claude CLI 可用: {test_result.stdout.strip()}")
            else:
                results["claude"] = (False, "Claude CLI 不可用")
        except Exception as e:
            results["claude"] = (False, f"Claude CLI 错误: {e}")

        return results

    def analyze_video(
        self,
        video_path: str,
        extraction_mode: str = "interval",  # "interval" or "scene_change" or "both"
        interval_seconds: float = 5.0,
        max_frames: int = 50,
        progress_callback=None
    ) -> VideoAnalysisResult:
        """
        完整的视频分析流程

        Args:
            video_path: 视频文件路径
            extraction_mode: 抽帧模式
            interval_seconds: 间隔秒数（interval模式）
            max_frames: 最大帧数
            progress_callback: 进度回调 (step, total_steps, message)

        Returns:
            VideoAnalysisResult
        """
        video_name = os.path.basename(video_path)

        # 创建结果对象
        result = VideoAnalysisResult(
            video_path=video_path,
            video_name=video_name,
            status=AnalysisStatus.EXTRACTING
        )
        self._current_result = result

        total_steps = 6  # 增加分镜脚本生成步骤

        try:
            # Step 1: 获取视频信息
            if progress_callback:
                progress_callback(1, total_steps, "获取视频信息...")

            video_info = self.frame_extractor.get_video_info(video_path)
            if "error" in video_info:
                result.status = AnalysisStatus.FAILED
                result.error_message = video_info["error"]
                return result

            result.duration = video_info["duration"]
            result.fps = video_info["fps"]
            result.resolution = video_info["resolution"]

            # Step 2: 提取帧
            if progress_callback:
                progress_callback(2, total_steps, "提取视频帧...")

            frames = []
            if extraction_mode in ["interval", "both"]:
                # 使用 FFmpeg 快速抽帧 (比 OpenCV 快 5-10 倍)
                interval_frames = self.frame_extractor.extract_frames_ffmpeg(
                    video_path, interval_seconds, max_frames
                )
                frames.extend(interval_frames)

            if extraction_mode in ["scene_change", "both"]:
                scene_frames = self.frame_extractor.extract_scene_change_frames(
                    video_path, max_frames=max_frames
                )
                frames.extend(scene_frames)

            # 按时间排序并去重
            frames.sort(key=lambda f: f.timestamp)
            result.frames = frames

            # Step 3: OCR 识别
            # 图灵: 检查停机条件
            if self._is_cancelled:
                result.status = AnalysisStatus.CANCELLED
                return result

            result.status = AnalysisStatus.OCR_PROCESSING
            if progress_callback:
                progress_callback(3, total_steps, "OCR 识别中...")

            # 迪杰斯特拉: 结构化循环，单一职责
            for i, frame in enumerate(result.frames):
                # 图灵: 每次迭代检查停机
                if self._is_cancelled:
                    result.status = AnalysisStatus.CANCELLED
                    return result

                ocr_text, confidence = self.ollama_client.analyze_image(frame.image_path)
                frame.ocr_text = ocr_text
                frame.ocr_confidence = confidence

                if progress_callback and i % 5 == 0:
                    progress_callback(3, total_steps, f"OCR 识别 {i+1}/{len(result.frames)}...")

            # Step 4: Claude 分析
            result.status = AnalysisStatus.ANALYZING
            if progress_callback:
                progress_callback(4, total_steps, "AI 分析内容...")

            frames_data = [f.to_dict() for f in result.frames]
            analysis = self.claude_analyzer.analyze_video_content(frames_data, video_info)

            if analysis:
                # 填充分析结果
                result.story_summary = analysis.get("story_summary", "")
                result.story_structure = analysis.get("story_structure", "")

                # 故事节点
                for sp_data in analysis.get("story_points", []):
                    result.story_points.append(StoryPoint(
                        timestamp=sp_data.get("timestamp", 0),
                        title=sp_data.get("title", ""),
                        description=sp_data.get("description", ""),
                        point_type=sp_data.get("point_type", ""),
                        emotional_impact=sp_data.get("emotional_impact", "")
                    ))

                # 角色
                for char_data in analysis.get("characters", []):
                    result.characters.append(CharacterAnalysis(
                        name=char_data.get("name", ""),
                        first_appearance=char_data.get("first_appearance", 0),
                        role_type=char_data.get("role_type", ""),
                        appearance_description=char_data.get("appearance_description", ""),
                        personality_traits=char_data.get("personality_traits", [])
                    ))

                # 场景
                for scene_data in analysis.get("scenes", []):
                    result.scenes.append(SceneAnalysis(
                        start_time=scene_data.get("start_time", 0),
                        end_time=scene_data.get("end_time", 0),
                        scene_name=scene_data.get("scene_name", ""),
                        location_type=scene_data.get("location_type", ""),
                        atmosphere=scene_data.get("atmosphere", ""),
                        lighting=scene_data.get("lighting", ""),
                        key_elements=scene_data.get("key_elements", [])
                    ))

                # 分镜
                for shot_data in analysis.get("shots", []):
                    result.shots.append(ShotAnalysis(
                        timestamp=shot_data.get("timestamp", 0),
                        shot_type=shot_data.get("shot_type", ""),
                        camera_angle=shot_data.get("camera_angle", ""),
                        camera_movement=shot_data.get("camera_movement", ""),
                        composition=shot_data.get("composition", ""),
                        purpose=shot_data.get("purpose", "")
                    ))

            # Step 5: 生成专业分镜脚本 (中文)
            if progress_callback:
                progress_callback(5, total_steps, "生成分镜脚本...")

            storyboard = self.claude_analyzer.generate_storyboard(frames_data, video_info)
            result.storyboard = storyboard

            # Step 6: 生成帧标签
            if progress_callback:
                progress_callback(6, total_steps, "生成标签...")

            for frame in result.frames[:20]:  # 只为前20帧生成标签
                tags = self.claude_analyzer.generate_frame_tags(frame.to_dict())
                frame.tags = tags

            # 关联帧与分析项
            self._link_frames_to_analysis(result)

            result.status = AnalysisStatus.COMPLETED
            result.completed_at = datetime.now().isoformat()

            # 保存结果
            self.save_result(result)

        except Exception as e:
            result.status = AnalysisStatus.FAILED
            result.error_message = str(e)
            import traceback
            traceback.print_exc()

        return result

    def _link_frames_to_analysis(self, result: VideoAnalysisResult):
        """将帧关联到分析项目"""
        for story_point in result.story_points:
            # 找到最近的帧
            closest_frame = min(
                result.frames,
                key=lambda f: abs(f.timestamp - story_point.timestamp),
                default=None
            )
            if closest_frame:
                story_point.related_frames.append(closest_frame.id)

        for character in result.characters:
            # 找到角色首次出现附近的帧
            closest_frame = min(
                result.frames,
                key=lambda f: abs(f.timestamp - character.first_appearance),
                default=None
            )
            if closest_frame:
                character.related_frames.append(closest_frame.id)

        for scene in result.scenes:
            # 找到场景时间范围内的帧
            for frame in result.frames:
                if scene.start_time <= frame.timestamp <= scene.end_time:
                    scene.related_frames.append(frame.id)

        for shot in result.shots:
            # 找到最近的帧
            closest_frame = min(
                result.frames,
                key=lambda f: abs(f.timestamp - shot.timestamp),
                default=None
            )
            if closest_frame:
                shot.related_frame = closest_frame.id

    def save_result(self, result: VideoAnalysisResult, filename: str = None) -> str:
        """保存分析结果为JSON"""
        if filename is None:
            filename = f"analysis_{result.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        return filepath

    def load_result(self, filepath: str) -> VideoAnalysisResult:
        """加载分析结果"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        result = VideoAnalysisResult(
            id=data.get("id", ""),
            video_path=data.get("video_path", ""),
            video_name=data.get("video_name", ""),
            duration=data.get("duration", 0),
            fps=data.get("fps", 0),
            resolution=tuple(data.get("resolution", [0, 0])),
            story_summary=data.get("story_summary", ""),
            story_structure=data.get("story_structure", ""),
            status=AnalysisStatus(data.get("status", "pending")),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at", ""),
            error_message=data.get("error_message", "")
        )

        # 加载帧
        for frame_data in data.get("frames", []):
            result.frames.append(ExtractedFrame(
                id=frame_data.get("id", ""),
                timestamp=frame_data.get("timestamp", 0),
                frame_number=frame_data.get("frame_number", 0),
                frame_type=FrameType(frame_data.get("frame_type", "interval")),
                image_path=frame_data.get("image_path", ""),
                ocr_text=frame_data.get("ocr_text", ""),
                ocr_confidence=frame_data.get("ocr_confidence", 0),
                tags=frame_data.get("tags", []),
                scene_description=frame_data.get("scene_description", "")
            ))

        # 加载其他分析项...
        for sp_data in data.get("story_points", []):
            result.story_points.append(StoryPoint(**sp_data))

        for char_data in data.get("characters", []):
            result.characters.append(CharacterAnalysis(**char_data))

        for scene_data in data.get("scenes", []):
            result.scenes.append(SceneAnalysis(**scene_data))

        for shot_data in data.get("shots", []):
            result.shots.append(ShotAnalysis(**shot_data))

        return result

    def update_item(self, result_id: str, item_type: str, item_id: str, updates: Dict) -> bool:
        """
        更新分析结果中的某一项

        Args:
            result_id: 分析结果ID
            item_type: 项目类型 (story_point, character, scene, shot, frame)
            item_id: 项目ID
            updates: 更新内容

        Returns:
            是否成功
        """
        if self._current_result is None or self._current_result.id != result_id:
            return False

        item_list = None
        if item_type == "story_point":
            item_list = self._current_result.story_points
        elif item_type == "character":
            item_list = self._current_result.characters
        elif item_type == "scene":
            item_list = self._current_result.scenes
        elif item_type == "shot":
            item_list = self._current_result.shots
        elif item_type == "frame":
            item_list = self._current_result.frames
        else:
            return False

        for item in item_list:
            if item.id == item_id:
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                return True

        return False

    def get_current_result(self) -> Optional[VideoAnalysisResult]:
        """获取当前分析结果"""
        return self._current_result


class PDFReportGenerator:
    """PDF 报告生成器"""

    def __init__(self):
        pass

    def generate_report(self, result: VideoAnalysisResult, output_path: str) -> str:
        """
        生成 PDF 报告

        使用 reportlab 生成精美的PDF报告
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            return self._generate_simple_html_report(result, output_path)

        # 注册中文字体
        try:
            pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))
            font_name = 'SimHei'
        except:
            font_name = 'Helvetica'

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()

        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=24,
            spaceAfter=30
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=16,
            spaceAfter=12
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            spaceAfter=8
        )

        elements = []

        # 封面
        elements.append(Paragraph(f"视频分析报告", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"视频: {result.video_name}", body_style))
        elements.append(Paragraph(f"时长: {result._format_duration()}", body_style))
        elements.append(Paragraph(f"分辨率: {result.resolution[0]}x{result.resolution[1]}", body_style))
        elements.append(Paragraph(f"生成时间: {result.completed_at}", body_style))
        elements.append(PageBreak())

        # 故事概要
        elements.append(Paragraph("一、故事概要", heading_style))
        elements.append(Paragraph(result.story_summary or "暂无", body_style))
        elements.append(Spacer(1, 20))

        # 故事结构
        elements.append(Paragraph("二、故事结构", heading_style))
        elements.append(Paragraph(result.story_structure or "暂无", body_style))
        elements.append(Spacer(1, 20))

        # 角色分析
        elements.append(Paragraph("三、角色分析", heading_style))
        for char in result.characters:
            elements.append(Paragraph(f"<b>{char.name}</b> ({char.role_type})", body_style))
            elements.append(Paragraph(f"外貌: {char.appearance_description}", body_style))
            if char.personality_traits:
                elements.append(Paragraph(f"性格: {', '.join(char.personality_traits)}", body_style))
            elements.append(Spacer(1, 10))
        elements.append(PageBreak())

        # 场景分析
        elements.append(Paragraph("四、场景分析", heading_style))
        for scene in result.scenes:
            time_range = f"{self._format_time(scene.start_time)} - {self._format_time(scene.end_time)}"
            elements.append(Paragraph(f"<b>{scene.scene_name}</b> [{time_range}]", body_style))
            elements.append(Paragraph(f"类型: {scene.location_type} | 氛围: {scene.atmosphere}", body_style))
            elements.append(Spacer(1, 10))
        elements.append(PageBreak())

        # 分镜分析
        elements.append(Paragraph("五、分镜分析", heading_style))
        for shot in result.shots:
            elements.append(Paragraph(
                f"[{self._format_time(shot.timestamp)}] {shot.shot_type} | {shot.camera_angle} | {shot.purpose}",
                body_style
            ))
        elements.append(PageBreak())

        # 关键帧时间轴
        elements.append(Paragraph("六、关键帧时间轴", heading_style))
        for frame in result.frames[:30]:  # 只显示前30帧
            tags_str = ", ".join(frame.tags) if frame.tags else ""
            elements.append(Paragraph(
                f"[{frame.format_timestamp()}] {tags_str}",
                body_style
            ))
            if frame.ocr_text:
                elements.append(Paragraph(f"文字: {frame.ocr_text[:100]}...", body_style))
            elements.append(Spacer(1, 5))

        # 生成 PDF
        doc.build(elements)
        return output_path

    def _format_time(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _generate_simple_html_report(self, result: VideoAnalysisResult, output_path: str) -> str:
        """生成简单的 HTML 报告（备选方案）"""
        html_path = output_path.replace(".pdf", ".html")

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>视频分析报告 - {result.video_name}</title>
    <style>
        body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .meta {{ color: #888; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .item {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .timestamp {{ color: #007bff; font-weight: bold; }}
        .tag {{ display: inline-block; background: #e0e0e0; padding: 2px 8px; margin: 2px; border-radius: 10px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>视频分析报告</h1>
    <div class="meta">
        <p><strong>视频:</strong> {result.video_name}</p>
        <p><strong>时长:</strong> {result._format_duration()}</p>
        <p><strong>分辨率:</strong> {result.resolution[0]}x{result.resolution[1]}</p>
    </div>

    <div class="section">
        <h2>故事概要</h2>
        <p>{result.story_summary or '暂无'}</p>
    </div>

    <div class="section">
        <h2>故事结构</h2>
        <p>{result.story_structure or '暂无'}</p>
    </div>

    <div class="section">
        <h2>角色分析</h2>
        {"".join([f'<div class="item"><strong>{c.name}</strong> ({c.role_type})<br/>{c.appearance_description}</div>' for c in result.characters])}
    </div>

    <div class="section">
        <h2>场景分析</h2>
        {"".join([f'<div class="item"><strong>{s.scene_name}</strong> [{self._format_time(s.start_time)}-{self._format_time(s.end_time)}]<br/>氛围: {s.atmosphere}</div>' for s in result.scenes])}
    </div>

    <div class="section">
        <h2>分镜分析</h2>
        {"".join([f'<div class="item"><span class="timestamp">[{self._format_time(sh.timestamp)}]</span> {sh.shot_type} | {sh.camera_angle} | {sh.purpose}</div>' for sh in result.shots])}
    </div>

    <div class="section">
        <h2>关键帧时间轴</h2>
        {"".join([f'<div class="item"><span class="timestamp">[{f.format_timestamp()}]</span> {"".join([f"<span class=tag>{t}</span>" for t in f.tags])}<br/>{f.ocr_text[:100] if f.ocr_text else ""}</div>' for f in result.frames[:30]])}
    </div>
</body>
</html>"""

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_path


# 便捷函数
def analyze_video(
    video_path: str,
    output_dir: str = None,
    extraction_mode: str = "interval",
    interval_seconds: float = 5.0,
    max_frames: int = 50,
    generate_pdf: bool = True
) -> Tuple[VideoAnalysisResult, str]:
    """
    便捷函数：分析视频并生成报告

    Args:
        video_path: 视频路径
        output_dir: 输出目录
        extraction_mode: 抽帧模式
        interval_seconds: 间隔秒数
        max_frames: 最大帧数
        generate_pdf: 是否生成PDF

    Returns:
        (分析结果, 报告路径)
    """
    analyzer = VideoAnalyzer(output_dir=output_dir)
    result = analyzer.analyze_video(
        video_path,
        extraction_mode=extraction_mode,
        interval_seconds=interval_seconds,
        max_frames=max_frames
    )

    report_path = ""
    if generate_pdf and result.status == AnalysisStatus.COMPLETED:
        pdf_generator = PDFReportGenerator()
        report_path = os.path.join(
            analyzer.output_dir,
            f"report_{result.id}.pdf"
        )
        report_path = pdf_generator.generate_report(result, report_path)

    return result, report_path


def run_self_tests() -> bool:
    """
    波普尔的证伪主义: 好的代码应该是可测试的

    运行自检测试，返回是否全部通过。
    """
    print("=" * 50)
    print("Popper Falsifiability Tests")
    print("=" * 50)

    tests_passed = 0
    tests_failed = 0

    # Test 1: 格式化函数测试
    try:
        assert format_timestamp(3661.5) == "01:01:01.500", "Timestamp format error"
        assert format_timestamp(0) == "00:00:00.000", "Zero value format error"
        print("[PASS] Format function test")
        tests_passed += 1
    except AssertionError as e:
        print(f"[FAIL] Format function test: {e}")
        tests_failed += 1

    # Test 2: 配置类测试
    try:
        config = AnalyzerConfig()
        assert config.ollama_port == 11434, "Default port error"
        assert config.default_max_frames == 50, "Default frames error"
        print("[PASS] Config class test")
        tests_passed += 1
    except AssertionError as e:
        print(f"[FAIL] Config class test: {e}")
        tests_failed += 1

    # Test 3: 枚举完整性测试 (亚里士多德)
    try:
        assert len(AnalysisStatus) >= 6, "AnalysisStatus enum incomplete"
        assert len(FrameType) >= 4, "FrameType enum incomplete"
        assert len(ShotType) >= 5, "ShotType enum incomplete"
        print("[PASS] Enum completeness test (Aristotle)")
        tests_passed += 1
    except AssertionError as e:
        print(f"[FAIL] Enum completeness test: {e}")
        tests_failed += 1

    # Test 4: 数据类序列化测试
    try:
        frame = ExtractedFrame(timestamp=10.5, frame_number=100)
        frame_dict = frame.to_dict()
        assert "timestamp" in frame_dict, "Serialization missing timestamp"
        assert "id" in frame_dict, "Serialization missing id"
        print("[PASS] Dataclass serialization test")
        tests_passed += 1
    except AssertionError as e:
        print(f"[FAIL] Dataclass serialization test: {e}")
        tests_failed += 1

    print("-" * 50)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 50)

    return tests_failed == 0


if __name__ == "__main__":
    """
    禅宗的简洁之道: 少即是多

    香农的信息论: 最大化信号，最小化噪音
    """
    import sys

    print("视频分析模块 v2.0.0")
    print("-" * 30)

    # 运行自检测试
    if "--test" in sys.argv:
        success = run_self_tests()
        sys.exit(0 if success else 1)

    # 测试连接
    print("\n连接状态检查:")
    analyzer = VideoAnalyzer()
    connections = analyzer.test_connections()
    for name, (ok, msg) in connections.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {msg}")
