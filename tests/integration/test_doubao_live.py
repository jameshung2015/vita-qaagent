"""Live network smoke test for Doubao chat completion.

Skips when ARK_API_KEY or ARK_MODEL_ID is not set to avoid accidental network calls.
Loads config/.env automatically for convenience.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.models.doubao_client import DoubaoClient
from src.utils.exceptions import ModelAPIError


# Auto-load config/.env so CI and local runs pick up credentials without manual export
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "config" / ".env")


@pytest.mark.live
def test_doubao_chat_completion_live():
    api_key = os.getenv("ARK_API_KEY")
    model_id = os.getenv("ARK_MODEL_ID")
    if not api_key or not model_id:
        pytest.skip("ARK_API_KEY or ARK_MODEL_ID not set; skipping live Doubao call")

    client = DoubaoClient()
    try:
        res = client.chat_completion(
            messages=[{"role": "user", "content": "用一句话回答：现在是集成测试。"}],
            temperature=0.0,
            max_tokens=32,
        )
    except ModelAPIError as e:
        if "InternalServiceError" in str(e):
            pytest.xfail(f"Doubao service 500: {e}")
        raise

    assert res.content
    assert isinstance(res.content, str)
    # model_id should echo back the requested model
    assert res.model == model_id
