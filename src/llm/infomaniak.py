"""
Infomaniak LLM Provider.

Uses Infomaniak AI API for chat, embeddings, and reranking.
"""

from __future__ import annotations

import os

import requests
import numpy as np
from typing import Any, Dict, List

from .provider import BaseLLMProvider
from ..config.settings import (
    IFK_LLM_MODEL,
    IFK_EMBEDDING_MODEL,
    IFK_RERANKER_MODEL,
    LLM_TIMEOUT,
)
from ..config import user_config


class InfomaniakProvider(BaseLLMProvider):
    """Infomaniak AI API provider."""

    def __init__(self):
        # Read credentials from user_config (fresh read) with env fallback
        cfg = user_config.load()
        self.product_id = cfg.get("ifk_product_id", "") or os.getenv("IFK_PRODUCT_ID", "")
        self.token = cfg.get("ifk_api_token", "") or os.getenv("IFK_API_TOKEN", "")
        self.llm_model = IFK_LLM_MODEL
        self.embedding_model = IFK_EMBEDDING_MODEL
        self.reranker_model = IFK_RERANKER_MODEL
        self.timeout = LLM_TIMEOUT

        if not self.product_id or not self.token:
            raise ValueError(
                "Infomaniak credentials not set. "
                "Please configure them via the setup screen."
            )

    @property
    def base_url(self) -> str:
        return f"https://api.infomaniak.com/2/ai/{self.product_id}/openai/v1"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

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

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=self.timeout
        )
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

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()

        result = response.json()
        return [item["embedding"] for item in result["data"]]

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank documents by relevance."""
        url = f"{self.base_url}/rerank"

        payload = {
            "model": self.reranker_model,
            "query": query,
            "documents": documents,
            "top_n": top_k
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            if "results" in result:
                return [
                    {
                        "index": r.get("index", i),
                        "document": documents[r.get("index", i)],
                        "score": r.get("relevance_score", r.get("score", 0))
                    }
                    for i, r in enumerate(result["results"][:top_k])
                ]
            elif "data" in result:
                return [
                    {
                        "index": r.get("index", i),
                        "document": documents[r.get("index", i)],
                        "score": r.get("score", 0)
                    }
                    for i, r in enumerate(result["data"][:top_k])
                ]
            else:
                return [
                    {"index": i, "document": doc, "score": 1.0}
                    for i, doc in enumerate(documents[:top_k])
                ]

        except requests.exceptions.HTTPError:
            # Fallback to embedding similarity
            return self._rerank_by_embedding(query, documents, top_k)

    def _rerank_by_embedding(
        self,
        query: str,
        documents: List[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback reranking using embedding similarity."""
        all_texts = [query] + documents
        embeddings = self.embed_texts(all_texts)

        query_emb = np.array(embeddings[0])
        doc_embs = np.array(embeddings[1:])

        # Cosine similarity
        query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        doc_norms = doc_embs / (np.linalg.norm(doc_embs, axis=1, keepdims=True) + 1e-8)
        scores = np.dot(doc_norms, query_norm)

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
        """Test connection to Infomaniak."""
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
