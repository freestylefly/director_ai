"""
Storyboard AI Generator
Auto-generate storyboard prompts from story/script using Claude
"""

import gradio as gr
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Output directory
OUTPUT_DIR = Path(__file__).parent / "storyboard_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Skill prompt
SKILL_PROMPT = """You are a professional storyboard designer. Break down the following story/script into multiple shots and generate standard storyboard prompts.

For each shot, use this EXACT format:

=== Shot [number] ===
Main Subject: [characters/objects]
Shot Type: [scene and action description]
Atmosphere: [mood/color]
Environment: [location]
Camera Movement: [movement, use "cut to" for multi-cut]
Angle: [angle description]
Special Technique: [technique]
Composition: [shot types, e.g., medium cut to close-up]
Style: [visual style]
Dynamic Control: [action description]
Dialogue: [character lines]

Chinese format:
=== Split {number} ===
Main body: [character/object]
Scene: [scene description and action]
Atmosphere: [mood/color tone]
Environment: [location]
Camera: [Movement, multi-mirror use "cut mirror"]
Perspective: [Perspective description]
Special Shooting Technique: [Technique]
Composition: [Shot composition]
Unified Style: [Visual Style]
Dynamic control: [action description]
Lines: [role lines]

Rules:
1. Each scene or emotional beat should be a separate shot
2. For quick cuts within one beat, use multi-segment format in camera movement
3. Include dialogue with format: [character]: "line"
4. Use cold colors for tense/sad scenes, warm for happy/romantic
5. Shot types: wide, medium, close-up, extreme close-up
6. Output in Chinese

Story/Script to convert:
"""


def generate_storyboard(story_text: str, style: str = "cinematic") -> str:
    """Generate storyboard prompts using Claude CLI"""

    if not story_text.strip():
        return "Please enter a story or script first."

    # Build prompt
    full_prompt = SKILL_PROMPT + story_text

    if style:
        full_prompt += f"\n\nVisual style preference: {style}"

    try:
        # Call Claude CLI
        result = subprocess.run(
            ["claude", "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Request timed out. Please try with a shorter story."
    except FileNotFoundError:
        return "Claude CLI not found. Please install Claude CLI first."
    except Exception as e:
        return f"Error: {str(e)}"


def save_storyboard(content: str, name: str) -> str:
    """Save storyboard to file"""
    if not content.strip():
        return "No content to save"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name or 'storyboard'}_{timestamp}.txt"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Saved: {filepath}"


def load_example_story():
    """Load example story"""
    return """深夜停车场，男主发现女友和另一个男人在一起。他手里拿着准备送给女友的礼物盒，整个人僵住了。

男主颤抖着看着这一幕，礼物盒从手中滑落，摔在地上碎了。

女友听到声音转过头，看到男主站在那里，脸色苍白。

女友: "你...你怎么来了？"

男主一言不发，转身离开。女友想要追上去，但被身边的男人拉住。

男主: (内心独白) "原来，一切都是假的..."

男主坐进自己的车里，双手紧握方向盘，泪水终于落下。"""


# CSS
CUSTOM_CSS = """
.output-area {
    font-family: 'Microsoft YaHei', monospace;
    line-height: 1.8;
}
"""


def create_ui():
    """Create Gradio UI"""

    with gr.Blocks(title="Storyboard AI Generator") as demo:

        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>Storyboard AI Generator</h1>
            <p>Input your story/script, AI will automatically generate professional storyboard prompts</p>
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Input Story/Script")

                story_input = gr.Textbox(
                    label="Story/Script",
                    placeholder="Enter your story, script, or scene description here...\n\nExample:\nLate night parking lot, the male lead discovers his girlfriend with another man...",
                    lines=15
                )

                style_choice = gr.Radio(
                    choices=["cinematic", "anime", "comic", "realistic"],
                    label="Visual Style",
                    value="cinematic"
                )

                with gr.Row():
                    generate_btn = gr.Button("Generate Storyboard", variant="primary", size="lg")
                    example_btn = gr.Button("Load Example", variant="secondary")

            with gr.Column(scale=1):
                gr.Markdown("### Generated Storyboard")

                output = gr.Textbox(
                    label="Storyboard Prompts",
                    lines=20,
                    elem_classes="output-area"
                )

                with gr.Row():
                    save_name = gr.Textbox(label="Save Name", placeholder="project_name", scale=2)
                    save_btn = gr.Button("Save", scale=1)

                save_status = gr.Textbox(label="", interactive=False)

        gr.Markdown("---")
        gr.Markdown("""
        ### Output Format Explanation

        | Field | Description |
        |-------|-------------|
        | Main Subject | Characters or objects in the shot |
        | Shot Type | Scene description with camera framing |
        | Atmosphere | Mood and color tone (cold/warm/tense/cozy) |
        | Environment | Location and setting details |
        | Camera Movement | Camera motion, "cut to" for multi-shot sequences |
        | Angle | Camera angle (eye-level, low angle, high angle) |
        | Special Technique | Special filming techniques (slow-mo, POV, etc.) |
        | Composition | Shot type transitions (medium cut to close-up) |
        | Style | Visual style consistency |
        | Dynamic Control | Action and movement description |
        | Dialogue | Character lines with speaker indicated |
        """)

        # Events
        generate_btn.click(
            generate_storyboard,
            inputs=[story_input, style_choice],
            outputs=[output]
        )

        example_btn.click(
            load_example_story,
            outputs=[story_input]
        )

        save_btn.click(
            save_storyboard,
            inputs=[output, save_name],
            outputs=[save_status]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7963,
        inbrowser=True
    )
