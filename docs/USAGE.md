# VITA QA Agent 使用手册

## 快速开始

### 基础使用（单PRD）

```bash
python cli/main.py generate \
  --prd metric/识人识物_用例设计原则与示例.md \
  --project recognition
```

### 增强使用（多PRD + URI）

```bash
python cli/main_v2.py generate \
  --prd local_prd1.md \
  --prd local_prd2.md \
  --prd https://example.com/remote_prd.md \
  --project multi_source
```

## 命令参数说明

### 通用参数

| 参数 | 简写 | 必填 | 说明 |
|------|------|------|------|
| `--prd` | `-p` | ✓ | PRD文档路径或URL |
| `--output` | `-o` | - | 输出目录（默认：outputs）|
| `--project` | - | - | 项目名称（默认：从PRD文件名提取）|
| `--metric` | `-m` | - | Metric文档路径或URL |
| `--principles` | - | - | 拆解原则文档路径或URL |
| `--provider` | - | - | 模型提供商（auto/doubao/g2m）|
| `--verbose` | `-v` | - | 详细输出 |

### CLI v2特有参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--prompts-config` | 自定义提示词配置文件 | config/prompts.yaml |
| `--merge-prds` | 是否合并多个PRD | true |

## 使用场景

### 场景1: 标准单PRD项目

```bash
python cli/main.py generate \
  --prd docs/feature.md \
  --project my_feature \
  --output results/
```

### 场景2: 多模块项目（多PRD）

```bash
python cli/main_v2.py generate \
  --prd modules/auth.md \
  --prd modules/payment.md \
  --prd modules/order.md \
  --project complete_system
```

### 场景3: 从远程获取PRD

```bash
python cli/main_v2.py generate \
  --prd https://docs.company.com/latest_prd.md \
  --metric https://docs.company.com/metrics.md \
  --project production
```

### 场景4: 自定义提示词优化

```bash
python cli/main_v2.py generate \
  --prd my_prd.md \
  --prompts-config custom_prompts.yaml \
  --verbose
```

## 输出文件说明

### 1. 测试用例JSONL
- 位置: `outputs/testcases/{项目名}_testcases_{时间戳}.jsonl`
- 格式: 每行一个JSON对象
- 用途: 可直接导入数据库

### 2. 场景JSONL
- 位置: `outputs/testcases/{项目名}_scenes_{时间戳}.jsonl`
- 格式: 场景定义列表
- 用途: 场景管理

### 3. 场景映射JSONL
- 位置: `outputs/testcases/{项目名}_scene_mappings_{时间戳}.jsonl`
- 格式: 用例与场景的映射关系
- 用途: 关联查询

### 4. Walkthrough Rule
- 位置: `outputs/rules/{项目名}_rule_{时间戳}.json`
- 格式: 完整的规则定义
- 用途: 规则复用和审查

### 5. Markdown报告
- 位置: `outputs/reports/{项目名}_summary_{时间戳}.md`
- 格式: 人类可读的汇总报告
- 用途: 团队沟通和存档

## 配置优化

### 提示词配置

编辑 `config/prompts.yaml` 优化生成质量：

```yaml
requirement_parser:
  system_prompt: |
    你是一个专业的测试工程师...（可修改）

global:
  default_temperature: 0.3  # 调整生成随机性（0-1）
  default_max_tokens: 4000  # 调整最大输出长度
  max_retries: 3            # 调整重试次数
```

### 环境变量

在 `config/.env` 中配置API Key：

```env
ARK_API_KEY=your_ark_api_key
G2M_API_KEY=your_g2m_api_key
```

## 常见问题

### Q: 如何处理大型PRD？
A: 使用多PRD功能拆分成多个文件，每个文件处理一个模块。

### Q: 生成质量不理想？
A: 尝试调整 `config/prompts.yaml` 中的提示词和参数。

### Q: 如何从URL加载PRD？
A: 使用 `cli/main_v2.py` 并指定HTTP(S) URL即可。

### Q: 支持哪些PRD格式？
A: 支持Markdown格式的PRD文档。

## 最佳实践

1. **模块化PRD**: 大型项目建议拆分多个PRD文件
2. **版本控制**: PRD使用Git管理，可以用URL引用特定版本
3. **提示词优化**: 针对特定领域调整提示词配置
4. **输出管理**: 使用有意义的project名称，便于识别
5. **定期备份**: 保存生成的规则文件，便于复用

## 进阶用法

### 批量处理

```bash
#!/bin/bash
for prd in prds/*.md; do
  python cli/main.py generate --prd "$prd" --project "$(basename $prd .md)"
done
```

### 集成到CI/CD

```yaml
# .github/workflows/testcase-gen.yml
- name: Generate Test Cases
  run: |
    python cli/main_v2.py generate \
      --prd ${{ github.event.pull_request.body }} \
      --project pr-${{ github.event.pull_request.number }}
```

---

更新时间: 2025-12-30
版本: 0.2.0
