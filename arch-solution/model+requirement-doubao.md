# Doubao（火山方舟）模型与工具需求说明（MODEL_REQUIREMENTS，OpenAI 兼容 SDK）
---

## 一、运行环境与通用依赖

- 运行环境
  - Python ≥ 3.8（建议 3.9+）
  - 操作系统：Windows / Linux / macOS
  - 网络：需可访问 `https://ark.cn-beijing.volces.com`（火山方舟 Ark 平台）
  - API Key 环境变量：`ARK_API_KEY`

- Python 依赖（建议）
  - `openai>=1.40.0`：OpenAI 兼容 Python SDK（通过配置 `base_url` 与 `api_key` 调用 Doubao）
  - 可选：`volcengine-python-sdk[ark]`（官方 Ark SDK，示例与排障更丰富）
  - 其他标准库：`os` / `json` / `base64` / `argparse` / `logging` / `datetime` / `typing`

> 说明：本文件以 OpenAI 兼容 SDK 为主，示例同时给出 Ark 官方 SDK 的等价写法以便对照。

---

## 二、文本生成模型（Chat API，经 OpenAI 兼容 SDK）

### 2.1 功能与场景

- 用途：纯文本生成、问答、结构化输出、上下文多轮对话、流式输出等。
- 示例参考：火山方舟文档《文本生成》

### 2.2 使用接口

- HTTP 方法：`POST`
- Base URL：`https://ark.cn-beijing.volces.com/api/v3`
- 路径：`/chat/completions`

OpenAI 兼容 SDK 初始化：

```python
import os
from openai import OpenAI

client = OpenAI(
	base_url="https://ark.cn-beijing.volces.com/api/v3",
	api_key=os.getenv("ARK_API_KEY"),
)

resp = client.chat.completions.create(
	model="doubao-seed-1-8-251215",  # 请按模型列表替换
	messages=[
		{"role": "user", "content": "请将下面段落结构化总结……"}
	],
	# 可选：max_tokens=300, temperature=0.7, stream=False
)
print(resp.choices[0].message.content)
```

### 2.3 模型列表

- 示例模型：`doubao-seed-1-8-251215`、`doubao-seed-1-6-251015` 等；实际可用模型与规格以官方 [模型列表](https://www.volcengine.com/docs/82379/1330310) 为准。

### 2.4 关键请求参数

- `model: str`：调用的模型 ID。
- `messages: list`：对话历史，含 `role`（`system`/`user`/`assistant`）与 `content`。
- `max_tokens: int`：限制最大输出长度。
- `temperature: float`：生成多样性（0.0–1.0）。
- `stream: bool`：是否启用流式响应（SSE）。
- `thinking: {"type": "enabled"|"disabled"}`：是否开启深度思考（部分模型支持）。

### 2.5 认证与安全

- HTTP Header：`Authorization: Bearer <ARK_API_KEY>`；`Content-Type: application/json`
- 生产要求：不在代码中硬编码真实密钥；统一使用环境变量或安全配置注入。

### 2.6 依赖库

- `openai`（主推）或 `volcengine-python-sdk[ark]`（可选）
- `json` / `logging`

### 2.7 流式输出（示例）

```python
stream = client.chat.completions.create(
	model="doubao-seed-1-8-251215",
	messages=[{"role": "user", "content": "深度思考与非深度思考区别？"}],
	stream=True,
)
for chunk in stream:
	if chunk.choices and chunk.choices[0].delta:
		print(chunk.choices[0].delta.content, end="")
```

---

## 三、多模态图像理解（Chat/Responses API，经 OpenAI 兼容 SDK）

### 3.1 功能与场景

- 用途：图片内容理解与描述，支持图文混排、多图输入、可选精细度控制与流式输出。
- 参考文档：《图片理解》（视觉理解能力）

### 3.2 使用接口与传图方式

- Base URL：`https://ark.cn-beijing.volces.com/api/v3`
- Chat API：`POST /chat/completions`（多轮对话，OpenAI Chat 格式）
- Responses API：`POST /responses`（单轮分析，结构化 input 项）

支持的图片传入方式：
1. Base64 Data URI：`data:image/<fmt>;base64,<base64_string>`（单图 ≤ 10MB，请求体 ≤ 64MB）
2. URL：公网可访问 URL（单图 ≤ 10MB，建议使用火山引擎 TOS）
3. 文件路径：`file://<local_path>`（仅 Responses API，单图 ≤ 512MB）

### 3.3 Chat API（OpenAI 兼容 SDK）示例

Base64 方式：

```python
import os, base64
from openai import OpenAI

client = OpenAI(base_url="https://ark.cn-beijing.volces.com/api/v3",
				api_key=os.getenv("ARK_API_KEY"))

def encode_file(path):
	with open(path, "rb") as f:
		return base64.b64encode(f.read()).decode("utf-8")

base64_img = encode_file("demo.png")

completion = client.chat.completions.create(
	model="doubao-seed-1-8-251215",
	messages=[{
		"role": "user",
		"content": [
			{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}},
			{"type": "text", "text": "这张图片的关键信息是什么？"}
		]
	}],
	# 可选：max_tokens=300
)
print(completion.choices[0].message.content)
```

URL 方式（多图示例）：

```python
completion = client.chat.completions.create(
	model="doubao-seed-1-8-251215",
	messages=[{
		"role": "user",
		"content": [
			{"type": "image_url", "image_url": {"url": "https://.../ark_demo_img_1.png"}},
			{"type": "image_url", "image_url": {"url": "https://.../ark_demo_img_2.png"}},
			{"type": "text", "text": "总结两张图共同信息点"}
		]
	}],
	max_tokens=300
)
```

精细度控制（detail / image_pixel_limit）：

```python
completion = client.chat.completions.create(
	model="doubao-seed-1-8-251215",
	messages=[{
		"role": "user",
		"content": [
			{"type": "image_url", "image_url": {"url": "https://.../ark_demo_img_1.png"}, "detail": "high"},
			{"type": "text", "text": "请按高精度理解图片细节"}
		]
	}]
)
```

### 3.4 Responses API（OpenAI 兼容 SDK）示例

结构化输入（Base64）：

```python
from openai import OpenAI
import os, base64

client = OpenAI(base_url="https://ark.cn-beijing.volces.com/api/v3",
				api_key=os.getenv("ARK_API_KEY"))

def encode_file(path):
	with open(path, "rb") as f:
		return base64.b64encode(f.read()).decode("utf-8")

base64_img = encode_file("demo.png")

resp = client.responses.create(
	model="doubao-seed-1-8-251215",
	input=[{
		"role": "user",
		"content": [
			{"type": "input_image", "image_url": f"data:image/png;base64,{base64_img}"},
			{"type": "input_text", "text": "识别图中主体并提取关键字段"}
		]
	}]
)
print(resp)
```

本地文件路径（仅 Responses API）：

```python
local_path = "C:/images/sample.png"  # Windows 示例
resp = client.responses.create(
	model="doubao-seed-1-8-251215",
	input=[{"role": "user", "content": [
		{"type": "input_image", "image_url": f"file://{local_path}"},
		{"type": "input_text", "text": "请分析图片内容"}
	]}]
)
```

### 3.5 认证与安全

- Header：`Authorization: Bearer <ARK_API_KEY>`；`Content-Type: application/json`
- 不在代码中硬编码生产环境密钥；支持不同密钥：`ARK_API_KEY`（统一）。

### 3.6 依赖库

- `openai` / `base64` / `os` / `json`

### 3.7 返回解析与流式

- Chat API 流式：按增量 `delta.content` 拼接；Responses API 流式：事件流逐步返回。
- 当使用 URL 或 `file://` 方式传图时，建议使用内网 TOS 加速与降费。

---

## 四、统一配置与安全要求（建议）

### 4.1 API Key 管理

- 统一环境变量：`ARK_API_KEY`；避免硬编码。
- 可使用 `.env` / 配置文件（示例文件而非真实密钥）或密钥管理服务。

### 4.2 网络与访问控制

- 对外访问域名：`ark.cn-beijing.volces.com`
- 使用 URL 传图：图片需存储于可达的对象存储（建议 TOS，内网通信更快更稳）。

### 4.3 日志与错误处理

- 统一使用 `logging` 输出；为 SDK/HTTP 调用设置合理 `timeout`；捕获异常。
- 对返回体解析增加健壮性：检查 `choices[0]` / `message` / `delta` 是否存在。

### 4.4 版本管理与验收

- 将本文件纳入代码仓库，随接入更新；
- 新增/调整模型或关键参数（如图像 detail、像素限制等）时同步更新。

---

## 五、快速试跑（Windows）

### 5.1 安装依赖

```bash
pip install openai
# 可选：pip install "volcengine-python-sdk[ark]"
```

### 5.2 设置环境变量（PowerShell）

```powershell
$env:ARK_API_KEY = "<your_ark_api_key>"
```

### 5.3 最小文本示例（OpenAI 兼容）

```python
import os
from openai import OpenAI

client = OpenAI(base_url="https://ark.cn-beijing.volces.com/api/v3",
				api_key=os.getenv("ARK_API_KEY"))
resp = client.chat.completions.create(
	model="doubao-seed-1-8-251215",
	messages=[{"role": "user", "content": "简述豆包的文本生成能力"}]
)
print(resp.choices[0].message.content)
```

---

> 备注：按需扩展其他能力（如工具调用、结构化输出、批量推理）时，请参考火山方舟官方文档并在本文件增补对应接口、参数与示例。

