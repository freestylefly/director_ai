"""
AI Storyboard Pro - Prompt Generator
Generates image prompts based on shot templates and references
"""

from typing import List, Optional, Dict
from models import (
    Shot, Character, Scene, Prop, StyleConfig, StoryboardProject,
    ShotTemplate, SlotWeights, StandardShotPrompt
)
from templates import get_template, TemplateDefinition


def build_camera_prompt(template: TemplateDefinition, shot: Shot) -> str:
    """Build camera description part of prompt"""
    camera = shot.camera if shot.camera else template.camera

    distance_map = {
        "extreme_wide": "extreme wide shot",
        "wide": "wide shot",
        "medium_wide": "medium wide shot",
        "medium": "medium shot",
        "close": "close-up shot"
    }

    parts = [distance_map.get(camera.distance, "medium shot")]

    # Add angle description
    if camera.vertical_angle < -20:
        parts.append("high angle overhead view")
    elif camera.vertical_angle < -5:
        parts.append("high angle shot")
    elif camera.vertical_angle > 20:
        parts.append("low angle heroic shot")
    elif camera.vertical_angle > 5:
        parts.append("slightly low angle")

    if abs(camera.horizontal_angle) > 15:
        parts.append("angled perspective")

    # Focal length description
    if camera.focal_length <= 24:
        parts.append("wide lens perspective")
    elif camera.focal_length >= 85:
        parts.append("telephoto compression, shallow depth of field")

    return ", ".join(parts)


def build_character_prompt(
    characters: List[Character],
    shot: Shot,
    template: TemplateDefinition
) -> str:
    """Build character description part of prompt with consistency"""
    if not characters:
        return ""

    char_descs = []

    for i, char in enumerate(characters):
        if char.id not in shot.characters_in_shot:
            continue

        # Use new consistency prompt method for detailed appearance
        consistency_prompt = char.get_consistency_prompt()
        if consistency_prompt and consistency_prompt != f"[{char.name}: ]":
            desc_parts = [consistency_prompt]
        else:
            # Fallback to basic description
            desc_parts = [char.name]
            if char.description:
                desc_parts.append(f"({char.description})")

        # For OTS shots, specify foreground/background
        if template.template_type == ShotTemplate.T5_OVER_SHOULDER:
            if i == 0:
                desc_parts.append("in foreground (back/shoulder visible, slightly blurred)")
            else:
                desc_parts.append("in focus, facing camera")

        # For POV shots, character might only have hands visible
        if template.template_type == ShotTemplate.T9_POV:
            desc_parts.append("(hands may be visible in frame)")

        # For following shots
        if template.template_type == ShotTemplate.T8_FOLLOWING:
            desc_parts.append("seen from behind, back view")

        char_descs.append(" ".join(desc_parts))

    return ", ".join(char_descs)


def build_scene_prompt(scene: Optional[Scene], template: TemplateDefinition) -> str:
    """Build scene description part of prompt"""
    if not scene:
        return ""

    parts = []

    if scene.name:
        parts.append(f"in {scene.name}")

    if scene.description:
        parts.append(scene.description[:150])

    if scene.light_direction:
        parts.append(f"lighting from {scene.light_direction}")

    if scene.color_temperature:
        temp_map = {
            "warm": "warm golden tones",
            "cool": "cool blue tones",
            "neutral": "neutral balanced lighting"
        }
        parts.append(temp_map.get(scene.color_temperature, scene.color_temperature))

    return ", ".join(parts)


def build_props_prompt(
    props: List[Prop],
    shot: Shot,
    template: TemplateDefinition
) -> str:
    """Build props description part of prompt"""
    if not props or not shot.props_in_shot:
        return ""

    prop_descs = []

    for prop in props:
        if prop.id not in shot.props_in_shot:
            continue

        desc = prop.name
        if prop.material:
            desc += f" ({prop.material})"
        if prop.size_reference:
            desc += f", {prop.size_reference}"

        # For closeup of props
        if template.template_type == ShotTemplate.T6_CLOSEUP and len(shot.props_in_shot) > 0:
            desc = f"focus on {desc}, detailed view"

        prop_descs.append(desc)

    if prop_descs:
        return "featuring " + ", ".join(prop_descs)
    return ""


def build_style_prompt(style: StyleConfig) -> str:
    """Build style description part of prompt"""
    parts = []

    # 中文风格名称映射（优先使用 preset_name 对应的中文风格）
    preset_style_map = {
        "Cartoon2D": "2D cartoon style, flat colors, clean lines, cel shading",
        "Anime": "anime style, vibrant colors, cel shading, Japanese animation",
        "Comic": "comic book style, bold outlines, halftone dots",
        "Watercolor": "watercolor painting style, soft edges, flowing colors",
        "Realistic3D": "3D realistic render, photorealistic 3D, high detail",
        "Cinematic": "cinematic style, film grain, dramatic lighting, movie quality",
        "GameCG": "game CG style, high quality 3D render, video game graphics",
        "Cyberpunk": "cyberpunk style, neon lights, futuristic, sci-fi atmosphere",
    }

    # 如果有 preset_name，优先使用对应的风格描述
    if style.preset_name and style.preset_name in preset_style_map:
        parts.append(preset_style_map[style.preset_name])
    else:
        # Render type (fallback)
        render_map = {
            "realistic": "photorealistic rendering",
            "illustration": "digital illustration style",
            "3d_render": "3D rendered",
            "watercolor": "watercolor painting style",
            "anime": "anime style",
            "comic": "comic book style",
            "cartoon": "2D cartoon style, flat colors, clean lines"
        }
        parts.append(render_map.get(style.render_type, style.render_type))

    # Color tone
    tone_map = {
        "warm": "warm color palette",
        "cool": "cool color palette",
        "high_saturation": "vibrant saturated colors",
        "low_saturation": "muted desaturated colors",
        "neutral": "balanced natural colors"
    }
    if style.color_tone in tone_map:
        parts.append(tone_map[style.color_tone])

    # Lighting style
    light_map = {
        "natural": "natural lighting",
        "studio": "studio lighting setup",
        "neon": "neon lighting, cyberpunk atmosphere",
        "backlit": "dramatic backlighting, rim light",
        "cinematic": "cinematic lighting, film-like"
    }
    if style.lighting_style in light_map:
        parts.append(light_map[style.lighting_style])

    # Texture
    texture_map = {
        "film_grain": "film grain texture, analog look",
        "digital_clean": "clean digital render",
        "noise": "subtle noise texture"
    }
    if style.texture in texture_map:
        parts.append(texture_map[style.texture])

    # Custom description
    if style.custom_description:
        parts.append(style.custom_description[:100])

    return ", ".join(parts)


def build_action_prompt(shot: Shot) -> str:
    """Build action/dialogue context prompt"""
    parts = []

    if shot.action:
        parts.append(shot.action)

    if shot.dialogue:
        # Extract emotional context from dialogue
        parts.append(f"during dialogue: '{shot.dialogue[:80]}...'")

    if shot.description:
        parts.append(shot.description)

    return ", ".join(parts)


def build_composition_prompt(template: TemplateDefinition, shot: Shot) -> str:
    """Build composition guidance prompt"""
    comp = shot.composition if shot.composition else template.composition
    parts = []

    # Subject position
    position_map = {
        "left_third": "subject positioned left third",
        "right_third": "subject positioned right third",
        "center": "centered composition"
    }
    if comp.subject_position in position_map and comp.rule_of_thirds:
        parts.append(position_map[comp.subject_position])

    # Blur effects
    if comp.foreground_blur:
        parts.append("foreground blur")
    if comp.background_blur:
        parts.append("background bokeh")

    # Depth
    if comp.depth_layers >= 3:
        parts.append("layered depth, foreground-midground-background")

    return ", ".join(parts)


def generate_shot_prompt(
    shot: Shot,
    project: StoryboardProject,
    include_technical: bool = True
) -> str:
    """
    Generate complete prompt for a single shot.
    风格放在开头，确保每张图片的提示词都包含统一风格。

    Args:
        shot: The shot to generate prompt for
        project: The project containing all references
        include_technical: Whether to include technical parameters

    Returns:
        Complete prompt string
    """
    template = get_template(shot.template)
    if not template:
        template = get_template(ShotTemplate.T4_STANDARD_MEDIUM)

    prompt_parts = []

    # 1. Style (放在最前面，作为整体基调)
    style_prompt = build_style_prompt(project.style)
    if style_prompt:
        prompt_parts.append(style_prompt)

    # 2. Camera/Shot type
    camera_prompt = build_camera_prompt(template, shot)
    if camera_prompt:
        prompt_parts.append(camera_prompt)

    # 3. Template-specific keywords
    if template.prompt_keywords:
        prompt_parts.append(template.prompt_keywords[0])

    # 4. Character description
    shot_characters = [
        project.get_character_by_id(cid)
        for cid in shot.characters_in_shot
    ]
    shot_characters = [c for c in shot_characters if c]
    char_prompt = build_character_prompt(shot_characters, shot, template)
    if char_prompt:
        prompt_parts.append(char_prompt)

    # 5. Action/Description
    action_prompt = build_action_prompt(shot)
    if action_prompt:
        prompt_parts.append(action_prompt)

    # 6. Scene description
    scene = project.get_scene_by_id(shot.scene_id)
    scene_prompt = build_scene_prompt(scene, template)
    if scene_prompt:
        prompt_parts.append(scene_prompt)

    # 7. Props
    shot_props = [
        project.get_prop_by_id(pid)
        for pid in shot.props_in_shot
    ]
    shot_props = [p for p in shot_props if p]
    props_prompt = build_props_prompt(shot_props, shot, template)
    if props_prompt:
        prompt_parts.append(props_prompt)

    # 8. Composition
    comp_prompt = build_composition_prompt(template, shot)
    if comp_prompt:
        prompt_parts.append(comp_prompt)

    # 9. Technical parameters
    if include_technical:
        prompt_parts.append("8K resolution, highly detailed")

    # Join all parts
    full_prompt = ", ".join(prompt_parts)

    return full_prompt


def generate_negative_prompt(template: TemplateDefinition) -> str:
    """Generate negative prompt based on template type"""
    base_negative = [
        "blurry", "low quality", "distorted", "deformed",
        "bad anatomy", "wrong proportions", "extra limbs",
        "cropped", "watermark", "signature", "text"
    ]

    # Template-specific negatives
    if template.template_type in [ShotTemplate.T6_CLOSEUP]:
        base_negative.extend(["too far", "full body", "wide shot"])

    if template.template_type == ShotTemplate.T1_ESTABLISHING_WIDE:
        base_negative.extend(["too close", "face focus", "portrait"])

    if template.template_type == ShotTemplate.T9_POV:
        base_negative.extend(["face of viewer visible", "self visible"])

    return ", ".join(base_negative)


def suggest_next_shot_template(
    current_template: ShotTemplate,
    narrative_context: str = ""
) -> List[ShotTemplate]:
    """
    Suggest next shot templates based on cinematic grammar.

    Returns list of suggested templates in order of preference.
    """
    suggestions = {
        ShotTemplate.T1_ESTABLISHING_WIDE: [
            ShotTemplate.T2_ENVIRONMENT_MEDIUM,
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T8_FOLLOWING
        ],
        ShotTemplate.T2_ENVIRONMENT_MEDIUM: [
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T3_FRAMED_SHOT,
            ShotTemplate.T6_CLOSEUP
        ],
        ShotTemplate.T3_FRAMED_SHOT: [
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T2_ENVIRONMENT_MEDIUM,
            ShotTemplate.T9_POV
        ],
        ShotTemplate.T4_STANDARD_MEDIUM: [
            ShotTemplate.T5_OVER_SHOULDER,
            ShotTemplate.T6_CLOSEUP,
            ShotTemplate.T7_LOW_ANGLE
        ],
        ShotTemplate.T5_OVER_SHOULDER: [
            ShotTemplate.T5_OVER_SHOULDER,  # Reverse shot
            ShotTemplate.T6_CLOSEUP,
            ShotTemplate.T4_STANDARD_MEDIUM
        ],
        ShotTemplate.T6_CLOSEUP: [
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T5_OVER_SHOULDER,
            ShotTemplate.T9_POV
        ],
        ShotTemplate.T7_LOW_ANGLE: [
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T6_CLOSEUP,
            ShotTemplate.T2_ENVIRONMENT_MEDIUM
        ],
        ShotTemplate.T8_FOLLOWING: [
            ShotTemplate.T9_POV,
            ShotTemplate.T2_ENVIRONMENT_MEDIUM,
            ShotTemplate.T3_FRAMED_SHOT
        ],
        ShotTemplate.T9_POV: [
            ShotTemplate.T6_CLOSEUP,
            ShotTemplate.T4_STANDARD_MEDIUM,
            ShotTemplate.T5_OVER_SHOULDER
        ],
    }

    return suggestions.get(current_template, [ShotTemplate.T4_STANDARD_MEDIUM])


# ==================== 标准提示语生成 ====================

# 景别映射
SHOT_TYPE_MAP = {
    ShotTemplate.T1_ESTABLISHING_WIDE: "远景/全景",
    ShotTemplate.T2_ENVIRONMENT_MEDIUM: "全景/中全景",
    ShotTemplate.T3_FRAMED_SHOT: "中景 (框式)",
    ShotTemplate.T4_STANDARD_MEDIUM: "中景",
    ShotTemplate.T5_OVER_SHOULDER: "中近景 (过肩)",
    ShotTemplate.T6_CLOSEUP: "特写/近景",
    ShotTemplate.T7_LOW_ANGLE: "中景 (仰拍)",
    ShotTemplate.T8_FOLLOWING: "中全景 (跟拍)",
    ShotTemplate.T9_POV: "主观视角"
}

# 运镜映射
CAMERA_MOVEMENT_MAP = {
    ShotTemplate.T1_ESTABLISHING_WIDE: "固定/缓慢横摇",
    ShotTemplate.T2_ENVIRONMENT_MEDIUM: "固定/轻微推拉",
    ShotTemplate.T3_FRAMED_SHOT: "固定",
    ShotTemplate.T4_STANDARD_MEDIUM: "固定/轻微推",
    ShotTemplate.T5_OVER_SHOULDER: "固定/轻微横移",
    ShotTemplate.T6_CLOSEUP: "固定/缓推",
    ShotTemplate.T7_LOW_ANGLE: "固定/缓慢仰升",
    ShotTemplate.T8_FOLLOWING: "跟移/稳定器跟拍",
    ShotTemplate.T9_POV: "手持/主观移动"
}

# 视角映射
ANGLE_MAP = {
    ShotTemplate.T1_ESTABLISHING_WIDE: "高角度俯拍 (上帝视角)",
    ShotTemplate.T2_ENVIRONMENT_MEDIUM: "平视/微俯",
    ShotTemplate.T3_FRAMED_SHOT: "平视",
    ShotTemplate.T4_STANDARD_MEDIUM: "平视",
    ShotTemplate.T5_OVER_SHOULDER: "平视/微仰",
    ShotTemplate.T6_CLOSEUP: "平视/微仰",
    ShotTemplate.T7_LOW_ANGLE: "低角度仰拍",
    ShotTemplate.T8_FOLLOWING: "中低角度/略高",
    ShotTemplate.T9_POV: "主观第一人称"
}

# 构图映射
COMPOSITION_MAP = {
    ShotTemplate.T1_ESTABLISHING_WIDE: "对称构图/三分法/引导线",
    ShotTemplate.T2_ENVIRONMENT_MEDIUM: "三分法/人景均衡",
    ShotTemplate.T3_FRAMED_SHOT: "框式构图/层次构图",
    ShotTemplate.T4_STANDARD_MEDIUM: "三分法/中心构图",
    ShotTemplate.T5_OVER_SHOULDER: "三分法/前景虚化",
    ShotTemplate.T6_CLOSEUP: "中心构图/三分法",
    ShotTemplate.T7_LOW_ANGLE: "对角线/三分法/仰角透视",
    ShotTemplate.T8_FOLLOWING: "中心构图/纵深引导",
    ShotTemplate.T9_POV: "主观视线/焦点构图"
}

# 动态控制映射
DYNAMIC_CONTROL_MAP = {
    ShotTemplate.T1_ESTABLISHING_WIDE: "静态/轻微动态",
    ShotTemplate.T2_ENVIRONMENT_MEDIUM: "轻微动态",
    ShotTemplate.T3_FRAMED_SHOT: "静态",
    ShotTemplate.T4_STANDARD_MEDIUM: "轻微动态/中等动态",
    ShotTemplate.T5_OVER_SHOULDER: "轻微动态",
    ShotTemplate.T6_CLOSEUP: "静态/微表情动态",
    ShotTemplate.T7_LOW_ANGLE: "中等动态/静态威压",
    ShotTemplate.T8_FOLLOWING: "中等动态/动态",
    ShotTemplate.T9_POV: "动态/主观运动"
}


def generate_atmosphere(shot: Shot, scene: Optional[Scene], style: StyleConfig) -> str:
    """根据场景和风格生成氛围描述"""
    atmosphere_parts = []

    # 根据色调
    tone_atmosphere = {
        "warm": "温暖",
        "cool": "冷峻",
        "high_saturation": "鲜艳活跃",
        "low_saturation": "沉稳内敛",
        "neutral": "平实自然"
    }
    if style.color_tone in tone_atmosphere:
        atmosphere_parts.append(tone_atmosphere[style.color_tone])

    # 根据灯光风格
    light_atmosphere = {
        "natural": "自然舒适",
        "studio": "专业精致",
        "neon": "赛博朋克/未来感",
        "backlit": "神秘/戏剧性",
        "cinematic": "电影质感"
    }
    if style.lighting_style in light_atmosphere:
        atmosphere_parts.append(light_atmosphere[style.lighting_style])

    # 根据场景色温
    if scene and scene.color_temperature:
        temp_atmosphere = {
            "warm": "温馨",
            "cool": "清冷",
            "neutral": "中性"
        }
        if scene.color_temperature in temp_atmosphere:
            atmosphere_parts.append(temp_atmosphere[scene.color_temperature])

    return "/".join(atmosphere_parts) if atmosphere_parts else "自然"


def generate_environment_description(scene: Optional[Scene], shot: Shot) -> str:
    """生成环境描述"""
    if not scene:
        return "未指定场景"

    env_parts = []

    if scene.name:
        env_parts.append(scene.name)

    if scene.description:
        env_parts.append(scene.description[:60])

    if scene.light_direction:
        env_parts.append(f"光源: {scene.light_direction}")

    return ", ".join(env_parts) if env_parts else "未指定"


def generate_special_technique(template: TemplateDefinition, shot: Shot) -> str:
    """根据模板生成特殊拍摄手法"""
    techniques = []

    # 根据模板类型
    if template.template_type == ShotTemplate.T1_ESTABLISHING_WIDE:
        techniques.append("航拍/大范围固定机位")
    elif template.template_type == ShotTemplate.T3_FRAMED_SHOT:
        techniques.append("利用门窗/建筑元素形成画框")
    elif template.template_type == ShotTemplate.T5_OVER_SHOULDER:
        techniques.append("浅景深虚化前景")
    elif template.template_type == ShotTemplate.T6_CLOSEUP:
        techniques.append("浅景深/背景虚化")
    elif template.template_type == ShotTemplate.T7_LOW_ANGLE:
        techniques.append("广角镜头增强透视")
    elif template.template_type == ShotTemplate.T8_FOLLOWING:
        techniques.append("稳定器/斯坦尼康跟拍")
    elif template.template_type == ShotTemplate.T9_POV:
        techniques.append("手持拍摄模拟主观")

    # 根据构图设置
    if shot.composition.foreground_blur:
        techniques.append("前景虚化")
    if shot.composition.background_blur:
        techniques.append("背景虚化")
    if shot.composition.depth_layers >= 3:
        techniques.append("多层景深")

    return ", ".join(techniques) if techniques else "标准拍摄"


def generate_style_consistency(style: StyleConfig) -> str:
    """生成风格统一描述"""
    parts = []

    # 渲染类型
    render_cn = {
        "realistic": "写实风格",
        "illustration": "插画风格",
        "3d_render": "3D渲染",
        "watercolor": "水彩风格",
        "anime": "动漫风格",
        "comic": "漫画风格"
    }
    if style.render_type in render_cn:
        parts.append(render_cn[style.render_type])

    # 色调
    tone_cn = {
        "warm": "暖色调",
        "cool": "冷色调",
        "high_saturation": "高饱和度",
        "low_saturation": "低饱和度",
        "neutral": "中性色调"
    }
    if style.color_tone in tone_cn:
        parts.append(tone_cn[style.color_tone])

    # 灯光
    light_cn = {
        "natural": "自然光",
        "studio": "影棚灯光",
        "neon": "霓虹灯光",
        "backlit": "逆光",
        "cinematic": "电影灯光"
    }
    if style.lighting_style in light_cn:
        parts.append(light_cn[style.lighting_style])

    # 质感
    texture_cn = {
        "film_grain": "胶片颗粒感",
        "digital_clean": "数码清晰",
        "noise": "轻微噪点"
    }
    if style.texture in texture_cn:
        parts.append(texture_cn[style.texture])

    return ", ".join(parts) if parts else "标准风格"


def generate_subject(shot: Shot, project: StoryboardProject) -> str:
    """生成主体描述"""
    subjects = []

    # 获取角色名称
    for char_id in shot.characters_in_shot:
        char = project.get_character_by_id(char_id)
        if char:
            subjects.append(char.name)

    # 如果有道具
    for prop_id in shot.props_in_shot:
        prop = project.get_prop_by_id(prop_id)
        if prop:
            subjects.append(prop.name)

    if subjects:
        return "、".join(subjects)
    return "环境/空镜"


def generate_shot_type_detail(shot: Shot, template: TemplateDefinition) -> str:
    """生成详细的景别描述（结合动作描述）"""
    base_type = SHOT_TYPE_MAP.get(shot.template, "中景")

    if shot.description:
        return f"{base_type} - {shot.description}"
    return base_type


def generate_angle_detail(shot: Shot, template: TemplateDefinition) -> str:
    """生成详细的视角描述"""
    base_angle = ANGLE_MAP.get(shot.template, "平视")

    # 根据模板添加详细信息
    details = []
    details.append(base_angle)

    if shot.action:
        details.append(shot.action)

    return "，".join(details) if len(details) > 1 else details[0]


def generate_dynamic_control_detail(shot: Shot, template: TemplateDefinition) -> str:
    """生成详细的动态控制描述"""
    base_dynamic = DYNAMIC_CONTROL_MAP.get(shot.template, "轻微动态")

    # 如果有具体动作描述，使用它
    if shot.action:
        return f"{shot.action}"
    elif shot.description:
        return f"{base_dynamic} - {shot.description[:50]}"
    return base_dynamic


def generate_standard_shot_prompt(
    shot: Shot,
    project: StoryboardProject
) -> StandardShotPrompt:
    """
    为单个分镜生成标准提示语。

    Args:
        shot: 分镜对象
        project: 项目对象，包含所有参考资源

    Returns:
        StandardShotPrompt: 标准提示语对象
    """
    template = get_template(shot.template)
    if not template:
        template = get_template(ShotTemplate.T4_STANDARD_MEDIUM)

    scene = project.get_scene_by_id(shot.scene_id)

    return StandardShotPrompt(
        subject=generate_subject(shot, project),
        shot_type=generate_shot_type_detail(shot, template),
        atmosphere=generate_atmosphere(shot, scene, project.style),
        environment=generate_environment_description(scene, shot),
        camera_movement=CAMERA_MOVEMENT_MAP.get(shot.template, "固定"),
        angle=generate_angle_detail(shot, template),
        special_technique=generate_special_technique(template, shot),
        composition=COMPOSITION_MAP.get(shot.template, "三分法"),
        style_consistency=generate_style_consistency(project.style),
        dynamic_control=generate_dynamic_control_detail(shot, template)
    )


def generate_standard_prompt_text(
    shot: Shot,
    project: StoryboardProject
) -> str:
    """
    生成格式化的标准提示语文本。

    Args:
        shot: 分镜对象
        project: 项目对象

    Returns:
        str: 格式化的提示语文本
    """
    std_prompt = generate_standard_shot_prompt(shot, project)
    return std_prompt.to_formatted_string()


if __name__ == "__main__":
    # Test prompt generation
    from models import Character, Scene, Prop, StyleConfig, Shot, StoryboardProject

    # Create test project
    project = StoryboardProject(name="Test Project")

    # Add character
    char = Character(
        name="Zhang San",
        description="Young professional man, dark suit, confident posture"
    )
    project.characters.append(char)

    # Add scene
    scene = Scene(
        name="Modern Office",
        description="Open plan office with floor-to-ceiling windows, afternoon light",
        light_direction="left side windows",
        color_temperature="warm"
    )
    project.scenes.append(scene)

    # Add prop
    prop = Prop(
        name="Mysterious Envelope",
        material="aged paper",
        size_reference="palm-sized"
    )
    project.props.append(prop)

    # Configure style
    project.style = StyleConfig(
        render_type="realistic",
        color_tone="warm",
        lighting_style="cinematic",
        texture="film_grain"
    )

    # Create shot
    shot = Shot(
        shot_number=1,
        template=ShotTemplate.T4_STANDARD_MEDIUM,
        description="Zhang San discovers the envelope on his desk",
        characters_in_shot=[char.id],
        scene_id=scene.id,
        props_in_shot=[prop.id],
        action="reaching for envelope with curious expression"
    )

    # Generate prompt
    prompt = generate_shot_prompt(shot, project)
    print("Generated Prompt:")
    print("-" * 50)
    print(prompt)

    # Generate standard prompt
    print("\n" + "=" * 50)
    print("Standard Shot Prompt:")
    print("-" * 50)
    std_prompt_text = generate_standard_prompt_text(shot, project)
    print(std_prompt_text)

    # Test different template types
    print("\n" + "=" * 50)
    print("Testing different templates:")
    print("-" * 50)

    for template_type in [ShotTemplate.T1_ESTABLISHING_WIDE, ShotTemplate.T6_CLOSEUP, ShotTemplate.T8_FOLLOWING]:
        shot.template = template_type
        std_prompt = generate_standard_shot_prompt(shot, project)
        print(f"\n[{template_type.value}]")
        print(std_prompt.to_formatted_string())


# ==================== LLM 调用模板 ====================

# LLM 生成分镜的提示词模板
LLM_STORYBOARD_TEMPLATE = """
你是一个专业的AI分镜师，请根据用户提供的故事大纲生成完整的分镜脚本。

## 输出格式要求

请严格按照以下JSON格式输出：

```json
{
  "project": {
    "name": "项目名称",
    "style": "风格名称",
    "aspect_ratio": "16:9"
  },
  "characters": [
    {
      "name": "角色名",
      "description": "详细的角色外貌描述，包含：体型、面部特征、发型发色、服装配饰、整体风格。描述要具体到可以直接用于AI绘图，60-100字"
    }
  ],
  "scenes": [
    {
      "name": "场景名",
      "description": "详细的场景描述，包含：地点类型、空间布局、光线氛围、色调风格、关键道具、环境细节。描述要具体到可以直接用于AI绘图，80-120字"
    }
  ],
  "shots": [
    {
      "template": "景别类型",
      "description": "镜头内容描述",
      "characters": ["出场角色名"],
      "scene": "场景名",
      "image_prompt": "图片生成提示词",
      "video_prompt": "视频生成提示词（含运镜）"
    }
  ]
}
```

## 可用的风格选项
- "2D卡通": 2D cartoon style, flat colors, clean lines, cel shading
- "3D卡通": 3D cartoon style, stylized 3D render, Pixar style
- "动漫风": anime style, vibrant colors, cel shading, Japanese animation
- "漫画风": comic book style, bold outlines, halftone dots
- "水彩画": watercolor painting style, soft edges, flowing colors
- "3D写实": 3D realistic render, photorealistic 3D, high detail
- "电影感": cinematic style, film grain, dramatic lighting, movie quality
- "游戏CG": game CG style, high quality 3D render, video game graphics
- "赛博朋克": cyberpunk style, neon lights, futuristic, sci-fi atmosphere
- "真人摄影": photorealistic, professional photography, real life

## 可用的景别类型
- "全景": 展示整体环境，建立空间感
- "中景": 展示人物半身和部分环境
- "特写": 聚焦面部表情或关键细节
- "过肩": 对话场景，从一个角色肩膀后看另一角色
- "低角度": 仰拍，增强角色气势
- "跟随": 跟随角色移动的动态镜头

## 图片提示词结构（image_prompt）
风格在前，按以下顺序组织：
1. 风格描述（必须放在最前面）
2. 景别和角度
3. 角色描述（含服装、动作、表情）
4. 场景描述（含氛围、光线）
5. 画质关键词

示例：
"2D cartoon style, flat colors, clean lines, cel shading, medium shot, cute chubby mascot horse with big sparkling eyes wearing red vest, happily waving at camera, festive Chinese New Year street with red lanterns, warm golden lighting, 8K resolution, highly detailed"

## 视频提示词结构（video_prompt）
基于图片提示词，添加动态和运镜描述：
1. 风格描述
2. 运镜类型（static/slow zoom in/slow zoom out/pan left-right/tracking shot）
3. 角色动作描述
4. 环境动态描述

示例：
"2D cartoon style, slow zoom in, cute mascot horse waving happily, ears twitching, lanterns swaying gently in breeze, festive atmosphere"

## 注意事项
1. 每个角色描述必须在每张图片提示词中保持一致
2. 风格关键词必须放在提示词最前面
3. 视频提示词要描述具体的动作和运镜
4. 7个镜头左右为宜，遵循叙事节奏
"""

# LLM 生成单张图片提示词的模板
LLM_IMAGE_PROMPT_TEMPLATE = """
请为以下镜头生成图片提示词。

## 项目风格
{style}

## 镜头信息
- 景别: {shot_type}
- 角色: {characters}
- 场景: {scene}
- 动作/描述: {description}

## 输出格式
请按以下结构输出提示词（英文）：

1. 风格描述（放在最前面）: {style_english}
2. 景别和角度: {shot_type} shot
3. 角色描述: [角色外貌、服装、动作、表情]
4. 场景描述: [环境、氛围、光线]
5. 画质: 8K resolution, highly detailed

示例输出：
"{style_english}, medium shot, [角色描述], [动作], [场景描述], warm lighting, 8K resolution, highly detailed"
"""

# LLM 生成视频提示词的模板
LLM_VIDEO_PROMPT_TEMPLATE = """
请基于以下图片提示词生成视频提示词。

## 原始图片提示词
{image_prompt}

## 期望的运镜效果
{camera_movement}

## 可用的运镜类型
- "静止": static shot
- "缓慢推进": slow zoom in, dolly in
- "缓慢拉远": slow zoom out, dolly out
- "左右平移": horizontal pan, tracking shot
- "跟随主体": follow shot, tracking the subject

## 输出格式
请生成简洁的视频提示词，包含：
1. 风格描述（保持与图片一致）
2. 运镜描述
3. 主要动作描述（角色做什么动作）
4. 环境动态描述（有什么在动）

示例输出：
"2D cartoon style, slow zoom in, mascot horse waving happily with sparkling eyes, ears twitching cutely, red lanterns swaying gently, festive atmosphere"
"""


def generate_llm_storyboard_prompt(story_idea: str, style: str = "2D卡通") -> str:
    """
    生成用于 LLM 调用的分镜生成提示词

    Args:
        story_idea: 用户的故事创意
        style: 期望的风格

    Returns:
        完整的 LLM 提示词
    """
    return f"""{LLM_STORYBOARD_TEMPLATE}

---

## 用户的故事创意
{story_idea}

## 期望的风格
{style}

请根据以上信息生成完整的分镜脚本JSON。确保：
1. 每个角色描述都包含"{style}"风格关键词
2. 每个场景描述都包含"{style}"风格关键词
3. 每个镜头的 image_prompt 都以风格描述开头
4. 每个镜头的 video_prompt 都包含运镜描述
"""


def generate_llm_image_prompt(
    shot: Shot,
    project: StoryboardProject,
    style_name: str = ""
) -> str:
    """
    生成用于 LLM 优化的图片提示词请求

    Args:
        shot: 镜头对象
        project: 项目对象
        style_name: 风格名称（中文）

    Returns:
        用于 LLM 的提示词请求
    """
    # 获取角色名称
    char_names = []
    for cid in shot.characters_in_shot:
        char = project.get_character_by_id(cid)
        if char:
            char_names.append(f"{char.name}: {char.description}")

    # 获取场景
    scene = project.get_scene_by_id(shot.scene_id)
    scene_desc = scene.description if scene else "未设置"

    # 景别
    shot_type = SHOT_TYPE_MAP.get(shot.template, "中景")

    # 风格映射
    style_map = {
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

    style_english = style_map.get(style_name, style_map.get("电影感"))

    return LLM_IMAGE_PROMPT_TEMPLATE.format(
        style=style_name or "电影感",
        shot_type=shot_type,
        characters="\n".join(char_names) if char_names else "无",
        scene=scene_desc,
        description=shot.description,
        style_english=style_english
    )


def generate_llm_video_prompt(
    image_prompt: str,
    camera_movement: str = "静止"
) -> str:
    """
    生成用于 LLM 优化的视频提示词请求

    Args:
        image_prompt: 原始图片提示词
        camera_movement: 运镜类型

    Returns:
        用于 LLM 的提示词请求
    """
    return LLM_VIDEO_PROMPT_TEMPLATE.format(
        image_prompt=image_prompt,
        camera_movement=camera_movement
    )


# 导出 LLM 模板常量供外部使用
__all__ = [
    'generate_shot_prompt',
    'generate_negative_prompt',
    'suggest_next_shot_template',
    'generate_standard_shot_prompt',
    'generate_standard_prompt_text',
    'LLM_STORYBOARD_TEMPLATE',
    'LLM_IMAGE_PROMPT_TEMPLATE',
    'LLM_VIDEO_PROMPT_TEMPLATE',
    'generate_llm_storyboard_prompt',
    'generate_llm_image_prompt',
    'generate_llm_video_prompt',
]
