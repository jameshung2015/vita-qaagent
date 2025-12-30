"""Test case generation agent."""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.base import BaseModelClient
from .requirement_parser import ParsedRequirement, Module, Feature, Flow
from ..utils.config_loader import get_config_loader

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """Agent for generating test cases from requirements and rules."""

    def __init__(self, model_client: BaseModelClient):
        """
        Initialize test case generator.

        Args:
            model_client: Model client for LLM calls
        """
        self.model_client = model_client
        self.config_loader = get_config_loader()

    def generate_testcases(
        self,
        parsed_requirement: ParsedRequirement,
        walkthrough_rule: Dict[str, Any],
        metric_content: Optional[str] = None,
        prd_content: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate test cases from requirements and rule.

        Args:
            parsed_requirement: Parsed requirement structure
            walkthrough_rule: Walkthrough rule

        Returns:
            Dictionary containing:
            - testcases: List of test case dicts
            - scenes: List of scene dicts
            - scene_mappings: List of scene-testcase mappings
            - relations: List of testcase relations
        """
        logger.info("Generating test cases...")

        testcases = []
        scenes = []
        scene_mappings = []
        relations = []

        # Extract scenario dimensions and template from rule
        raw_dimensions = walkthrough_rule.get("scenario_dimensions", [])
        scenario_dimensions = []
        for dim in raw_dimensions:
            if isinstance(dim, dict):
                name = dim.get("name") or dim.get("dimension") or dim.get("id") or str(dim)
                dim_id = dim.get("dimension_id") or dim.get("id") or dim.get("dimension") or name
                norm = {**dim}
                norm.setdefault("name", name)
                norm.setdefault("dimension_id", dim_id)
                scenario_dimensions.append(norm)
            else:
                scenario_dimensions.append({"name": str(dim), "dimension_id": str(dim)})
        testcase_template = walkthrough_rule.get("testcase_template", {})
        raw_scene_rules = walkthrough_rule.get("scene_rules", [])
        if isinstance(raw_scene_rules, dict):
            scene_rules = raw_scene_rules.get("rules", []) if isinstance(raw_scene_rules.get("rules", []), list) else []
        elif isinstance(raw_scene_rules, list):
            scene_rules = raw_scene_rules
        else:
            scene_rules = []
        module_mapping = walkthrough_rule.get("module_mapping", {})

        metric_ctx = self._trim_context(metric_content, limit=1200)
        prd_ctx = self._trim_context(prd_content, limit=1500)

        # Generate test cases for each module/feature/flow
        for module in parsed_requirement.modules:
            for feature in module.features:
                for flow in feature.flows:
                    # Generate cases for applicable scenario dimensions
                    for dimension in scenario_dimensions:
                        if self._is_dimension_applicable(flow, dimension):
                            case = self._generate_single_testcase(
                                module=module,
                                feature=feature,
                                flow=flow,
                                dimension=dimension,
                                template=testcase_template,
                                module_mapping=module_mapping,
                                project_name=parsed_requirement.project_name,
                                metric_context=metric_ctx,
                                prd_context=prd_ctx
                            )
                            testcases.append(case)

        # Generate scenes based on scene_rules
        if scene_rules:
            scenes = self._generate_scenes(scene_rules)

            # Map testcases to scenes
            scene_mappings = self._map_testcases_to_scenes(
                testcases, scenes, scene_rules
            )

        logger.info(f"Generated {len(testcases)} test cases, {len(scenes)} scenes")

        return {
            "testcases": testcases,
            "scenes": scenes,
            "scene_mappings": scene_mappings,
            "relations": relations,
        }

    def _is_dimension_applicable(
        self,
        flow: Flow,
        dimension: Dict[str, Any]
    ) -> bool:
        """Check if scenario dimension applies to flow."""
        applies_to = dimension.get("applies_to_flow_types", [])
        if not applies_to:
            return True
        return flow.type in applies_to

    def _generate_single_testcase(
        self,
        module: Module,
        feature: Feature,
        flow: Flow,
        dimension: Dict[str, Any],
        template: Dict[str, Any],
        module_mapping: Dict[str, Any],
        project_name: str,
        metric_context: Optional[str] = None,
        prd_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a single test case."""
        # Build basic case structure
        case = {}

        fields_conf = template.get("fields", {}) if isinstance(template, dict) else {}
        # Some rule generations return a descriptive list; fall back to defaults when not dict
        fields = fields_conf if isinstance(fields_conf, dict) else {}

        # Generate case_id
        case_id_config = fields.get("case_id", {})
        prefix = case_id_config.get("prefix", "case_")
        case["case_id"] = f"{prefix}{uuid.uuid4().hex[:12]}"

        # Generate title
        title_pattern = fields.get("title", {}).get("pattern", "{feature_name}-{flow_name}")
        case["title"] = self._apply_pattern(title_pattern, {
            "feature_name": feature.name,
            "flow_name": flow.name,
            "dimension_name": dimension.get("name", "")
        })

        # Set project_name
        case["project_name"] = project_name

        # Set module
        case["module"] = module.name

        # Set feature
        case["feature"] = feature.name

        # Determine level (P0-P3) only; default to template-provided value
        level_field = fields.get("level", {})
        level_val = level_field.get("default", "P2")
        if level_val not in {"P0", "P1", "P2", "P3"}:
            level_val = "P2"
        case["level"] = level_val

        # Set status
        case["status"] = fields.get("status", {}).get("value", "NA")

        # Set owner and executor
        case["owner"] = fields.get("owner", {}).get("default", "TBD")
        case["executor"] = fields.get("executor", {}).get("default", "agent")

        # Generate steps and expected_result using LLM
        steps_config = fields.get("steps", {})
        expected_config = fields.get("expected_result", {})
        if not expected_config.get("strategy"):
            expected_config = {**expected_config, "strategy": "llm_generate_text"}

        if steps_config.get("strategy") == "llm_generate_list":
            case["steps"] = self._generate_steps_with_llm(
                feature, flow, dimension
            )
        else:
            case["steps"] = flow.steps

        if expected_config.get("strategy") == "llm_generate_text":
            case["expected_result"] = self._generate_expected_result_with_llm(
                feature,
                flow,
                dimension,
                case["steps"],
                metric_context,
                prd_context
            )
        else:
            case["expected_result"] = "请根据步骤验证预期结果"

        # Set precondition
        case["precondition"] = "; ".join(flow.preconditions) if flow.preconditions else "无"

        # Set source and environment
        case["source"] = fields.get("source", {}).get("default", "需求")
        case["environment"] = fields.get("environment", {}).get("default", "台架")

        # Set remark
        case["remark"] = ""

        # Set timestamps
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        case["create_time"] = now
        case["update_time"] = now

        # Store metadata for later scene mapping
        case["_metadata"] = {
            "module_id": module.id,
            "feature_id": feature.id,
            "flow_id": flow.id,
            "flow_type": flow.type,
            "dimension_id": dimension.get("dimension_id", "")
        }

        return case

    def _apply_pattern(self, pattern: str, values: Dict[str, str]) -> str:
        """Apply pattern with values."""
        result = pattern
        for key, value in values.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    def _generate_steps_with_llm(
        self,
        feature: Feature,
        flow: Flow,
        dimension: Dict[str, Any]
    ) -> List[str]:
        """Generate test steps using LLM."""
        # If flow already has steps, use them
        if flow.steps:
            return flow.steps

        # Otherwise, generate with LLM
        prompt = f"""请为以下测试场景生成详细的测试步骤。

功能：{feature.name}
描述：{feature.description}

流程：{flow.name}
流程类型：{flow.type}

场景维度：{dimension.get('name')}

要求：
1. 生成清晰、可执行的测试步骤
2. 每个步骤要具体，包含操作对象和操作内容
3. 步骤数量控制在3-8步
4. 以JSON数组格式输出，例如：["步骤1", "步骤2", "步骤3"]

请直接输出JSON数组，不要包含其他说明。
"""

        try:
            response = self.model_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=800
            )

            # Extract JSON array
            content = response.content.strip()
            if "```" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                content = content[start:end]

            steps = json.loads(content)
            return steps if isinstance(steps, list) else [str(steps)]

        except Exception as e:
            logger.warning(f"Failed to generate steps with LLM: {e}")
            return [f"执行{feature.name}的{flow.name}操作"]

    def _generate_expected_result_with_llm(
        self,
        feature: Feature,
        flow: Flow,
        dimension: Dict[str, Any],
        steps: List[str],
        metric_context: Optional[str] = None,
        prd_context: Optional[str] = None
    ) -> str:
        """Generate expected result using LLM."""
        steps_formatted = chr(10).join(f"{i+1}. {step}" for i, step in enumerate(steps))
        prompt = self.config_loader.get_prompt(
            "testcase_generator",
            "expected_result_prompt_template",
            feature_name=feature.name,
            flow_name=flow.name,
            dimension_name=dimension.get("name"),
            steps_formatted=steps_formatted
        )

        extras = []
        if metric_context:
            extras.append(f"附加Metric参考：\n{metric_context}")
        if prd_context:
            extras.append(f"需求片段：\n{prd_context}")
        if extras:
            prompt = f"{prompt}\n\n" + "\n\n".join(extras)

        try:
            response = self.model_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )

            return response.content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate expected result with LLM: {e}")
            return f"{feature.name}功能正常执行，达到预期效果"

    @staticmethod
    def _trim_context(text: Optional[str], limit: int = 1200) -> Optional[str]:
        """Keep context within a safe length for prompts."""
        if not text:
            return None
        clean = text.strip()
        if len(clean) <= limit:
            return clean
        return clean[:limit] + "..."

    def _generate_scenes(
        self,
        scene_rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate scenes from scene rules."""
        scenes = []
        for rule in scene_rules:
            scene_id = rule.get("scene_id") or f"scene_{uuid.uuid4().hex[:8]}"
            # Ensure downstream mapping can reuse the generated id
            rule.setdefault("scene_id", scene_id)
            # Accept common keys from rule files: scene / scene_name / dimension
            scene_name = rule.get("scene_name") or rule.get("scene") or rule.get("dimension", "")
            # Prefer explicit scene_desc; otherwise derive from considerations/mapping_rule
            if rule.get("scene_desc"):
                scene_desc = rule.get("scene_desc")
            elif rule.get("considerations"):
                # Join considerations as a short bullet-like text
                scene_desc = "；".join(str(item) for item in rule.get("considerations") if item)
            else:
                scene_desc = rule.get("mapping_rule", "")
            scene = {
                "scene_id": scene_id,
                "scene_name": scene_name,
                "scene_desc": scene_desc,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            scenes.append(scene)
        return scenes

    def _map_testcases_to_scenes(
        self,
        testcases: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        scene_rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Map test cases to scenes based on rules."""
        mappings = []

        for case in testcases:
            metadata = case.get("_metadata", {})

            for scene_rule in scene_rules:
                applies_to = scene_rule.get("applies_to", {})

                # Check if testcase matches scene criteria
                matches = True

                if "module_id_in" in applies_to:
                    if metadata.get("module_id") not in applies_to["module_id_in"]:
                        matches = False

                if "dimension_id_in" in applies_to:
                    if metadata.get("dimension_id") not in applies_to["dimension_id_in"]:
                        matches = False

                if matches:
                    mapping = {
                        "mapping_id": f"mapping_{uuid.uuid4().hex[:12]}",
                        "scene_id": scene_rule.get("scene_id"),
                        "case_id": case["case_id"],
                        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    mappings.append(mapping)

        return mappings
