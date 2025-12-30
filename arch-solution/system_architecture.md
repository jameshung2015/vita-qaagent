# VITA QA Agent 系统架构文档

## 架构概览

VITA QA Agent 采用分层架构设计，从底层模型客户端到上层CLI工具，提供完整的测试用例自动生成解决方案。

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Layer (用户接口层)                 │
│  cli/main.py (单入口，支持多PRD/URL/merge/materialize)  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 Agent Layer (智能代理层)                 │
│  RequirementParser | RuleGenerator | TestCaseGenerator  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│               Model Client Layer (模型客户端层)          │
│     DoubaoClient (优先) | G2MClient (兼容)              │
│              ModelFactory (自动选择)                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Data Entities & Materialize Layer (数据实体)     │
│  Pydantic实体: TestCase / CaseScene / SceneMapping /    │
│  CaseRelation / TestCaseIndexDocument; materializer将     │
│  生成结果落盘steps/expected文本并产出DB/ES JSONL         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 Utils Layer (工具层)                     │
│  ErrorHandler | ConfigLoader | FileLoader | Logger      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              External Services (外部服务)                │
│  Doubao API | G2M API | File System | Remote URLs | ES  │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. CLI Layer (用户接口层)

**职责**: 提供命令行接口，处理用户输入，协调各组件工作

**组件**:
- `cli/main.py`: 增强版CLI (v0.2.0+, 单入口)

**特性**:
- 参数解析和验证
- 友好的进度显示
- 错误处理和用户提示

### 2. Agent Layer (智能代理层)

**职责**: 实现核心业务逻辑，使用LLM进行智能分析和生成

#### RequirementParser (需求解析Agent)
- **输入**: PRD文档、Metric定义
- **输出**: 结构化需求对象
- **功能**:
  - 提取模块、功能、流程
  - 识别场景类型
  - 提取前后置条件

#### RuleGenerator (规则生成Agent)
- **输入**: 解析后的需求、拆解原则、Metric
- **输出**: Walkthrough Rule
- **功能**:
  - 定义场景维度
  - 生成优先级规则
  - 配置字段模板

#### TestCaseGenerator (用例生成Agent)
- **输入**: 需求、Walkthrough Rule
- **输出**: 测试用例、场景、映射关系
- **功能**:
  - 生成测试步骤
  - 生成预期结果
  - 分配优先级
  - 创建场景映射

### 3. Model Client Layer (模型客户端层)

**职责**: 封装模型API调用，提供统一接口

#### DoubaoClient
- OpenAI兼容SDK
- 支持文本和多模态
- 优先使用

#### G2MClient
- 直接HTTP请求
- 兼容G2M接口
- 自动fallback

#### ModelFactory
- 自动选择最佳客户端
- 统一配置管理

**特性** (v0.2.0+):
- 自动重试机制（3次）
- 指数退避策略
- 超时检测
- 详细错误日志

### 4. Data Entities & Materialize Layer (数据实体与落盘)

**职责**: 将生成结果对齐关系型表与ES索引，落盘文本供路径存储，并产出可直接入库/索引的JSONL。

**组件**:
- `src/entities/db_models.py`: TestCase / CaseScene / CaseSceneMapping / CaseRelation / TestCaseIndexDocument 枚举与时间格式化
- `src/entities/materializer.py`: 写入 steps/expected/scene 文本文件；构造 DB/ES Pydantic 实体；输出 db_* 与 es_docs_* JSONL

**ES 支撑能力**:
- 字段映射对齐 `arch-solution/db+requirement.md` 中的 `test_case_index`（keyword/text + ik_max_word/ik_smart，BM25）
- 支持 steps/expected/title 全文检索与相似度；scene_ids/scene_names 精准/模糊过滤
- 文档ID与关系库 `case_id` 对齐，便于增量同步与删除

### 4. Utils Layer (工具层)

**职责**: 提供通用工具函数和辅助功能

#### ErrorHandler
- 自定义异常体系
- 错误处理装饰器
- 自动重试机制
- JSON验证工具

#### ConfigLoader (v0.2.0+)
- YAML配置加载
- 提示词模板管理
- 全局参数配置
- 热加载支持

#### FileLoader (v0.2.0+)
- 本地文件加载
- HTTP(S) URL支持
- 多文件合并
- URI自动识别

#### Logger
- 分级日志
- 文件和控制台输出
- 结构化日志

## 数据流

### 完整流程

```
用户输入PRD
    ↓
[CLI Layer] 参数解析和验证
    ↓
[FileLoader] 加载PRD内容（支持URI）
    ↓
[ConfigLoader] 加载提示词配置
    ↓
[ModelFactory] 初始化模型客户端
    ↓
[RequirementParser] 解析PRD → 结构化需求
    ↓
[RuleGenerator] 生成Walkthrough Rule
    ↓
[TestCaseGenerator] 生成测试用例
    ↓
[FileUtils] 保存输出文件（JSONL/JSON/MD）
    ↓
输出结果
```

### 错误处理流程

```
API调用
    ↓
出现错误
    ↓
[ErrorHandler] 捕获异常
    ↓
判断异常类型
    ├─ 超时 → 重试（最多3次）
    ├─ API错误 → 记录详情 → 重试
    └─ 其他错误 → 记录日志 → 抛出
    ↓
最终成功或失败
```

## 配置管理

### 配置文件

- `config/.env`: 环境变量（API Key等）
- `config/prompts.yaml`: LLM提示词配置
- `config/model_config.json`: 模型参数（可选）

### 配置优先级

1. 命令行参数
2. 自定义配置文件
3. 默认配置文件
4. 代码内默认值

## 扩展性设计

### 添加新模型

1. 继承 `BaseModelClient`
2. 实现 `chat_completion` 和 `multimodal_completion`
3. 在 `ModelFactory` 中注册

### 添加新Agent

1. 创建新Agent类
2. 注入 `ModelClient`
3. 使用 `ConfigLoader` 加载提示词
4. 在CLI中集成

### 自定义提示词

1. 复制 `config/prompts.yaml`
2. 修改提示词内容
3. 使用 `--prompts-config` 参数

## 性能优化

### 缓存机制

- 配置文件缓存（首次加载后复用）
- 模型客户端单例模式

### 异步支持（规划中）

- 并发处理多个PRD
- 异步API调用

## 安全性

### API Key管理

- 环境变量存储
- 不提交到版本控制
- `.gitignore`保护

### 输入验证

- PRD格式验证
- URI安全检查
- JSON schema验证

### 错误信息

- 敏感信息脱敏
- 详细日志本地存储
- 用户友好的错误提示

## 依赖关系

```
CLI v2
  ├── Agent Layer
  │   ├── RequirementParser
  │   ├── RuleGenerator
  │   └── TestCaseGenerator
  ├── Model Client Layer
  │   ├── DoubaoClient
  │   ├── G2MClient
  │   └── ModelFactory
  └── Utils Layer
      ├── ErrorHandler
      ├── ConfigLoader
      ├── FileLoader
      └── Logger

Agent Layer → Model Client Layer
Agent Layer → Utils Layer
Model Client Layer → Utils Layer (ErrorHandler)
```

## 版本演进

### v0.1.0
- 基础Agent系统
- Doubao和G2M支持
- 单PRD处理
- CLI v1

### v0.2.0 (当前)
- 增强错误处理
- 可配置提示词
- 多PRD和URI支持
- CLI v2

### v0.3.0 (规划)
- Web UI
- 批量处理
- 缓存优化
- 更多模型支持

---

最后更新: 2025-12-30
版本: 0.2.0
