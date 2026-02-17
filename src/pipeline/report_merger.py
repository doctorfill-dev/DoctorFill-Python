"""
Report Merger - Extract and merge text from PDF and TXT reports.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import List, Union

import fitz  # PyMuPDF

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def merge_reports(files: List[Union[str, Path]]) -> str:
    """
    Merge text from multiple report files (PDF or TXT).

    Args:
        files: List of file paths (PDF or TXT)

    Returns:
        Combined text from all files

    Raises:
        ValueError: If no files provided or unsupported format
    """
    if not files:
        raise ValueError("No report files provided")

    texts = []
    for file_path in files:
        path = Path(file_path)
        text = _extract_text_from_file(path)
        cleaned = _clean_text(text)
        if cleaned:
            texts.append(cleaned)

    return "\n\n".join(texts)


def _extract_text_from_file(file_path: Path) -> str:
    """
    Extract text from a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is not supported
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    elif suffix == ".txt":
        return _extract_text_from_txt(file_path)
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
        )


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    with fitz.open(pdf_path) as doc:
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        return "\n\n".join(pages)


def _extract_text_from_txt(txt_path: Path) -> str:
    """Extract text from a TXT file."""
    # Try common encodings
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            return txt_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    # Fallback: read with errors ignored
    return txt_path.read_text(encoding="utf-8", errors="ignore")


def _clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)

    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()
