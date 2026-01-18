"""
AI Storyboard Pro - 9 Shot Templates (T1-T9)
Based on ai_storyboard_pro_framework.md
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from models import ShotTemplate, CameraSettings, CompositionSettings, SlotWeights


@dataclass
class TemplateDefinition:
    """Complete definition of a shot template"""
    template_type: ShotTemplate
    name_cn: str
    name_en: str
    short_code: str
    category: str  # establishing, focus, dynamic
    description_cn: str
    typical_use_cn: str
    camera: CameraSettings
    composition: CompositionSettings
    slot_weights: SlotWeights
    special_requirements: List[str]
    prompt_keywords: List[str]


# Template Definitions
SHOT_TEMPLATES: Dict[ShotTemplate, TemplateDefinition] = {

    # ==================== Establishing Category ====================

    ShotTemplate.T1_ESTABLISHING_WIDE: TemplateDefinition(
        template_type=ShotTemplate.T1_ESTABLISHING_WIDE,
        name_cn="全景俯瞰",
        name_en="Establishing Wide",
        short_code="EST-W",
        category="establishing",
        description_cn="上帝视角,交代环境,建立空间感",
        typical_use_cn="开场建立、场景转换、时间流逝",
        camera=CameraSettings(
            distance="extreme_wide",
            vertical_angle=-45,
            horizontal_angle=0,
            focal_length=24
        ),
        composition=CompositionSettings(
            subject_scale=0.15,
            horizon_position="upper_third",
            depth_layers=3,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.5,
            scene=0.9,
            props=0.3,
            style=0.4
        ),
        special_requirements=[],
        prompt_keywords=[
            "establishing shot", "bird's eye view", "overhead angle",
            "wide landscape", "environmental context", "aerial perspective"
        ]
    ),

    ShotTemplate.T2_ENVIRONMENT_MEDIUM: TemplateDefinition(
        template_type=ShotTemplate.T2_ENVIRONMENT_MEDIUM,
        name_cn="环境中景",
        name_en="Medium Wide / Environment Medium",
        short_code="ENV-M",
        category="establishing",
        description_cn="人景平衡,角色与环境同等重要",
        typical_use_cn="角色入场、环境互动、群像展示",
        camera=CameraSettings(
            distance="wide",
            vertical_angle=0,
            horizontal_angle=10,
            focal_length=35
        ),
        composition=CompositionSettings(
            subject_scale=0.35,
            horizon_position="middle",
            depth_layers=2,
            rule_of_thirds=True,
            subject_position="left_third",
            foreground_blur=False,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.7,
            scene=0.7,
            props=0.5,
            style=0.4
        ),
        special_requirements=[],
        prompt_keywords=[
            "medium wide shot", "full body", "environmental context",
            "character in scene", "establishing character"
        ]
    ),

    ShotTemplate.T3_FRAMED_SHOT: TemplateDefinition(
        template_type=ShotTemplate.T3_FRAMED_SHOT,
        name_cn="框中框",
        name_en="Framed Shot",
        short_code="FRM",
        category="establishing",
        description_cn="空间层次感,通过门窗等元素形成画中画效果",
        typical_use_cn="空间转场、偷窥视角、增加层次",
        camera=CameraSettings(
            distance="medium_wide",
            vertical_angle=0,
            horizontal_angle=0,
            focal_length=50
        ),
        composition=CompositionSettings(
            subject_scale=0.3,
            horizon_position="middle",
            depth_layers=3,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=True,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.7,
            scene=0.8,
            props=0.8,
            style=0.4
        ),
        special_requirements=["frame_element: door/window/arch/foliage"],
        prompt_keywords=[
            "framed composition", "frame within frame", "doorway shot",
            "window frame", "through the door", "layered depth",
            "foreground framing element"
        ]
    ),

    # ==================== Focus Category ====================

    ShotTemplate.T4_STANDARD_MEDIUM: TemplateDefinition(
        template_type=ShotTemplate.T4_STANDARD_MEDIUM,
        name_cn="标准中景",
        name_en="Standard Medium Shot",
        short_code="STD-M",
        category="focus",
        description_cn="叙事主力,腰部以上构图",
        typical_use_cn="对话、独白、常规叙事",
        camera=CameraSettings(
            distance="medium",
            vertical_angle=0,
            horizontal_angle=5,
            focal_length=50
        ),
        composition=CompositionSettings(
            subject_scale=0.55,
            horizon_position="middle",
            depth_layers=2,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=True
        ),
        slot_weights=SlotWeights(
            character=0.85,
            scene=0.5,
            props=0.6,
            style=0.4
        ),
        special_requirements=["framing: waist_up", "headroom: 10%"],
        prompt_keywords=[
            "medium shot", "waist up", "mid shot", "standard framing",
            "conversational distance", "narrative shot"
        ]
    ),

    ShotTemplate.T5_OVER_SHOULDER: TemplateDefinition(
        template_type=ShotTemplate.T5_OVER_SHOULDER,
        name_cn="过肩镜头",
        name_en="Over-the-Shoulder Shot",
        short_code="OTS",
        category="focus",
        description_cn="对话场景,前景角色虚化,焦点角色清晰",
        typical_use_cn="双人对话、对峙、访谈",
        camera=CameraSettings(
            distance="medium",
            vertical_angle=3,
            horizontal_angle=25,
            focal_length=50
        ),
        composition=CompositionSettings(
            subject_scale=0.4,
            horizon_position="middle",
            depth_layers=2,
            rule_of_thirds=True,
            subject_position="right_third",
            foreground_blur=True,
            background_blur=True
        ),
        slot_weights=SlotWeights(
            character=0.85,  # Focus character high weight
            scene=0.4,
            props=0.5,
            style=0.4
        ),
        special_requirements=[
            "requires two characters",
            "foreground_character: back_shoulder_visible",
            "foreground_blur: slight",
            "focus_character: face_clear"
        ],
        prompt_keywords=[
            "over the shoulder shot", "OTS", "dialogue framing",
            "two-shot", "conversation", "shoulder in foreground",
            "blurred foreground figure"
        ]
    ),

    ShotTemplate.T6_CLOSEUP: TemplateDefinition(
        template_type=ShotTemplate.T6_CLOSEUP,
        name_cn="特写",
        name_en="Close-up",
        short_code="CU",
        category="focus",
        description_cn="情绪放大,面部或道具特写",
        typical_use_cn="情绪表达、重要道具展示、悬念揭示",
        camera=CameraSettings(
            distance="close",
            vertical_angle=3,
            horizontal_angle=10,
            focal_length=85
        ),
        composition=CompositionSettings(
            subject_scale=0.8,
            horizon_position="middle",
            depth_layers=1,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=True
        ),
        slot_weights=SlotWeights(
            character=0.95,
            scene=0.2,
            props=0.8,
            style=0.3
        ),
        special_requirements=["framing: face/object", "background_blur: heavy"],
        prompt_keywords=[
            "close-up", "closeup shot", "face detail", "emotional closeup",
            "tight framing", "portrait shot", "shallow depth of field",
            "bokeh background"
        ]
    ),

    # ==================== Dynamic Category ====================

    ShotTemplate.T7_LOW_ANGLE: TemplateDefinition(
        template_type=ShotTemplate.T7_LOW_ANGLE,
        name_cn="低角度仰拍",
        name_en="Low Angle Shot",
        short_code="LA",
        category="dynamic",
        description_cn="力量/压迫感,仰视角度",
        typical_use_cn="英雄出场、权威展示、压迫感营造",
        camera=CameraSettings(
            distance="medium",
            vertical_angle=22,
            horizontal_angle=0,
            focal_length=35
        ),
        composition=CompositionSettings(
            subject_scale=0.6,
            horizon_position="lower_third",
            depth_layers=2,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.85,
            scene=0.6,
            props=0.5,
            style=0.4
        ),
        special_requirements=["sky_visible: often", "power_dynamic: subject_dominant"],
        prompt_keywords=[
            "low angle shot", "worm's eye view", "looking up",
            "heroic angle", "power shot", "imposing figure",
            "sky in background"
        ]
    ),

    ShotTemplate.T8_FOLLOWING: TemplateDefinition(
        template_type=ShotTemplate.T8_FOLLOWING,
        name_cn="跟随视角",
        name_en="Following Shot",
        short_code="FOL",
        category="dynamic",
        description_cn="沉浸跟随,从背后拍摄",
        typical_use_cn="角色移动、探索未知、制造悬念",
        camera=CameraSettings(
            distance="medium",
            vertical_angle=8,
            horizontal_angle=0,
            focal_length=35
        ),
        composition=CompositionSettings(
            subject_scale=0.4,
            horizon_position="middle",
            depth_layers=3,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.75,
            scene=0.8,
            props=0.5,
            style=0.4
        ),
        special_requirements=[
            "subject_visibility: back_view",
            "environment_reveal: progressive"
        ],
        prompt_keywords=[
            "following shot", "tracking shot", "from behind",
            "back view", "walking forward", "into the scene",
            "character back", "exploration"
        ]
    ),

    ShotTemplate.T9_POV: TemplateDefinition(
        template_type=ShotTemplate.T9_POV,
        name_cn="主观镜头",
        name_en="POV Shot (Point of View)",
        short_code="POV",
        category="dynamic",
        description_cn="第一人称视角,视角主人不出镜",
        typical_use_cn="发现场景、阅读文件、观察他人",
        camera=CameraSettings(
            distance="medium",
            vertical_angle=0,
            horizontal_angle=0,
            focal_length=40
        ),
        composition=CompositionSettings(
            subject_scale=0.5,
            horizon_position="middle",
            depth_layers=2,
            rule_of_thirds=True,
            subject_position="center",
            foreground_blur=False,
            background_blur=False
        ),
        slot_weights=SlotWeights(
            character=0.3,
            scene=0.85,
            props=0.8,
            style=0.4
        ),
        special_requirements=[
            "pov_owner: specified_character (not visible)",
            "hand_visible: optional",
            "focus_target: scene/other_character/object"
        ],
        prompt_keywords=[
            "POV shot", "point of view", "first person view",
            "subjective camera", "through someone's eyes",
            "hands in frame optional", "looking at"
        ]
    ),
}


def get_template(template_type: ShotTemplate) -> TemplateDefinition:
    """Get template definition by type"""
    return SHOT_TEMPLATES.get(template_type)


def get_template_by_code(short_code: str) -> Optional[TemplateDefinition]:
    """Get template by short code (e.g., 'CU', 'OTS')"""
    for template in SHOT_TEMPLATES.values():
        if template.short_code == short_code:
            return template
    return None


def get_templates_by_category(category: str) -> List[TemplateDefinition]:
    """Get all templates in a category"""
    return [t for t in SHOT_TEMPLATES.values() if t.category == category]


def get_template_choices_cn() -> List[tuple]:
    """Get template choices for Gradio dropdown (Chinese)"""
    choices = []
    for template in SHOT_TEMPLATES.values():
        label = f"{template.short_code} | {template.name_cn} - {template.description_cn}"
        choices.append((label, template.template_type.value))
    return choices


def get_template_summary() -> str:
    """Get a summary of all templates for display"""
    lines = []

    # Group by category
    for category, category_cn in [
        ("establishing", "建立类"),
        ("focus", "聚焦类"),
        ("dynamic", "动势类")
    ]:
        lines.append(f"\n=== {category_cn} ===")
        templates = get_templates_by_category(category)
        for t in templates:
            lines.append(f"  {t.short_code}: {t.name_cn} ({t.name_en})")
            lines.append(f"       {t.description_cn}")
            lines.append(f"       典型用途: {t.typical_use_cn}")

    return "\n".join(lines)


# Template Quick Reference Table
TEMPLATE_QUICK_REF = """
| Template | Code | Distance | V.Angle | Weights (C/S/P/St) |
|----------|------|----------|---------|-------------------|
| T1 Full Wide | EST-W | Extreme | -45 deg | 0.5/0.9/0.3/0.4 |
| T2 Env Medium | ENV-M | Wide | 0 deg | 0.7/0.7/0.5/0.4 |
| T3 Framed | FRM | Med-Wide | 0 deg | 0.7/0.8/0.8/0.4 |
| T4 Standard | STD-M | Medium | 0 deg | 0.85/0.5/0.6/0.4 |
| T5 OTS | OTS | Medium | 0-5 deg | 0.85/0.4/0.5/0.4 |
| T6 Closeup | CU | Close | 0-5 deg | 0.95/0.2/0.8/0.3 |
| T7 Low Angle | LA | Medium | +15-30 | 0.85/0.6/0.5/0.4 |
| T8 Following | FOL | Medium | +5-10 | 0.75/0.8/0.5/0.4 |
| T9 POV | POV | Variable | Variable | 0.3/0.85/0.8/0.4 |
"""


if __name__ == "__main__":
    print("=== Shot Template Summary ===")
    print(get_template_summary())
    print("\n" + TEMPLATE_QUICK_REF)
