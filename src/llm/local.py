"""
Local LLM Provider (LM Studio).

Uses local LM Studio server for chat and embeddings.
"""

from __future__ import annotations

import os

import requests
from typing import Any, Dict, List

from .provider import BaseLLMProvider
from ..config.settings import (
    LMSTUDIO_MODEL,
    LMSTUDIO_EMBEDDING_MODEL,
    LLM_TIMEOUT,
)
from ..config import user_config


class LocalProvider(BaseLLMProvider):
    """LM Studio local provider."""

    def __init__(self):
        cfg = user_config.load()
        self.base_url = cfg.get("lmstudio_base_url", "") or os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self.llm_model = LMSTUDIO_MODEL
        self.embedding_model = LMSTUDIO_EMBEDDING_MODEL
        self.timeout = LLM_TIMEOUT
        self._reranker = None

    def _get_reranker(self):
        """Lazy load local reranker."""
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except ImportError:
                pass
        return self._reranker

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Generate a chat completion."""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings."""
        url = f"{self.base_url}/embeddings"

        payload = {
            "model": self.embedding_model,
            "input": texts
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        return [item["embedding"] for item in result["data"]]

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank using local cross-encoder."""
        reranker = self._get_reranker()

        if reranker is None:
            # Fallback: return documents in original order
            return [
                {"index": i, "document": doc, "score": 1.0 - (i * 0.1)}
                for i, doc in enumerate(documents[:top_k])
            ]

        pairs = [(query, doc) for doc in documents]
        scores = reranker.predict(pairs)

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "index": idx,
                "document": documents[idx],
                "score": float(score)
            }
            for idx, score in indexed_scores[:top_k]
        ]

    def test_connection(self) -> bool:
        """Test connection to LM Studio."""
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
