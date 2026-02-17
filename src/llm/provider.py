"""
LLM Provider - Abstract interface for LLM services.

Supports multiple backends: Infomaniak (default) and Local (LM Studio).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

class ProviderType(Enum):
    """Available LLM providers."""
    LOCAL = "local"
    INFOMANIAK = "infomaniak"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Generate a chat completion."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank documents by relevance to query."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the provider."""
        pass


def get_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """
    Get the appropriate LLM provider.

    Args:
        provider_type: Override the default provider type

    Returns:
        Configured LLM provider instance
    """
    if provider_type is None:
        from ..config import user_config
        cfg = user_config.load()
        provider_type = cfg.get("llm_provider", "") or os.getenv("LLM_PROVIDER", "infomaniak")
    provider = provider_type

    if provider == "local":
        from .local import LocalProvider
        return LocalProvider()
    elif provider == "infomaniak":
        from .infomaniak import InfomaniakProvider
        return InfomaniakProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}")
