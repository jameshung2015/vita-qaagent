# Walkthrough Rule 规范与示例（WALKTHROUGH_RULE_SPEC）

> 目标：给生产脚本/Agent 一个**机器可执行**的规则结构，让它可以“从需求 → 按规则逐条生成用例”，且与 `db requirement.md`、`model requirement.md` 完全对齐，并对大模型友好。

---

## 一、Walkthrough Rule 顶层结构

Walkthrough rule 建议采用单一 JSON 对象形式（可保存为 `.json` 或 `.jsonl` 中的单行），结构如下：

```json
{
  "rule_id": "login_v1",
  "name": "登录功能用例生成规则",
  "version": "1.0.0",
  "description": "适用于账户登录相关功能的用例自动生成规则。",
  "metadata": {
    "created_by": "agent",
    "create_time": "2025-12-30 10:00:00",
    "domain": "web_app_login",
    "language": "zh-CN"
  },
  "input_spec": { ... },
  "module_mapping": { ... },
  "scenario_dimensions": [ ... ],
  "testcase_template": { ... },
  "priority_rules": [ ... ],
  "relation_rules": [ ... ],
  "scene_rules": [ ... ],
  "output_format": { ... }
}
```

各字段含义见下文详细说明。

---

## 二、`input_spec`：输入约定

说明规则期望的**需求输入结构**，方便上游“需求解析 Agent”对齐，也方便脚本校验：

```json
{
  "input_spec": {
    "expected_input_types": ["prd_markdown", "table_markdown"],
    "prd_structure_hint": {
      "sections": [
        {"name": "功能描述", "required": true},
        {"name": "业务流程", "required": false},
        {"name": "异常场景", "required": false}
      ]
    },
    "parsed_requirement_schema": {
      "modules": "list[Module]",
      "Module": {
        "id": "str",
        "name": "str",
        "description": "str",
        "features": "list[Feature]"
      },
      "Feature": {
        "id": "str",
        "name": "str",
        "description": "str",
        "flows": "list[Flow]"
      },
      "Flow": {
        "id": "str",
        "name": "str",
        "type": "['happy','exception','boundary','performance','security']",
        "steps": "list[str]",
        "preconditions": "list[str]",
        "postconditions": "list[str]"
      }
    }
  }
}
```

要点：
- **不强制**真实输入完全一致，但给出“期望的解析后结构”；
- 需求解析 Agent 负责尽量映射到这个 schema（modules/features/flows）。

---

## 三、`module_mapping`：模块与 DB/ES 字段映射

决定如何从需求中的模块/功能点映射到 `module_id` / `module_name` 等字段：

```json
{
  "module_mapping": {
    "default_module": "通用模块",
    "rules": [
      {
        "match_type": "keyword_in_name",
        "keywords": ["登录", "login"],
        "module_id": "login",
        "module_name": "用户登录模块"
      },
      {
        "match_type": "keyword_in_name",
        "keywords": ["注册", "sign up", "signup"],
        "module_id": "signup",
        "module_name": "用户注册模块"
      }
    ],
    "fallback_strategy": "use_feature_name_as_module_name"
  }
}
```

要点：
- `rules` 可按顺序匹配：只要 feature/flow 名称中命中关键字，就设置对应 `module_id` 与 `module_name`；
- `fallback_strategy`：匹配不到时的兜底逻辑，可选：
  - `default_module`（使用 `default_module_id`）；
  - `use_feature_name_as_module_name`；
  - `use_module_from_parsed_requirement` 等。

---

## 四、`scenario_dimensions`：场景维度与用例分类

用于指定从每个 Flow 需要派生哪些用例类型，以及命名约定：

```json
{
  "scenario_dimensions": [
    {
      "dimension_id": "happy_path",
      "name": "正常流",
      "applies_to_flow_types": ["happy"],
      "case_title_pattern": "{feature_name}-{flow_name}-正常", 
      "required": true
    },
    {
      "dimension_id": "invalid_credential",
      "name": "账号/密码错误",
      "applies_to_flow_types": ["happy", "exception"],
      "case_title_pattern": "{feature_name}-{flow_name}-错误凭证", 
      "generation_hints": [
        "覆盖错误账号、错误密码、账号未注册等子场景",
        "至少生成3条子用例：错误账号、错误密码、账号未注册"
      ]
    },
    {
      "dimension_id": "boundary_input_length",
      "name": "输入长度边界",
      "applies_to_flow_types": ["boundary", "happy"],
      "case_title_pattern": "{feature_name}-{flow_name}-长度边界",
      "generation_hints": [
        "针对账号/密码字段，覆盖最短长度、最长长度、超过上限、为空",
        "如 PRD 未指定长度，按账号6-20位、密码8-20位的行业常规推断"
      ]
    },
    {
      "dimension_id": "security_bruteforce",
      "name": "安全-暴力尝试",
      "applies_to_flow_types": ["security", "exception"],
      "optional": true
    }
  ]
}
```

要点：
- 每个 Flow 可以被多个 dimension 组合生成多条用例；
- `case_title_pattern` 使用占位符：`{feature_name}`、`{flow_name}`、`{dimension_name}` 等；
- `generation_hints` 指导大模型如何拓展子场景。

---

## 五、`testcase_template`：用例字段模板（与 DB / 模板对齐）

定义生成用例时的“字段清单 + 默认值 + 文本风格”：

```json
{
  "testcase_template": {
    "fields": {
      "case_id": {
        "strategy": "auto_uuid_with_prefix",
        "prefix": "case_" ,
        "description": "用例编号，对应模板'用例编号'列，可采用 项目-模块-子模块_序号 或 UUID 前缀形式"
      },
      "title": {
        "strategy": "from_pattern",
        "pattern": "{feature_name}-{flow_name}-{dimension_name}",
        "max_length": 256,
        "description": "用例名，对应模板'用例名'列"
      },
      "project_name": {
        "strategy": "from_context_or_case_id",
        "description": "项目名(算法大类)，可从全局输入或从 case_id 前缀中解析"
      },
      "module": {
        "strategy": "from_module_mapping",
        "description": "模块，对应模板'模块'列，可为模块名称或路径"
      },
      "feature": {
        "strategy": "from_feature_name",
        "description": "功能，对应模板'功能'列，简短功能项"
      },
      "priority": {
        "strategy": "from_priority_rules",
        "default": "中",
        "description": "抽象优先级(高/中/低)，可由 level(P0–P3) 推导，用于统计/报表/ES 精准筛选"
      },
      "level": {
        "strategy": "from_level_rules",
        "default": "P2",
        "allowed_values": ["P0", "P1", "P2", "P3"],
        "description": "用例等级，对应模板'用例等级'列"
      },
      "status": {
        "strategy": "fixed",
        "value": "NA",
        "allowed_values": ["OK", "NOK", "BLOCK", "NA"],
        "description": "测试结果状态，对应模板'测试结果'列，生成阶段通常默认 NA"
      },
      "owner": {
        "strategy": "from_config_or_fixed",
        "default": "TBD",
        "description": "测试负责人，对应模板'测试负责人'列，可从配置中指定默认负责人"
      },
      "executor": {
        "strategy": "from_owner_or_fixed",
        "default": "agent",
        "description": "实际执行人，可与 owner 重合，主要用于审计与统计"
      },
      "steps": {
        "strategy": "llm_generate_list",
        "style": {
          "step_prefix": "数字序号",
          "language": "zh-CN",
          "granularity": "细粒度",
          "max_steps": 10
        },
        "store": {
          "mode": "path",
          "field": "steps_path",
          "description": "与 DB 中 steps_path 字段对齐，用于后续写入文件并记录路径"
        },
        "description": "操作步骤，对应模板'操作步骤'列，Agent 负责生成文本并由落地层写入路径"
      },
      "expected_result": {
        "strategy": "llm_generate_text",
        "style": {
          "language": "zh-CN",
          "focus": ["界面结果", "后端状态", "数据校验"],
          "max_length": 512
        },
        "store": {
          "mode": "path",
          "field": "expected_result_path",
          "description": "与 DB 中 expected_result_path 字段对齐"
        },
        "description": "预期结果，对应模板'预期结果'列"
      },
      "precondition": {
        "strategy": "llm_or_input",
        "description": "前置条件，对应模板'前置条件'列，可由用户提供或由 LLM 总结"
      },
      "source": {
        "strategy": "from_input_or_fixed",
        "default": "需求",
        "allowed_values": ["需求", "文档", "测试计划", "用例库", "问题单"],
        "description": "用例来源，对应模板'用例来源'列"
      },
      "environment": {
        "strategy": "from_config_or_fixed",
        "default": "台架",
        "allowed_values": ["台架", "实车", "台架+实车", "云环境", "本地"],
        "description": "测试环境，对应模板'测试环境'列"
      },
      "remark": {
        "strategy": "llm_or_input",
        "description": "备注，对应模板'备注'列，可记录截图/日志路径/缺陷编号等"
      },
      "scene_ids": {
        "strategy": "from_scene_rules",
        "multiple": true,
        "description": "场景 ID 列表，用于生成 case_scene / case_scene_mapping 及 ES scene_ids 字段"
      },
      "create_time": {
        "strategy": "now",
        "format": "YYYY-MM-DD HH:MM:SS"
      },
      "update_time": {
        "strategy": "now",
        "format": "YYYY-MM-DD HH:MM:SS"
      }
    },
    "llm_prompts": {
      "steps_prompt": "你是测试工程师，请基于以下信息，生成详细的测试步骤列表...",
      "expected_result_prompt": "你是测试工程师，请为给定的测试步骤生成清晰的预期结果..."
    }
  }
}
```

要点：
- `strategy` 枚举示例：
  - `auto_uuid_with_prefix` / `from_pattern` / `fixed` / `from_module_mapping` / `from_priority_rules` / `from_scene_rules` / `llm_generate_list` / `llm_generate_text`；
- `llm_prompts` 可以是模板，由 Agent 根据具体 feature/flow/dimension 动态填充。

---

## 六、`priority_rules`：优先级分配规则

让用例生成时自动给出 `高/中/低`：

```json
{
  "priority_rules": [
    {
      "name": "核心登录成功高优先级",
      "conditions": {
        "module_id_in": ["login"],
        "dimension_id_in": ["happy_path"],
        "flow_type_in": ["happy"]
      },
      "priority": "高"
    },
    {
      "name": "安全相关高优先级",
      "conditions": {
        "dimension_id_in": ["security_bruteforce"]
      },
      "priority": "高"
    },
    {
      "name": "异常和边界中优先级",
      "conditions": {
        "flow_type_in": ["exception", "boundary"]
      },
      "priority": "中"
    },
    {
      "name": "其他低优先级",
      "conditions": {
        "otherwise": true
      },
      "priority": "低"
    }
  ]
}
```

要点：
- 条件字段可包括：`module_id_in`、`module_name_contains`、`dimension_id_in`、`flow_type_in`、`feature_name_contains` 等；
- 从上到下匹配，命中第一个即确定优先级。

---

## 七、`relation_rules`：用例间关系生成

可选，用于自动生成 `case_relation` 数据（依赖/关联/阻塞/衍生）：

```json
{
  "relation_rules": [
    {
      "name": "同一Feature的正常流和异常流互相关联",
      "relation_type": "关联",
      "source_selector": {
        "dimension_id_in": ["happy_path"]
      },
      "target_selector": {
        "dimension_id_in": ["invalid_credential", "boundary_input_length"]
      },
      "remark_pattern": "{source_title} 与 {target_title} 属于同一登录场景的正常与异常配套用例"
    },
    {
      "name": "安全用例依赖于正常登录",
      "relation_type": "依赖",
      "source_selector": {
        "dimension_id_in": ["security_bruteforce"]
      },
      "target_selector": {
        "dimension_id_in": ["happy_path"]
      },
      "remark_pattern": "安全用例 {source_title} 依赖于基础登录用例 {target_title}"
    }
  ]
}
```

要点：
- 生成逻辑：
  - 在生成完所有用例后，对用例集合执行规则扫描；
  - `source_selector` 与 `target_selector` 针对用例的元信息（module/dimension/flow_type 等）过滤；
  - 对匹配对生成 `case_relation` 记录。

---

## 八、`scene_rules`：场景与用例映射

用于自动生成 `case_scene` 和 `case_scene_mapping`：

```json
{
  "scene_rules": [
    {
      "scene_id": "scene_login_happy",
      "scene_name": "登录成功场景",
      "scene_desc": "覆盖所有用户成功登录的正常路径，包括账号密码登录、手机号登录等。",
      "applies_to": {
        "module_id_in": ["login"],
        "dimension_id_in": ["happy_path"]
      }
    },
    {
      "scene_id": "scene_login_failure",
      "scene_name": "登录失败场景",
      "scene_desc": "覆盖各种登录失败的路径，包括账号未注册、密码错误、账号被锁定等。",
      "applies_to": {
        "module_id_in": ["login"],
        "dimension_id_in": ["invalid_credential"]
      }
    }
  ],
  "default_scene_strategy": "none"
}
```

要点：
- 对每个用例，根据元信息匹配 `applies_to`，将其加入对应 `scene_id`；
- `scene_desc` 字段后续可映射到 `case_scene.scene_desc_path` 或 ES 文本字段。

---

## 九、`output_format`：输出控制（Markdown / JSONL）

指定最终输出的格式与文件结构，方便生产脚本统一处理。JSONL 输出采用“按实体多文件、扁平记录”的约定，文件名中的 `{project_name}` 默认来自 PRD 名称或调用参数中的项目名标识：

```json
{
  "output_format": {
    "jsonl": {
      "enabled": true,
      "record_structure": "flat", 
      "project_name_source": "from_prd_name_or_cli", 
      "files": {
        "testcases": "{project_name}_testcases.jsonl",
        "relations": "{project_name}_relations.jsonl",
        "scenes": "{project_name}_scenes.jsonl",
        "scene_mappings": "{project_name}_scene_mappings.jsonl"
      },
      "include_relations": true,
      "include_scenes": true
    },
    "markdown": {
      "enabled": true,
      "file_pattern": "{project_name}_testcases.md",
      "sections": [
        {
          "id": "overview",
          "title": "用例总览",
          "content_type": "summary"
        },
        {
          "id": "by_module",
          "title": "按模块划分的用例列表",
          "content_type": "table_by_module",
          "columns": [
            "case_id", "title", "module_name", "priority", "scene_names"
          ]
        },
        {
          "id": "detail",
          "title": "用例详情",
          "content_type": "detail_per_case",
          "include_fields": [
            "case_id", "title", "module_name", "priority", "steps", "expected_result"
          ]
        }
      ]
    }
  }
}
```

要点：
- `record_structure`：
  - `flat`：每个 JSONL 记录仅为 `test_case`；`relations`、`scenes` 单独文件/表；
  - `with_links`：在每条用例内嵌 `scene_ids`、`related_case_ids` 等。

---

## 十、完整 Walkthrough Rule 示例（精简版）

> 以下为一个“登录功能”场景的精简完整示例，实际可存为 `walkthrough_rule_login_v1.json`：

```json
{
  "rule_id": "login_v1",
  "name": "登录功能用例生成规则",
  "version": "1.0.0",
  "description": "适用于标准 Web 登录功能的用例生成。",
  "metadata": {
    "created_by": "agent",
    "create_time": "2025-12-30 10:00:00",
    "domain": "web_app_login",
    "language": "zh-CN"
  },
  "input_spec": {
    "expected_input_types": ["prd_markdown", "table_markdown"],
    "parsed_requirement_schema": {
      "modules": "list[Module]",
      "Module": {"id": "str", "name": "str", "features": "list[Feature]"},
      "Feature": {"id": "str", "name": "str", "description": "str", "flows": "list[Flow]"},
      "Flow": {"id": "str", "name": "str", "type": "['happy','exception','boundary']", "steps": "list[str]"}
    }
  },
  "module_mapping": {
    "default_module_id": "common",
    "default_module_name": "通用模块",
    "rules": [
      {"match_type": "keyword_in_name", "keywords": ["登录", "login"], "module_id": "login", "module_name": "用户登录模块"}
    ],
    "fallback_strategy": "default_module"
  },
  "scenario_dimensions": [
    {"dimension_id": "happy_path", "name": "正常流", "applies_to_flow_types": ["happy"], "case_title_pattern": "{feature_name}-{flow_name}-正常", "required": true},
    {"dimension_id": "invalid_credential", "name": "账号/密码错误", "applies_to_flow_types": ["happy", "exception"], "case_title_pattern": "{feature_name}-{flow_name}-错误凭证"}
  ],
  "testcase_template": {
    "fields": {
      "case_id": {"strategy": "auto_uuid_with_prefix", "prefix": "case_"},
      "title": {"strategy": "from_pattern", "pattern": "{feature_name}-{flow_name}-{dimension_name}", "max_length": 256},
      "project_name": {"strategy": "from_context_or_case_id"},
      "module": {"strategy": "from_module_mapping"},
      "feature": {"strategy": "from_feature_name"},
      "level": {"strategy": "from_level_rules", "default": "P2"},
      "priority": {"strategy": "from_priority_rules", "default": "中"},
      "status": {"strategy": "fixed", "value": "NA"},
      "owner": {"strategy": "from_config_or_fixed", "default": "TBD"},
      "executor": {"strategy": "from_owner_or_fixed", "default": "agent"},
      "steps": {"strategy": "llm_generate_list"},
      "expected_result": {"strategy": "llm_generate_text"},
      "scene_ids": {"strategy": "from_scene_rules", "multiple": true},
      "create_time": {"strategy": "now"},
      "update_time": {"strategy": "now"}
    }
  },
  "priority_rules": [
    {"name": "核心登录成功高优先级", "conditions": {"module_id_in": ["login"], "dimension_id_in": ["happy_path"]}, "priority": "高"},
    {"name": "其他中优先级", "conditions": {"otherwise": true}, "priority": "中"}
  ],
  "relation_rules": [
    {"name": "正常流与错误凭证关联", "relation_type": "关联", "source_selector": {"dimension_id_in": ["happy_path"]}, "target_selector": {"dimension_id_in": ["invalid_credential"]}, "remark_pattern": "{source_title} 与 {target_title} 为同一登录场景的正常和错误凭证用例"}
  ],
  "scene_rules": [
    {"scene_id": "scene_login_happy", "scene_name": "登录成功场景", "scene_desc": "覆盖所有用户成功登录的路径。", "applies_to": {"module_id_in": ["login"], "dimension_id_in": ["happy_path"]}},
    {"scene_id": "scene_login_failure", "scene_name": "登录失败场景", "scene_desc": "覆盖所有登录失败路径。", "applies_to": {"module_id_in": ["login"], "dimension_id_in": ["invalid_credential"]}}
  ],
  "output_format": {
    "jsonl": {"enabled": true, "file_pattern": "{project_name}_testcases.jsonl", "record_structure": "flat", "include_relations": true, "include_scenes": true},
    "markdown": {"enabled": true, "file_pattern": "{project_name}_testcases.md"}
  }
}
```

---

## 十一、给 Agent 的使用建议

- **规则生成 Agent** 输出的就是上述结构（或子集），存为 JSON；
- **用例生成 Agent** 的输入包括：
  - `parsed_requirements`（modules/features/flows），
  - `walkthrough_rule`（本规范 JSON），
  - 以及用户提供的拆解原则文本；
- 用例生成逻辑严格遵循：
  - 先根据 `module_mapping` 和 `scenario_dimensions` 确定“要生成哪些用例”；
  - 再根据 `testcase_template` + LLM prompt 填充每个字段；
  - 最后根据 `priority_rules` / `scene_rules` / `relation_rules` 补完元数据。
