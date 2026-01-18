"""
智能导入模块 - 支持多种格式文件的解析和AI分析
支持格式: PDF, Word, Markdown, 图片(JPG/PNG), 网页(HTML)
通过 Claude CLI 进行智能分类整理规划
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re

# 文件解析库
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from PIL import Image
except ImportError:
    Image = None


class FileParser:
    """多格式文件解析器"""

    @staticmethod
    def parse_pdf(filepath: str) -> str:
        """解析PDF文件"""
        if PyPDF2 is None:
            return "[错误] 未安装PyPDF2库"

        try:
            text_content = []
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            return "\n\n".join(text_content)
        except Exception as e:
            return f"[错误] PDF解析失败: {str(e)}"

    @staticmethod
    def parse_word(filepath: str) -> str:
        """解析Word文档"""
        if DocxDocument is None:
            return "[错误] 未安装python-docx库"

        try:
            doc = DocxDocument(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            return f"[错误] Word解析失败: {str(e)}"

    @staticmethod
    def parse_markdown(filepath: str) -> str:
        """解析Markdown文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # 返回原始Markdown文本，保留格式信息
            return content
        except Exception as e:
            return f"[错误] Markdown解析失败: {str(e)}"

    @staticmethod
    def parse_html(filepath: str) -> str:
        """解析HTML/网页文件"""
        if BeautifulSoup is None:
            return "[错误] 未安装beautifulsoup4库"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator='\n')
            # 清理多余空行
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)
        except Exception as e:
            return f"[错误] HTML解析失败: {str(e)}"

    @staticmethod
    def parse_image(filepath: str) -> str:
        """解析图片文件 - 返回图片描述占位符"""
        if Image is None:
            return "[错误] 未安装Pillow库"

        try:
            img = Image.open(filepath)
            width, height = img.size
            mode = img.mode
            filename = os.path.basename(filepath)

            return f"""[图片文件]
文件名: {filename}
尺寸: {width}x{height}
模式: {mode}

请根据图片内容描述场景或角色。
图片路径: {filepath}
"""
        except Exception as e:
            return f"[错误] 图片解析失败: {str(e)}"

    @staticmethod
    def parse_text(filepath: str) -> str:
        """解析纯文本文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception as e:
                return f"[错误] 文本解析失败: {str(e)}"

    @classmethod
    def parse_file(cls, filepath: str) -> Tuple[str, str]:
        """
        根据文件类型自动选择解析器
        返回: (文件类型, 解析内容)
        """
        ext = Path(filepath).suffix.lower()

        parsers = {
            '.pdf': ('PDF', cls.parse_pdf),
            '.docx': ('Word', cls.parse_word),
            '.doc': ('Word', cls.parse_word),
            '.md': ('Markdown', cls.parse_markdown),
            '.markdown': ('Markdown', cls.parse_markdown),
            '.html': ('HTML', cls.parse_html),
            '.htm': ('HTML', cls.parse_html),
            '.jpg': ('图片', cls.parse_image),
            '.jpeg': ('图片', cls.parse_image),
            '.png': ('图片', cls.parse_image),
            '.txt': ('文本', cls.parse_text),
        }

        if ext in parsers:
            file_type, parser = parsers[ext]
            content = parser(filepath)
            return file_type, content
        else:
            return '未知', f"[错误] 不支持的文件格式: {ext}"


class ClaudeAnalyzer:
    """使用Claude CLI进行智能分析"""

    ANALYSIS_PROMPT = """请分析以下内容，将其转换为分镜脚本格式。

输入内容:
{content}

请按照以下JSON格式输出分镜规划:
```json
{{
    "project_name": "项目名称",
    "description": "项目描述",
    "aspect_ratio": "16:9",
    "style": "电影感",
    "characters": [
        {{"name": "角色名", "description": "角色外貌、服装、特征描述"}}
    ],
    "scenes": [
        {{"name": "场景名", "description": "场景环境、光线、氛围描述"}}
    ],
    "shots": [
        {{
            "template": "全景/中景/特写/过肩/低角度/跟随",
            "description": "镜头描述",
            "characters": ["出镜角色名"],
            "scene": "场景名"
        }}
    ]
}}
```

分析要求:
1. 识别文本中的角色，提取外貌特征
2. 识别场景/地点，描述环境氛围
3. 将故事分解为合适的镜头序列
4. 选择合适的镜头类型（全景用于建立场景，中景用于对话，特写用于情感表达等）
5. 确保镜头之间有良好的叙事连贯性

只输出JSON，不要其他解释。"""

    @classmethod
    def analyze_with_claude(cls, content: str, file_type: str) -> Tuple[bool, str]:
        """
        调用Claude CLI分析内容
        返回: (成功与否, JSON字符串或错误信息)
        """
        prompt = cls.ANALYSIS_PROMPT.format(content=content[:8000])  # 限制长度

        try:
            # 创建临时文件存储prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(prompt)
                prompt_file = f.name

            # 调用Claude CLI
            result = subprocess.run(
                ['claude', '-p', prompt, '--output-format', 'text'],
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8'
            )

            # 清理临时文件
            os.unlink(prompt_file)

            if result.returncode == 0:
                output = result.stdout
                # 提取JSON部分
                json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接解析整个输出
                    json_str = output.strip()

                # 验证JSON格式
                try:
                    json.loads(json_str)
                    return True, json_str
                except json.JSONDecodeError:
                    return False, f"Claude返回的不是有效JSON:\n{output}"
            else:
                return False, f"Claude CLI错误: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Claude CLI超时"
        except FileNotFoundError:
            return False, "未找到Claude CLI，请确保已安装并配置PATH"
        except Exception as e:
            return False, f"调用Claude CLI失败: {str(e)}"

    @classmethod
    def generate_default_analysis(cls, content: str, file_type: str) -> str:
        """
        当Claude CLI不可用时，生成默认分析模板
        """
        # 简单的文本分析
        lines = content.split('\n')
        title = lines[0][:50] if lines else "未命名项目"

        default_json = {
            "project_name": title,
            "description": f"从{file_type}文件导入的项目",
            "aspect_ratio": "16:9",
            "style": "电影感",
            "characters": [
                {"name": "角色1", "description": "请填写角色描述"},
                {"name": "角色2", "description": "请填写角色描述"}
            ],
            "scenes": [
                {"name": "场景1", "description": "请填写场景描述"}
            ],
            "shots": [
                {
                    "template": "全景",
                    "description": "开场镜头 - 请编辑描述",
                    "characters": [],
                    "scene": "场景1"
                },
                {
                    "template": "中景",
                    "description": "主要镜头 - 请编辑描述",
                    "characters": ["角色1"],
                    "scene": "场景1"
                }
            ]
        }

        return json.dumps(default_json, ensure_ascii=False, indent=2)


class SmartImporter:
    """智能导入器 - 整合文件解析和AI分析"""

    def __init__(self):
        self.parser = FileParser()
        self.analyzer = ClaudeAnalyzer()

    def import_file(self, filepath: str, use_claude: bool = True) -> Dict[str, Any]:
        """
        导入文件并分析
        返回: {
            'success': bool,
            'file_type': str,
            'raw_content': str,
            'analyzed_json': str,
            'message': str
        }
        """
        result = {
            'success': False,
            'file_type': '',
            'raw_content': '',
            'analyzed_json': '',
            'message': ''
        }

        # 检查文件是否存在
        if not os.path.exists(filepath):
            result['message'] = f"文件不存在: {filepath}"
            return result

        # 解析文件
        file_type, content = self.parser.parse_file(filepath)
        result['file_type'] = file_type
        result['raw_content'] = content

        if content.startswith('[错误]'):
            result['message'] = content
            return result

        # AI分析
        if use_claude:
            success, json_str = self.analyzer.analyze_with_claude(content, file_type)
            if success:
                result['success'] = True
                result['analyzed_json'] = json_str
                result['message'] = f"成功分析{file_type}文件"
            else:
                # Claude失败，使用默认模板
                result['success'] = True
                result['analyzed_json'] = self.analyzer.generate_default_analysis(content, file_type)
                result['message'] = f"Claude分析失败，已生成默认模板。原因: {json_str}"
        else:
            result['success'] = True
            result['analyzed_json'] = self.analyzer.generate_default_analysis(content, file_type)
            result['message'] = f"已从{file_type}文件生成默认模板"

        return result

    def import_multiple_files(self, filepaths: List[str]) -> Dict[str, Any]:
        """
        导入多个文件并合并分析
        """
        all_content = []
        file_types = []

        for filepath in filepaths:
            file_type, content = self.parser.parse_file(filepath)
            if not content.startswith('[错误]'):
                all_content.append(f"=== {os.path.basename(filepath)} ({file_type}) ===\n{content}")
                file_types.append(file_type)

        if not all_content:
            return {
                'success': False,
                'message': "没有成功解析任何文件"
            }

        combined_content = "\n\n".join(all_content)

        # 分析合并内容
        success, json_str = self.analyzer.analyze_with_claude(combined_content, '+'.join(set(file_types)))

        return {
            'success': success,
            'file_types': file_types,
            'raw_content': combined_content,
            'analyzed_json': json_str if success else self.analyzer.generate_default_analysis(combined_content, 'mixed'),
            'message': f"成功分析{len(filepaths)}个文件" if success else "使用默认模板"
        }


def validate_and_fix_json(json_str: str) -> Tuple[bool, str, str]:
    """
    验证并修复JSON格式
    返回: (是否有效, 修复后的JSON, 错误信息)
    """
    try:
        data = json.loads(json_str)

        # 验证必需字段
        required_fields = ['project_name', 'characters', 'scenes', 'shots']
        for field in required_fields:
            if field not in data:
                data[field] = [] if field in ['characters', 'scenes', 'shots'] else "未命名"

        # 设置默认值
        data.setdefault('description', '')
        data.setdefault('aspect_ratio', '16:9')
        data.setdefault('style', '电影感')

        return True, json.dumps(data, ensure_ascii=False, indent=2), ""
    except json.JSONDecodeError as e:
        return False, json_str, f"JSON格式错误: {str(e)}"


# 测试函数
if __name__ == "__main__":
    importer = SmartImporter()

    # 测试文件解析
    test_content = """
    # 咖啡厅的故事

    ## 角色
    - 小明：25岁程序员，戴眼镜，穿格子衫
    - 小红：23岁设计师，长发，穿白裙

    ## 场景
    咖啡厅内，阳光透过玻璃窗洒入

    ## 剧情
    小明在咖啡厅写代码，小红走进来找座位...
    """

    # 生成默认分析
    json_result = ClaudeAnalyzer.generate_default_analysis(test_content, "Markdown")
    print("默认分析结果:")
    print(json_result)
