# VITA QA Agent - 自动化测试用例生成系统

基于大模型的智能测试用例生成工具，支持从PRD文档自动生成结构化测试用例。

## 功能特性

- 🤖 **智能解析**: 自动解析PRD文档，提取模块、功能和流程信息
- 📋 **规则生成**: 基于需求和原则生成Walkthrough Rule
- 🧪 **用例生成**: 自动生成符合数据库规范的结构化测试用例
- 🔄 **多模型支持**: 支持Doubao（豆包）和G2M模型，可自动切换
- 📊 **多格式输出**: 支持JSONL、Markdown等多种输出格式
- 🎯 **优先级智能**: 自动分配用例优先级和等级

## 架构说明

本系统基于以下架构文档实现：
- `arch-solution/agent_requirement.md` - Agent需求规范
- `arch-solution/model+requirement-doubao.md` - Doubao模型接口
- `arch-solution/model+requirement-g2m.md` - G2M模型接口
- `arch-solution/db+requirement.md` - 数据库设计规范
- `arch-solution/walkthrough_rule_spec.md` - Walkthrough Rule规范
- `metric/识人识物_用例设计原则与示例.md` - 用例设计原则（PRD示例）

## 目录结构

```
vita-qaagent/
├── src/                    # 核心源代码
│   ├── models/            # 模型客户端
│   │   ├── base.py        # 基础接口
│   │   ├── doubao_client.py   # Doubao客户端
│   │   ├── g2m_client.py      # G2M客户端
│   │   └── model_factory.py   # 模型工厂
│   ├── agents/            # Agent实现
│   │   ├── requirement_parser.py   # 需求解析Agent
│   │   ├── rule_generator.py       # 规则生成Agent
│   │   └── testcase_generator.py   # 用例生成Agent
│   └── utils/             # 工具函数
│       ├── logger.py      # 日志配置
│       └── file_utils.py  # 文件操作
├── cli/                   # CLI命令行工具
│   └── main.py           # 主入口
├── tests/                 # 测试代码
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
├── frontend/             # 前端（预留）
├── outputs/              # 输出目录
│   ├── testcases/       # 测试用例输出
│   ├── rules/           # Walkthrough Rule输出
│   ├── reports/         # 报告输出
│   └── logs/            # 日志文件
├── history/              # 历史记录
├── config/               # 配置文件
│   ├── .env.example     # 环境变量模板
│   └── README.md        # 配置说明
├── arch-solution/        # 架构文档
├── metric/               # 指标和PRD示例
└── requirements.txt      # Python依赖

```

## 快速开始

### 1. 环境准备

```bash
# Python 3.9+
python --version

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API Key

复制配置模板并填写API Key：

```bash
cp config/.env.example config/.env
```

编辑 `config/.env`，填入你的API Key：

```env
# 优先使用Doubao（豆包/火山方舟）
ARK_API_KEY=ae3d2401-a6ac-481f-a958-673b17d7b38c

# 或使用G2M（可选，作为备选）
G2M_API_KEY=your_g2m_key_here
```

> ⚠️ **重要**: 请勿将真实的API Key提交到版本控制系统！

### 3. 运行示例

使用识人识物PRD生成测试用例：

```bash
python cli/main.py generate \
  --prd metric/识人识物_用例设计原则与示例.md \
  --project recognition \
  --output outputs \
  --verbose
```

查看输出：

```bash
# 查看生成的测试用例
ls outputs/testcases/

# 查看生成的规则
ls outputs/rules/

# 查看Markdown报告
ls outputs/reports/
```

### 4. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 查看覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 使用说明

### 基本命令

```bash
# 查看帮助
python cli/main.py --help

# 查看版本
python cli/main.py version

# 生成测试用例
python cli/main.py generate --prd <PRD文件路径> [选项]
```

### 命令参数

| 参数 | 简写 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `--prd` | `-p` | ✓ | PRD文档路径（Markdown格式） | `metric/识人识物_用例设计原则与示例.md` |
| `--project` | - | - | 项目名称（默认使用文件名） | `recognition` |
| `--output` | `-o` | - | 输出目录（默认：outputs） | `outputs` |
| `--metric` | `-m` | - | Metric文档路径（可选） | `metric/模块分类.md` |
| `--principles` | - | - | 用例拆解原则文档路径（可选） | `docs/principles.md` |
| `--provider` | - | - | 模型提供商（auto/doubao/g2m，默认：auto） | `doubao` |
| `--save-rule` | - | - | 是否保存生成的规则（默认：True） | - |
| `--verbose` | `-v` | - | 详细输出 | - |

### 使用示例

#### 1. 最简单的用法

```bash
python cli/main.py generate --prd my_prd.md
```

#### 2. 指定项目名称和输出目录

```bash
python cli/main.py generate \
  --prd docs/login_feature.md \
  --project login_module \
  --output results/
```

#### 3. 使用Metric和拆解原则

```bash
python cli/main.py generate \
  --prd docs/feature.md \
  --metric metric/classification.md \
  --principles docs/decomposition_rules.md \
  --project myproject
```

#### 4. 指定使用Doubao模型

```bash
python cli/main.py generate \
  --prd docs/feature.md \
  --provider doubao \
  --verbose
```

## 输出说明

生成完成后，会在输出目录生成以下文件：

### 1. 测试用例JSONL (`testcases/项目名_testcases_时间戳.jsonl`)

每行一个JSON对象，包含完整的测试用例信息：

```json
{
  "case_id": "case_abc123",
  "title": "人脸检测-正常检测流程-正常",
  "project_name": "recognition",
  "module": "人脸识别模块",
  "feature": "人脸检测",
  "level": "P0",
  "priority": "高",
  "status": "NA",
  "steps": ["步骤1", "步骤2", "步骤3"],
  "expected_result": "检测成功并返回人脸位置",
  "precondition": "摄像头正常工作",
  "source": "需求",
  "environment": "台架",
  "owner": "TBD",
  "executor": "agent",
  "remark": "",
  "create_time": "2025-12-30 10:00:00",
  "update_time": "2025-12-30 10:00:00"
}
```

### 2. 场景JSONL (`testcases/项目名_scenes_时间戳.jsonl`)

场景定义，可选输出。

### 3. 场景映射JSONL (`testcases/项目名_scene_mappings_时间戳.jsonl`)

测试用例与场景的映射关系。

### 4. Walkthrough Rule (`rules/项目名_rule_时间戳.json`)

生成的测试用例生成规则，可复用于同类项目。

### 5. Markdown报告 (`reports/项目名_summary_时间戳.md`)

人类可读的测试用例汇总报告。

## 数据库集成

生成的JSONL文件可直接导入数据库。字段与 `arch-solution/db+requirement.md` 中定义的表结构完全对齐：

- `test_case` 表
- `case_scene` 表
- `case_scene_mapping` 表
- `case_relation` 表

### 导入示例（MySQL）

```bash
# 使用工具导入JSONL到MySQL
# （需要自行实现或使用ETL工具）
```

## 开发指南

### 添加新的模型支持

1. 在 `src/models/` 创建新的客户端类，继承 `BaseModelClient`
2. 实现 `chat_completion` 和 `multimodal_completion` 方法
3. 在 `model_factory.py` 中注册新模型

### 自定义Agent逻辑

- 修改 `src/agents/requirement_parser.py` 调整需求解析逻辑
- 修改 `src/agents/rule_generator.py` 调整规则生成策略
- 修改 `src/agents/testcase_generator.py` 调整用例生成细节

### 运行开发模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 运行
python cli/main.py generate --prd test.md --verbose
```

## 故障排查

### 常见问题

**Q: 提示 "ARK_API_KEY not found"**

A: 请确保已在 `config/.env` 中设置了 `ARK_API_KEY`，或通过环境变量导出。

**Q: 生成的用例数量为0**

A: 检查PRD文档格式是否正确，建议参考 `metric/识人识物_用例设计原则与示例.md` 的格式。

**Q: 模型调用超时**

A: 检查网络连接，确保可以访问 Doubao 或 G2M 的API端点。可尝试增加timeout设置。

### 日志位置

所有日志保存在 `outputs/logs/` 目录，按时间戳命名。

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

内部项目，仅供授权人员使用。

## 联系方式

如有问题，请联系项目维护者。

---

**版本**: 0.1.0
**最后更新**: 2025-12-30
