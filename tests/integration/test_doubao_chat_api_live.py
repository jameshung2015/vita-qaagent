"""Live responses.create test using OpenAI-compatible SDK sample."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from openai import OpenAI, APIError

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "config" / ".env")


@pytest.mark.live
def test_doubao_responses_create_with_tools():
    api_key = os.getenv("ARK_API_KEY")
    # Force the requested model for this sample
    model_id = "ep-20251230165319-6fwz7"
    if not api_key:
        pytest.skip("ARK_API_KEY not set; skipping live responses call")

    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key,
    )

    tools = [{"type": "web_search", "max_keyword": 2}]

    try:
        resp = client.responses.create(
            model=model_id,
            input=[{"role": "user", "content": "北京的天气怎么样？"}],
            tools=tools,
        )
    except APIError as e:
        if getattr(e, "status_code", None) and e.status_code >= 500:
            pytest.xfail(f"Doubao responses service {e.status_code}: {e}")
        raise

    assert resp, "empty response"
