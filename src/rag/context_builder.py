"""
Context Builder - Assemble context within token budget.

Manages token counting and context window limits.
"""

from __future__ import annotations

from typing import List, Tuple

from ..config.settings import RAG_MAX_INPUT_TOKENS

# Try to import tiktoken
try:
    import tiktoken
    _encoding = tiktoken.get_encoding("cl100k_base")
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    _encoding = None


def count_tokens(text: str) -> int:
    """
    Count tokens in text.

    Uses tiktoken if available, otherwise approximates.
    """
    if HAS_TIKTOKEN and _encoding:
        return len(_encoding.encode(text))
    else:
        # Approximation: ~4 characters per token
        return len(text) // 4


def build_context(
    scored_docs: List[Tuple[str, float]],
    max_tokens: int = RAG_MAX_INPUT_TOKENS
) -> str:
    """
    Build context string within token limit.

    Args:
        scored_docs: List of (document, score) tuples, sorted by score desc
        max_tokens: Maximum tokens for context

    Returns:
        Combined context string
    """
    final_docs = []
    current_tokens = 0

    for doc, score in scored_docs:
        doc_tokens = count_tokens(doc)

        if current_tokens + doc_tokens < max_tokens:
            final_docs.append(doc)
            current_tokens += doc_tokens
        else:
            break

    return "\n---\n".join(final_docs)
