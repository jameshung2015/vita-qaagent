"""Requirement parsing agent."""

import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..models.base import BaseModelClient

logger = logging.getLogger(__name__)


class Module(BaseModel):
    """Module structure."""
    id: str
    name: str
    description: str = ""
    features: List["Feature"] = []


class Feature(BaseModel):
    """Feature structure."""
    id: str
    name: str
    description: str = ""
    flows: List["Flow"] = []


class Flow(BaseModel):
    """Flow structure."""
    id: str
    name: str
    type: str  # 'happy', 'exception', 'boundary', 'performance', 'security'
    steps: List[str] = []
    preconditions: List[str] = []
    postconditions: List[str] = []


class ParsedRequirement(BaseModel):
    """Parsed requirement structure."""
    project_name: str
    modules: List[Module] = []
    metadata: Dict[str, Any] = {}


class RequirementParser:
    """Agent for parsing PRD/requirements into structured format."""

    def __init__(self, model_client: BaseModelClient):
        """
        Initialize requirement parser.

        Args:
            model_client: Model client for LLM calls
        """
        self.model_client = model_client

    def parse(
        self,
        prd_content: str,
        metric_content: Optional[str] = None,
        project_name: str = "default_project",
    ) -> ParsedRequirement:
        """
        Parse PRD content into structured requirements.

        Args:
            prd_content: PRD markdown content
            metric_content: Optional metric/module classification content
            project_name: Project name

        Returns:
            ParsedRequirement object
        """
        logger.info(f"Parsing requirements for project: {project_name}")

        # Build prompt for LLM
        prompt = self._build_parse_prompt(prd_content, metric_content)

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的测试工程师，擅长分析需求文档并提取模块、功能和流程信息。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Call LLM
        response = self.model_client.chat_completion(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent parsing
            max_tokens=4000,
        )

        # Parse LLM response
        try:
            parsed_data = self._extract_json_from_response(response.content)

            # Build ParsedRequirement
            modules = []
            for mod_data in parsed_data.get("modules", []):
                features = []
                for feat_data in mod_data.get("features", []):
                    flows = []
                    for flow_data in feat_data.get("flows", []):
                        flows.append(Flow(**flow_data))
                    features.append(Feature(
                        id=feat_data.get("id", ""),
                        name=feat_data.get("name", ""),
                        description=feat_data.get("description", ""),
                        flows=flows
                    ))
                modules.append(Module(
                    id=mod_data.get("id", ""),
                    name=mod_data.get("name", ""),
                    description=mod_data.get("description", ""),
                    features=features
                ))

            result = ParsedRequirement(
                project_name=project_name,
                modules=modules,
                metadata=parsed_data.get("metadata", {})
            )

            logger.info(f"Successfully parsed {len(modules)} modules")
            return result

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(f"Response content: {response.content}")
            raise

    def _build_parse_prompt(
        self,
        prd_content: str,
        metric_content: Optional[str] = None
    ) -> str:
        """Build prompt for requirement parsing."""
        prompt = f"""请分析以下需求文档(PRD)，提取出结构化的模块、功能和流程信息。

## 需求文档内容：
{prd_content}

"""

        if metric_content:
            prompt += f"""## 模块分类参考：
{metric_content}

"""

        prompt += """## 输出要求：
仅输出一个JSON代码块，必须是严格合法的JSON（UTF-8，无额外文本/注释/反斜杠转义，字符串内不得换行，步骤数组中每个元素单行表述）。
请以JSON格式输出，包含以下结构：
```json
{
  "modules": [
    {
      "id": "模块ID (英文小写，使用下划线)",
      "name": "模块名称",
      "description": "模块描述",
      "features": [
        {
          "id": "功能ID",
          "name": "功能名称",
          "description": "功能描述",
          "flows": [
            {
              "id": "流程ID",
              "name": "流程名称",
              "type": "流程类型 (happy/exception/boundary/performance/security)",
              "steps": ["步骤1", "步骤2", ...],
              "preconditions": ["前置条件1", ...],
              "postconditions": ["后置条件1", ...]
            }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "total_modules": 模块总数,
    "total_features": 功能总数
  }
}
```
请仔细分析需求文档，提取所有模块和功能点。对于每个功能，识别其正常流程(happy)、异常流程(exception)、边界情况(boundary)等。确保输出可以直接被JSON解析，无多余字段、无多余文本。
"""

        return prompt

    @staticmethod
    def _extract_json_from_response(response: str) -> Dict[str, Any]:
        """Extract and repair JSON from LLM response (handle markdown code blocks)."""
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

        def _collapse_newlines_inside_strings(text: str) -> str:
            result_chars = []
            in_string = False
            escape = False
            for ch in text:
                if escape:
                    result_chars.append(ch)
                    escape = False
                    continue
                if ch == "\\":
                    result_chars.append(ch)
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    result_chars.append(ch)
                    continue
                if in_string and ch in ["\n", "\r"]:
                    result_chars.append(" ")
                    continue
                result_chars.append(ch)
            return "".join(result_chars)

        def _remove_trailing_commas(text: str) -> str:
            import re
            return re.sub(r",(\s*[}\]])", r"\1", text)

        repaired = _collapse_newlines_inside_strings(json_str)
        repaired = _remove_trailing_commas(repaired)

        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON after repair: {e}")
            logger.error(f"Original JSON string: {json_str}")
            logger.error(f"Repaired JSON string: {repaired}")
            raise
