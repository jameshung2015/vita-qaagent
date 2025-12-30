# VITA QA Agent v0.2.0 发布说明

发布日期: 2025-12-30

## 🎉 主要更新

VITA QA Agent v0.2.0 带来了三大重要功能增强，显著提升了系统的稳定性、可配置性和灵活性。

## ✨ 新功能

### 1. 增强的错误处理机制 🛡️

#### 自定义异常体系
新增专门的异常类，提供更精确的错误分类：

```python
from src.utils.exceptions import ModelAPIError, ParsingError

try:
    result = model_client.chat_completion(...)
except ModelAPIError as e:
    print(f"API错误: {e.status_code} - {e.response_text}")
except ParsingError as e:
    print(f"解析失败: {e.content}")
```

#### 自动重试机制
模型调用支持自动重试和指数退避：

- **重试次数**: 3次
- **退避策略**: 2秒 → 4秒 → 8秒
- **超时处理**: 自动检测并重试
- **错误日志**: 详细的上下文记录

#### 错误处理装饰器
简化错误处理代码：

```python
@handle_errors("操作失败", reraise=True)
def my_function():
    ...
```

**收益**:
- ✅ 更稳定的模型API调用
- ✅ 更清晰的错误信息
- ✅ 更好的故障恢复能力

### 2. 可配置的LLM提示词系统 🎨

#### YAML配置文件
所有提示词集中管理在 `config/prompts.yaml`:

```yaml
requirement_parser:
  system_prompt: |
    你是一个专业的测试工程师...

  parse_prompt_template: |
    请分析以下需求文档...
    {prd_content}

global:
  default_temperature: 0.3
  max_retries: 3
```

#### 动态加载和自定义
支持运行时指定自定义配置：

```bash
python cli/main_v2.py generate \
  --prd my_prd.md \
  --prompts-config my_custom_prompts.yaml
```

#### 优化空间
可以通过修改配置文件来：
- 调整Agent角色定义
- 优化输出格式要求
- 修改生成参数（温度、tokens等）
- 添加更多上下文信息

**收益**:
- ✅ 无需修改代码即可优化生成质量
- ✅ 支持A/B测试不同提示词
- ✅ 团队共享最佳配置

### 3. 多PRD文件和URI输入支持 🌐

#### 多文件输入
一次性处理多个PRD文档：

```bash
python cli/main_v2.py generate \
  --prd module_a.md \
  --prd module_b.md \
  --prd module_c.md \
  --project complete_system
```

#### URI支持
支持从本地或远程加载：

```bash
# 本地文件
--prd /path/to/local.md

# HTTP URL
--prd https://docs.company.com/prd.md

# 混合使用
--prd local.md --prd https://example.com/remote.md
```

#### 智能合并
自动合并多个PRD为统一文档：
- 添加章节标题
- 保持文档结构
- 可选择不合并（分别处理）

**收益**:
- ✅ 支持大型项目的模块化PRD管理
- ✅ 从CI/CD或文档平台直接获取PRD
- ✅ 团队协作更方便

## 🚀 CLI v2 增强版

新增 `cli/main_v2.py` 提供所有新功能：

```bash
# 查看帮助
python cli/main_v2.py --help

# 查看版本
python cli/main_v2.py version

# 多PRD + 自定义提示词
python cli/main_v2.py generate \
  --prd prd1.md --prd prd2.md \
  --prompts-config custom.yaml \
  --project myproject \
  --verbose
```

**新增参数**:
- `--prd` (可重复多次)
- `--prompts-config` (自定义提示词)
- `--merge-prds` (控制是否合并)

## 📁 新增文件

```
vita-qaagent/
├── cli/
│   └── main_v2.py              # CLI增强版
├── config/
│   └── prompts.yaml            # 提示词配置
├── src/utils/
│   ├── exceptions.py           # 自定义异常
│   ├── error_handler.py        # 错误处理工具
│   ├── config_loader.py        # 配置加载器
│   └── file_loader.py          # URI加载器
├── docs/
│   └── ENHANCEMENTS.md         # 详细功能说明
├── CHANGELOG.md                # 更新日志
└── RELEASE_v0.2.0.md          # 本文件
```

## 📊 代码统计

- **新增代码**: ~1,600行
- **新增文件**: 9个
- **更新文件**: 2个
- **新增文档**: 3个

## 🔄 向后兼容

**100% 向后兼容**:
- 原有 `cli/main.py` 保持不变
- 所有现有功能继续工作
- 可以逐步迁移到v2

## 📚 文档更新

- [ENHANCEMENTS.md](docs/ENHANCEMENTS.md) - 详细功能说明和使用示例
- [CHANGELOG.md](CHANGELOG.md) - 版本更新日志
- [README.md](README.md) - 更新主文档（待更新）

## 🎯 使用示例

### 示例1: 多模块项目

```bash
python cli/main_v2.py generate \
  --prd modules/user_management.md \
  --prd modules/payment_system.md \
  --prd modules/order_processing.md \
  --metric shared/metrics.md \
  --project enterprise_system
```

### 示例2: 远程PRD + 自定义配置

```bash
python cli/main_v2.py generate \
  --prd https://docs.internal.com/latest_prd.md \
  --prompts-config tuned_prompts.yaml \
  --project production_v2
```

### 示例3: 优化提示词测试

```bash
python cli/main_v2.py generate \
  --prd test_prd.md \
  --prompts-config test_prompts.yaml \
  --verbose \
  --project prompt_optimization
```

## ⚡ 性能改进

- 错误恢复时间减少：自动重试避免手动重新运行
- 网络故障容忍性提升：超时自动重试
- 配置加载优化：缓存机制

## 🐛 Bug修复

- 修复模型API超时未正确处理的问题
- 修复JSON解析失败时的错误消息不清晰
- 改进文件操作的异常处理

## 📝 TODO (未来版本)

- [ ] 支持更多URI协议 (FTP, S3等)
- [ ] 提示词在线编辑器
- [ ] 批量PRD处理模式
- [ ] 缓存机制
- [ ] Web UI集成

## 🙏 致谢

感谢所有测试和反馈的用户！

## 📞 反馈

如有问题或建议，请：
1. 查看 [docs/ENHANCEMENTS.md](docs/ENHANCEMENTS.md) 详细文档
2. 检查 [CHANGELOG.md](CHANGELOG.md) 已知问题
3. 提交 Issue 或联系团队

---

**版本**: v0.2.0
**发布日期**: 2025-12-30
**Git标签**: v0.2.0
**分支**: claude/develop-qa-agent-3X613
