"""
Document Chunker - Split documents into overlapping chunks.

Uses intelligent boundary detection for clean splits.
"""

from __future__ import annotations

import re
from typing import List

from ..config.settings import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP


def chunk_documents(
    texts: List[str],
    chunk_size: int = RAG_CHUNK_SIZE,
    overlap: int = RAG_CHUNK_OVERLAP
) -> List[str]:
    """
    Split documents into overlapping chunks.

    Args:
        texts: List of document texts
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between consecutive chunks

    Returns:
        List of text chunks
    """
    # Combine all texts
    full_text = "\n".join(texts)

    # Clean excessive whitespace
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)

    chunks = []
    start = 0
    text_len = len(full_text)

    while start < text_len:
        end = start + chunk_size

        if end < text_len:
            # Find good break point
            end = _find_break_point(full_text, start, end)

        chunk = full_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap
        if start >= end:
            start = end

    return chunks


def _find_break_point(text: str, start: int, end: int) -> int:
    """
    Find a good break point near the end position.

    Prefers paragraph breaks, then sentence breaks.
    """
    # Search zone: last 100 characters before end
    search_start = max(start, end - 100)
    search_zone = text[search_start:end]

    # Try paragraph break (double newline)
    matches = list(re.finditer(r'\n\n', search_zone))
    if matches:
        return search_start + matches[-1].end()

    # Try sentence break
    matches = list(re.finditer(r'(?<=[.?!])\s', search_zone))
    if matches:
        return search_start + matches[-1].end()

    # No good break found, use original end
    return end
