# 苍何 API 接口文档

> Base URL: `https://api.canghe.ai`
> 认证方式: `Authorization: Bearer YOUR_API_KEY`

---

## 快速开始

### 在 AI 分镜 Pro 中使用

1. 打开应用，在右侧面板找到 **🎨 图像生成** 配置
2. 选择 **苍何 API (云端)**
3. 输入你的 API Key
4. 选择模型：
   - **Nano-Banana (Google Imagen)**: 高质量图像，推荐
   - **即梦 (Jimeng)**: 字节跳动模型，支持中文
5. 点击 **保存配置**

### 环境变量配置

```bash
# .env 文件
IMAGE_BACKEND=canghe
CANGHE_API_KEY=your_api_key_here
```

---

## 一、Chat Completions (聊天补全)

### 接口信息
| 项目 | 值 |
|------|-----|
| **端点** | `POST /v1/chat/completions` |
| **协议** | 兼容 OpenAI API |

### 请求示例
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "Say this is a test!"}],
  "temperature": 0.7
}
```

### 响应示例
```json
{
   "id": "chatcmpl-abc123",
   "object": "chat.completion",
   "created": 1677858242,
   "model": "gpt-3.5-turbo-0301",
   "usage": {
      "prompt_tokens": 13,
      "completion_tokens": 7,
      "total_tokens": 20
   },
   "choices": [
      {
         "message": {
            "role": "assistant",
            "content": "\n\nThis is a test!"
         },
         "finish_reason": "stop",
         "index": 0
      }
   ]
}
```

---

## 二、Fal.ai 图像生成平台

### 状态码
| 状态 | 说明 |
|------|------|
| `IN_QUEUE` | 排队中 |
| `IN_PROGRESS` | 生成中 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |

### 2.1 文生图 (nano-banana)

| 项目 | 值 |
|------|-----|
| **端点** | `POST /fal-ai/nano-banana` |
| **官方文档** | https://fal.ai/models/fal-ai/nano-banana |

#### 请求参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 生成图片的提示词 |
| `num_images` | integer | ❌ | 生成数量 1-4，默认 1 |

#### 请求示例
```json
{
    "prompt": "An action shot of a black lab swimming in a pool",
    "num_images": 1
}
```

#### 响应示例 (提交后)
```json
{
    "status": "IN_QUEUE",
    "request_id": "e7e9202c-efb8-40f2-81c3-13b3f7aaa4ca",
    "response_url": "https://queue.fal.run/fal-ai/nano-banana/requests/e7e9202c-efb8-40f2-81c3-13b3f7aaa4ca",
    "status_url": "https://queue.fal.run/fal-ai/nano-banana/requests/e7e9202c-efb8-40f2-81c3-13b3f7aaa4ca/status",
    "cancel_url": "https://queue.fal.run/fal-ai/nano-banana/requests/e7e9202c-efb8-40f2-81c3-13b3f7aaa4ca/cancel",
    "queue_position": 0
}
```

### 2.2 图片编辑 (nano-banana/edit)

| 项目 | 值 |
|------|-----|
| **端点** | `POST /fal-ai/nano-banana/edit` |
| **官方文档** | https://fal.ai/models/fal-ai/nano-banana/edit |

#### 请求参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 编辑提示词 |
| `image_urls` | array[string] | ✅ | 需要编辑的图片 URL |
| `num_images` | integer | ❌ | 生成数量 1-4，默认 1 |

#### 请求示例
```json
{
  "prompt": "make a photo of the man driving the car down the california coastline",
  "image_urls": [
    "https://example.com/image1.png",
    "https://example.com/image2.png"
  ],
  "num_images": 1
}
```

### 2.3 获取请求结果

| 项目 | 值 |
|------|-----|
| **端点** | `GET /fal-ai/{model_name}/requests/{request_id}` |

#### 路径参数
| 参数 | 说明 |
|------|------|
| `model_name` | 模型名称，如 `nano-banana` |
| `request_id` | 任务 ID |

#### 完成响应示例
```json
{
    "seed": 2841475369,
    "images": [
        {
            "url": "https://fal.media/files/tiger/xxx.jpg",
            "width": 1024,
            "height": 1024,
            "content_type": "image/jpeg"
        }
    ],
    "prompt": "Put the little duckling on top of the woman's t-shirt.",
    "has_nsfw_concepts": [false]
}
```

---

## 三、视频生成 - VEO (Google)

### 状态码
| 状态 | 说明 |
|------|------|
| `pending` | 等待中 |
| `image_downloading` | 图片下载中 |
| `video_generating` | 视频生成中 |
| `video_generation_completed` | 视频生成完成 |
| `video_generation_failed` | 视频生成失败 |
| `video_upsampling` | 视频超分中 |
| `video_upsampling_completed` | 超分完成 |
| `video_upsampling_failed` | 超分失败 |
| `completed` | 全部完成 |
| `failed` | 失败 |
| `error` | 错误 |

### 3.1 创建视频

| 项目 | 值 |
|------|-----|
| **端点** | `POST /v1/video/create` |

#### 请求参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | 模型名称 |
| `prompt` | string | ✅ | 提示词 |
| `images` | array[string] | ❌ | 图片 URL (根据模型类型) |
| `enhance_prompt` | boolean | ❌ | 中文自动转英文 |
| `enable_upsample` | boolean | ❌ | 启用超分辨率 |
| `aspect_ratio` | string | ❌ | 宽高比 "16:9" / "9:16" (仅 veo3) |

#### 支持的模型
| 模型 | 说明 | 图片支持 |
|------|------|----------|
| `veo2` | 基础版 | - |
| `veo2-fast` | 快速版 | - |
| `veo2-fast-frames` | 支持首尾帧 | 最多 2 张 |
| `veo2-fast-components` | 素材合成 | 最多 3 张 |
| `veo2-pro` | 高质量版 | - |
| `veo2-pro-components` | Pro + 素材 | 最多 3 张 |
| `veo3` | VEO3 基础 | - |
| `veo3-fast` | VEO3 快速 | - |
| `veo3-fast-frames` | VEO3 + 帧 | 最多 2 张 |
| `veo3-frames` | VEO3 帧控制 | - |
| `veo3-pro` | VEO3 高质量 | - |
| `veo3-pro-frames` | Pro + 首帧 | 最多 1 张 |
| `veo3.1` | 最新版 | - |
| `veo3.1-fast` | 最新快速 | - |
| `veo3.1-pro` | 最新高质量 | - |
| `veo3.1-components` | 最新 + 素材 | 最多 3 张 |

#### 请求示例
```json
{
    "enable_upsample": true,
    "enhance_prompt": true,
    "images": ["https://example.com/image.png"],
    "model": "veo3.1-fast",
    "prompt": "make animate",
    "aspect_ratio": "16:9"
}
```

#### 响应示例
```json
{
    "id": "veo3-fast-frames:1757555257-PORrVn9sa9",
    "status": "pending",
    "status_update_time": 1757555257582
}
```

### 3.2 查询视频任务

| 项目 | 值 |
|------|-----|
| **端点** | `GET /v1/video/query?id={task_id}` |

#### 响应示例 (完成)
```json
{
    "id": "xxx",
    "status": "completed",
    "video_url": "https://...",
    "enhanced_prompt": "...",
    "status_update_time": 1750323167003
}
```

---

## 四、视频生成 - 即梦 (Jimeng)

### 状态码
| 状态 | 说明 |
|------|------|
| `NOT_START` | 未开始 |
| `SUBMITTED` | 已提交 |
| `QUEUED` | 排队中 |
| `IN_PROGRESS` | 进行中 |
| `FAILURE` | 失败 |
| `SUCCESS` | 成功 |

### 4.1 提交视频任务 (即梦原生接口)

| 项目 | 值 |
|------|-----|
| **端点** | `POST /jimeng/submit/videos` |

#### 请求参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 提示词 |
| `image_url` | string | ❌ | 图生视频需要传此参数 |
| `duration` | integer | ✅ | 视频时长: 5 或 10 秒 |
| `aspect_ratio` | string | ✅ | "1:1", "21:9", "16:9", "9:16", "4:3", "3:4" |
| `cfg_scale` | number | ✅ | 引导系数 |

#### 请求示例
```json
{
    "prompt": "一只小猪在高速公路上快乐的奔跑",
    "duration": 5,
    "aspect_ratio": "21:9",
    "cfg_scale": 0.5
}
```

#### 响应示例
```json
{
    "code": "success",
    "message": "",
    "data": "cgt-20250829165122-qkwch"
}
```

### 4.2 查询即梦任务 (免费)

| 项目 | 值 |
|------|-----|
| **端点** | `GET /jimeng/fetch/{task_id}` |

#### 响应示例 (成功)
```json
{
    "code": "success",
    "message": "",
    "data": {
        "task_id": "cgt-20250829165122-qkwch",
        "status": "SUCCESS",
        "data": {
            "video": "https://ark-content-generation-cn-beijing.tos-cn-beijing.volces.com/xxx.mp4",
            "status": "SUCCESS"
        }
    }
}
```

### 4.3 即梦视频 (统一接口)

| 项目 | 值 |
|------|-----|
| **端点** | `POST /v1/video/create` |
| **模型** | `jimeng-video-3.0` |

#### 请求参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | `jimeng-video-3.0` |
| `prompt` | string | ✅ | 提示词 |
| `aspect_ratio` | string | ✅ | "2:3", "3:2", "1:1" |
| `size` | string | ✅ | "720P" |
| `images` | array[string] | ❌ | 图片链接 (图生视频) |

#### 请求示例
```json
{
    "model": "jimeng-video-3.0",
    "prompt": "cat fish",
    "aspect_ratio": "3:2",
    "size": "720P",
    "images": []
}
```

---

## 五、接口调用流程

### 图像生成流程 (Fal.ai)
```
1. POST /fal-ai/nano-banana
   ↓ 返回 request_id
2. GET /fal-ai/nano-banana/requests/{request_id}
   ↓ 轮询直到 status = COMPLETED
3. 获取 images[].url
```

### 视频生成流程 (VEO)
```
1. POST /v1/video/create
   ↓ 返回 id
2. GET /v1/video/query?id={id}
   ↓ 轮询直到 status = completed
3. 获取 video_url
```

### 视频生成流程 (即梦)
```
1. POST /jimeng/submit/videos
   ↓ 返回 task_id
2. GET /jimeng/fetch/{task_id}
   ↓ 轮询直到 status = SUCCESS
3. 获取 data.video
```

---

## 六、错误处理

### HTTP 状态码
| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器错误 |

### 通用错误响应
```json
{
    "error": {
        "message": "Invalid API key",
        "type": "invalid_request_error",
        "code": "invalid_api_key"
    }
}
```
