# G2M 模型与工具需求说明（MODEL_REQUIREMENTS）
---

## 一、运行环境与通用依赖

- **运行环境**
  - Python ≥ 3.8（建议 3.9+）
  - 操作系统：Windows / Linux / macOS
  - 网络：需可访问 `https://llmproxy.gwm.cn`（以及 `http://llmproxy.gwm.cn` 图像生成接口）
  - G2M_API_KEY ： <managed via config/.env，示例不再展示真实值>

- **Python 依赖（来自 `requirements.txt` + 代码实际使用）**
  - `requests>=2.25.1`：HTTP 调用 G2M 大模型平台 API
  - `beautifulsoup4>=4.9.3`：网页解析（用于 `g2m-webextrac.py` 等）
  - `html2text>=2020.1.16`：HTML 转 Markdown 或纯文本
  - `lxml>=4.6.3`：HTML / XML 解析
  - `pathlib>=1.0.1`：文件路径处理（视频分析子项目）
  - 其他标准库：`os` / `sys` / `json` / `base64` / `logging` / `datetime` / `argparse` / `re` / `typing` 等

---

## 二、文本生成模型（`g2m-modeltest.py`）

### 2.1 功能与场景

- 用途：纯文本大模型调用，用于问答、说明生成、问题改写和优化等。
- 示例脚本：`g2m-modeltest.py`

### 2.2 使用接口

- HTTP 方法：`POST`
- URL：`https://llmproxy.gwm.cn/v1/completions`

### 2.3 模型列表

- `default/qwen3-235b-a22b-instruct`
- `default/qwen3-235b-a22b-thinking`
- `default/qwen3-coder-30b-a3b-instruct`

> 以上模型名称来自示例脚本注释，可按平台实际支持情况增减。

### 2.4 关键请求参数

- `model: str`
  - 描述：指定调用的文本模型名称（如 `default/qwen3-235b-a22b-instruct`）。
- `prompt: str`
  - 描述：完整的用户输入文本，可包含指令、问题与上下文。
- `temperature: float`
  - 范围：0.0–1.0（示例脚本中为 `0.7`）。
  - 含义：控制生成结果的随机性/创意度，越高越发散。
- `stream: bool`
  - 描述：是否开启流式输出。
  - 在示例中为 `False`，即一次性返回完整 JSON 结果。

### 2.5 认证与安全

- HTTP Header：
  - `Authorization: <api_token>`
- 示例脚本中使用了硬编码 Token，仅用于演示：
  - 生产要求：
    - 不在代码中硬编码真实密钥；
    - 统一通过 `config/.env` 管理密钥并在运行时载入为环境变量（如 `G2M_API_KEY`）。

### 2.6 依赖库

- `requests`
- `json`

---

## 三、多模态图像理解模型（`g2m-modeltest-vl.py`）

### 3.1 功能与场景

- 用途：图像内容理解与描述，提取图像中关键信息，支持图文多模态问答。
- 示例脚本：`g2m-modeltest-vl.py`

### 3.2 使用接口

- HTTP 方法：`POST`
- URL：`https://llmproxy.gwm.cn/v1/chat/completions`

### 3.3 模型列表

- 默认模型：
  - `default/qwen3-omni-30b-a3b-captioner`
- 其他候选模型（示例脚本注释中给出，可替换）：
  - `default/qwen3-vl-30b-a3b-instruct`
  - `default/minicpm-v-4-5`

### 3.4 图片传输方式

1. **Base64 Data URI 方式（一次性会话）**
   - 步骤：
     - 本地读取图片二进制 → `base64.b64encode` → 字符串；
     - 拼接为 Data URI：`data:image/jpeg;base64,<base64_string>`；
   - 特点：
     - 服务端不会缓存图片，适合一次性调用场景；
     - 无需暴露内网 URL。

2. **URL 方式（多轮对话，可缓存）**
   - 要求：
     - 图片需存储在集团内部机器；
     - 服务端可直接 `wget` 访问（无网络限制或鉴权问题）。
   - 特点：
     - 服务端会自动下载并缓存图片；
     - 多轮对话中重复使用同一图片时，可直接复用缓存。

### 3.5 关键请求参数

- `model: str`
- `messages: list`
  - 结构类似 OpenAI Chat 格式，示例：
    - `role: "user"`
    - `content: [`
      - `{ "type": "text", "text": "请分析下这张图片都有哪些内容， 并提取关键信息。" }`,
      - `{ "type": "image_url", "image_url": { "url": "<data-uri 或 http-url>" } }`
      - `]`
- `temperature: float`
  - 控制回答多样性，示例为 `0.7`。
- `stream: bool`
  - 是否开启流式输出；示例中设为 `True`，通过 SSE 格式逐步返回内容。

### 3.6 返回解析（流式）

- 响应 Body 按行返回，示例处理逻辑：
  - 每行字符串形如：`data: { ... }`；
  - 行内容为 `"data: [DONE]"` 表示流结束；
  - 实际内容在 JSON 的 `choices[0].delta.content` 字段中；
  - 客户端脚本将每个 delta 片段追加到完整文本中并即时打印。

### 3.7 认证与安全

- HTTP Header：
  - `Authorization: <api_token>`
- 示例脚本中同样使用硬编码 Token，生产环境应改为环境变量或配置文件管理。
  - 统一约定：从 `config/.env` 加载并注入环境变量。

### 3.8 依赖库

- `requests`
- `json`
- `base64`
- `os`
- `re`

---

## 四、语音识别 ASR 模型（`g2m-modeltest-aud.py`）

### 4.1 功能与场景

- 用途：将音频文件或 URL 发送到 G2M ASR 接口，获得转写文本结果，支持可选时间戳。 
- 示例脚本：`g2m-modeltest-aud.py`

### 4.2 使用接口

- HTTP 方法：`POST`
- URL：`https://llmproxy.gwm.cn/v1/audio/translations`

### 4.3 默认模型

- `default/whisper-large-v3-turbo`

### 4.4 API Key 读取策略

脚本内提供了较完善的 API Key 加载逻辑，推荐统一采用：

1. 优先从环境变量：`G2M_API_KEY` 读取（通过 `config/.env` 统一管理并在启动时加载）；
2. 不再提交 `.g2m_api_key` 等明文文件到仓库；如需本地覆盖，可使用不纳入版本控制的 `config/.env` 或系统环境变量。
3. 如果以上都未配置，可选择：
   - 通过命令行参数 `--key` 显式传入；
   - 或退回到硬编码 `HARDCODED_KEY`（仅建议在受控测试环境使用）。

### 4.5 音频输入方式

1. `--file <path>`：本地音频文件
   - 由脚本读取并转换为 Data URI：`data:<mime>;base64,<...>`；
   - MIME 类型根据扩展名简单推断：
     - `.wav` → `audio/wav`
     - `.mp3` → `audio/mpeg`
     - `.m4a` / `.aac` → `audio/mp4`
     - `.ogg` / `.opus` → `audio/ogg`

2. `--url <http(s)://...>`：远程音频 URL
   - 需保证服务端可访问（建议内网 OSS / 对象存储等）。

`--file` 与 `--url` 二选一，脚本中设置为互斥必选。

### 4.6 关键请求参数

- `model: str`
  - 默认值：`default/whisper-large-v3`，可通过 `--model` 覆盖。
- `audio_url: str`
  - 当使用 `--file` 时：Data URI；
  - 当使用 `--url` 时：远程音频 URL。
- `language: str`（可选）
  - 示例：`"zh"`, `"en"`；指定识别语言，若模型支持自动检测则可省略。
- `timestamp: bool`（可选）
  - `True` 时请求带时间戳的分段结果（视服务端实际支持字段而定）。

### 4.7 命令行参数（工具层要求）

- `--file`：本地音频文件路径。
- `--url`：远程音频 URL。
- `--model`：覆盖默认模型名。
- `--language`：指定语言代码。
- `--timestamp`：是否请求时间戳信息。
- `--key`：显式传入 API Key，优先级高于环境变量和文件。

### 4.8 认证与安全

- HTTP Header：
  - `Authorization: Bearer <api_key>`
  - `Content-Type: application/json`

### 4.9 依赖库

- `requests`
- `json`
- `base64`
- `argparse`
- `os` / `sys`

---

## 五、图像生成模型（`g2m-imgmodeltest.py`）

### 5.1 功能与场景

- 用途：根据文本 Prompt 生成图片，并将结果保存到本地目录 `generated_images/`。
- 示例脚本：`g2m-imgmodeltest.py`

### 5.2 使用接口

- HTTP 方法：`POST`
- URL：`http://llmproxy.gwm.cn/v1/images/generations`

### 5.3 模型列表

- 默认模型：`default/z-image-turbo`
- 可根据平台实际支持添加其他图像生成模型（如写实风格、动漫风格等）。
  - `default/flux-1-dev`

### 5.4 关键请求参数

- `prompt: str`
  - 描述：图像生成的详细描述，可包括：主体、风格、光照、分辨率、构图等。
- `model: str`
  - 示例：`"default/flux-1-dev"`。
- `denoise: float`
  - 范围：0.0–1.0；
  - 示例：`1.0`；
  - 含义：降噪强度或重绘力度，数值越高，结果越偏向完全重绘/随机。

### 5.5 返回格式与结果保存

- 响应 JSON 结构（按示例假设）：
  - `data: [ { "file_name": "xxx.png", "content": "<base64-encoded-bytes>" }, ... ]`
- 客户端处理逻辑：
  1. 解析 JSON，遍历 `data` 列表；
  2. 如果存在 `file_name` 字段，则直接使用；否则基于当前时间戳和序号生成 `image_<timestamp>_<i>.png`；
  3. 对 `content` 字段执行 base64 解码，得到图像二进制；
  4. 写入到 `generated_images/<file_name>`；若目录不存在则自动创建。

### 5.6 认证与安全

- HTTP Header：
  - `Authorization: <api_token>`
- 同样建议不要在代码中硬编码真实 Token，通过环境变量或配置文件注入。
  - 统一约定：使用 `config/.env` 提供 `G2M_IMAGE_API_KEY` 等变量，脚本启动时加载。

### 5.7 依赖库

- `requests`
- `json`
- `base64`
- `os`
- `logging`
- `datetime`
- `typing`

---

## 六、其他工具脚本（按需补充）

以下脚本涉及文件解析、OCR、视频处理等能力，其底层可能仍复用上述模型接口或调用第三方工具，建议在使用前进一步确认各自依赖：

- `batch_pdf2md.py`
  - 预期用途：批量将 PDF 转换为 Markdown/文本；
  - 可能依赖：`pdfplumber` / `PyPDF2` 等（需打开脚本确认）。

- `g2m-fileextrac.py`
  - 预期用途：通用文件内容抽取（如 docx/xlsx/pptx 等）；
  - 可能依赖：`python-docx` / `openpyxl` / `python-pptx` 等。

- `g2m-ocr.py`
  - 预期用途：调用 G2M OCR 接口或本地 OCR 库，将图片转换为文本。

- `g2m-plugin-backpaint.py` / `g2m-plugin-screengrap.py`
  - 预期用途：配合前端或桌面插件进行截图抓取、背景处理、图像预处理等。

- `g2m-videoASRextrac.py`
  - 预期用途：调用 `ffmpeg` 从视频中抽取音轨并送入 ASR 模型；
  - 依赖：`ffmpeg` 二进制、`subprocess` / `moviepy` 等（视实现而定）。

- `g2m-videoGen.py`
  - 预期用途：基于脚本/文本生成视频，或对现有视频进行加工；
  - 可能依赖：`ffmpeg` 及视频处理库。

- `g2m-webextrac.py`
  - 预期用途：网页抓取与正文抽取；
  - 依赖：`requests`、`beautifulsoup4`、`html2text`、`lxml` 等。

> 如果需要，可以为上述每个脚本单独扩展一节，精确列出所使用的模型接口、参数和外部工具（例如 ffmpeg 的安装要求、路径配置等）。

---

## 七、统一配置与安全要求（建议）

### 7.1 API Key 管理

- 不允许在代码中硬编码生产环境 API Key；
- 统一通过 `config/.env` 管理密钥，并在版本控制中仅提交示例文件 `config/.env.example`；运行时由启动脚本或操作系统注入环境变量：
  - `G2M_API_KEY`、`G2M_VL_API_KEY`、`G2M_IMAGE_API_KEY`
  - `ARK_API_KEY`（Doubao）

### 7.2 网络与访问控制

- 对外访问域名：`llmproxy.gwm.cn`；
- 若使用 URL 方式传输图片/音频：
  - 资源需部署在集团内网可达的对象存储或文件服务器；
  - 确保不会出现跨网访问失败、鉴权失败等问题。

### 7.3 日志与错误处理

- 统一使用 `logging` 模块输出日志，区分 INFO / WARNING / ERROR 级别；
- 对 `requests` 调用增加：
  - 合理的 `timeout`；
  - 异常捕获（`requests.exceptions.RequestException`）；
- 对返回体解析增加健壮性：
  - 捕获 `json.JSONDecodeError`；
  - 对关键字段缺失给出清晰的错误信息。

### 7.4 版本管理与验收

- 建议将本文件 `MODEL_REQUIREMENTS.md` 纳入代码仓库，随代码版本更新；
- 每次新增/调整模型接口或关键参数时，同步更新本文件；
- 在模型接入验收（如 `NM_Acceptance_Checklist`）中，可直接引用本文件作为模型配置与依赖的依据。

---

> 如需对 `video-analyze/` 子项目或其他目录下的模型调用进行同样颗粒度的梳理，可在本文件后续章节中继续扩展，例如：`八、视频内容分析服务模型需求`，并写明对应 Python 模块、前端调用方式以及部署要求。