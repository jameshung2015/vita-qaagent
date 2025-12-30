"""Base model client interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class Message(BaseModel):
    """Chat message."""
    role: str
    content: str


class ModelResponse(BaseModel):
    """Model response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class BaseModelClient(ABC):
    """Abstract base class for model clients."""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages
            model: Model name (optional, uses default if not provided)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            ModelResponse object
        """
        pass

    @abstractmethod
    def multimodal_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate multimodal completion (text + images).

        Args:
            messages: List of messages with text and image content
            model: Model name (optional)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse object
        """
        pass
