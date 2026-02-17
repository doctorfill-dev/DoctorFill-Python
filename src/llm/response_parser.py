"""
Response Parser - Robust JSON extraction from LLM responses.

Handles various edge cases like markdown code blocks, trailing commas, etc.
"""

import re
import json
from typing import Any, Dict, List, Optional

# Try to import json_repair for better handling
try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response text.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Comments (//)
    - Trailing commas
    - Whitespace issues

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    if not text:
        return None

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Find JSON-like content
    text = text.strip()

    # Try to find object or array
    obj_match = re.search(r'\{[\s\S]*\}', text)
    arr_match = re.search(r'\[[\s\S]*\]', text)

    json_str = None
    if obj_match:
        json_str = obj_match.group()
    elif arr_match:
        json_str = arr_match.group()
    else:
        json_str = text

    # Clean up the JSON string
    json_str = _clean_json_string(json_str)

    # Try parsing
    return _parse_json(json_str)


def _clean_json_string(text: str) -> str:
    """Clean a JSON string for parsing."""
    # Remove single-line comments (// ...)
    text = re.sub(r'//[^\n]*', '', text)

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Normalize whitespace (but preserve escaped newlines in strings)
    # Only replace actual newlines outside of strings
    result = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if not in_string and char == '\n':
            result.append(' ')
        else:
            result.append(char)

    return ''.join(result).strip()


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON with multiple fallback strategies."""
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Use json_repair if available
    if HAS_JSON_REPAIR:
        try:
            return json_repair.loads(text)
        except Exception:
            pass

    # Strategy 3: Try fixing common issues manually
    try:
        # Replace single quotes with double quotes
        fixed = text.replace("'", '"')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Try to extract just the fields array
    try:
        match = re.search(r'"fields"\s*:\s*(\[[\s\S]*?\])', text)
        if match:
            fields = json.loads(match.group(1))
            return {"fields": fields}
    except Exception:
        pass

    return None


def parse_rag_response(text: str) -> List[Dict[str, Any]]:
    """
    Parse a RAG response containing field values.

    Expected format:
    {
        "fields": [
            {"id": "X.Y", "value": "...", "source_quote": "...", "confidence": 0.9},
            ...
        ]
    }

    Args:
        text: Raw LLM response

    Returns:
        List of field response dicts
    """
    data = extract_json(text)

    if data is None:
        return []

    # Handle different response formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "fields" in data:
            return data["fields"]
        elif "results" in data:
            return data["results"]
        else:
            # Single response - wrap in list
            return [data]

    return []


def validate_field_response(response: Dict[str, Any]) -> bool:
    """Check if a field response has required fields."""
    return (
        isinstance(response, dict) and
        "id" in response
    )
