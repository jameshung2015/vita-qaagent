"""Model factory for creating model clients."""

import os
import logging
from typing import Optional, Literal

from .base import BaseModelClient
from .doubao_client import DoubaoClient
from .g2m_client import G2MClient

logger = logging.getLogger(__name__)

ModelProvider = Literal["doubao", "g2m", "auto"]


class ModelFactory:
    """Factory for creating model clients."""

    @staticmethod
    def create_client(
        provider: ModelProvider = "auto",
        **kwargs
    ) -> BaseModelClient:
        """
        Create a model client based on provider.

        Args:
            provider: Model provider ("doubao", "g2m", or "auto")
                     "auto" will try Doubao first, then fall back to G2M
            **kwargs: Additional arguments to pass to client constructor

        Returns:
            BaseModelClient instance

        Raises:
            ValueError: If provider is invalid or no API keys are available
        """
        if provider == "auto":
            # Try Doubao first
            if os.getenv("ARK_API_KEY"):
                logger.info("Auto-selecting Doubao (ARK_API_KEY found)")
                return DoubaoClient(**kwargs)
            elif os.getenv("G2M_API_KEY"):
                logger.info("Auto-selecting G2M (G2M_API_KEY found)")
                return G2MClient(**kwargs)
            else:
                raise ValueError(
                    "No API keys found. Set ARK_API_KEY or G2M_API_KEY in environment."
                )

        elif provider == "doubao":
            logger.info("Creating Doubao client")
            return DoubaoClient(**kwargs)

        elif provider == "g2m":
            logger.info("Creating G2M client")
            return G2MClient(**kwargs)

        else:
            raise ValueError(f"Invalid provider: {provider}. Use 'doubao', 'g2m', or 'auto'.")


def get_default_client(**kwargs) -> BaseModelClient:
    """
    Get default model client (Doubao preferred, with G2M fallback).

    Args:
        **kwargs: Additional arguments to pass to client constructor

    Returns:
        BaseModelClient instance
    """
    return ModelFactory.create_client(provider="auto", **kwargs)
