"""
AI Creative Generator - Claude CLI Integration
Automated story analysis, character/scene/prop extraction
Chinese prompt generation for ComfyUI
"""

import os
import json
import subprocess
import tempfile
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================
# 模块级 LLM 配置（可被 app.py 动态设置）
# ============================================
_llm_provider = "Claude Code CLI"  # 默认使用 Claude CLI
_llm_api_key = ""
_llm_api_url = ""


def set_llm_config(provider: str = None, api_key: str = None, api_url: str = None):
    """设置 LLM 配置（由 app.py 调用）"""
    global _llm_provider, _llm_api_key, _llm_api_url
    if provider is not None:
        _llm_provider = provider
    if api_key is not None:
        _llm_api_key = api_key
    if api_url is not None:
        _llm_api_url = api_url


def get_llm_config() -> Dict[str, str]:
    """获取当前 LLM 配置"""
    return {
        "provider": _llm_provider,
        "api_key": _llm_api_key,
        "api_url": _llm_api_url
    }


class AssetType(Enum):
    """Type of generated asset"""
    CHARACTER = "character"
    SCENE = "scene"
    PROP = "prop"


class ArtStyle(Enum):
    """Art style for generation"""
    REALISTIC = "realistic"
    ANIME = "anime"
    COMIC = "comic"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil_painting"
    SKETCH = "sketch"


@dataclass
class CharacterInfo:
    """Extracted character information"""
    name: str = ""
    age: str = ""
    gender: str = ""
    appearance: str = ""
    clothing: str = ""
    personality: str = ""
    role: str = ""  # main, supporting, antagonist, etc.
    generated_prompt: str = ""
    ref_images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "appearance": self.appearance,
            "clothing": self.clothing,
            "personality": self.personality,
            "role": self.role,
            "generated_prompt": self.generated_prompt
        }


@dataclass
class SceneInfo:
    """Extracted scene information"""
    name: str = ""
    location_type: str = ""  # indoor, outdoor, etc.
    description: str = ""
    lighting: str = ""
    atmosphere: str = ""
    time_of_day: str = ""
    weather: str = ""
    generated_prompt: str = ""
    ref_images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "location_type": self.location_type,
            "description": self.description,
            "lighting": self.lighting,
            "atmosphere": self.atmosphere,
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "generated_prompt": self.generated_prompt
        }


@dataclass
class PropInfo:
    """Extracted prop information"""
    name: str = ""
    category: str = ""  # furniture, vehicle, weapon, etc.
    description: str = ""
    material: str = ""
    size: str = ""
    importance: str = ""  # key_item, background, etc.
    generated_prompt: str = ""
    ref_images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "material": self.material,
            "size": self.size,
            "importance": self.importance,
            "generated_prompt": self.generated_prompt
        }


@dataclass
class ShotInfo:
    """Story shot/frame information"""
    template: str = "中景"  # 全景, 中景, 特写, 过肩
    description: str = ""
    characters: List[str] = field(default_factory=list)  # character names
    scene: str = ""  # scene name

    def to_dict(self) -> Dict:
        return {
            "template": self.template,
            "description": self.description,
            "characters": self.characters,
            "scene": self.scene
        }


@dataclass
class StoryAnalysisResult:
    """Result of story analysis"""
    success: bool = False
    project_name: str = ""
    description: str = ""
    genre: str = ""
    style: str = ""  # art style
    characters: List[CharacterInfo] = field(default_factory=list)
    scenes: List[SceneInfo] = field(default_factory=list)
    props: List[PropInfo] = field(default_factory=list)
    shots: List[ShotInfo] = field(default_factory=list)
    error: str = ""


class AICreativeGenerator:
    """
    AI Creative Generator using Claude CLI
    Analyzes story text and generates Chinese prompts for image generation
    """

    # Style name mapping (Chinese)
    STYLE_NAMES = {
        ArtStyle.REALISTIC: "写实风格",
        ArtStyle.ANIME: "日系动漫风格",
        ArtStyle.COMIC: "美漫风格",
        ArtStyle.WATERCOLOR: "水彩画风格",
        ArtStyle.OIL_PAINTING: "油画风格",
        ArtStyle.SKETCH: "素描风格"
    }

    # Story analysis prompt template (for full story text)
    STORY_ANALYSIS_PROMPT = """请分析以下剧情文本，提取角色、场景和重要道具信息。

剧情文本:
{story_text}

请按以下JSON格式输出分析结果（只输出JSON，不要其他解释）:
```json
{{
    "project_name": "项目名称（根据剧情总结）",
    "description": "剧情简介（50字以内）",
    "genre": "题材类型（如：爱情/动作/悬疑/奇幻等）",
    "characters": [
        {{
            "name": "角色名",
            "age": "年龄",
            "gender": "性别",
            "appearance": "外貌描述（发型、五官、体型等）",
            "clothing": "服装描述",
            "personality": "性格特点",
            "role": "角色定位（主角/配角/反派等）"
        }}
    ],
    "scenes": [
        {{
            "name": "场景名称",
            "location_type": "室内/室外/混合",
            "description": "场景详细描述",
            "lighting": "光线描述",
            "atmosphere": "氛围描述",
            "time_of_day": "时间段",
            "weather": "天气（如适用）"
        }}
    ],
    "props": [
        {{
            "name": "道具名称",
            "category": "道具类型",
            "description": "道具描述",
            "material": "材质",
            "size": "尺寸描述",
            "importance": "重要性（关键道具/背景道具）"
        }}
    ]
}}
```

分析要求:
1. 仔细阅读剧情，识别所有出现的角色
2. 提取角色的外貌、服装等视觉特征
3. 识别剧情中的场景/地点
4. 提取重要的道具和物品
5. 如果信息不明确，根据上下文合理推断"""

    # Story CREATION prompt (for one-sentence ideas)
    STORY_CREATION_PROMPT = """根据以下故事创意，创作一个完整的分镜故事，包含角色、场景、道具和7个分镜设定。

故事创意:
{story_idea}

请发挥创意，根据这个简短的创意，创作一个完整的故事设定。要求:
1. 创建2-4个有特色的角色，包含非常详细的外貌和服装描述
2. 设计2-3个具体的场景/地点
3. 添加1-3个重要的道具
4. 给故事起一个吸引人的名字
5. 设计7个分镜，包含详细的画面描述

角色描述示例格式（必须达到这个详细程度）:
"超级Q萌的胖胖小马吉祥物，圆滚滚的身体，大大的眼睛闪闪发光，粉嫩的脸蛋，穿着红色小马甲，背着金色福袋，走路一颠一颠超可爱"
"Q版70岁老爷爷，圆圆的脸，笑眯眯的眼睛，穿红色唐装，胸前绣着骏马图案，慈祥可爱"

场景描述示例格式:
"2D卡通风格的喜庆街道，Q萌马形灯笼高挂，红色横幅飘扬，到处是可爱的马年装饰"
"温馨的咖啡厅，落地窗透进柔和的阳光，木质桌椅整齐排列，绿植点缀，空气中弥漫着咖啡香气"

分镜描述示例格式（必须包含动作、表情、对话）:
"Q萌福宝马蹦蹦跳跳走在街上，胖胖的身体一颠一颠，背上的福袋晃来晃去，超级可爱"
"福宝马用小蹄子从福袋里掏出金色马蹄铁挂件，眼睛弯成月牙：送你马到成功！"

请按以下JSON格式输出（只输出JSON，不要其他解释）:
```json
{{
    "project_name": "故事名称（吸引人的标题）",
    "description": "剧情简介（50-100字，生动有趣）",
    "genre": "题材类型",
    "style": "画面风格（如：2D卡通、电影感、写实风等）",
    "characters": [
        {{
            "name": "角色名（中文名）",
            "age": "年龄（如：25岁）",
            "gender": "性别",
            "appearance": "非常详细的外貌描述，包括：脸型、眼睛、发型颜色、表情特点、身材体型、特殊标记等，至少50字",
            "clothing": "非常详细的服装描述，包括：款式、颜色、图案、配饰、鞋子等，至少30字",
            "personality": "性格特点，加入可爱或有趣的动作习惯",
            "role": "主角/配角/反派"
        }}
    ],
    "scenes": [
        {{
            "name": "场景名称",
            "location_type": "室内/室外",
            "description": "非常详细的场景描述，包括：环境布置、装饰物品、色彩氛围、特色元素等，至少60字",
            "lighting": "光线描述（如：柔和的自然光、温暖的灯光等）",
            "atmosphere": "氛围描述（如：温馨浪漫、欢乐热闹等）",
            "time_of_day": "时间段",
            "weather": "天气（如适用）"
        }}
    ],
    "props": [
        {{
            "name": "道具名称",
            "category": "道具类型",
            "description": "道具详细描述，包括外观特征",
            "material": "材质",
            "size": "尺寸",
            "importance": "关键道具/背景道具"
        }}
    ],
    "shots": [
        {{
            "template": "全景/中景/特写/过肩",
            "description": "非常详细的画面描述，包含：角色动作、表情细节、情绪、对话（如有），至少40字",
            "characters": ["出现的角色名"],
            "scene": "场景名"
        }}
    ]
}}
```

重要：
- 所有描述必须非常详细、生动、具体
- 角色描述要包含动作习惯和可爱/有趣的特点
- 分镜描述要包含具体的动作和表情，可以加入对话
- 如果是可爱风格，多用萌萌的、可爱的、Q萌等词汇"""

    # Character prompt generation template
    CHARACTER_PROMPT_TEMPLATE = """请为以下角色生成适合AI绘图的中文提示语。

角色信息:
- 姓名: {name}
- 年龄: {age}
- 性别: {gender}
- 外貌: {appearance}
- 服装: {clothing}
- 性格: {personality}
- 角色定位: {role}

艺术风格: {style}

请生成一段中文提示语，用于生成该角色的立绘/半身像。
要求:
1. 提示语必须是中文
2. 包含外貌特征、服装细节
3. 适当的表情和姿态
4. 匹配指定的艺术风格
5. 加入质量相关的描述词

只输出提示语，不要其他解释。"""

    # Scene prompt generation template
    SCENE_PROMPT_TEMPLATE = """请为以下场景生成适合AI绘图的中文提示语。

场景信息:
- 名称: {name}
- 类型: {location_type}
- 描述: {description}
- 光线: {lighting}
- 氛围: {atmosphere}
- 时间: {time_of_day}
- 天气: {weather}

艺术风格: {style}

请生成一段中文提示语，用于生成该场景的概念图。
要求:
1. 提示语必须是中文
2. 包含环境细节、光线效果
3. 体现场景氛围
4. 匹配指定的艺术风格
5. 加入质量相关的描述词

只输出提示语，不要其他解释。"""

    # Prop prompt generation template
    PROP_PROMPT_TEMPLATE = """请为以下道具生成适合AI绘图的中文提示语。

道具信息:
- 名称: {name}
- 类型: {category}
- 描述: {description}
- 材质: {material}
- 尺寸: {size}

艺术风格: {style}

请生成一段中文提示语，用于生成该道具的产品图/设定图。
要求:
1. 提示语必须是中文
2. 包含材质、细节描述
3. 白色或简洁背景
4. 匹配指定的艺术风格
5. 加入质量相关的描述词

只输出提示语，不要其他解释。"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def _call_canghe_api(self, prompt: str) -> Tuple[bool, str]:
        """
        调用苍何 API 进行文本生成
        Returns: (success, output or error)
        """
        global _llm_api_key, _llm_api_url

        # 获取 API key（可能从图像生成配置共享）
        api_key = _llm_api_key
        if not api_key:
            try:
                from image_generator import _canghe_api_key
                api_key = _canghe_api_key
            except:
                pass

        if not api_key:
            return False, "苍何 API Key 未配置"

        api_url = _llm_api_url or "https://api.canghe.ai/v1/chat/completions"

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "gemini-2.0-flash",
                "messages": [
                    {"role": "system", "content": "你是一个专业的分镜故事创作助手，擅长根据用户输入创作详细的角色、场景和镜头设定。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4096
            }

            # 尝试更新 app.py 的监控状态
            try:
                from app import api_monitor_start, api_monitor_end
                api_monitor_start("苍何 API (故事)")
            except:
                pass

            print(f"[苍何 API] 正在调用 chat/completions...")
            response = requests.post(api_url, headers=headers, json=data, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                # 获取 token 使用量
                usage = result.get("usage", {})
                tokens_used = usage.get("total_tokens", len(content) // 4 if content else 0)

                if content:
                    print(f"[苍何 API] ✓ 生成成功 ({len(content)} 字符, {tokens_used} tokens)")
                    try:
                        from app import api_monitor_end
                        api_monitor_end("苍何 API (故事)", tokens_used, True)
                    except:
                        pass
                    return True, content
                else:
                    try:
                        from app import api_monitor_end
                        api_monitor_end("苍何 API (故事)", 0, False)
                    except:
                        pass
                    return False, "苍何 API 返回空内容"
            else:
                error_msg = f"苍何 API 调用失败: {response.status_code} - {response.text[:200]}"
                print(f"[苍何 API] ✗ {error_msg}")
                try:
                    from app import api_monitor_end
                    api_monitor_end("苍何 API (故事)", 0, False)
                except:
                    pass
                return False, error_msg

        except requests.exceptions.Timeout:
            try:
                from app import api_monitor_end
                api_monitor_end("苍何 API (故事)", 0, False)
            except:
                pass
            return False, "苍何 API 请求超时"
        except Exception as e:
            try:
                from app import api_monitor_end
                api_monitor_end("苍何 API (故事)", 0, False)
            except:
                pass
            return False, f"苍何 API 调用错误: {str(e)}"

    def _call_claude_cli(self, prompt: str) -> Tuple[bool, str]:
        """
        Call Claude CLI with the given prompt.
        如果配置了苍何 API，则使用苍何 API，失败时不回退到 Claude CLI。
        Returns: (success, output or error)
        """
        global _llm_provider, _llm_api_key

        # 调试日志
        print(f"[AICreativeGenerator] _call_claude_cli called, provider={_llm_provider}, has_key={bool(_llm_api_key)}")

        # 检查是否配置了苍何 API
        if "苍何" in _llm_provider:
            success, output = self._call_canghe_api(prompt)
            if success:
                return success, output
            # 苍何 API 失败，直接返回错误，不回退到 Claude CLI
            print(f"[LLM] 苍何 API 调用失败: {output}")
            return False, f"苍何 API 调用失败: {output}"

        # 使用 Claude CLI
        import shutil
        import os
        import tempfile
        import platform

        # 尝试更新监控状态
        try:
            from app import api_monitor_start
            api_monitor_start("Claude CLI (故事)")
        except:
            pass

        try:
            is_windows = platform.system() == "Windows"

            # 查找 claude 命令
            claude_cmd = None
            if is_windows:
                # Windows 上尝试多种方式
                for cmd in ["claude.cmd", "claude.exe", "claude"]:
                    found = shutil.which(cmd)
                    if found:
                        claude_cmd = found
                        break
                # 尝试常见的 npm 全局安装路径
                if not claude_cmd:
                    npm_path = os.path.expanduser('~\\AppData\\Roaming\\npm\\claude.cmd')
                    if os.path.exists(npm_path):
                        claude_cmd = npm_path
            else:
                claude_cmd = shutil.which('claude')

            if not claude_cmd:
                try:
                    from app import api_monitor_end
                    api_monitor_end("Claude CLI (故事)", 0, False)
                except:
                    pass
                return False, "Claude CLI not found. Please ensure it's installed and in PATH."

            # 使用临时文件传递长 prompt，避免命令行参数限制
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(prompt)
                temp_file = f.name

            try:
                # Windows 上使用 shell=True 确保正确执行
                if is_windows:
                    # 使用临时文件作为输入
                    cmd_str = f'type "{temp_file}" | "{claude_cmd}" -p - --output-format text'
                    result = subprocess.run(
                        cmd_str,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        encoding='utf-8',
                        errors='replace',
                        shell=True
                    )
                else:
                    # 使用 stdin 方式传递 prompt
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        result = subprocess.run(
                            [claude_cmd, '-p', '-', '--output-format', 'text'],
                            stdin=f,
                            capture_output=True,
                            text=True,
                            timeout=self.timeout,
                            encoding='utf-8'
                        )
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass

            if result.returncode == 0:
                output = result.stdout.strip()
                # 估算 token 消耗
                tokens_estimate = (len(prompt) + len(output)) // 4
                try:
                    from app import api_monitor_end
                    api_monitor_end("Claude CLI (故事)", tokens_estimate, True)
                except:
                    pass
                return True, output
            else:
                try:
                    from app import api_monitor_end
                    api_monitor_end("Claude CLI (故事)", 0, False)
                except:
                    pass
                return False, f"Claude CLI error: {result.stderr}"

        except subprocess.TimeoutExpired:
            try:
                from app import api_monitor_end
                api_monitor_end("Claude CLI (故事)", 0, False)
            except:
                pass
            return False, "Claude CLI timeout"
        except FileNotFoundError:
            try:
                from app import api_monitor_end
                api_monitor_end("Claude CLI (故事)", 0, False)
            except:
                pass
            return False, "Claude CLI not found. Please ensure it's installed and in PATH."
        except Exception as e:
            try:
                from app import api_monitor_end
                api_monitor_end("Claude CLI (故事)", 0, False)
            except:
                pass
            return False, f"Error calling Claude CLI: {str(e)}"

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text response"""
        # Try to find JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to parse entire text as JSON
            json_str = text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except:
                    pass
            return None

    def analyze_story(self, story_text: str) -> StoryAnalysisResult:
        """
        Analyze story text and extract characters, scenes, and props.
        For short inputs (< 100 chars), will CREATE a story from the idea.
        For longer inputs, will ANALYZE the existing story.

        Args:
            story_text: The story/script text to analyze, or a short story idea

        Returns:
            StoryAnalysisResult with extracted information
        """
        result = StoryAnalysisResult()

        if not story_text.strip():
            result.error = "Story text is empty"
            return result

        # Determine if this is a short idea or a full story
        text_length = len(story_text.strip())
        is_short_idea = text_length < 100

        # Prepare prompt based on input type
        if is_short_idea:
            # Short idea: CREATE a complete story
            prompt = self.STORY_CREATION_PROMPT.format(
                story_idea=story_text.strip()
            )
        else:
            # Full story: ANALYZE and extract
            prompt = self.STORY_ANALYSIS_PROMPT.format(
                story_text=story_text[:8000]  # Limit length
            )

        # Call Claude CLI
        success, output = self._call_claude_cli(prompt)
        if not success:
            # Try fallback generation for short ideas
            if is_short_idea:
                return self._generate_fallback_story(story_text.strip())
            result.error = output
            return result

        # Parse JSON response
        data = self._extract_json(output)
        if not data:
            result.error = f"Failed to parse response as JSON. Response: {output[:500]}"
            return result

        # Extract project info
        result.project_name = data.get("project_name", "Untitled")
        result.description = data.get("description", "")
        result.genre = data.get("genre", "")

        # Extract characters
        for char_data in data.get("characters", []):
            char = CharacterInfo(
                name=char_data.get("name", ""),
                age=char_data.get("age", ""),
                gender=char_data.get("gender", ""),
                appearance=char_data.get("appearance", ""),
                clothing=char_data.get("clothing", ""),
                personality=char_data.get("personality", ""),
                role=char_data.get("role", "")
            )
            result.characters.append(char)

        # Extract scenes
        for scene_data in data.get("scenes", []):
            scene = SceneInfo(
                name=scene_data.get("name", ""),
                location_type=scene_data.get("location_type", ""),
                description=scene_data.get("description", ""),
                lighting=scene_data.get("lighting", ""),
                atmosphere=scene_data.get("atmosphere", ""),
                time_of_day=scene_data.get("time_of_day", ""),
                weather=scene_data.get("weather", "")
            )
            result.scenes.append(scene)

        # Extract props
        for prop_data in data.get("props", []):
            prop = PropInfo(
                name=prop_data.get("name", ""),
                category=prop_data.get("category", ""),
                description=prop_data.get("description", ""),
                material=prop_data.get("material", ""),
                size=prop_data.get("size", ""),
                importance=prop_data.get("importance", "")
            )
            result.props.append(prop)

        # Extract shots
        for shot_data in data.get("shots", []):
            shot = ShotInfo(
                template=shot_data.get("template", "中景"),
                description=shot_data.get("description", ""),
                characters=shot_data.get("characters", []),
                scene=shot_data.get("scene", "")
            )
            result.shots.append(shot)

        # Extract style
        result.style = data.get("style", "")

        result.success = True
        return result

    def _generate_fallback_story(self, story_idea: str) -> StoryAnalysisResult:
        """
        Generate a basic story when Claude CLI is unavailable.
        Creates simple but complete content based on the story idea.
        """
        result = StoryAnalysisResult()
        result.success = True

        # Extract keywords from idea
        idea_lower = story_idea.lower()

        # Determine genre
        if any(k in idea_lower for k in ['爱情', '恋爱', '浪漫', '爱']):
            result.genre = "爱情"
            result.project_name = f"爱情故事 - {story_idea[:10]}"
        elif any(k in idea_lower for k in ['末世', '僵尸', '丧尸', '病毒', '废墟', '废墟', '生存', '灾难']):
            result.genre = "末世"
            result.project_name = f"末世求生 - {story_idea[:10]}"
        elif any(k in idea_lower for k in ['动作', '追逐', '战斗', '打']):
            result.genre = "动作"
            result.project_name = f"动作故事 - {story_idea[:10]}"
        elif any(k in idea_lower for k in ['悬疑', '神秘', '侦探', '案件']):
            result.genre = "悬疑"
            result.project_name = f"悬疑故事 - {story_idea[:10]}"
        elif any(k in idea_lower for k in ['奇幻', '魔法', '仙', '玄幻']):
            result.genre = "奇幻"
            result.project_name = f"奇幻故事 - {story_idea[:10]}"
        elif any(k in idea_lower for k in ['科幻', '未来', '机器', '太空']):
            result.genre = "科幻"
            result.project_name = f"科幻故事 - {story_idea[:10]}"
        else:
            result.genre = "剧情"
            result.project_name = f"故事 - {story_idea[:15]}"

        result.description = f"基于「{story_idea}」创作的分镜故事"

        # Create default characters based on genre
        if result.genre == "爱情":
            result.characters = [
                CharacterInfo(
                    name="男主角",
                    age="28岁",
                    gender="男",
                    appearance="英俊的脸庞，深邃的眼神，短发整齐，身材高挑修长",
                    clothing="深蓝色休闲西装，白色衬衫，黑色休闲鞋",
                    personality="温柔体贴，略带忧郁",
                    role="主角"
                ),
                CharacterInfo(
                    name="女主角",
                    age="25岁",
                    gender="女",
                    appearance="清秀温婉，长发及腰，大眼睛，皮肤白皙，身材纤细",
                    clothing="白色连衣裙，配上简单的项链，浅色高跟鞋",
                    personality="善良温柔，偶尔倔强",
                    role="主角"
                ),
            ]
            result.scenes = [
                SceneInfo(
                    name="咖啡厅",
                    location_type="室内",
                    description="温馨的咖啡厅，落地窗透进柔和的阳光，木质桌椅整齐排列，绿植点缀，空气中弥漫着咖啡香气",
                    lighting="柔和的自然光，透过窗户洒入",
                    atmosphere="温馨浪漫，舒适惬意",
                    time_of_day="下午",
                    weather="晴天"
                ),
                SceneInfo(
                    name="城市街道",
                    location_type="室外",
                    description="繁华的都市街道，两旁是现代建筑和店铺，行人来往，路灯和霓虹装点夜景",
                    lighting="黄昏的光线，金色阳光斜射",
                    atmosphere="热闹却不喧嚣",
                    time_of_day="黄昏",
                    weather="晴天"
                ),
            ]
        elif result.genre == "动作":
            result.characters = [
                CharacterInfo(
                    name="主角",
                    age="32岁",
                    gender="男",
                    appearance="棱角分明的脸庞，锐利的眼神，短发，身材健壮，有一道小伤疤在眉角",
                    clothing="黑色皮夹克，深色T恤，工装裤，军靴",
                    personality="冷静果断，正义感强",
                    role="主角"
                ),
                CharacterInfo(
                    name="反派",
                    age="40岁",
                    gender="男",
                    appearance="阴沉的面容，留着精心修剪的短胡须，高大威猛，眼神冷酷",
                    clothing="黑色西装，红色领带，皮手套",
                    personality="狡诈阴险，野心勃勃",
                    role="反派"
                ),
            ]
            result.scenes = [
                SceneInfo(
                    name="废弃工厂",
                    location_type="室内",
                    description="荒废的工厂厂房，锈迹斑斑的机器设备，破碎的窗户，灰尘弥漫，钢架结构若隐若现",
                    lighting="昏暗的光线，从破窗透入",
                    atmosphere="紧张危险，压抑沉重",
                    time_of_day="夜晚",
                    weather="阴天"
                ),
                SceneInfo(
                    name="城市天台",
                    location_type="室外",
                    description="高楼天台，可以俯瞰整个城市夜景，护栏边缘，风吹过",
                    lighting="城市灯光反射，霓虹闪烁",
                    atmosphere="高度紧张，对峙氛围",
                    time_of_day="深夜",
                    weather="多云"
                ),
            ]
        elif result.genre == "末世":
            result.characters = [
                CharacterInfo(
                    name="幸存者",
                    age="28岁",
                    gender="男",
                    appearance="饱经风霜的面容，眼神警惕而坚毅，乱蓬蓬的短发沾满灰尘，脸上有擦伤和泥渍，身材精瘦但充满力量感",
                    clothing="破旧的皮夹克，内搭脏兮兮的格子衬衫，战术背心上挂满弹夹和工具，军绿色工装裤，重型军靴",
                    personality="沉默寡言但行动果断，在末世中学会了不轻信任何人",
                    role="主角"
                ),
                CharacterInfo(
                    name="女医生",
                    age="32岁",
                    gender="女",
                    appearance="疲惫但仍保持镇定的面容，黑发凌乱地扎成马尾，眼镜片有裂痕，皮肤苍白，眼下有深深的黑眼圈",
                    clothing="沾满血迹的白大褂里面是灰色卫衣，牛仔裤膝盖处磨破，运动鞋，肩上背着医疗包",
                    personality="冷静理智，坚持救死扶伤的信念，是团队的精神支柱",
                    role="配角"
                ),
                CharacterInfo(
                    name="僵尸",
                    age="不详",
                    gender="不详",
                    appearance="腐烂发灰的皮肤，血红浑浊的双眼空洞无神，嘴角流着黑色血液，身体扭曲变形，部分肌肉外露",
                    clothing="破烂不堪的衣物残片，有的穿着赌场制服，有的穿着游客服装",
                    personality="失去理智，只剩下对鲜血和活人的本能渴望",
                    role="反派"
                ),
            ]
            result.scenes = [
                SceneInfo(
                    name="废弃赌场",
                    location_type="室内",
                    description="曾经辉煌的赌场大厅现已沦为废墟，老虎机东倒西歪，有些还在闪烁着诡异的残光，赌桌上散落着筹码和干涸的血迹，水晶吊灯摇摇欲坠，地上堆满碎玻璃和废墟",
                    lighting="残破的霓虹灯忽明忽暗，透过破碎天窗的月光投下阴森的光影",
                    atmosphere="死寂中弥漫着腐烂的恶臭，危机四伏",
                    time_of_day="深夜",
                    weather="阴沉"
                ),
                SceneInfo(
                    name="末日街道",
                    location_type="室外",
                    description="曾经繁华的拉斯维加斯大道现已荒芜，巨型LED广告牌残破闪烁，废弃汽车堵塞道路，街道两旁是倒塌的建筑和燃烧后的残骸，远处有僵尸成群游荡",
                    lighting="灰暗的天空透着诡异的红色，残存的霓虹灯映照着废墟",
                    atmosphere="死亡的寂静被远处的嘶吼声偶尔打破",
                    time_of_day="黄昏",
                    weather="阴霾"
                ),
            ]
        else:
            # Default characters for other genres
            result.characters = [
                CharacterInfo(
                    name="主角",
                    age="30岁",
                    gender="男",
                    appearance="普通但有特色的面容，黑色短发，眼神坚定，身材匀称",
                    clothing="日常便装，深色外套，休闲裤，运动鞋",
                    personality="正直勇敢，善于思考",
                    role="主角"
                ),
                CharacterInfo(
                    name="配角",
                    age="28岁",
                    gender="女",
                    appearance="知性美丽，中长发，戴眼镜，气质优雅",
                    clothing="职业装，白衬衫，黑色半裙，高跟鞋",
                    personality="聪明机智，善解人意",
                    role="配角"
                ),
            ]
            result.scenes = [
                SceneInfo(
                    name="主场景",
                    location_type="室内",
                    description="根据故事需要设定的主要场景，现代简约风格，光线充足，陈设整洁",
                    lighting="自然光与人工照明结合",
                    atmosphere="符合剧情氛围",
                    time_of_day="白天",
                    weather="晴天"
                ),
                SceneInfo(
                    name="次要场景",
                    location_type="室外",
                    description="户外环境，可以是公园、街道或广场，绿化良好，环境宜人",
                    lighting="自然光",
                    atmosphere="开阔舒适",
                    time_of_day="下午",
                    weather="晴天"
                ),
            ]

        # Add a basic prop
        result.props = [
            PropInfo(
                name="手机",
                category="电子设备",
                description="现代智能手机，黑色外壳，大屏幕",
                material="金属和玻璃",
                size="手掌大小",
                importance="背景道具"
            )
        ]

        # Add detailed shots based on genre
        char_names = [c.name for c in result.characters]
        scene_names = [s.name for s in result.scenes]
        main_char = char_names[0] if char_names else "主角"
        second_char = char_names[1] if len(char_names) > 1 else "配角"
        main_scene = scene_names[0] if scene_names else "主场景"
        second_scene = scene_names[1] if len(scene_names) > 1 else "次要场景"

        if result.genre == "爱情":
            result.shots = [
                ShotInfo(template="全景", description=f"温馨的{main_scene}全景，阳光透过窗户洒入，光影斑驳，温暖而惬意的氛围弥漫整个空间", characters=[], scene=main_scene),
                ShotInfo(template="中景", description=f"{main_char}独自坐在靠窗的位置，神情若有所思，手指轻轻敲打着桌面，眼神中带着淡淡的期待", characters=[main_char], scene=main_scene),
                ShotInfo(template="中景", description=f"{second_char}推门走入，长发随着动作轻轻飘动，一抹温柔的笑容挂在嘴角，像是初春的微风", characters=[second_char], scene=main_scene),
                ShotInfo(template="特写", description=f"{main_char}抬头看见来人，眼睛微微睁大，瞳孔中倒映着{second_char}的身影，嘴角不自觉地上扬", characters=[main_char], scene=main_scene),
                ShotInfo(template="过肩", description=f"从{main_char}肩后望去，{second_char}正走向这边，阳光在她身后形成温暖的光晕，宛如画中人", characters=[main_char, second_char], scene=main_scene),
                ShotInfo(template="中景", description=f"两人面对面坐下，{second_char}双手捧着咖啡杯，微微低头，睫毛投下淡淡的阴影，{main_char}目不转睛地看着她", characters=[main_char, second_char], scene=main_scene),
                ShotInfo(template="全景", description=f"黄昏时分的{second_scene}，暖橙色的晚霞铺满天际，两个人并肩走着，影子在地面拉得很长很长", characters=[main_char, second_char], scene=second_scene),
            ]
            result.style = "电影感"
        elif result.genre == "动作":
            result.shots = [
                ShotInfo(template="全景", description=f"夜幕下的{main_scene}，锈迹斑斑的钢架在月光下投下狰狞的阴影，气氛紧张压抑", characters=[], scene=main_scene),
                ShotInfo(template="中景", description=f"{main_char}警惕地穿行在阴影中，肌肉紧绷，眼神如鹰隼般锐利，随时准备应对危险", characters=[main_char], scene=main_scene),
                ShotInfo(template="特写", description=f"{main_char}的眼睛在黑暗中闪烁着冷光，额头沁出细密的汗珠，嘴唇紧抿成一条线", characters=[main_char], scene=main_scene),
                ShotInfo(template="低角度", description=f"{second_char}从阴影中现身，黑色风衣随风舞动，居高临下地俯视着前方，气势逼人", characters=[second_char], scene=main_scene),
                ShotInfo(template="中景", description=f"两人对峙，空气仿佛凝固，{main_char}握紧双拳，{second_char}冷笑着缓缓逼近", characters=[main_char, second_char], scene=main_scene),
                ShotInfo(template="跟随", description=f"激烈的追逐在{second_scene}展开，{main_char}飞身跃过障碍物，身形矫健如猎豹", characters=[main_char], scene=second_scene),
                ShotInfo(template="全景", description=f"最终对决，两道身影在月光下交锋，拳风呼啸，火花四溅，城市夜景成为壮观的背景", characters=[main_char, second_char], scene=second_scene),
            ]
            result.style = "电影感"
        elif result.genre == "末世":
            third_char = char_names[2] if len(char_names) > 2 else "僵尸"
            result.shots = [
                ShotInfo(template="全景", description=f"{main_scene}的全貌，残破的老虎机闪烁着诡异的光芒，地上散落着筹码和干涸的血迹，空气中弥漫着死亡的气息", characters=[], scene=main_scene),
                ShotInfo(template="中景", description=f"{main_char}小心翼翼地穿行在倒塌的赌桌之间，手中紧握着武器，眼神警惕地扫视四周，每一步都如履薄冰", characters=[main_char], scene=main_scene),
                ShotInfo(template="特写", description=f"{main_char}的脸部特写，额头沁出冷汗，瞳孔收缩，听到远处传来令人毛骨悚然的嘶吼声", characters=[main_char], scene=main_scene),
                ShotInfo(template="中景", description=f"{second_char}在角落里为一名伤员包扎伤口，动作熟练但眼中满是疲惫，背后的医疗包几乎见底", characters=[second_char], scene=main_scene),
                ShotInfo(template="低角度", description=f"一群{third_char}从黑暗中涌出，腐烂的身躯扭曲着向前爬行，血红的眼睛在霓虹残光中闪烁", characters=[third_char], scene=main_scene),
                ShotInfo(template="跟随", description=f"{main_char}拉着{second_char}在{second_scene}上狂奔，身后是穷追不舍的僵尸群，废弃汽车和残骸成为天然路障", characters=[main_char, second_char], scene=second_scene),
                ShotInfo(template="全景", description=f"末日黄昏下的{second_scene}，两个幸存者的身影在废墟中渐行渐远，残破的霓虹灯牌在身后闪烁着最后的光芒", characters=[main_char, second_char], scene=second_scene),
            ]
            result.style = "电影感"
        else:
            result.shots = [
                ShotInfo(template="全景", description=f"{main_scene}的环境全貌，光线明亮，整洁有序，营造出舒适的氛围", characters=[], scene=main_scene),
                ShotInfo(template="中景", description=f"{main_char}站在{main_scene}中央，神情专注，仿佛在思考着什么重要的事情", characters=[main_char], scene=main_scene),
                ShotInfo(template="特写", description=f"{main_char}的面部特写，眼神中透露出坚定和智慧，嘴角带着自信的微笑", characters=[main_char], scene=main_scene),
                ShotInfo(template="中景", description=f"{second_char}走入画面，两人目光交汇，仿佛心意相通，默契十足", characters=[main_char, second_char], scene=main_scene),
                ShotInfo(template="过肩", description=f"从{main_char}背后看去，{second_char}正在说着什么，表情认真而诚恳", characters=[main_char, second_char], scene=main_scene),
                ShotInfo(template="中景", description=f"两人一起走出{main_scene}，来到{second_scene}，阳光洒在他们身上", characters=[main_char, second_char], scene=second_scene),
                ShotInfo(template="全景", description=f"{second_scene}的远景，两个人的身影渐行渐远，画面充满希望和温暖", characters=[main_char, second_char], scene=second_scene),
            ]
            result.style = "电影感"

        return result

    def generate_character_prompt(
        self,
        character: CharacterInfo,
        style: ArtStyle = ArtStyle.REALISTIC
    ) -> str:
        """
        Generate Chinese prompt for character image

        Args:
            character: Character information
            style: Art style to use

        Returns:
            Chinese prompt string for image generation
        """
        style_name = self.STYLE_NAMES.get(style, "写实风格")

        prompt = self.CHARACTER_PROMPT_TEMPLATE.format(
            name=character.name or "角色",
            age=character.age or "未知",
            gender=character.gender or "未知",
            appearance=character.appearance or "普通外貌",
            clothing=character.clothing or "日常服装",
            personality=character.personality or "",
            role=character.role or "角色",
            style=style_name
        )

        success, output = self._call_claude_cli(prompt)
        if success:
            character.generated_prompt = output
            return output
        else:
            # Fallback: Generate basic prompt
            fallback = self._generate_fallback_character_prompt(character, style_name)
            character.generated_prompt = fallback
            return fallback

    def generate_scene_prompt(
        self,
        scene: SceneInfo,
        style: ArtStyle = ArtStyle.REALISTIC
    ) -> str:
        """
        Generate Chinese prompt for scene image

        Args:
            scene: Scene information
            style: Art style to use

        Returns:
            Chinese prompt string for image generation
        """
        style_name = self.STYLE_NAMES.get(style, "写实风格")

        prompt = self.SCENE_PROMPT_TEMPLATE.format(
            name=scene.name or "场景",
            location_type=scene.location_type or "室内",
            description=scene.description or "普通环境",
            lighting=scene.lighting or "自然光",
            atmosphere=scene.atmosphere or "平静",
            time_of_day=scene.time_of_day or "白天",
            weather=scene.weather or "",
            style=style_name
        )

        success, output = self._call_claude_cli(prompt)
        if success:
            scene.generated_prompt = output
            return output
        else:
            # Fallback: Generate basic prompt
            fallback = self._generate_fallback_scene_prompt(scene, style_name)
            scene.generated_prompt = fallback
            return fallback

    def generate_prop_prompt(
        self,
        prop: PropInfo,
        style: ArtStyle = ArtStyle.REALISTIC
    ) -> str:
        """
        Generate Chinese prompt for prop image

        Args:
            prop: Prop information
            style: Art style to use

        Returns:
            Chinese prompt string for image generation
        """
        style_name = self.STYLE_NAMES.get(style, "写实风格")

        prompt = self.PROP_PROMPT_TEMPLATE.format(
            name=prop.name or "道具",
            category=prop.category or "物品",
            description=prop.description or "普通物品",
            material=prop.material or "不明材质",
            size=prop.size or "中等大小",
            style=style_name
        )

        success, output = self._call_claude_cli(prompt)
        if success:
            prop.generated_prompt = output
            return output
        else:
            # Fallback: Generate basic prompt
            fallback = self._generate_fallback_prop_prompt(prop, style_name)
            prop.generated_prompt = fallback
            return fallback

    def _generate_fallback_character_prompt(self, char: CharacterInfo, style: str) -> str:
        """Generate fallback prompt when Claude CLI fails"""
        parts = ["人物立绘"]

        if char.name:
            parts.append(char.name)
        if char.age:
            parts.append(f"{char.age}岁")
        if char.gender:
            parts.append(char.gender)

        if char.appearance:
            parts.append(f"外貌特征：{char.appearance}")
        if char.clothing:
            parts.append(f"服装：{char.clothing}")

        parts.append(style)
        parts.append("高质量，细节丰富，专业水准")

        return "，".join(parts)

    def _generate_fallback_scene_prompt(self, scene: SceneInfo, style: str) -> str:
        """Generate fallback prompt when Claude CLI fails"""
        parts = ["场景概念图"]

        if scene.name:
            parts.append(scene.name)
        if scene.location_type:
            parts.append(f"{scene.location_type}场景")
        if scene.description:
            parts.append(f"环境：{scene.description}")
        if scene.lighting:
            parts.append(f"光线：{scene.lighting}")
        if scene.atmosphere:
            parts.append(f"氛围：{scene.atmosphere}")

        parts.append(style)
        parts.append("高质量，细节丰富，专业水准")

        return "，".join(parts)

    def _generate_fallback_prop_prompt(self, prop: PropInfo, style: str) -> str:
        """Generate fallback prompt when Claude CLI fails"""
        parts = ["道具设定图"]

        if prop.name:
            parts.append(prop.name)
        if prop.category:
            parts.append(prop.category)
        if prop.description:
            parts.append(prop.description)
        if prop.material:
            parts.append(f"材质：{prop.material}")

        parts.append("白色背景")
        parts.append(style)
        parts.append("高质量，细节丰富")

        return "，".join(parts)

    def batch_generate_prompts(
        self,
        analysis: StoryAnalysisResult,
        style: ArtStyle = ArtStyle.REALISTIC
    ) -> StoryAnalysisResult:
        """
        Generate prompts for all extracted assets

        Args:
            analysis: Story analysis result
            style: Art style to use

        Returns:
            Updated StoryAnalysisResult with generated prompts
        """
        # Generate character prompts
        for char in analysis.characters:
            self.generate_character_prompt(char, style)

        # Generate scene prompts
        for scene in analysis.scenes:
            self.generate_scene_prompt(scene, style)

        # Generate prop prompts
        for prop in analysis.props:
            self.generate_prop_prompt(prop, style)

        return analysis


@dataclass
class ReviewResult:
    """Result of quality review"""
    score: float = 0.0  # 1-10
    passed: bool = False
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    summary: str = ""


class QualityReviewer:
    """
    Quality reviewer using Claude CLI
    Reviews generated images against specifications
    """

    REVIEW_PROMPT = """请评估以下AI生成的{asset_type}图像质量。

预期内容:
{expected_content}

生成使用的提示语:
{prompt}

请评估图像是否符合预期，并给出评分和建议。

按以下JSON格式输出（只输出JSON）:
```json
{{
    "score": 评分(1-10的数字),
    "passed": 是否通过(true/false，7分以上为通过),
    "issues": ["问题1", "问题2"],
    "suggestions": ["改进建议1", "改进建议2"],
    "summary": "总体评价（50字以内）"
}}
```"""

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def _call_claude_cli(self, prompt: str) -> Tuple[bool, str]:
        """Call Claude CLI"""
        import shutil
        import platform

        try:
            is_windows = platform.system() == "Windows"

            # 查找 claude 命令
            claude_cmd = None
            if is_windows:
                for cmd in ["claude.cmd", "claude.exe", "claude"]:
                    found = shutil.which(cmd)
                    if found:
                        claude_cmd = found
                        break
            else:
                claude_cmd = shutil.which('claude')

            if not claude_cmd:
                return False, "Claude CLI not found"

            if is_windows:
                # Windows 上使用 shell=True
                escaped_prompt = prompt.replace('"', '\\"')
                cmd_str = f'"{claude_cmd}" -p "{escaped_prompt}" --output-format text'
                result = subprocess.run(
                    cmd_str,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding='utf-8',
                    errors='replace',
                    shell=True
                )
            else:
                result = subprocess.run(
                    [claude_cmd, '-p', prompt, '--output-format', 'text'],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding='utf-8'
                )

            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, result.stderr
        except Exception as e:
            return False, str(e)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text"""
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text.strip()

        try:
            return json.loads(json_str)
        except:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except:
                    pass
            return None

    def review_character(self, character: CharacterInfo) -> ReviewResult:
        """Review generated character image"""
        expected = f"角色: {character.name}, 外貌: {character.appearance}, 服装: {character.clothing}"
        return self._do_review("角色", expected, character.generated_prompt)

    def review_scene(self, scene: SceneInfo) -> ReviewResult:
        """Review generated scene image"""
        expected = f"场景: {scene.name}, 描述: {scene.description}, 氛围: {scene.atmosphere}"
        return self._do_review("场景", expected, scene.generated_prompt)

    def review_prop(self, prop: PropInfo) -> ReviewResult:
        """Review generated prop image"""
        expected = f"道具: {prop.name}, 描述: {prop.description}, 材质: {prop.material}"
        return self._do_review("道具", expected, prop.generated_prompt)

    def _do_review(self, asset_type: str, expected: str, prompt: str) -> ReviewResult:
        """Perform the review"""
        result = ReviewResult()

        review_prompt = self.REVIEW_PROMPT.format(
            asset_type=asset_type,
            expected_content=expected,
            prompt=prompt
        )

        success, output = self._call_claude_cli(review_prompt)
        if not success:
            result.summary = f"Review failed: {output}"
            result.score = 5.0  # Default score
            return result

        data = self._extract_json(output)
        if not data:
            result.summary = "Failed to parse review response"
            result.score = 5.0
            return result

        result.score = float(data.get("score", 5))
        result.passed = data.get("passed", result.score >= 7)
        result.issues = data.get("issues", [])
        result.suggestions = data.get("suggestions", [])
        result.summary = data.get("summary", "")

        return result


# Factory functions
def create_ai_generator(timeout: int = 120) -> AICreativeGenerator:
    """Create AI creative generator"""
    return AICreativeGenerator(timeout=timeout)


def create_quality_reviewer(timeout: int = 60) -> QualityReviewer:
    """Create quality reviewer"""
    return QualityReviewer(timeout=timeout)


# Test function
if __name__ == "__main__":
    # Test story analysis
    test_story = """
    咖啡厅的午后，阳光透过落地窗洒入室内。

    李明，一个28岁的年轻作家，戴着黑框眼镜，穿着深蓝色毛衣，正坐在靠窗的位置，
    面前是一台银色笔记本电脑。他眉头微皱，似乎在思考着什么。

    王薇推门走了进来，她26岁，是一名设计师，长发披肩，穿着白色连衣裙，
    脚踩小白鞋，手里拿着一本素描本。她环顾四周，寻找着空位。

    咖啡厅里弥漫着咖啡的香气，木质桌椅整齐排列，绿色植物点缀在各处，
    营造出温馨舒适的氛围。
    """

    generator = create_ai_generator()

    print("Analyzing story...")
    result = generator.analyze_story(test_story)

    if result.success:
        print(f"Project: {result.project_name}")
        print(f"Genre: {result.genre}")
        print(f"\nCharacters ({len(result.characters)}):")
        for char in result.characters:
            print(f"  - {char.name}: {char.appearance}")

        print(f"\nScenes ({len(result.scenes)}):")
        for scene in result.scenes:
            print(f"  - {scene.name}: {scene.description[:50]}...")

        print(f"\nProps ({len(result.props)}):")
        for prop in result.props:
            print(f"  - {prop.name}: {prop.description}")

        # Generate prompts
        print("\nGenerating prompts...")
        generator.batch_generate_prompts(result, ArtStyle.REALISTIC)

        for char in result.characters:
            print(f"\n[{char.name}] Prompt:")
            print(f"  {char.generated_prompt[:100]}...")
    else:
        print(f"Analysis failed: {result.error}")
