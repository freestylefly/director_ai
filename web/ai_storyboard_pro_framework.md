# AI 分镜生成器 Pro 方案框架

## 一、系统定位

一套基于多源视觉参考的智能分镜生成系统，核心能力是将分散的角色、场景、道具、风格参考图融合为连贯的分镜序列，同时保持跨镜头的视觉一致性。

**技术底座**：Nana Banana Pro 模型作为统一的一致性引擎，所有视觉元素的锁定与生成均通过该模型完成。

---

## 二、输入层架构

### 2.1 五槽位参考系统

| 槽位 | 功能 | 输入形式 | 处理策略 |
|-----|------|---------|---------|
| **角色槽** | 定义出镜人物 | 1-5张人物参考图/角色 | 视觉注入（高保真） |
| **场景槽** | 定义空间环境 | 1-3张场景参考图 | 视觉注入 + 语义补充 |
| **道具槽** | 定义关键物品 | 单物品抠图或完整图 | 视觉注入（局部） |
| **风格槽** | 定义视觉调性 | 风格参考图或预设选择 | 语义提取为主，视觉为辅 |
| **叙事槽** | 定义内容骨架 | 文本大纲/剧本片段 | 纯文本解析 |

### 2.2 角色槽深化设计

每个角色作为独立实体管理，支持多角色并行：

```
角色实体结构：
├── 角色ID（唯一标识）
├── 角色名称（用于剧本关联）
├── 参考图集（3-5张为宜，涵盖正面/侧面/不同表情）
├── 特征锁定项
│   ├── 面部特征（强制锁定）
│   ├── 体型比例（强制锁定）
│   ├── 标志性服装（可选锁定）
│   └── 发型发色（强制锁定）
└── 一致性权重（默认0.8，可调0.5-1.0）
```

### 2.3 场景槽深化设计

场景需要同时锁定空间结构和氛围调性：

```
场景实体结构：
├── 场景ID
├── 场景名称（如"主角公寓客厅"）
├── 空间参考图（定义物理布局）
├── 氛围参考图（可选，定义光照/时间段）
├── 空间描述文本（补充参考图未覆盖的细节）
├── 锁定项
│   ├── 空间结构（强制）
│   ├── 光照方向（推荐锁定）
│   └── 色温基调（推荐锁定）
└── 一致性权重（默认0.6）
```

### 2.4 道具槽深化设计

关键道具需要跨镜头保持外观一致：

```
道具实体结构：
├── 道具ID
├── 道具名称（如"魔法书"、"祖传手表"）
├── 参考图（最好是白底抠图或多角度展示）
├── 尺寸参照（相对于人物的比例描述）
├── 材质描述（金属/木质/布料等）
└── 一致性权重（默认0.7）
```

### 2.5 风格槽深化设计

风格采用混合策略——优先语义化，复杂风格才用视觉注入：

```
风格配置结构：
├── 风格模式
│   ├── 预设风格（从风格库选择）
│   ├── 参考图风格（上传风格参考）
│   └── 自定义描述（纯文本定义）
├── 风格维度
│   ├── 渲染类型（写实/插画/3D渲染/水彩...）
│   ├── 色彩倾向（暖调/冷调/高饱和/低饱和...）
│   ├── 光影风格（自然光/影棚光/霓虹/逆光...）
│   └── 画面质感（电影胶片/数码清晰/噪点颗粒...）
└── 风格权重（默认0.4，建议不超过0.5以免干扰角色）
```

---

## 三、9宫镜头模版系统

### 3.1 模版总览

按叙事功能分为三大类九种基础镜头：

```
┌─────────────────────────────────────────────────────────────┐
│                      建 立 类                                │
│  （交代环境、建立空间感）                                      │
├───────────────────┬───────────────────┬───────────────────┤
│   T1 全景俯瞰      │   T2 环境中景      │   T3 框中框        │
│   上帝视角         │   人景平衡         │   空间层次感       │
├───────────────────┴───────────────────┴───────────────────┤
│                      聚 焦 类                                │
│  （突出角色、引导注意力）                                      │
├───────────────────┬───────────────────┬───────────────────┤
│   T4 标准中景      │   T5 过肩镜头      │   T6 特写          │
│   叙事主力         │   对话场景         │   情绪放大         │
├───────────────────┴───────────────────┴───────────────────┤
│                      动 势 类                                │
│  （营造氛围、增强代入感）                                      │
├───────────────────┬───────────────────┬───────────────────┤
│   T7 低角度仰拍    │   T8 跟随视角      │   T9 主观镜头      │
│   力量/压迫感      │   沉浸跟随         │   第一人称         │
└───────────────────┴───────────────────┴───────────────────┘
```

### 3.2 各模版详细参数

#### T1 全景俯瞰 (Establishing Wide)

```yaml
camera:
  distance: extreme_wide
  vertical_angle: -45  # 负值为俯视
  horizontal_angle: 0
  focal_length: 24mm
  
composition:
  subject_scale: 0.1-0.2  # 角色占画面比例
  horizon_position: upper_third
  depth_layers: 3  # 前中后景层次
  
slot_weights:
  character: 0.5  # 降权，角色只是环境点缀
  scene: 0.9      # 主导
  props: 0.3
  style: 0.4
  
typical_use: 开场建立、场景转换、时间流逝
```

#### T2 环境中景 (Medium Wide)

```yaml
camera:
  distance: wide
  vertical_angle: 0  # 平视
  horizontal_angle: 0-15
  focal_length: 35mm
  
composition:
  subject_scale: 0.3-0.4
  horizon_position: middle
  rule_of_thirds: true
  subject_position: left_third | right_third
  
slot_weights:
  character: 0.7
  scene: 0.7
  props: 0.5
  style: 0.4
  
typical_use: 角色入场、环境互动、群像展示
```

#### T3 框中框 (Framed Shot)

```yaml
camera:
  distance: medium_wide
  vertical_angle: 0
  horizontal_angle: 0
  focal_length: 50mm
  
composition:
  frame_element: door | window | arch | foliage
  subject_scale: 0.25-0.35
  foreground_blur: true
  depth_of_field: shallow
  
slot_weights:
  character: 0.7
  scene: 0.8
  props: 0.8  # 框体元素可能来自道具槽
  style: 0.4
  
typical_use: 空间转场、偷窥视角、增加层次
```

#### T4 标准中景 (Medium Shot)

```yaml
camera:
  distance: medium
  vertical_angle: 0
  horizontal_angle: 0-10
  focal_length: 50mm
  
composition:
  framing: waist_up
  subject_scale: 0.5-0.6
  headroom: 10%
  looking_room: true  # 角色视线方向留白
  
slot_weights:
  character: 0.85
  scene: 0.5
  props: 0.6
  style: 0.4
  
typical_use: 对话、独白、常规叙事
```

#### T5 过肩镜头 (Over-the-Shoulder)

```yaml
camera:
  distance: medium
  vertical_angle: 0-5
  horizontal_angle: 20-30
  focal_length: 50mm
  
composition:
  foreground_character: back_shoulder_visible
  foreground_blur: slight
  focus_character: face_clear
  subject_scale: 0.4
  
slot_weights:
  character_fg: 0.6  # 前景角色降权
  character_bg: 0.85  # 焦点角色保持高权重
  scene: 0.4
  props: 0.5
  style: 0.4
  
special_requirement: 需要同时调用两个角色槽实例
typical_use: 双人对话、对峙、访谈
```

#### T6 特写 (Close-up)

```yaml
camera:
  distance: close
  vertical_angle: 0-5
  horizontal_angle: 0-15
  focal_length: 85mm
  
composition:
  framing: face | object
  subject_scale: 0.7-0.9
  background_blur: heavy
  eye_level: middle_frame  # 眼睛在画面中部
  
slot_weights:
  character: 0.95  # 最高权重
  scene: 0.2      # 几乎忽略，背景虚化
  props: 0.8      # 如果是道具特写则主导
  style: 0.3
  
typical_use: 情绪表达、重要道具展示、悬念揭示
```

#### T7 低角度仰拍 (Low Angle)

```yaml
camera:
  distance: medium | medium_wide
  vertical_angle: 15-30  # 正值为仰视
  horizontal_angle: 0
  focal_length: 35mm
  
composition:
  subject_scale: 0.5-0.7
  sky_visible: often
  foreshortening: slight
  power_dynamic: subject_dominant
  
slot_weights:
  character: 0.85
  scene: 0.6
  props: 0.5
  style: 0.4
  
typical_use: 英雄出场、权威展示、压迫感营造
```

#### T8 跟随视角 (Following Shot)

```yaml
camera:
  distance: medium
  vertical_angle: 5-10  # 略高于角色
  horizontal_angle: 0  # 正后方
  focal_length: 35mm
  
composition:
  subject_position: center_lower
  subject_visibility: back_view
  subject_scale: 0.3-0.5
  environment_reveal: progressive
  
slot_weights:
  character: 0.75  # 背影，可略降
  scene: 0.8       # 环境展示重要
  props: 0.5
  style: 0.4
  
special_requirement: 角色槽需要背影参考或系统自动推断
typical_use: 角色移动、探索未知、制造悬念
```

#### T9 主观镜头 (POV Shot)

```yaml
camera:
  distance: variable
  vertical_angle: variable  # 模拟角色视线
  horizontal_angle: variable
  focal_length: 35-50mm
  
composition:
  pov_owner: specified_character
  owner_visible: false  # 视角主人不出镜
  hand_visible: optional  # 可选显示角色的手
  focus_target: scene | other_character | object
  
slot_weights:
  character: 0.3   # 仅用于可能出现的手部
  scene: 0.85      # 主导
  props: 0.8       # 视线焦点可能是道具
  style: 0.4
  
typical_use: 发现场景、阅读文件、观察他人
```

---

## 四、一致性控制引擎

### 4.1 Nana Banana Pro 集成架构

所有视觉元素的一致性锁定统一通过 Nana Banana Pro 模型实现：

```
┌────────────────────────────────────────────────────────────────┐
│                    一致性控制流程                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  参考图输入 ──→ 特征提取器 ──→ 特征向量库                        │
│      │              │              │                           │
│      │              ▼              │                           │
│      │     ┌───────────────┐      │                           │
│      │     │ Nana Banana   │      │                           │
│      └────→│    Pro        │←─────┘                           │
│            │   Engine      │                                   │
│            └───────┬───────┘                                   │
│                    │                                           │
│                    ▼                                           │
│            ┌───────────────┐                                   │
│            │  权重混合器    │←── 镜头模版权重配置                │
│            └───────┬───────┘                                   │
│                    │                                           │
│                    ▼                                           │
│            ┌───────────────┐                                   │
│            │  图像生成      │←── Prompt（来自叙事槽+风格槽）     │
│            └───────┬───────┘                                   │
│                    │                                           │
│                    ▼                                           │
│              最终分镜图像                                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 多槽位权重融合策略

当多个槽位同时作用时，采用加权融合而非简单叠加：

```python
# 伪代码示意
def compute_final_weights(shot_template, user_overrides=None):
    # 获取模版默认权重
    base_weights = TEMPLATE_WEIGHTS[shot_template]
    
    # 应用用户自定义覆盖
    if user_overrides:
        for slot, weight in user_overrides.items():
            base_weights[slot] = weight
    
    # 权重归一化（确保总权重不超载）
    total = sum(base_weights.values())
    if total > 2.5:  # 经验阈值，过高会导致生成混乱
        scale_factor = 2.5 / total
        base_weights = {k: v * scale_factor for k, v in base_weights.items()}
    
    return base_weights
```

### 4.3 冲突解决机制

当不同槽位的参考图存在视觉冲突时：

**优先级规则**（从高到低）：
1. 角色面部特征（最高优先，不可妥协）
2. 角色体型服装
3. 道具外观
4. 场景空间结构
5. 场景光照氛围
6. 整体风格调性（最低优先，必要时牺牲）

**实际处理**：
- 如果风格参考图中有人物，系统自动提取纯风格特征，过滤人物信息
- 如果场景参考图的光照与风格槽冲突，以风格槽为准
- 如果道具比例与场景比例不协调，以场景为基准缩放道具

---

## 五、处理层工作流

### 5.1 分镜生成流水线

```
输入 ──→ 预处理 ──→ 分镜规划 ──→ 逐帧生成 ──→ 一致性校验 ──→ 输出
```

**阶段一：预处理**
- 解析所有槽位输入
- 对每个参考图进行特征提取
- 建立角色/场景/道具的特征向量索引
- 风格槽语义化提取（生成风格描述文本）

**阶段二：分镜规划**
- 解析叙事槽文本，识别场景切换点
- 根据叙事节奏自动推荐镜头模版序列
- 用户可手动调整镜头选择
- 为每个分镜分配所需槽位实例（哪些角色出镜、在哪个场景）

**阶段三：逐帧生成**
- 按分镜序列顺序执行
- 每帧调用 Nana Banana Pro 引擎
- 输入：镜头模版参数 + 槽位权重 + 对应参考图 + 生成prompt
- 输出：单帧分镜图像

**阶段四：一致性校验**
- 对生成的分镜序列进行一致性评分
- 检测项：角色面部相似度、服装连续性、场景连贯性
- 低于阈值的帧标记为需重新生成
- 支持单帧重生成而不影响整体

### 5.2 Prompt 自动构建

每个分镜的最终 Prompt 由多个来源自动拼装：

```
[镜头描述] + [角色描述] + [动作描述] + [场景描述] + [风格描述] + [技术参数]

示例：
"medium shot, slight low angle, [character_A] standing with arms crossed, 
confident expression, looking at camera, in [scene_office] modern office 
with floor-to-ceiling windows, afternoon sunlight, [style] cinematic 
lighting, film grain, shallow depth of field, 8K resolution"
```

其中 `[character_A]`、`[scene_office]`、`[style]` 为占位符，由系统自动关联到对应槽位的特征向量。

---

## 六、输出层设计

### 6.1 输出格式矩阵

| 输出类型 | 格式 | 用途 |
|---------|------|------|
| 分镜图像序列 | PNG/JPG | 视觉预览、汇报展示 |
| 分镜板文档 | PDF | 打印、传阅、存档 |
| 结构化数据 | JSON | 下游系统对接、二次编辑 |
| 项目工程文件 | 自定义格式 | 保存完整项目状态，支持重新打开编辑 |

### 6.2 JSON 输出结构

```json
{
  "project_meta": {
    "name": "项目名称",
    "created_at": "2025-01-05T10:30:00Z",
    "version": "1.0"
  },
  "references": {
    "characters": [
      {
        "id": "char_001",
        "name": "主角张三",
        "ref_images": ["uploads/char_001_front.png", "uploads/char_001_side.png"],
        "features_locked": ["face", "body_type", "hair"]
      }
    ],
    "scenes": [
      {
        "id": "scene_001", 
        "name": "公司办公室",
        "ref_image": "uploads/office_ref.png",
        "description": "现代风格开放式办公区，落地窗，白色调"
      }
    ],
    "props": [
      {
        "id": "prop_001",
        "name": "神秘信封",
        "ref_image": "uploads/envelope.png"
      }
    ],
    "style": {
      "mode": "reference_image",
      "ref_image": "uploads/style_cinematic.png",
      "description": "电影感，胶片质感，青橙色调"
    }
  },
  "storyboard": [
    {
      "shot_number": 1,
      "template": "T2_environment_medium",
      "description": "张三走进办公室",
      "characters_in_shot": ["char_001"],
      "scene": "scene_001",
      "props_in_shot": [],
      "camera": {
        "distance": "wide",
        "vertical_angle": 0,
        "horizontal_angle": 10,
        "focal_length": 35
      },
      "slot_weights": {
        "character": 0.7,
        "scene": 0.7,
        "props": 0,
        "style": 0.4
      },
      "generated_prompt": "medium wide shot, [char_001] walking into frame...",
      "output_image": "outputs/shot_001.png",
      "consistency_score": 0.92
    },
    {
      "shot_number": 2,
      "template": "T6_closeup",
      "description": "张三注意到桌上的信封",
      "characters_in_shot": ["char_001"],
      "scene": "scene_001",
      "props_in_shot": ["prop_001"],
      "camera": {
        "distance": "close",
        "vertical_angle": -10,
        "horizontal_angle": 0,
        "focal_length": 85
      },
      "slot_weights": {
        "character": 0.5,
        "scene": 0.2,
        "props": 0.85,
        "style": 0.3
      },
      "generated_prompt": "close-up shot of mysterious envelope on desk...",
      "output_image": "outputs/shot_002.png",
      "consistency_score": 0.95
    }
  ]
}
```

### 6.3 分镜板可视化布局

```
┌─────────────────────────────────────────────────────────────────┐
│  AI 分镜生成器 Pro - 项目：《办公室悬疑》                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Shot 1    │  │   Shot 2    │  │   Shot 3    │             │
│  │  [图像区]   │  │  [图像区]   │  │  [图像区]   │             │
│  │             │  │             │  │             │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ T2 环境中景 │  │ T6 特写     │  │ T5 过肩     │             │
│  │ 张三入场    │  │ 信封特写    │  │ 张三拆信    │             │
│  │ 场景:办公室 │  │ 道具:信封   │  │ 双角色      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Shot 4    │  │   Shot 5    │  │   Shot 6    │             │
│  │  [图像区]   │  │  [图像区]   │  │  [图像区]   │             │
│  │             │  │             │  │             │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ T4 标准中景 │  │ T9 主观     │  │ T7 仰拍     │             │
│  │ 阅读信件    │  │ 信件内容    │  │ 震惊反应    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、用户界面流程

### 7.1 主要操作流程

```
Step 1: 创建项目
    └── 输入项目名称、选择画幅比例（16:9 / 9:16 / 1:1）

Step 2: 配置参考素材
    ├── 上传/创建角色（支持多角色）
    ├── 上传/创建场景（支持多场景）
    ├── 上传关键道具（可选）
    └── 选择/上传风格参考

Step 3: 编写叙事大纲
    └── 文本输入或导入剧本片段

Step 4: 生成分镜规划
    ├── 系统自动推荐镜头序列
    └── 用户手动调整（增删改镜头、更换模版）

Step 5: 执行生成
    ├── 逐帧生成预览
    ├── 一致性检查
    └── 问题帧重新生成

Step 6: 导出
    └── 选择输出格式，下载成品
```

### 7.2 界面布局建议

```
┌────────────────────────────────────────────────────────────────────┐
│  [项目名] [保存] [导出]                              [设置] [帮助] │
├──────────────┬─────────────────────────────────────────────────────┤
│              │                                                     │
│   素材面板   │                    分镜画布                          │
│              │                                                     │
│  ┌────────┐  │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
│  │ 角色   │  │   │ S1  │ │ S2  │ │ S3  │ │ S4  │ │ S5  │ ...     │
│  ├────────┤  │   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘         │
│  │ 场景   │  │                                                     │
│  ├────────┤  │   ┌─────────────────────────────────────────────┐   │
│  │ 道具   │  │   │                                             │   │
│  ├────────┤  │   │              当前帧大图预览                  │   │
│  │ 风格   │  │   │                                             │   │
│  └────────┘  │   │                                             │   │
│              │   └─────────────────────────────────────────────┘   │
│              │                                                     │
├──────────────┴─────────────────────────────────────────────────────┤
│                           属性编辑区                               │
│  当前帧: Shot 3 | 模版: T5过肩 | 角色: 张三,李四 | 场景: 办公室    │
│  [镜头参数调整] [权重滑块] [Prompt微调] [重新生成此帧]              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 八、技术实现路径

### 8.1 推荐技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| 前端界面 | React + TypeScript | 组件化开发，类型安全 |
| 画布交互 | Fabric.js 或 Konva | 分镜板拖拽、缩放 |
| 后端服务 | Python FastAPI | 处理生成请求、管理队列 |
| 生成引擎 | Nana Banana Pro API | 核心图像生成与一致性控制 |
| 存储 | PostgreSQL + S3 | 项目数据 + 图像资源 |
| 任务队列 | Celery + Redis | 异步处理生成任务 |

### 8.2 简化实现路径（MVP）

如果先做最小可行产品验证概念：

| 组件 | MVP方案 |
|-----|---------|
| 界面 | Gradio 快速搭建 |
| 生成引擎 | 直接调用 Nana Banana Pro 接口 |
| 存储 | 本地文件系统 |
| 分镜规划 | 手动配置，暂不做自动推荐 |

---

## 九、扩展功能规划

### 9.1 Phase 2 功能

- **自动分镜建议**：根据叙事文本，AI自动推荐镜头类型和序列
- **镜头语法检查**：检测常见分镜错误（如180度轴线问题）
- **批量风格迁移**：一键将整个项目切换到新风格
- **角色表情库**：为每个角色预生成多种表情，分镜时直接选用

### 9.2 Phase 3 功能

- **动态分镜**：生成带有简单镜头运动的短视频片段
- **AI配乐建议**：根据分镜情绪推荐背景音乐
- **多人协作**：团队共同编辑同一分镜项目
- **版本管理**：分镜修改历史追溯与比较

---

## 十、附录

### A. 镜头模版快速参考卡

| 模版 | 简称 | 距离 | 垂直角度 | 典型权重(角/景/道/风) |
|-----|------|------|---------|---------------------|
| T1 全景俯瞰 | EST-W | 远 | -45° | 0.5/0.9/0.3/0.4 |
| T2 环境中景 | ENV-M | 中远 | 0° | 0.7/0.7/0.5/0.4 |
| T3 框中框 | FRM | 中远 | 0° | 0.7/0.8/0.8/0.4 |
| T4 标准中景 | STD-M | 中 | 0° | 0.85/0.5/0.6/0.4 |
| T5 过肩 | OTS | 中 | 0-5° | 0.6+0.85/0.4/0.5/0.4 |
| T6 特写 | CU | 近 | 0-5° | 0.95/0.2/0.8/0.3 |
| T7 低角度 | LA | 中 | +15-30° | 0.85/0.6/0.5/0.4 |
| T8 跟随 | FOL | 中 | +5-10° | 0.75/0.8/0.5/0.4 |
| T9 主观 | POV | 可变 | 可变 | 0.3/0.85/0.8/0.4 |

### B. 常见问题处理

**Q: 角色在不同镜头中面部不一致怎么办？**
A: 提高角色槽权重至0.9以上，确保参考图包含多角度面部照片，必要时单独为该帧重新生成。

**Q: 风格参考图中的人物特征渗透到了我的角色上？**
A: 将风格槽切换为"纯文本模式"，手动描述风格特征而非使用图片参考；或降低风格权重至0.3以下。

**Q: 场景在连续镜头中光照方向不一致？**
A: 在场景槽中明确指定光照方向描述（如"窗户在画面左侧，自然光从左侧照入"），并在每帧prompt中保持一致。

**Q: 道具比例在不同景别中不协调？**
A: 在道具槽中添加比例参照描述（如"信封大小约为成年人手掌大小"），系统会据此在不同景别中自动调整。

---

*文档版本: v1.0*
*最后更新: 2025-01-05*
