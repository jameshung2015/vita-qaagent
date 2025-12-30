"""Doubao (Volcengine Ark) model client using OpenAI-compatible SDK."""

import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import requests.exceptions

from .base import BaseModelClient, ModelResponse
from ..utils.exceptions import ModelAPIError, ModelTimeoutError
from ..utils.error_handler import safe_model_call

logger = logging.getLogger(__name__)


class DoubaoClient(BaseModelClient):
    """Client for Doubao models via Volcengine Ark API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        default_model: str = None,
    ):
        """
        Initialize Doubao client.

        Args:
            api_key: ARK API key (defaults to ARK_API_KEY env var)
            base_url: Ark API base URL
            default_model: Default model to use
        """
        self.api_key = api_key or os.getenv("ARK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ARK_API_KEY not found. Set it in environment or pass to constructor."
            )

        self.base_url = base_url
        # Prefer explicit arg, then env, then a project-safe default endpoint
        self.default_model = default_model or os.getenv("ARK_MODEL_ID") or "ep-20251230165319-6fwz7"

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        logger.info(
            "Initialized DoubaoClient with base_url=%s, model=%s",
            base_url,
            self.default_model,
        )

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
        Generate chat completion using Doubao text model.

        Args:
            messages: List of chat messages with 'role' and 'content'
            model: Model name (uses default if not provided)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to use streaming (not yet supported in this wrapper)
            **kwargs: Additional parameters for the API

        Returns:
            ModelResponse with generated content
        """
        model = model or self.default_model

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        # Add any additional kwargs
        params.update(kwargs)

        logger.debug(f"Calling Doubao chat completion with model={model}")

        def _call():
            try:
                response = self.client.chat.completions.create(**params)

                if not response.choices:
                    raise ModelAPIError("No response choices returned from model")

                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None

                return ModelResponse(
                    content=content,
                    model=model,
                    usage=usage
                )

            except TimeoutError as e:
                raise ModelTimeoutError(f"Request timeout: {e}")
            except requests.exceptions.Timeout as e:
                raise ModelTimeoutError(f"Request timeout: {e}")
            except requests.exceptions.RequestException as e:
                raise ModelAPIError(f"API request failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in Doubao call: {e}")
                raise ModelAPIError(f"Model call failed: {str(e)}")

        return safe_model_call(_call, max_retries=3, retry_delay=2.0)

    def multimodal_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate multimodal completion (text + images) using Doubao.

        Args:
            messages: List of messages with content arrays containing text and image_url types
            model: Model name (uses default if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse with generated content

        Example message format:
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
                    {"type": "text", "text": "Describe this image"}
                ]
            }
        """
        model = model or self.default_model

        try:
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            params.update(kwargs)

            logger.debug(f"Calling Doubao multimodal completion with model={model}")

            response = self.client.chat.completions.create(**params)

            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None

            return ModelResponse(
                content=content,
                model=model,
                usage=usage
            )

        except Exception as e:
            logger.error(f"Error calling Doubao multimodal completion: {e}")
            raise
