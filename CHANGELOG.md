# Changelog

All notable changes to VITA QA Agent will be documented in this file.

## [0.2.0] - 2025-12-30

### Added
- **增强错误处理机制**
  - 新增自定义异常类 (`src/utils/exceptions.py`)
  - 添加错误处理装饰器和工具函数 (`src/utils/error_handler.py`)
  - 模型客户端支持自动重试和超时处理
  - 更详细的错误日志和上下文信息

- **可配置的LLM提示词系统**
  - YAML格式的提示词配置文件 (`config/prompts.yaml`)
  - 配置加载器支持动态加载和热更新 (`src/utils/config_loader.py`)
  - 支持自定义提示词优化生成质量
  - 全局配置管理（温度、最大tokens、重试次数等）

- **多PRD文件和URI输入支持**
  - 支持同时加载多个PRD文档
  - 支持本地文件路径和HTTP(S) URL
  - 自动合并多个PRD为统一文档
  - URI加载器 (`src/utils/file_loader.py`)

- **CLI v2 增强版** (`cli/main_v2.py`)
  - 支持 `--prd` 参数重复使用加载多个PRD
  - 支持 `--prompts-config` 指定自定义提示词配置
  - 支持 `--merge-prds` 控制是否合并多个PRD
  - 更友好的错误提示和进度显示

### Changed
- 模型客户端增强错误处理（Doubao和G2M）
- 改进日志输出格式和详细程度
- requirements.txt 更新依赖项

### Fixed
- 模型API调用的超时和重试逻辑
- JSON解析的健壮性
- 文件操作的错误处理

## [0.1.0] - 2025-12-30

### Added
- 初始版本发布
- 核心Agent系统（需求解析、规则生成、用例生成）
- Doubao和G2M模型客户端
- CLI命令行工具
- 单元测试和集成测试
- 完整文档（README, QUICKSTART）

---

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
