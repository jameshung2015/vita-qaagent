"""G2M model client using direct HTTP requests."""

import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional
import requests

from .base import BaseModelClient, ModelResponse

logger = logging.getLogger(__name__)


class G2MClient(BaseModelClient):
    """Client for G2M models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://llmproxy.gwm.cn",
        default_text_model: str = "default/qwen3-235b-a22b-instruct",
        default_vl_model: str = "default/qwen3-omni-30b-a3b-captioner",
    ):
        """
        Initialize G2M client.

        Args:
            api_key: G2M API key (defaults to G2M_API_KEY env var)
            base_url: G2M API base URL
            default_text_model: Default text model
            default_vl_model: Default vision-language model
        """
        self.api_key = api_key or os.getenv("G2M_API_KEY")
        if not self.api_key:
            raise ValueError(
                "G2M_API_KEY not found. Set it in environment or pass to constructor."
            )

        self.base_url = base_url
        self.default_text_model = default_text_model
        self.default_vl_model = default_vl_model

        logger.info(f"Initialized G2MClient with base_url={base_url}")

    def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make HTTP request to G2M API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"G2M API request failed: {e}")
            raise

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """
        Generate chat completion using G2M text model.

        Args:
            messages: List of chat messages
            model: Model name (uses default if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            stream: Whether to use streaming (not supported in this implementation)
            **kwargs: Additional parameters

        Returns:
            ModelResponse with generated content
        """
        model = model or self.default_text_model

        # G2M uses /v1/completions for text generation with prompt format
        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        try:
            logger.debug(f"Calling G2M chat completion with model={model}")
            response = self._make_request("/v1/completions", payload)

            # Extract content from response
            content = response.get("choices", [{}])[0].get("text", "")

            usage = response.get("usage")

            return ModelResponse(
                content=content,
                model=model,
                usage=usage
            )

        except Exception as e:
            logger.error(f"Error calling G2M chat completion: {e}")
            raise

    def multimodal_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate multimodal completion using G2M vision-language model.

        Args:
            messages: List of messages with text and image content
            model: Model name (uses default VL model if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse with generated content
        """
        model = model or self.default_vl_model

        # G2M uses /v1/chat/completions for multimodal
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        try:
            logger.debug(f"Calling G2M multimodal completion with model={model}")
            response = self._make_request("/v1/chat/completions", payload)

            # Extract content from streaming or non-streaming response
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            usage = response.get("usage")

            return ModelResponse(
                content=content,
                model=model,
                usage=usage
            )

        except Exception as e:
            logger.error(f"Error calling G2M multimodal completion: {e}")
            raise

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a single prompt string."""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        return "\n".join(prompt_parts)
