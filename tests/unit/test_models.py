"""Unit tests for model clients."""

import pytest
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.models.doubao_client import DoubaoClient
from src.models.g2m_client import G2MClient
from src.models.model_factory import ModelFactory, get_default_client
from src.models.base import ModelResponse


class TestDoubaoClient:
    """Test Doubao client."""

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ARK_API_KEY"):
                DoubaoClient()

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = DoubaoClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.default_model == "ep-20251230165319-6fwz7"

    def test_env_model_override(self):
        """Env ARK_MODEL_ID overrides default model name."""
        with patch.dict(os.environ, {"ARK_API_KEY": "test_key", "ARK_MODEL_ID": "ep-test"}, clear=True):
            client = DoubaoClient()
            assert client.default_model == "ep-test"

    def test_chat_completion_success(self):
        """Chat completion returns ModelResponse with usage when API succeeds."""
        with patch.dict(os.environ, {"ARK_API_KEY": "test_key"}):
            with patch("src.models.doubao_client.OpenAI") as mock_openai:
                mock_response = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                    usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
                )

                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                client = DoubaoClient()
                res = client.chat_completion(
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.1,
                    model="doubao-custom",
                )

                assert res.content == "ok"
                assert res.model == "doubao-custom"
                assert res.usage == {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
                mock_client.chat.completions.create.assert_called_once_with(
                    model="doubao-custom",
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.1,
                    stream=False,
                )


class TestG2MClient:
    """Test G2M client."""

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="G2M_API_KEY"):
                G2MClient()

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = G2MClient(api_key="test_key")
        assert client.api_key == "test_key"

    def test_messages_to_prompt(self):
        """Test converting messages to prompt."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        prompt = G2MClient._messages_to_prompt(messages)
        assert "System: You are helpful" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt


class TestModelFactory:
    """Test model factory."""

    def test_create_doubao_client(self):
        """Test creating Doubao client."""
        with patch.dict(os.environ, {"ARK_API_KEY": "test_key"}):
            client = ModelFactory.create_client(provider="doubao")
            assert isinstance(client, DoubaoClient)

    def test_create_g2m_client(self):
        """Test creating G2M client."""
        with patch.dict(os.environ, {"G2M_API_KEY": "test_key"}):
            client = ModelFactory.create_client(provider="g2m")
            assert isinstance(client, G2MClient)

    def test_auto_select_doubao(self):
        """Test auto-selecting Doubao when ARK_API_KEY is present."""
        with patch.dict(os.environ, {"ARK_API_KEY": "test_key"}):
            client = ModelFactory.create_client(provider="auto")
            assert isinstance(client, DoubaoClient)

    def test_auto_select_g2m(self):
        """Test auto-selecting G2M when only G2M_API_KEY is present."""
        with patch.dict(os.environ, {"G2M_API_KEY": "test_key"}, clear=True):
            client = ModelFactory.create_client(provider="auto")
            assert isinstance(client, G2MClient)

    def test_invalid_provider(self):
        """Test invalid provider raises error."""
        with pytest.raises(ValueError, match="Invalid provider"):
            ModelFactory.create_client(provider="invalid")
