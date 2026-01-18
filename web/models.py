"""
AI Storyboard Pro - Data Models
Based on ai_storyboard_pro_framework.md
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime


class AssetGenerationStatus(Enum):
    """Status of asset generation"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_PENDING = "review_pending"


class GeneratedAssetType(Enum):
    """Type of generated asset"""
    CHARACTER = "character"
    SCENE = "scene"
    PROP = "prop"


class ShotTemplate(Enum):
    """9 Shot Template Types"""
    T1_ESTABLISHING_WIDE = "T1_establishing_wide"      # Full landscape overview
    T2_ENVIRONMENT_MEDIUM = "T2_environment_medium"    # Character-environment balance
    T3_FRAMED_SHOT = "T3_framed_shot"                  # Frame within frame
    T4_STANDARD_MEDIUM = "T4_standard_medium"          # Narrative workhorse
    T5_OVER_SHOULDER = "T5_over_shoulder"              # Dialogue scene
    T6_CLOSEUP = "T6_closeup"                          # Emotion emphasis
    T7_LOW_ANGLE = "T7_low_angle"                      # Power/authority
    T8_FOLLOWING = "T8_following"                      # Immersive tracking
    T9_POV = "T9_pov"                                  # First person view


class StyleMode(Enum):
    """Style Configuration Modes"""
    PRESET = "preset"
    REFERENCE_IMAGE = "reference_image"
    CUSTOM_TEXT = "custom_text"


@dataclass
class CameraSettings:
    """Camera parameters for a shot"""
    distance: str = "medium"  # extreme_wide, wide, medium_wide, medium, close
    vertical_angle: float = 0  # Negative=looking down, Positive=looking up
    horizontal_angle: float = 0
    focal_length: int = 50  # mm


@dataclass
class CompositionSettings:
    """Composition parameters for a shot"""
    subject_scale: float = 0.5  # 0.0-1.0 ratio in frame
    horizon_position: str = "middle"  # upper_third, middle, lower_third
    depth_layers: int = 2
    rule_of_thirds: bool = True
    subject_position: str = "center"  # left_third, center, right_third
    foreground_blur: bool = False
    background_blur: bool = False


@dataclass
class SlotWeights:
    """Weight distribution for different reference slots"""
    character: float = 0.8
    scene: float = 0.6
    props: float = 0.5
    style: float = 0.4

    def normalize(self, max_total: float = 2.5) -> 'SlotWeights':
        """Normalize weights to prevent generation chaos"""
        total = self.character + self.scene + self.props + self.style
        if total > max_total:
            scale = max_total / total
            return SlotWeights(
                character=self.character * scale,
                scene=self.scene * scale,
                props=self.props * scale,
                style=self.style * scale
            )
        return self


@dataclass
class CharacterAppearance:
    """Detailed character appearance for consistency"""
    gender: str = ""  # male, female, other
    age: str = ""  # child, teen, young_adult, adult, middle_aged, elderly
    ethnicity: str = ""  # asian, caucasian, african, latino, etc.
    skin_tone: str = ""  # fair, light, medium, tan, dark
    height: str = ""  # short, average, tall
    body_type: str = ""  # slim, average, athletic, muscular, heavy
    # Face
    face_shape: str = ""  # oval, round, square, heart, long
    eye_color: str = ""
    eye_shape: str = ""  # round, almond, narrow, large
    nose: str = ""  # small, average, large, pointed, flat
    lips: str = ""  # thin, average, full
    # Hair
    hair_color: str = ""
    hair_style: str = ""  # short, medium, long, bald, ponytail, bun, etc.
    hair_texture: str = ""  # straight, wavy, curly, coily
    # Distinguishing features
    facial_hair: str = ""  # none, stubble, beard, mustache
    glasses: str = ""  # none, round, square, cat-eye
    scars: str = ""
    tattoos: str = ""
    other_features: str = ""  # moles, freckles, dimples, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gender": self.gender,
            "age": self.age,
            "ethnicity": self.ethnicity,
            "skin_tone": self.skin_tone,
            "height": self.height,
            "body_type": self.body_type,
            "face_shape": self.face_shape,
            "eye_color": self.eye_color,
            "eye_shape": self.eye_shape,
            "nose": self.nose,
            "lips": self.lips,
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "hair_texture": self.hair_texture,
            "facial_hair": self.facial_hair,
            "glasses": self.glasses,
            "scars": self.scars,
            "tattoos": self.tattoos,
            "other_features": self.other_features
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterAppearance':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_prompt_string(self) -> str:
        """Generate consistent appearance prompt string"""
        parts = []
        if self.gender:
            parts.append(self.gender)
        if self.age:
            age_map = {
                "child": "young child",
                "teen": "teenager",
                "young_adult": "young adult in their 20s",
                "adult": "adult in their 30s",
                "middle_aged": "middle-aged person in their 40s-50s",
                "elderly": "elderly person"
            }
            parts.append(age_map.get(self.age, self.age))
        if self.ethnicity:
            parts.append(f"{self.ethnicity} ethnicity")
        if self.skin_tone:
            parts.append(f"{self.skin_tone} skin")
        if self.height:
            parts.append(f"{self.height} height")
        if self.body_type:
            parts.append(f"{self.body_type} build")
        if self.face_shape:
            parts.append(f"{self.face_shape} face")
        if self.eye_color:
            parts.append(f"{self.eye_color} eyes")
        if self.eye_shape:
            parts.append(f"{self.eye_shape} eye shape")
        if self.hair_color and self.hair_style:
            parts.append(f"{self.hair_color} {self.hair_style} hair")
        elif self.hair_color:
            parts.append(f"{self.hair_color} hair")
        elif self.hair_style:
            parts.append(f"{self.hair_style} hair")
        if self.hair_texture:
            parts.append(f"{self.hair_texture} hair texture")
        if self.facial_hair and self.facial_hair != "none":
            parts.append(f"with {self.facial_hair}")
        if self.glasses and self.glasses != "none":
            parts.append(f"wearing {self.glasses} glasses")
        if self.scars:
            parts.append(f"scar: {self.scars}")
        if self.tattoos:
            parts.append(f"tattoo: {self.tattoos}")
        if self.other_features:
            parts.append(self.other_features)
        return ", ".join(parts)


@dataclass
class CharacterOutfit:
    """Character clothing/outfit for consistency"""
    top: str = ""  # shirt, blouse, jacket, etc.
    top_color: str = ""
    bottom: str = ""  # pants, skirt, shorts
    bottom_color: str = ""
    outerwear: str = ""  # coat, hoodie, blazer
    outerwear_color: str = ""
    footwear: str = ""
    accessories: str = ""  # hat, scarf, jewelry, watch
    style_keywords: str = ""  # casual, formal, streetwear, vintage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top": self.top,
            "top_color": self.top_color,
            "bottom": self.bottom,
            "bottom_color": self.bottom_color,
            "outerwear": self.outerwear,
            "outerwear_color": self.outerwear_color,
            "footwear": self.footwear,
            "accessories": self.accessories,
            "style_keywords": self.style_keywords
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterOutfit':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_prompt_string(self) -> str:
        """Generate consistent outfit prompt string"""
        parts = []
        if self.style_keywords:
            parts.append(f"{self.style_keywords} style")
        if self.top:
            top_desc = f"{self.top_color} {self.top}".strip() if self.top_color else self.top
            parts.append(f"wearing {top_desc}")
        if self.bottom:
            bottom_desc = f"{self.bottom_color} {self.bottom}".strip() if self.bottom_color else self.bottom
            parts.append(bottom_desc)
        if self.outerwear:
            outer_desc = f"{self.outerwear_color} {self.outerwear}".strip() if self.outerwear_color else self.outerwear
            parts.append(outer_desc)
        if self.footwear:
            parts.append(self.footwear)
        if self.accessories:
            parts.append(f"accessories: {self.accessories}")
        return ", ".join(parts)


@dataclass
class Character:
    """Character entity for reference slot"""
    id: str = field(default_factory=lambda: f"char_{uuid.uuid4().hex[:8]}")
    name: str = ""
    ref_images: List[str] = field(default_factory=list)  # 3-5 images recommended
    features_locked: List[str] = field(default_factory=lambda: ["face", "body_type", "hair"])
    costume_locked: bool = False
    consistency_weight: float = 0.8  # 0.5-1.0
    description: str = ""
    # New: Detailed appearance for consistency
    appearance: CharacterAppearance = field(default_factory=CharacterAppearance)
    outfit: CharacterOutfit = field(default_factory=CharacterOutfit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "ref_images": self.ref_images,
            "features_locked": self.features_locked,
            "costume_locked": self.costume_locked,
            "consistency_weight": self.consistency_weight,
            "description": self.description,
            "appearance": self.appearance.to_dict(),
            "outfit": self.outfit.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        appearance_data = data.pop("appearance", {})
        outfit_data = data.pop("outfit", {})
        char = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if appearance_data:
            char.appearance = CharacterAppearance.from_dict(appearance_data)
        if outfit_data:
            char.outfit = CharacterOutfit.from_dict(outfit_data)
        return char

    def get_consistency_prompt(self) -> str:
        """Generate full consistency prompt for this character"""
        parts = [f"[{self.name}:"]

        # Appearance
        appearance_str = self.appearance.to_prompt_string()
        if appearance_str:
            parts.append(appearance_str)

        # Outfit (if locked)
        if self.costume_locked:
            outfit_str = self.outfit.to_prompt_string()
            if outfit_str:
                parts.append(outfit_str)

        # Fallback to description if no detailed appearance
        if not appearance_str and self.description:
            parts.append(self.description)

        parts.append("]")
        return " ".join(parts)


@dataclass
class Scene:
    """Scene entity for reference slot"""
    id: str = field(default_factory=lambda: f"scene_{uuid.uuid4().hex[:8]}")
    name: str = ""
    space_ref_image: str = ""  # Physical layout reference
    atmosphere_ref_image: str = ""  # Optional: lighting/time reference
    description: str = ""  # Text supplement for details
    locked_features: List[str] = field(default_factory=lambda: ["space_structure"])
    light_direction: str = ""  # e.g., "from left window"
    color_temperature: str = ""  # e.g., "warm", "cool", "neutral"
    consistency_weight: float = 0.6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "space_ref_image": self.space_ref_image,
            "atmosphere_ref_image": self.atmosphere_ref_image,
            "description": self.description,
            "locked_features": self.locked_features,
            "light_direction": self.light_direction,
            "color_temperature": self.color_temperature,
            "consistency_weight": self.consistency_weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        return cls(**data)


@dataclass
class Prop:
    """Prop entity for reference slot"""
    id: str = field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    name: str = ""
    ref_image: str = ""  # Best if white background cutout
    size_reference: str = ""  # e.g., "palm-sized"
    material: str = ""  # e.g., "metal", "wood", "fabric"
    consistency_weight: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "ref_image": self.ref_image,
            "size_reference": self.size_reference,
            "material": self.material,
            "consistency_weight": self.consistency_weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prop':
        return cls(**data)


@dataclass
class StyleConfig:
    """Style configuration for reference slot"""
    mode: StyleMode = StyleMode.PRESET
    preset_name: str = ""  # When mode=PRESET
    ref_image: str = ""  # When mode=REFERENCE_IMAGE
    custom_description: str = ""  # When mode=CUSTOM_TEXT
    render_type: str = "realistic"  # realistic, illustration, 3d_render, watercolor
    color_tone: str = "neutral"  # warm, cool, high_saturation, low_saturation
    lighting_style: str = "natural"  # natural, studio, neon, backlit
    texture: str = "digital_clean"  # film_grain, digital_clean, noise
    weight: float = 0.4  # Recommend <= 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "preset_name": self.preset_name,
            "ref_image": self.ref_image,
            "custom_description": self.custom_description,
            "render_type": self.render_type,
            "color_tone": self.color_tone,
            "lighting_style": self.lighting_style,
            "texture": self.texture,
            "weight": self.weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StyleConfig':
        data = data.copy()
        data["mode"] = StyleMode(data["mode"])
        return cls(**data)


@dataclass
class StandardShotPrompt:
    """Standard shot prompt template for professional storyboarding"""
    subject: str = ""             # 主体: 主要角色/物体
    shot_type: str = ""           # 景别: 场景动作描述
    atmosphere: str = ""          # 氛围: 冷色/暖色/紧张/温馨等
    environment: str = ""         # 环境: 场景环境描述
    camera_movement: str = ""     # 运镜: 详细的镜头运动和切镜描述
    angle: str = ""               # 视角: 详细的视角描述
    special_technique: str = ""   # 特殊拍摄手法: 切镜/慢动作/长镜头等
    composition: str = ""         # 构图: 中景切特写切近景等
    style_consistency: str = ""   # 风格统一: 色调/光影/质感描述
    dynamic_control: str = ""     # 动态控制: 具体动作描述

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "shot_type": self.shot_type,
            "atmosphere": self.atmosphere,
            "environment": self.environment,
            "camera_movement": self.camera_movement,
            "angle": self.angle,
            "special_technique": self.special_technique,
            "composition": self.composition,
            "style_consistency": self.style_consistency,
            "dynamic_control": self.dynamic_control
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardShotPrompt':
        # 兼容旧数据（没有subject字段）
        if 'subject' not in data:
            data['subject'] = ''
        return cls(**data)

    def to_formatted_string(self) -> str:
        """Generate formatted standard prompt string"""
        lines = []
        if self.subject:
            lines.append(f"主体: {self.subject}")
        if self.shot_type:
            lines.append(f"景别: {self.shot_type}")
        if self.atmosphere:
            lines.append(f"氛围: {self.atmosphere}")
        if self.environment:
            lines.append(f"环境: {self.environment}")
        if self.camera_movement:
            lines.append(f"运镜: {self.camera_movement}")
        if self.angle:
            lines.append(f"视角: {self.angle}")
        if self.special_technique:
            lines.append(f"特殊拍摄手法: {self.special_technique}")
        if self.composition:
            lines.append(f"构图: {self.composition}")
        if self.style_consistency:
            lines.append(f"风格统一: {self.style_consistency}")
        if self.dynamic_control:
            lines.append(f"动态控制: {self.dynamic_control}")
        return "\n".join(lines)


@dataclass
class Shot:
    """Single storyboard shot"""
    shot_number: int = 1
    template: ShotTemplate = ShotTemplate.T4_STANDARD_MEDIUM
    description: str = ""
    characters_in_shot: List[str] = field(default_factory=list)  # Character IDs
    scene_id: str = ""
    props_in_shot: List[str] = field(default_factory=list)  # Prop IDs
    camera: CameraSettings = field(default_factory=CameraSettings)
    composition: CompositionSettings = field(default_factory=CompositionSettings)
    slot_weights: SlotWeights = field(default_factory=SlotWeights)
    dialogue: str = ""
    action: str = ""
    generated_prompt: str = ""
    standard_prompt: StandardShotPrompt = field(default_factory=StandardShotPrompt)  # 新增标准提示语
    output_image: str = ""
    output_video: str = ""  # 生成的视频路径
    consistency_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_number": self.shot_number,
            "template": self.template.value,
            "description": self.description,
            "characters_in_shot": self.characters_in_shot,
            "scene_id": self.scene_id,
            "props_in_shot": self.props_in_shot,
            "camera": {
                "distance": self.camera.distance,
                "vertical_angle": self.camera.vertical_angle,
                "horizontal_angle": self.camera.horizontal_angle,
                "focal_length": self.camera.focal_length
            },
            "composition": {
                "subject_scale": self.composition.subject_scale,
                "horizon_position": self.composition.horizon_position,
                "depth_layers": self.composition.depth_layers,
                "rule_of_thirds": self.composition.rule_of_thirds,
                "subject_position": self.composition.subject_position,
                "foreground_blur": self.composition.foreground_blur,
                "background_blur": self.composition.background_blur
            },
            "slot_weights": {
                "character": self.slot_weights.character,
                "scene": self.slot_weights.scene,
                "props": self.slot_weights.props,
                "style": self.slot_weights.style
            },
            "dialogue": self.dialogue,
            "action": self.action,
            "generated_prompt": self.generated_prompt,
            "standard_prompt": self.standard_prompt.to_dict(),
            "output_image": self.output_image,
            "output_video": self.output_video,
            "consistency_score": self.consistency_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Shot':
        shot = cls()
        shot.shot_number = data.get("shot_number", 1)
        shot.template = ShotTemplate(data.get("template", "T4_standard_medium"))
        shot.description = data.get("description", "")
        shot.characters_in_shot = data.get("characters_in_shot", [])
        shot.scene_id = data.get("scene_id", "")
        shot.props_in_shot = data.get("props_in_shot", [])

        cam_data = data.get("camera", {})
        shot.camera = CameraSettings(
            distance=cam_data.get("distance", "medium"),
            vertical_angle=cam_data.get("vertical_angle", 0),
            horizontal_angle=cam_data.get("horizontal_angle", 0),
            focal_length=cam_data.get("focal_length", 50)
        )

        comp_data = data.get("composition", {})
        shot.composition = CompositionSettings(
            subject_scale=comp_data.get("subject_scale", 0.5),
            horizon_position=comp_data.get("horizon_position", "middle"),
            depth_layers=comp_data.get("depth_layers", 2),
            rule_of_thirds=comp_data.get("rule_of_thirds", True),
            subject_position=comp_data.get("subject_position", "center"),
            foreground_blur=comp_data.get("foreground_blur", False),
            background_blur=comp_data.get("background_blur", False)
        )

        weight_data = data.get("slot_weights", {})
        shot.slot_weights = SlotWeights(
            character=weight_data.get("character", 0.8),
            scene=weight_data.get("scene", 0.6),
            props=weight_data.get("props", 0.5),
            style=weight_data.get("style", 0.4)
        )

        shot.dialogue = data.get("dialogue", "")
        shot.action = data.get("action", "")
        shot.generated_prompt = data.get("generated_prompt", "")

        # 解析标准提示语
        std_prompt_data = data.get("standard_prompt", {})
        if std_prompt_data:
            shot.standard_prompt = StandardShotPrompt.from_dict(std_prompt_data)
        else:
            shot.standard_prompt = StandardShotPrompt()

        shot.output_image = data.get("output_image", "")
        shot.output_video = data.get("output_video", "")
        shot.consistency_score = data.get("consistency_score", 0.0)

        return shot


@dataclass
class StoryboardProject:
    """Complete storyboard project"""
    name: str = "Untitled Project"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    aspect_ratio: str = "16:9"  # 16:9, 9:16, 1:1

    # Reference slots
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    props: List[Prop] = field(default_factory=list)
    style: StyleConfig = field(default_factory=StyleConfig)

    # Narrative slot
    narrative_text: str = ""

    # Storyboard
    shots: List[Shot] = field(default_factory=list)

    # Generation settings for consistency
    generation_seed: int = -1  # -1 for random, positive number to lock seed
    lock_seed: bool = True  # Whether to use fixed seed across all shots (default: enabled)

    def get_character_by_id(self, char_id: str) -> Optional[Character]:
        for c in self.characters:
            if c.id == char_id:
                return c
        return None

    def get_scene_by_id(self, scene_id: str) -> Optional[Scene]:
        for s in self.scenes:
            if s.id == scene_id:
                return s
        return None

    def get_prop_by_id(self, prop_id: str) -> Optional[Prop]:
        for p in self.props:
            if p.id == prop_id:
                return p
        return None

    def get_consistency_prefix(self) -> str:
        """
        Generate a consistency prefix for all prompts in the project.
        This includes style description and main character appearances.
        """
        parts = []

        # Style consistency
        style_parts = []
        if self.style.render_type:
            render_map = {
                "realistic": "photorealistic",
                "illustration": "digital illustration",
                "3d_render": "3D rendered",
                "watercolor": "watercolor style",
                "anime": "anime style",
                "comic": "comic book style"
            }
            style_parts.append(render_map.get(self.style.render_type, self.style.render_type))

        if self.style.color_tone:
            tone_map = {
                "warm": "warm color palette",
                "cool": "cool color palette",
                "high_saturation": "vibrant colors",
                "low_saturation": "muted colors"
            }
            if self.style.color_tone in tone_map:
                style_parts.append(tone_map[self.style.color_tone])

        if self.style.lighting_style:
            light_map = {
                "natural": "natural lighting",
                "studio": "studio lighting",
                "cinematic": "cinematic lighting",
                "neon": "neon lighting"
            }
            if self.style.lighting_style in light_map:
                style_parts.append(light_map[self.style.lighting_style])

        if self.style.custom_description:
            style_parts.append(self.style.custom_description[:80])

        if style_parts:
            parts.append(f"[Style: {', '.join(style_parts)}]")

        # Main characters consistency (first 3 characters)
        for char in self.characters[:3]:
            char_prompt = char.get_consistency_prompt()
            if char_prompt and char_prompt != f"[{char.name}: ]":
                parts.append(char_prompt)

        return " ".join(parts) if parts else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_meta": {
                "name": self.name,
                "created_at": self.created_at,
                "updated_at": datetime.now().isoformat(),
                "version": self.version,
                "aspect_ratio": self.aspect_ratio,
                "generation_seed": self.generation_seed,
                "lock_seed": self.lock_seed
            },
            "references": {
                "characters": [c.to_dict() for c in self.characters],
                "scenes": [s.to_dict() for s in self.scenes],
                "props": [p.to_dict() for p in self.props],
                "style": self.style.to_dict()
            },
            "narrative": self.narrative_text,
            "storyboard": [shot.to_dict() for shot in self.shots]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StoryboardProject':
        project = cls()

        meta = data.get("project_meta", {})
        project.name = meta.get("name", "Untitled Project")
        project.created_at = meta.get("created_at", datetime.now().isoformat())
        project.updated_at = meta.get("updated_at", datetime.now().isoformat())
        project.version = meta.get("version", "1.0")
        project.aspect_ratio = meta.get("aspect_ratio", "16:9")
        project.generation_seed = meta.get("generation_seed", -1)
        project.lock_seed = meta.get("lock_seed", True)  # Default to True for consistency

        refs = data.get("references", {})
        project.characters = [Character.from_dict(c) for c in refs.get("characters", [])]
        project.scenes = [Scene.from_dict(s) for s in refs.get("scenes", [])]
        project.props = [Prop.from_dict(p) for p in refs.get("props", [])]
        if "style" in refs:
            project.style = StyleConfig.from_dict(refs["style"])

        project.narrative_text = data.get("narrative", "")
        project.shots = [Shot.from_dict(s) for s in data.get("storyboard", [])]

        return project


@dataclass
class GeneratedAsset:
    """Record of AI-generated asset (character/scene/prop image)"""
    id: str = field(default_factory=lambda: f"asset_{uuid.uuid4().hex[:8]}")
    asset_type: GeneratedAssetType = GeneratedAssetType.CHARACTER
    name: str = ""
    description: str = ""
    prompt: str = ""  # Chinese prompt used for generation
    negative_prompt: str = ""
    status: AssetGenerationStatus = AssetGenerationStatus.PENDING
    image_path: str = ""
    ref_image_path: str = ""  # Reference image if used
    generation_params: Dict[str, Any] = field(default_factory=dict)
    review_score: float = 0.0
    review_summary: str = ""
    review_issues: List[str] = field(default_factory=list)
    review_suggestions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_type": self.asset_type.value,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "status": self.status.value,
            "image_path": self.image_path,
            "ref_image_path": self.ref_image_path,
            "generation_params": self.generation_params,
            "review_score": self.review_score,
            "review_summary": self.review_summary,
            "review_issues": self.review_issues,
            "review_suggestions": self.review_suggestions,
            "created_at": self.created_at,
            "generation_time": self.generation_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneratedAsset':
        asset = cls()
        asset.id = data.get("id", asset.id)
        asset.asset_type = GeneratedAssetType(data.get("asset_type", "character"))
        asset.name = data.get("name", "")
        asset.description = data.get("description", "")
        asset.prompt = data.get("prompt", "")
        asset.negative_prompt = data.get("negative_prompt", "")
        asset.status = AssetGenerationStatus(data.get("status", "pending"))
        asset.image_path = data.get("image_path", "")
        asset.ref_image_path = data.get("ref_image_path", "")
        asset.generation_params = data.get("generation_params", {})
        asset.review_score = data.get("review_score", 0.0)
        asset.review_summary = data.get("review_summary", "")
        asset.review_issues = data.get("review_issues", [])
        asset.review_suggestions = data.get("review_suggestions", [])
        asset.created_at = data.get("created_at", datetime.now().isoformat())
        asset.generation_time = data.get("generation_time", 0.0)
        return asset


@dataclass
class ComfyUISettings:
    """ComfyUI connection settings"""
    host: str = "127.0.0.1"
    port: int = 8188
    use_https: bool = False
    custom_workflow_path: str = ""
    default_model: str = ""
    timeout: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "use_https": self.use_https,
            "custom_workflow_path": self.custom_workflow_path,
            "default_model": self.default_model,
            "timeout": self.timeout
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComfyUISettings':
        return cls(
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 8188),
            use_https=data.get("use_https", False),
            custom_workflow_path=data.get("custom_workflow_path", ""),
            default_model=data.get("default_model", ""),
            timeout=data.get("timeout", 300)
        )
