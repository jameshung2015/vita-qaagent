# Ollama 模型与工具需求说明（MODEL_REQUIREMENTS，Ollama 接入）
---

## 一、运行环境与通用依赖

- 运行环境
  - Python ≥ 3.8（建议 3.9+）
  - 操作系统：Windows / Linux / macOS
  - 网络：可访问 Ollama 主机（本地或远程），若使用 Ollama Cloud 请确保网络策略与认证可达
  - 环境变量（可选）：`OLLAMA_HOST`（例如 `http://localhost:11434`）

- Python 依赖（建议）
  - `requests`：用于与 Ollama HTTP API 通信
  - `websocket-client`（可选）：用于需要的实时/流式交互场景
  - `pydantic`（可选）：用于结构化输入/输出校验
  - 其他标准库：`os` / `json` / `logging` / `base64` / `typing` / `argparse`

> 说明：Ollama 提供本地模型托管与 HTTP API（默认监听 11434 端口）。文档与 CLI 在不同版本中略有差异，请以本地 Ollama 服务版本为准。

---

## 二、支持的模型（示例）

下列模型为当前工作区 Ollama 可用模型示例（以 `ollama list` 输出为参考）：

- `kimi-k2-thinking:cloud` (ID: 9752ffb77f53)
- `qwen3-vl:235b-cloud` (ID: 7fc468f95411)
- `deepseek-v3.1:671b-cloud` (ID: d3749919e45f)
- `qwen3:4b` (ID: e55aed6fe643)
- `deepseek-r1:1.5b` (ID: e0979632db5a)
- `qwen2.5-coder:1.5b` (ID: 6d3abb8d2d53)

在文件中使用模型标识时，优先用名称（例如 `qwen3:4b`）；当需要追踪镜像 ID 或排障时，可同时记录 ID 字段。

---

## 三、HTTP API 使用指南（基础：Ollama 本地/远程 API）

Ollama 提供 REST API，可用于生成文本、处理多模态输入（取决于模型能力），常见模式如下：

- 默认 Base URL（本地）：`http://localhost:11434`（如远程部署，改为 `http(s)://<host>:<port>`）
- 主要端点：`POST /api/generate`（请求体包含 `model` 与 `prompt`）

示例：最小文本生成请求（使用 `requests`）

```python
import os
import requests

host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
url = f"{host}/api/generate"

payload = {
    "model": "qwen3:4b",
    "prompt": "用中文简述 Qwen-3 的适用场景与优势。",
    "options": {"max_tokens": 300, "temperature": 0.2}
}

resp = requests.post(url, json=payload, timeout=30)
resp.raise_for_status()
print(resp.json())
```

注意：不同版本的 Ollama API 在 `prompt` 字段结构上可能有差别（有的版本使用 `messages` 模拟 OpenAI Chat），在调用前请查看 `http://<host>:11434/api/docs` 或 `ollama` CLI 文档。

---

## 四、流式输出与多轮对话

- 流式：部分 Ollama 部署支持 SSE 或 WebSocket 风格的流式输出；若需要流式，请使用 `requests` 的流式响应（`stream=True`）或 WebSocket 客户端。
- 多轮对话：若模型或 API 支持 `messages`（role/message 格式），请保持历史上下文在客户端并按需截断；若仅接受 `prompt` 字符串，可自行拼接对话历史。

流式示例（SSE 风格、伪代码）：

```python
import requests

url = "http://localhost:11434/api/generate"
payload = {"model": "qwen3:4b", "prompt": "流式输出示例...", "options": {"stream": True}}
with requests.post(url, json=payload, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
```

---

## 五、多模态（图像）能力

是否支持图像取决于所选模型（如 `qwen3-vl*` 或 `kimi-k2-thinking` 具备视觉理解能力）。常见传图方式：

- Base64 data URI：将图片编码为 `data:image/<fmt>;base64,<data>` 并嵌入 `prompt` 或 `input` 字段
- URL：将可公网访问或内网可达的图片 URL 放入 `prompt` 指定的位置
- 文件上传：若 Ollama API/部署支持 multipart 上传，可直接上传文件（部分版本支持）

图像示例（Base64 嵌入）

```python
import base64, os, requests

host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
url = f"{host}/api/generate"

def encode_file(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

img_data = encode_file('demo.png')
prompt = f"[IMAGE:data:image/png;base64,{img_data}]\n请描述这张图片的关键内容。"

payload = {"model": "qwen3-vl:235b-cloud", "prompt": prompt}
resp = requests.post(url, json=payload, timeout=60)
print(resp.json())
```

---

## 六、模型选择建议与资源对齐

- `qwen3:4b`：大型通用语言模型，适合需要较强生成能力、长上下文和复杂推理的场景；资源需求高（内存/显卡）
- `qwen3-vl:235b-cloud` / `kimi-k2-thinking:cloud`：视觉-语言多模态模型，适合图像理解、文图混合任务；推荐用于图像标注、图像与文本联合检索
- `deepseek-v3.1:671b-cloud` / `deepseek-r1:1.5b`：偏检索/搜索与理解优化的模型，适用于信息抽取、短文本检索增强任务
- `qwen2.5-coder:1.5b`：代码生成/理解优化，适合自动化脚本生成、代码补全或开发者辅助工具

在生产部署中，请根据延迟、吞吐、成本与质量进行权衡：优先在开发环境用小模型快速验证用例，再在需要的场景下迁移到大模型。

---

## 七、认证、网络与安全

- 如果 Ollama 部署启用了身份认证或反向代理，请在 `OLLAMA_HOST` 中包含协议与端口，并为请求添加必要的 `Authorization` header 或代理证书。
- 日志：使用 `logging` 并对敏感输出（如原始用户 PII）做脱敏处理。
- 不在代码中硬编码访问凭证；若需要密钥管理，使用系统环境或安全服务。

---

## 八、错误处理与鲁棒性

- 检查 HTTP 返回码并对 4xx/5xx 做重试或回退。对生成结果做健壮的解析：模型可能返回部分无效 JSON 或非结构化文本。
- 超时与限速：为请求设置合理 `timeout`，在受限资源或负载高时使用指数退避策略重试。

---

## 九、示例脚本与实用工具

- 列出本地模型（使用 `ollama list`）并在脚本中解析输出以做可用性检查
- 简易 wrapper：创建 `ollama_client.py`（示例）封装 `generate()` 与流式逻辑

示例 `ollama_client.py`（简化版）

```python
import os
import requests

class OllamaClient:
    def __init__(self, host=None):
        self.host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.base = f"{self.host}/api"

    def generate(self, model, prompt, options=None, timeout=60):
        payload = {"model": model, "prompt": prompt}
        if options:
            payload['options'] = options
        resp = requests.post(f"{self.base}/generate", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def stream_generate(self, model, prompt, options=None):
        payload = {"model": model, "prompt": prompt}
        if options:
            payload['options'] = options
        with requests.post(f"{self.base}/generate", json=payload, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    yield line.decode('utf-8')
```

---

## 十、快速试跑（Windows）

1. 安装依赖

```powershell
pip install requests websocket-client
```

2. 设置 `OLLAMA_HOST`（若使用默认本地端口可跳过）

```powershell
$env:OLLAMA_HOST = "http://localhost:11434"
```

3. 运行示例

```powershell
python -c "from ollama_client import OllamaClient; c=OllamaClient(); print(c.generate('qwen3:4b', '简述Qwen-3模型'))"
```

---

## 十一、拓展与注意事项

- 若使用 Ollama Cloud（受托托管的服务），请检查额外的认证、访问控制与计费策略
- 若需要 OpenAI Chat-like `messages` 支持，可在客户端将 `messages` 转换为适合模型的 `prompt` 模板，或查找 Ollama 版本支持的 chat 格式
- 在 CI 中测试时，可使用小模型或 mock 服务以节省资源

---

如需我将 `ollama_client.py` 加入 `src/` 并更新 `requirements.txt`，我可以继续实现并运行单元测试。
