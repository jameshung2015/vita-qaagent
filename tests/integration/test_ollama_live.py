"""Live network smoke test for Ollama chat completion.

Skips when OLLAMA_HOST or OLLAMA_MODEL is not set to avoid accidental network calls.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure project root is importable as package 'src' when running tests
import sys
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.models.ollama_client import OllamaClient


# Auto-load config/.env so CI and local runs pick up credentials without manual export
load_dotenv(ROOT_DIR / "config" / ".env")


@pytest.mark.live
def test_ollama_chat_completion_live():
    host = os.getenv("OLLAMA_HOST")
    model = os.getenv("OLLAMA_MODEL")
    if not host or not model:
        pytest.skip("OLLAMA_HOST or OLLAMA_MODEL not set; skipping live Ollama call")

    client = OllamaClient()
    res = client.chat_completion(
        messages=[{"role": "user", "content": "用一句话回答：现在是 Ollama 集成测试。"}],
        temperature=0.0,
        max_tokens=32,
    )

    assert res.content
    assert isinstance(res.content, str)
    assert res.model == model
