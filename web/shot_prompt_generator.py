"""
Shot Prompt Generator - Simple Storyboard Prompt Tool
Independent tool for generating standard storyboard prompts with cut support
"""

import gradio as gr
from dataclasses import dataclass, field
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent / "prompt_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class ShotSegment:
    """Single shot segment (for multi-cut shots)"""
    description: str = ""      # What happens in this segment
    shot_type: str = "中景"    # Shot type: 远景/全景/中景/近景/特写
    angle: str = ""            # Camera angle description


@dataclass
class ShotPrompt:
    """Complete shot prompt with multiple segments"""
    subject: str = ""                           # Main subject
    scene_description: str = ""                 # Overall scene description
    atmosphere: str = ""                        # Atmosphere/mood
    environment: str = ""                       # Environment description
    segments: List[ShotSegment] = field(default_factory=list)  # Cut segments
    special_technique: str = ""                 # Special techniques
    style: str = ""                             # Style consistency
    dynamic_control: str = ""                   # Dynamic/action control

    def generate_camera_movement(self) -> str:
        """Generate camera movement description from segments"""
        if not self.segments:
            return "固定"

        if len(self.segments) == 1:
            return "固定"

        parts = []
        for i, seg in enumerate(self.segments, 1):
            desc = f"第{i}个{seg.description}"
            if i < len(self.segments):
                desc += "，切镜"
            parts.append(desc)
        return "".join(parts)

    def generate_angle(self) -> str:
        """Generate angle description from segments"""
        if not self.segments:
            return "平视"

        parts = []
        for i, seg in enumerate(self.segments, 1):
            if seg.angle:
                parts.append(f"第{i}个{seg.angle}")
        return "，".join(parts) if parts else "平视"

    def generate_composition(self) -> str:
        """Generate composition description from segments"""
        if not self.segments:
            return "中景"

        shot_types = [seg.shot_type for seg in self.segments if seg.shot_type]
        if shot_types:
            return "切".join(shot_types)
        return "中景"

    def generate_special_technique(self) -> str:
        """Generate special technique description"""
        if len(self.segments) > 1:
            return "切镜" + (f", {self.special_technique}" if self.special_technique else "")
        return self.special_technique or "标准拍摄"

    def to_formatted_string(self) -> str:
        """Generate the standard formatted prompt string"""
        lines = [
            f"主体: {self.subject}",
            f"景别: {self.scene_description}",
            f"氛围: {self.atmosphere}",
            f"环境: {self.environment}",
            f"运镜: {self.generate_camera_movement()}",
            f"视角: {self.generate_angle()}",
            f"特殊拍摄手法: {self.generate_special_technique()}",
            f"构图: {self.generate_composition()}",
            f"风格统一: {self.style}",
            f"动态控制: {self.dynamic_control}"
        ]
        return "\n".join(lines)


# Presets
ATMOSPHERE_PRESETS = ["冷色", "暖色", "紧张", "温馨", "神秘", "浪漫", "压抑", "欢快", "悲伤", "恐怖"]
SHOT_TYPE_PRESETS = ["远景", "全景", "中景", "近景", "特写", "大特写"]
STYLE_PRESETS = ["写实风格", "电影质感", "动漫风格", "漫画风格", "水彩风格", "黑白风格"]


def generate_prompt(
    subject: str,
    scene_description: str,
    atmosphere: str,
    environment: str,
    # Segment 1
    seg1_desc: str, seg1_type: str, seg1_angle: str,
    # Segment 2 (optional)
    seg2_desc: str, seg2_type: str, seg2_angle: str,
    # Segment 3 (optional)
    seg3_desc: str, seg3_type: str, seg3_angle: str,
    # Other
    extra_technique: str,
    style: str,
    dynamic_control: str
) -> str:
    """Generate the formatted prompt"""

    # Build segments
    segments = []

    if seg1_desc.strip():
        segments.append(ShotSegment(
            description=seg1_desc.strip(),
            shot_type=seg1_type,
            angle=seg1_angle.strip()
        ))

    if seg2_desc.strip():
        segments.append(ShotSegment(
            description=seg2_desc.strip(),
            shot_type=seg2_type,
            angle=seg2_angle.strip()
        ))

    if seg3_desc.strip():
        segments.append(ShotSegment(
            description=seg3_desc.strip(),
            shot_type=seg3_type,
            angle=seg3_angle.strip()
        ))

    # Create prompt
    prompt = ShotPrompt(
        subject=subject.strip(),
        scene_description=scene_description.strip(),
        atmosphere=atmosphere.strip(),
        environment=environment.strip(),
        segments=segments,
        special_technique=extra_technique.strip(),
        style=style.strip(),
        dynamic_control=dynamic_control.strip()
    )

    return prompt.to_formatted_string()


def save_prompt(prompt_text: str, name: str) -> str:
    """Save prompt to file"""
    if not prompt_text.strip():
        return "No prompt to save"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name or 'shot'}_{timestamp}.txt"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(prompt_text)

    return f"Saved to: {filepath}"


def load_example():
    """Load example data"""
    return (
        "男主",                                          # subject
        "对着停车场的一个阴暗处的车子发呆",                    # scene_description
        "冷色",                                          # atmosphere
        "停车场夜幕降临",                                  # environment
        "男主的背影在发抖", "中景", "男主的背",               # segment 1
        "手部抱着礼品盒颤抖", "特写", "手部抱着礼品",          # segment 2
        "礼品盒掉落地面毁坏", "近景", "礼品盒掉落地面",        # segment 3
        "",                                              # extra_technique
        "",                                              # style
        "人站在地上抱着盒子颤抖，盒子掉到地上"                # dynamic_control
    )


# CSS
CSS = """
.main-container { max-width: 1000px; margin: 0 auto; }
.segment-box {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    border-left: 3px solid #0071e3;
}
.output-box {
    background: #1a1a2e;
    color: #00ff88;
    font-family: monospace;
    padding: 16px;
    border-radius: 8px;
}
.title { text-align: center; margin-bottom: 20px; }
"""


def create_ui():
    """Create Gradio UI"""

    with gr.Blocks(title="Shot Prompt Generator") as demo:

        gr.HTML("""
        <div class="title">
            <h1>Shot Prompt Generator</h1>
            <p>Simple tool for generating standard storyboard prompts with multi-cut support</p>
        </div>
        """)

        with gr.Row():
            # Left: Input
            with gr.Column(scale=1):
                gr.Markdown("### Basic Info")
                subject = gr.Textbox(label="Main Subject", placeholder="e.g. Male lead")
                scene_description = gr.Textbox(
                    label="Scene Description (for Shot Type field)",
                    placeholder="e.g. Staring at a car in a dark corner of parking lot",
                    lines=2
                )

                with gr.Row():
                    atmosphere = gr.Dropdown(
                        choices=ATMOSPHERE_PRESETS,
                        label="Atmosphere",
                        value="冷色",
                        allow_custom_value=True
                    )
                    style = gr.Dropdown(
                        choices=[""] + STYLE_PRESETS,
                        label="Style",
                        value="",
                        allow_custom_value=True
                    )

                environment = gr.Textbox(
                    label="Environment",
                    placeholder="e.g. Parking lot at nightfall"
                )

                gr.Markdown("---")
                gr.Markdown("### Shot Segments (Multi-Cut Support)")
                gr.Markdown("*Fill in multiple segments for automatic cut transitions*")

                # Segment 1
                with gr.Group(elem_classes="segment-box"):
                    gr.Markdown("**Segment 1** (Required)")
                    seg1_desc = gr.Textbox(label="Description", placeholder="e.g. Male lead's back trembling")
                    with gr.Row():
                        seg1_type = gr.Dropdown(choices=SHOT_TYPE_PRESETS, label="Shot Type", value="中景")
                        seg1_angle = gr.Textbox(label="Angle", placeholder="e.g. Male lead's back")

                # Segment 2
                with gr.Group(elem_classes="segment-box"):
                    gr.Markdown("**Segment 2** (Optional - Cut)")
                    seg2_desc = gr.Textbox(label="Description", placeholder="e.g. Hands holding gift box trembling")
                    with gr.Row():
                        seg2_type = gr.Dropdown(choices=SHOT_TYPE_PRESETS, label="Shot Type", value="特写")
                        seg2_angle = gr.Textbox(label="Angle", placeholder="e.g. Hands holding gift")

                # Segment 3
                with gr.Group(elem_classes="segment-box"):
                    gr.Markdown("**Segment 3** (Optional - Cut)")
                    seg3_desc = gr.Textbox(label="Description", placeholder="e.g. Gift box falls and breaks")
                    with gr.Row():
                        seg3_type = gr.Dropdown(choices=SHOT_TYPE_PRESETS, label="Shot Type", value="近景")
                        seg3_angle = gr.Textbox(label="Angle", placeholder="e.g. Gift box falling")

                gr.Markdown("---")
                gr.Markdown("### Additional")
                extra_technique = gr.Textbox(label="Extra Special Technique", placeholder="Optional")
                dynamic_control = gr.Textbox(
                    label="Dynamic Control",
                    placeholder="Describe the action/movement",
                    lines=2
                )

            # Right: Output
            with gr.Column(scale=1):
                gr.Markdown("### Generated Prompt")

                output = gr.Textbox(
                    label="Generated Prompt (Copy from here)",
                    lines=15
                )

                with gr.Row():
                    generate_btn = gr.Button("Generate", variant="primary", size="lg")
                    example_btn = gr.Button("Load Example", variant="secondary")

                gr.Markdown("---")

                with gr.Row():
                    save_name = gr.Textbox(label="Save Name", placeholder="shot_name", scale=2)
                    save_btn = gr.Button("Save to File", scale=1)

                save_status = gr.Textbox(label="", interactive=False)

                gr.Markdown("---")
                gr.Markdown("### Output Format")
                gr.Markdown("""
                ```
                主体: [Subject]
                景别: [Scene Description]
                氛围: [Atmosphere]
                环境: [Environment]
                运镜: [Auto-generated from segments with cuts]
                视角: [Auto-generated from segment angles]
                特殊拍摄手法: [Auto: 切镜 if multi-segment]
                构图: [Auto: Shot types joined with 切]
                风格统一: [Style]
                动态控制: [Dynamic Control]
                ```
                """)

        # Event handlers
        generate_btn.click(
            generate_prompt,
            inputs=[
                subject, scene_description, atmosphere, environment,
                seg1_desc, seg1_type, seg1_angle,
                seg2_desc, seg2_type, seg2_angle,
                seg3_desc, seg3_type, seg3_angle,
                extra_technique, style, dynamic_control
            ],
            outputs=[output]
        )

        example_btn.click(
            load_example,
            outputs=[
                subject, scene_description, atmosphere, environment,
                seg1_desc, seg1_type, seg1_angle,
                seg2_desc, seg2_type, seg2_angle,
                seg3_desc, seg3_type, seg3_angle,
                extra_technique, style, dynamic_control
            ]
        )

        save_btn.click(
            save_prompt,
            inputs=[output, save_name],
            outputs=[save_status]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7962,
        inbrowser=True
    )
