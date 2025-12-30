"""Walkthrough rule generation agent."""

import logging
import json
from typing import Dict, Any, Optional

from ..models.base import BaseModelClient
from .requirement_parser import ParsedRequirement

logger = logging.getLogger(__name__)


class RuleGenerator:
    """Agent for generating walkthrough rules from requirements."""

    def __init__(self, model_client: BaseModelClient):
        """
        Initialize rule generator.

        Args:
            model_client: Model client for LLM calls
        """
        self.model_client = model_client

    def generate_rule(
        self,
        parsed_requirement: ParsedRequirement,
        decomposition_principles: Optional[str] = None,
        metric_definitions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate walkthrough rule from parsed requirements.

        Args:
            parsed_requirement: Parsed requirement structure
            decomposition_principles: Test case decomposition principles
            metric_definitions: Metric definitions for module classification

        Returns:
            Walkthrough rule as dictionary
        """
        logger.info("Generating walkthrough rule...")

        # Build prompt
        prompt = self._build_rule_prompt(
            parsed_requirement,
            decomposition_principles,
            metric_definitions
        )

        messages = [
            {
                "role": "system",
                "content": "你是一个测试架构师，擅长设计测试用例生成规则。请根据需求和原则，生成结构化的测试用例walkthrough规则。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Call LLM
        response = self.model_client.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=6000,
        )

        # Parse response
        try:
            rule = self._extract_json_from_response(response.content)

            # Validate and enhance rule
            rule = self._enhance_rule(rule, parsed_requirement)

            logger.info("Successfully generated walkthrough rule")
            return rule

        except Exception as e:
            logger.error(f"Error generating rule: {e}")
            logger.error(f"Response content: {response.content}")
            raise

    def _build_rule_prompt(
        self,
        parsed_requirement: ParsedRequirement,
        decomposition_principles: Optional[str],
        metric_definitions: Optional[str]
    ) -> str:
        """Build prompt for rule generation."""
        # Convert parsed requirement to string
        modules_summary = []
        for module in parsed_requirement.modules:
            features_summary = [f.name for f in module.features]
            modules_summary.append(f"- {module.name}: {', '.join(features_summary)}")

        req_summary = "\n".join(modules_summary)

        prompt = f"""请为以下项目生成测试用例walkthrough规则。

## 项目名称：
{parsed_requirement.project_name}

## 模块和功能概览：
{req_summary}

"""

        if decomposition_principles:
            prompt += f"""## 用例拆解原则：
{decomposition_principles}

"""

        if metric_definitions:
            prompt += f"""## 模块分类规则(Metric)：
{metric_definitions}

"""

        prompt += """## 输出要求：
请生成符合walkthrough_rule_spec规范的JSON结构，包含：

1. **rule_id**: 规则唯一标识
2. **name**: 规则名称
3. **version**: 版本号 (如 "1.0.0")
4. **description**: 规则描述
5. **module_mapping**: 模块映射规则，定义如何从需求中识别模块
6. **scenario_dimensions**: 场景维度列表，定义需要生成哪些类型的用例
   - happy_path: 正常流
   - invalid_input: 无效输入
   - boundary: 边界值
   - exception: 异常处理
   - security: 安全相关
   等
7. **testcase_template**: 用例字段模板，定义每个字段如何生成
8. **priority_rules**: 优先级分配规则
9. **relation_rules**: 用例关系规则(可选)
10. **scene_rules**: 场景规则
11. **output_format**: 输出格式配置

请确保生成的规则：
- 覆盖所有识别到的模块和功能
- 定义清晰的场景维度，涵盖正常、异常、边界等情况
- 优先级规则合理，核心功能为高优先级
- 字段模板完整，与数据库字段对齐

输出纯JSON格式，不要包含其他说明文字。
"""

        return prompt

    def _enhance_rule(
        self,
        rule: Dict[str, Any],
        parsed_requirement: ParsedRequirement
    ) -> Dict[str, Any]:
        """Enhance and validate generated rule."""
        # Ensure required fields exist
        if "rule_id" not in rule:
            rule["rule_id"] = f"{parsed_requirement.project_name}_v1"

        if "version" not in rule:
            rule["version"] = "1.0.0"

        if "metadata" not in rule:
            rule["metadata"] = {
                "created_by": "agent",
                "project_name": parsed_requirement.project_name,
                "language": "zh-CN"
            }

        # Ensure scenario_dimensions exists
        if "scenario_dimensions" not in rule or not rule["scenario_dimensions"]:
            rule["scenario_dimensions"] = self._get_default_scenario_dimensions()

        # Ensure testcase_template exists
        if "testcase_template" not in rule:
            rule["testcase_template"] = self._get_default_testcase_template()

        # Ensure priority_rules exists
        if "priority_rules" not in rule:
            rule["priority_rules"] = self._get_default_priority_rules()

        return rule

    @staticmethod
    def _get_default_scenario_dimensions() -> list:
        """Get default scenario dimensions."""
        return [
            {
                "dimension_id": "happy_path",
                "name": "正常流",
                "applies_to_flow_types": ["happy"],
                "case_title_pattern": "{feature_name}-{flow_name}-正常",
                "required": True
            },
            {
                "dimension_id": "invalid_input",
                "name": "无效输入",
                "applies_to_flow_types": ["exception"],
                "case_title_pattern": "{feature_name}-{flow_name}-无效输入"
            },
            {
                "dimension_id": "boundary",
                "name": "边界值",
                "applies_to_flow_types": ["boundary"],
                "case_title_pattern": "{feature_name}-{flow_name}-边界"
            }
        ]

    @staticmethod
    def _get_default_testcase_template() -> dict:
        """Get default testcase template."""
        return {
            "fields": {
                "case_id": {"strategy": "auto_uuid_with_prefix", "prefix": "case_"},
                "title": {"strategy": "from_pattern", "pattern": "{feature_name}-{flow_name}-{dimension_name}"},
                "module": {"strategy": "from_module_mapping"},
                "feature": {"strategy": "from_feature_name"},
                "level": {"strategy": "from_level_rules", "default": "P2"},
                "priority": {"strategy": "from_priority_rules", "default": "中"},
                "status": {"strategy": "fixed", "value": "NA"},
                "steps": {"strategy": "llm_generate_list"},
                "expected_result": {"strategy": "llm_generate_text"},
                "create_time": {"strategy": "now"},
                "update_time": {"strategy": "now"}
            }
        }

    @staticmethod
    def _get_default_priority_rules() -> list:
        """Get default priority rules."""
        return [
            {
                "name": "核心正常流高优先级",
                "conditions": {"dimension_id_in": ["happy_path"]},
                "priority": "高",
                "level": "P0"
            },
            {
                "name": "异常和边界中优先级",
                "conditions": {"dimension_id_in": ["invalid_input", "boundary"]},
                "priority": "中",
                "level": "P1"
            },
            {
                "name": "其他低优先级",
                "conditions": {"otherwise": True},
                "priority": "低",
                "level": "P2"
            }
        ]

    @staticmethod
    def _extract_json_from_response(response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise
