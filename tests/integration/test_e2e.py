"""End-to-end integration test."""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.models.base import BaseModelClient, ModelResponse
from src.agents.requirement_parser import RequirementParser
from src.agents.rule_generator import RuleGenerator
from src.agents.testcase_generator import TestCaseGenerator


class MockModelClient(BaseModelClient):
    """Mock model client for testing."""

    def chat_completion(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        """Mock chat completion."""
        user_content = messages[-1]["content"]

        # Parse requirement request
        if "分析以下需求文档" in user_content or "PRD" in user_content:
            return ModelResponse(
                content='''```json
{
  "modules": [
    {
      "id": "face_recognition",
      "name": "人脸识别模块",
      "description": "识别车内乘员的人脸特征",
      "features": [
        {
          "id": "face_detect",
          "name": "人脸检测",
          "description": "检测车内乘员的人脸",
          "flows": [
            {
              "id": "happy_detect",
              "name": "正常检测流程",
              "type": "happy",
              "steps": ["启动摄像头", "扫描车内", "检测人脸", "返回结果"],
              "preconditions": ["摄像头正常"],
              "postconditions": ["返回人脸位置"]
            },
            {
              "id": "no_face",
              "name": "无人脸场景",
              "type": "exception",
              "steps": ["启动摄像头", "扫描车内", "未检测到人脸"],
              "preconditions": ["摄像头正常"],
              "postconditions": ["返回空结果"]
            }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "total_modules": 1,
    "total_features": 1
  }
}
```''',
                model="mock",
            )

        # Generate rule request
        elif "生成测试用例walkthrough规则" in user_content or "walkthrough_rule_spec" in user_content:
            return ModelResponse(
                content='''```json
{
  "rule_id": "face_recognition_v1",
  "name": "人脸识别用例生成规则",
  "version": "1.0.0",
  "description": "人脸识别功能的测试用例生成规则",
  "module_mapping": {
    "default_module_id": "face_recognition",
    "default_module_name": "人脸识别模块",
    "rules": []
  },
  "scenario_dimensions": [
    {
      "dimension_id": "happy_path",
      "name": "正常流",
      "applies_to_flow_types": ["happy"],
      "case_title_pattern": "{feature_name}-{flow_name}-正常"
    },
    {
      "dimension_id": "exception",
      "name": "异常场景",
      "applies_to_flow_types": ["exception"],
      "case_title_pattern": "{feature_name}-{flow_name}-异常"
    }
  ],
  "priority_rules": [
    {
      "name": "正常流高优先级",
      "conditions": {"dimension_id_in": ["happy_path"]},
      "priority": "高",
      "level": "P0"
    }
  ]
}
```''',
                model="mock",
            )

        # Generate steps request
        elif "测试步骤" in user_content:
            return ModelResponse(
                content='["打开系统", "执行操作", "验证结果"]',
                model="mock",
            )

        # Generate expected result request
        elif "预期结果" in user_content:
            return ModelResponse(
                content="系统正常执行，返回预期结果",
                model="mock",
            )

        else:
            return ModelResponse(
                content="Mock response",
                model="mock",
            )

    def multimodal_completion(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        """Mock multimodal completion."""
        return ModelResponse(
            content="Mock multimodal response",
            model="mock",
        )


class TestEndToEnd:
    """End-to-end integration test."""

    def test_full_pipeline(self):
        """Test the full pipeline from PRD to test cases."""
        # Create mock client
        client = MockModelClient()

        # Sample PRD content
        prd_content = """
# 人脸识别功能需求

## 功能描述
系统需要能够识别车内乘员的人脸特征。

## 业务流程
1. 启动摄像头
2. 扫描车内环境
3. 检测人脸
4. 返回识别结果
"""

        # Step 1: Parse requirements
        parser = RequirementParser(client)
        parsed_req = parser.parse(
            prd_content=prd_content,
            project_name="test_project",
        )

        assert parsed_req.project_name == "test_project"
        assert len(parsed_req.modules) > 0
        assert parsed_req.modules[0].name == "人脸识别模块"

        # Step 2: Generate rule
        rule_gen = RuleGenerator(client)
        rule = rule_gen.generate_rule(parsed_req)

        assert "rule_id" in rule
        assert "scenario_dimensions" in rule
        assert len(rule["scenario_dimensions"]) > 0

        # Step 3: Generate test cases
        case_gen = TestCaseGenerator(client)
        result = case_gen.generate_testcases(
            parsed_requirement=parsed_req,
            walkthrough_rule=rule,
        )

        testcases = result["testcases"]
        assert len(testcases) > 0

        # Verify testcase structure
        tc = testcases[0]
        assert "case_id" in tc
        assert "title" in tc
        assert "module" in tc
        assert "priority" in tc
        assert "level" in tc
        assert "steps" in tc
        assert "expected_result" in tc

        # Verify priority assignment
        assert tc["priority"] in ["高", "中", "低"]
        assert tc["level"] in ["P0", "P1", "P2", "P3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
