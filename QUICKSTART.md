# VITA QA Agent 快速开始指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置API Key

API Key已预配置在 `config/.env`：
- ARK_API_KEY=ae3d2401-a6ac-481f-a958-673b17d7b38c

## 3. 运行示例（单入口 main.py，默认 materialize）

```bash
python cli/main.py generate \
  --prd metric/识人识物_用例设计原则与示例.md \
  --project recognition \
  --output outputs \
  --merge-prds \
  --materialize \
  --verbose
```

### 示例2: 查看帮助

```bash
python cli/main.py --help
python cli/main.py generate --help
```

### 示例3: 多PRD+自定义prompts

```bash
python cli/main.py generate \
  --prd prd/a.md --prd prd/b.md \
  --prompts-config config/prompts.yaml \
  --no-merge-prds
```

### 示例4: 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v
```

## 4. 查看输出

生成完成后，查看输出文件：

```bash
# 测试用例JSONL（含 db_* / es_docs_*）
ls outputs/testcases/

# Walkthrough Rule
cat outputs/rules/recognition_rule_*.json

# Markdown报告
cat outputs/reports/recognition_summary_*.md
```

## 5. 项目结构

```
vita-qaagent/
├── src/              # 核心源代码
│   ├── models/      # 模型客户端
│   ├── agents/      # Agent实现
│   └── utils/       # 工具函数
├── cli/             # CLI工具
├── tests/           # 测试
├── outputs/         # 输出目录
├── config/          # 配置
└── README.md        # 详细文档
```

## 6. 关键特性

✓ **智能解析**: 自动解析PRD文档
✓ **规则生成**: 生成Walkthrough Rule
✓ **用例生成**: 自动生成测试用例
✓ **多模型**: 支持Doubao（优先）和G2M
✓ **多格式**: JSONL、JSON、Markdown输出
✓ **数据库/ES对齐**: 提供 db_* 与 es_docs_* 实体化输出

## 7. 常见问题

**Q: 如何修改模型？**
A: 使用 `--provider` 参数，如 `--provider doubao` 或 `--provider g2m`

**Q: 输出在哪里？**
A: 默认在 `outputs/` 目录，可通过 `--output` 指定

**Q: 如何自定义用例生成规则？**
A: 提供 `--principles` 参数指定拆解原则文档

## 8. 下一步

阅读完整文档: [README.md](README.md)

---
快速上手时间: < 5分钟
