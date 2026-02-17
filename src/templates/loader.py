"""
Template Loader - Load manual templates from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_manual_template(template_json: Path) -> Optional[Dict[str, Any]]:
    """
    Load a manual template from JSON file.

    Args:
        template_json: Path to template JSON file

    Returns:
        Template dict or None if not found
    """
    if not template_json.exists():
        return None

    try:
        data = json.loads(template_json.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, IOError):
        return None


def extract_questions_from_template(template: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract questions from a loaded template.

    Args:
        template: Loaded template dict

    Returns:
        List of {"id": ..., "question": ...} dicts
    """
    questions = []

    fields = template.get("fields", [])
    for field in fields:
        if "id" not in field:
            continue

        question = field.get("question") or field.get("q")
        if not question:
            continue

        questions.append({
            "id": field["id"],
            "question": question,
            "type": field.get("type", field.get("t", "text"))
        })

    return questions


def extract_xfa_mappings(template: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract ID to XFA path mappings from template.

    Args:
        template: Loaded template dict

    Returns:
        Dict of field_id -> xfa_path
    """
    mappings = {}

    fields = template.get("fields", [])
    for field in fields:
        field_id = field.get("id")
        xfa_path = field.get("xml_path") or field.get("xfa_path")

        if field_id and xfa_path:
            mappings[field_id] = xfa_path

    return mappings
