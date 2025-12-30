# VITA QA Agent 增强功能说明

## 版本 0.2.0 新增功能

### 1. 增强的错误处理机制

#### 1.1 自定义异常类

位置: `src/utils/exceptions.py`

新增专门的异常类型，提供更精确的错误分类和上下文信息：

- `QAAgentError`: 基础异常类
- `ModelClientError`: 模型客户端相关错误
- `ModelAPIError`: API调用错误（包含状态码和响应文本）
- `ModelTimeoutError`: 超时错误
- `ParsingError`: 解析错误（保存原始内容）
- `ValidationError`: 数据验证错误
- `ConfigurationError`: 配置错误
- `FileOperationError`: 文件操作错误
- `AgentExecutionError`: Agent执行错误（包含阶段信息）

**使用示例:**
```python
from src.utils.exceptions import ModelAPIError

try:
    response = model_client.chat_completion(...)
except ModelAPIError as e:
    print(f"API错误: {e}")
    print(f"状态码: {e.status_code}")
    print(f"响应内容: {e.response_text}")
```

#### 1.2 错误处理工具

位置: `src/utils/error_handler.py`

**错误处理装饰器:**
```python
from src.utils.error_handler import handle_errors

@handle_errors("解析需求失败", reraise=True)
def parse_requirement(content):
    # 自动记录错误并重新抛出
    ...
```

**安全的模型调用:**
```python
from src.utils.error_handler import safe_model_call

def call_model():
    return client.chat_completion(...)

# 自动重试3次，指数退避
result = safe_model_call(call_model, max_retries=3, retry_delay=2.0)
```

**JSON验证:**
```python
from src.utils.error_handler import validate_json_response

response = model.generate(...)
data = validate_json_response(
    response,
    required_fields=["modules", "metadata"]
)
```

#### 1.3 模型客户端增强

**Doubao客户端改进:**
- 自动重试机制（3次，指数退避）
- 超时检测和处理
- 详细的错误日志
- API响应验证

**G2M客户端改进:**
- 相同的错误处理逻辑
- HTTP状态码检查
- 请求异常捕获

### 2. 可配置的LLM提示词系统

#### 2.1 提示词配置文件

位置: `config/prompts.yaml`

YAML格式的提示词配置，支持三个Agent的所有提示词：

```yaml
# 需求解析Agent
requirement_parser:
  system_prompt: |
    你是一个专业的测试工程师...

  parse_prompt_template: |
    请分析以下需求文档...
    {prd_content}
    {metric_section}

# 规则生成Agent
rule_generator:
  system_prompt: |
    你是一个测试架构师...

  generate_prompt_template: |
    请为以下项目生成规则...

# 用例生成Agent
testcase_generator:
  steps_prompt_template: |
    请为以下场景生成步骤...

  expected_result_prompt_template: |
    请为以下步骤生成预期结果...

# 全局配置
global:
  default_temperature: 0.3
  default_max_tokens: 4000
  max_retries: 3
  retry_delay: 2.0
```

#### 2.2 配置加载器

位置: `src/utils/config_loader.py`

**使用方式:**
```python
from src.utils.config_loader import get_prompt, get_config

# 获取格式化的提示词
prompt = get_prompt(
    agent_name="requirement_parser",
    prompt_key="parse_prompt_template",
    prd_content="...",
    metric_section="..."
)

# 获取全局配置
temperature = get_config("default_temperature", default=0.7)
max_retries = get_config("max_retries", default=3)
```

**自定义配置:**
```bash
# 使用自定义提示词配置
python cli/main_v2.py generate \
  --prd my_prd.md \
  --prompts-config my_custom_prompts.yaml
```

#### 2.3 提示词优化建议

修改 `config/prompts.yaml` 来优化生成质量：

1. **调整系统提示词** - 改变Agent的角色和行为
2. **优化模板变量** - 添加更多上下文信息
3. **修改生成要求** - 调整输出格式和质量标准
4. **调整参数** - 温度、tokens、重试次数等

### 3. 多PRD文件和URI输入支持

#### 3.1 URI加载器

位置: `src/utils/file_loader.py`

**功能:**
- 支持本地文件路径
- 支持HTTP(S) URL
- 自动检测URI类型
- 超时和重试处理

**使用示例:**
```python
from src.utils.file_loader import load_content_from_uri

# 本地文件
content = load_content_from_uri("docs/prd.md")

# 远程URL
content = load_content_from_uri("https://example.com/prd.md")
```

#### 3.2 多PRD支持

**加载多个PRD:**
```python
from src.utils.file_loader import load_multiple_prds

prds = load_multiple_prds([
    "local_prd1.md",
    "local_prd2.md",
    "https://example.com/remote_prd.md"
])

# 结果: [{"uri": "...", "name": "...", "content": "..."}, ...]
```

**合并PRD:**
```python
from src.utils.file_loader import merge_prd_contents

merged = merge_prd_contents(prds)
# 自动添加章节标题和分隔
```

#### 3.3 CLI v2 使用方式

位置: `cli/main_v2.py`

**单个PRD:**
```bash
python cli/main_v2.py generate \
  --prd metric/识人识物_用例设计原则与示例.md \
  --project recognition
```

**多个本地PRD:**
```bash
python cli/main_v2.py generate \
  --prd prd1.md \
  --prd prd2.md \
  --prd prd3.md \
  --project multi_module
```

**从URL加载:**
```bash
python cli/main_v2.py generate \
  --prd https://raw.githubusercontent.com/.../prd.md \
  --project remote
```

**混合本地和远程:**
```bash
python cli/main_v2.py generate \
  --prd local_base.md \
  --prd https://example.com/addon.md \
  --project hybrid
```

**不合并PRD（分别处理）:**
```bash
python cli/main_v2.py generate \
  --prd prd1.md \
  --prd prd2.md \
  --merge-prds=false
```

**使用自定义提示词:**
```bash
python cli/main_v2.py generate \
  --prd my_prd.md \
  --prompts-config custom_prompts.yaml \
  --project custom
```

### 4. 其他改进

#### 4.1 增强的日志系统
- 结构化错误日志
- Agent执行阶段追踪
- 上下文信息记录

#### 4.2 更好的用户体验
- 清晰的错误消息
- 详细的进度提示
- 友好的失败恢复

#### 4.3 代码质量提升
- 类型注解完善
- 文档字符串更新
- 异常处理规范化

## 兼容性说明

### 向后兼容
- 原有的 `cli/main.py` 保持不变
- 所有现有功能继续工作
- 新功能通过 `cli/main_v2.py` 提供

### 升级建议
1. 安装新依赖: `pip install -r requirements.txt`
2. 尝试使用 `cli/main_v2.py`
3. 根据需要自定义 `config/prompts.yaml`
4. 逐步迁移到新版CLI

## 示例场景

### 场景1: 多项目PRD合并

```bash
# 合并多个子系统的PRD
python cli/main_v2.py generate \
  --prd prds/login_module.md \
  --prd prds/payment_module.md \
  --prd prds/order_module.md \
  --project complete_system
```

### 场景2: 远程PRD + 本地配置

```bash
# 从远程加载PRD，使用本地metric和原则
python cli/main_v2.py generate \
  --prd https://docs.company.com/latest_prd.md \
  --metric local_metrics.md \
  --principles local_principles.md \
  --project latest_version
```

### 场景3: 优化提示词调试

```bash
# 使用自定义提示词测试生成质量
python cli/main_v2.py generate \
  --prd test_prd.md \
  --prompts-config test_prompts.yaml \
  --verbose \
  --project prompt_tuning
```

## 故障排查

### 问题1: URI加载失败
**错误**: `Failed to load URL: Connection timeout`
**解决**:
- 检查网络连接
- 尝试增加timeout（修改`file_loader.py`中的默认值）
- 使用本地缓存的PRD文件

### 问题2: 提示词配置无效
**错误**: `Missing variable ... for prompt template`
**解决**:
- 检查YAML格式是否正确
- 确保模板变量与代码中的参数匹配
- 参考默认的`config/prompts.yaml`

### 问题3: 多PRD合并问题
**现象**: 生成的用例不符合预期
**解决**:
- 尝试使用`--merge-prds=false`分别处理
- 检查各个PRD的格式是否一致
- 使用`--verbose`查看详细日志

## 下一步计划

- [ ] 支持更多URI协议（FTP, S3等）
- [ ] 提示词模板在线编辑器
- [ ] 批量PRD处理模式
- [ ] 缓存机制优化
- [ ] Web UI集成

---

更新时间: 2025-12-30
版本: 0.2.0
