# 测试用例生成 Agent 技术需求（AGENT_REQUIREMENT）

## 1. 目标与整体工作流

### 1.1 业务目标
- 支持从自然语言需求文档（PRD、表格化需求等）自动生成测试用例。
- 支持根据“用例拆解原则 + 模块分类规则（metric）”生成标准化的 walkthrough rule。
- 支持按照 walkthrough rule 批量/逐条生成结构化测试用例，并能落地到后端存储（DB + ES）。
- 全流程对本地大模型/G2M 平台友好，输入输出可直接用于二次推理与评审。

### 1.2 工作流分解

1. **输入阶段**
   - 用户上传/粘贴：
     - PRD 文本（Markdown/纯文本）；
     - 表格需求（Markdown 表格 / CSV / JSON）。
   - 用户输入/选择：
     - 用例拆解原则（文本规则，如边界值、等价类、异常路径等）；
     - 模块分类规则 metric（参考 `metric/` 下文档，为大模型友好的结构化描述）。

2. **规则生成阶段（Walkthrough Rule 生成）**
   - Agent 基于：
     - 需求文本 + 表格；
     - 用例拆解原则；
     - 模块分类 metric；
   - 产出：**用例 walkthrough rule**，结构化描述如何从需求逐条生成用例，包括：
     - 模块/功能拆分规则；
     - 场景枚举维度（正常流/异常流/边界/性能/安全等）；
     - 每条用例需覆盖的字段模板（标题、前置条件、步骤、预期结果、优先级、关联场景/模块等），与 DB/ES 字段对齐；
     - 输出格式约束（Markdown、JSONL）。

3. **用例生成阶段**
   - 依据 walkthrough rule，对需求进行逐条 walkthrough：
     - 为每个功能点、场景、路径生成一条或多条测试用例；
     - 每条用例直接输出为结构化 JSON（对齐 `db requirement` 的 `test_case`、`case_scene`、`case_relation` 等字段）；
     - 并可按模板渲染为 Markdown 用例文档。

4. **落地与同步阶段（与 DB/ES 集成预留）**
   - 生成的 JSONL 可：
     - 直接写入关系型 DB；
     - 通过现有数据同步脚本写入 ES；
     - 或导出为标准化 JSON/Markdown 供人工校验后导入。

---

## 2. 技术栈与框架要求

1. **编程语言与环境**
   - Python ≥ 3.9。
   - 使用 `venv` 创建虚拟环境：
     - 约定目录：`venv/`。

2. **Agent 框架**
   - 基于 **LangChain 1.x** + **DeepAgent 风格的多阶段/多工具 Agent**：
     - 使用 LangChain 的：（https://docs.langchain.com/oss/python/deepagents/overview）
       - `ChatModel` 封装 G2M 文本/多模态模型；
       - `Tools` / `Runnable` 组合实现：文档解析、规则生成、用例生成；
       - `AgentExecutor`（或 Runnable graph）组织 workflow。
     - DeepAgent 思路：
       - 将整体流程拆分为多个子 Agent / 子任务节点（需求解析、metric 整理、rule 生成、用例生成）；
       - 使用显式的状态对象在节点之间传递（如 `Context` / `State` dataclass）。

3. **输入输出格式支持**
   - **Markdown**：
     - 输入：PRD 文档、拆解原则、metric 说明可以是 Markdown。
     - 输出：
       - 用例 walkthrough rule 的 Markdown 说明文档；
       - 用例清单的 Markdown（表格形式）。
   - **JSONL**：
     - 对于机器消费/落地 DB/ES：
       - 每行一个 JSON 对象，对齐 `db requirement` 中的字段设计；
       - 适配：`test_case`、`case_scene`、`case_scene_mapping`、`case_relation`。

4. **模型调用与配置（统一配置）**
   - 模型能力与接口严格参考 `arch-solution/model requirement.md`：
     - 文本生成：`/v1/completions`；
     - 多模态图文：`/v1/chat/completions`（如后续需要解析图表 PRD）；
     - 暂不强依赖 ASR、图像生成，如用到则按 MODEL_REQUIREMENTS 扩展工具。
   - **统一配置文件**（例如 `config/model_config.json`）：
     - 包含：
       - `base_url`（如 `https://llmproxy.gwm.cn` / `http://llmproxy.gwm.cn`）；
       - 各类模型名称：
         - `text_model`（如 `default/qwen3-235b-a22b-instruct`）；
         - `text_coder_model`（如 `default/qwen3-coder-30b-a3b-instruct`，可用于代码/规则生成）；
      - 认证方式：API Key 读取策略（统一从 `config/.env` 加载并注入环境变量，如 `G2M_API_KEY`；不再提交 `.g2m_api_key` 明文文件）。
     - Agent 通过统一的 `ModelClient` 封装访问，避免到处硬编码。

5. **依赖管理**
   - 新建 `requirements.txt`，至少包含：
     - `langchain>=0.3.0`（或实际 1.x 对应版本号）；
     - `requests`（用于直连 G2M 接口时或自定义 client）；
     - `pydantic`（用于 schema 定义、JSON 校验）；
     - `typer` / `argparse`（命令行接口，可选）；
     - `python-dotenv`（可选，用于本地 `.env` 管理）。

---

## 3. 与 DB / ES 需求的对齐（参考 `db requirement.md`）

### 3.1 核心实体映射

Agent 生成的用例数据结构需与以下表结构兼容：

- `test_case`
  - 对应字段（最小集）：
    - `case_id`：Agent 需生成唯一 ID（可使用 UUID 或前缀+自增）；
    - `title`：测试用例标题；
    - `module`：模块名称或路径，对应模板“模块”列；
    - `level`：`P0/P1/P2/P3`，对应模板“用例等级”，为主业务优先级字段；
    - `priority`：`高/中/低`，从 `level` 派生，用于统计/报表/ES 精准筛选；
    - `status`：测试结果，枚举：`OK/NOK/BLOCK/NA`，生成阶段默认 `NA`；
    - `create_time`：生成时间戳；
    - `update_time`：最近更新时间戳；
    - `executor`：可留空或默认 `agent`; 
    - `steps` / `expected_result`：
      - Agent 侧输出为 **逻辑字段**：步骤文本和预期结果文本；
      - 落地脚本负责将文本写入文件/对象存储并生成 `steps_path` / `expected_result_path`，同时同步全文到 ES。

- `case_scene`
  - Agent 可基于需求中的“场景”定义生成：
    - `scene_id`：唯一 ID；
    - `scene_name`：场景名称；
    - `scene_desc_path`：同 `steps_path`，Agent 输出为 `scene_desc` 文本。

- `case_scene_mapping`
  - 定义场景与用例间多对多关系：
    - `mapping_id`：唯一 ID；
    - `scene_id`、`case_id`：引用上述 ID。

- `case_relation`
  - 可选，由 Agent 推理用例间逻辑关系：
    - `relation_type`：`依赖/关联/阻塞/衍生`；
    - `remark`：简要说明。

### 3.2 JSON / JSONL 输出字段规范

- 顶层字段命名：全部 `snake_case`，与 DB 字段保持一致或可映射。
- 用例 JSON 示例（单条）：

```json
{
  "case_id": "case_0001",
  "title": "登录成功-正确账号密码",
  "module": "用户登录模块",
  "level": "P0",
  "priority": "高",
  "status": "NA",
  "steps": [
    "打开登录页",
    "输入已注册账号",
    "输入正确密码",
    "点击登录按钮"
  ],
  "expected_result": "跳转至首页，展示用户昵称",
  "scene_ids": ["scene_login_happy"]
}
```

- JSONL：每行一个如上结构或带额外字段（如 `scene_mappings`、`relations`）。

### 3.3 大模型友好性

- 所有 Agent 中间产出（规则、草稿用例）均使用：
  - 结构化 JSON 或结构清晰的 Markdown（标题+表格）。
- 避免多层嵌套（≤ 2 层），字段解释清晰。
- Walkthrough Rule 需明确约定：
  - 生成时的必填字段、推荐字段；
  - 枚举值、默认值；
  - 如何映射到 DB/ES 字段。

---

## 4. Agent 角色与模块划分

### 4.1 核心 Agent 角色

1. **需求解析 Agent**
   - 输入：PRD/表格（Markdown/JSON）、模块 metric。
   - 输出：结构化需求对象：
     - 模块列表、功能点列表、场景草图。

2. **规则生成 Agent（Walkthrough Rule Agent）**
   - 输入：结构化需求 + 拆解原则 + metric。
   - 输出：
     - `walkthrough_rule`（JSON + 对应 Markdown 说明）：
       - 模块划分规则；
       - 用例分类维度；
       - 字段模板与映射；
       - 命名约定、优先级分配规则等。

3. **用例生成 Agent**
   - 输入：需求对象 + `walkthrough_rule`。
   - 输出：
     - 测试用例 JSONL；
     - 可选：用例 Markdown 表格。

4. **校验与汇总 Agent（可选）**
   - 任务：
     - 对生成的用例集进行覆盖度、冗余度、规范性检查；
     - 输出校验报告（Markdown），辅助人工评审。

### 4.2 DeepAgent / LangChain 结构建议

- 使用一个统一的 `State`（例如 Pydantic `BaseModel`）：
  - `raw_prd_md`、`raw_table_md`、`decomposition_principles`、`metric_definitions`；
  - `parsed_requirements`、`walkthrough_rule`、`test_cases` 等。
- 各 Agent 作为一个 `Runnable` / 工具节点：
  - `parse_requirements_node`；
  - `generate_walkthrough_rule_node`；
  - `generate_testcases_node`；
  - `validate_testcases_node`。
- 通过 LangChain Runnable graph 或 AgentExecutor 组织有向流程图。

---

## 5. 命令行与使用方式（工具层）

### 5.1 基本 CLI

- 提供一个入口脚本：`main.py`（或 `cli.py`），支持：
  - 从文件读取 PRD/表格（Markdown/JSON）；
  - 从文件读取拆解原则、metric；
  - 指定输出目录：
    - `--out-md`：Walkthrough rule + 用例 Markdown；
    - `--out-jsonl`：标准化 JSONL；
  - 选择是否只生成 walkthrough rule，或完整跑到用例生成。

示例：

```bash
python main.py \
  --prd docs/prd_login.md \
  --metric metric/login_metric.md \
  --rules docs/decomposition_rules.md \
  --out-md outputs/login_testcases.md \
  --out-jsonl outputs/login_testcases.jsonl
```

### 5.2 配置加载

- 支持通过：
  - `--config config/model_config.json` 指定模型与 API 设置；
  - 默认从 `config/model_config.json` 读取；
  - 环境变量 `G2M_API_KEY` 提供鉴权（来源于统一的 `config/.env`）。

---

## 6. 非功能与质量要求

- **可测试性**：
  - 核心解析与格式转换逻辑尽量纯 Python，可编写单元测试；
  - 大模型调用部分用接口封装，便于 mock。

- **日志与可观测性**：
  - 使用 `logging`，记录每阶段输入输出摘要（避免敏感数据泄露）。

- **扩展性**：
  - 预留：
    - 向量检索（ES/向量库）作为辅助检索；
    - 图谱导出接口，与 `db requirement` 中图谱能力对接。

---

> 本需求文件用于约束“测试用例生成 Agent”的实现，需与 `db requirement.md`、`model requirement.md` 协同维护，后续如有架构/接口调整需同步更新本文件。