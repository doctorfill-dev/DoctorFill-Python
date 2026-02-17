"""
Template Manager - Hybrid template system (manual + auto).

Prefers manual templates when available, falls back to auto-generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..config.settings import TEMPLATES_DIR, FORMS_DIR
from ..config.form_registry import (
    FormDescriptor,
    get_form_descriptor,
    get_form_by_name,
    available_forms,
)
from ..templates.loader import (
    load_manual_template,
    extract_questions_from_template,
    extract_xfa_mappings,
)


@dataclass
class FormTemplate:
    """Template for a form with questions and XFA mappings."""
    form_id: str
    form_name: str
    fields: List[Dict[str, Any]]
    id_to_xfa_map: Dict[str, str]
    questions: Dict[str, str]
    is_manual: bool = True

    def get_rag_questions(self) -> List[Dict[str, str]]:
        """Get questions formatted for RAG pipeline."""
        result = []
        for f in self.fields:
            if "id" in f and "question" in f:
                result.append({
                    "id": f["id"],
                    "question": f["question"]
                })
        return result

    def get_xfa_path(self, field_id: str) -> Optional[str]:
        """Get XFA path for a field ID."""
        return self.id_to_xfa_map.get(field_id)

    def get_field_type(self, field_id: str) -> str:
        """Get field type for a field ID."""
        for f in self.fields:
            if f.get("id") == field_id:
                return f.get("type", "text")
        return "text"


class TemplateManager:
    """
    Manages form templates with hybrid manual/auto approach.

    Priority:
    1. Manual template (if exists and valid)
    2. Auto-generated template (from PDF extraction)
    """

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        forms_dir: Optional[Path] = None
    ):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.forms_dir = forms_dir or FORMS_DIR
        self._cache: Dict[str, FormTemplate] = {}

    def get_template(self, form_id: str) -> FormTemplate:
        """
        Get template for a form.

        Args:
            form_id: Form UUID string or name

        Returns:
            FormTemplate instance

        Raises:
            ValueError: If form not found
        """
        # Check cache
        if form_id in self._cache:
            return self._cache[form_id]

        # Get descriptor
        descriptor = self.get_descriptor(form_id)

        # Try manual template first
        template = self._load_manual_template(descriptor)

        if template is None:
            # Fall back to auto-generation
            template = self._generate_template(descriptor)

        # Cache and return
        self._cache[form_id] = template
        return template

    def get_descriptor(self, form_id: str) -> FormDescriptor:
        """Get form descriptor by ID or name."""
        try:
            # Try as UUID
            return get_form_descriptor(form_id)
        except ValueError:
            pass

        try:
            # Try as name
            return get_form_by_name(form_id)
        except ValueError:
            raise ValueError(f"Unknown form: {form_id}")

    def list_forms(self) -> List[Dict[str, Any]]:
        """List available forms."""
        forms = available_forms()
        return [
            {
                "id": str(f.id),
                "name": f.name,
                "label": f.label,
                "has_template": f.has_manual_template
            }
            for f in forms
        ]

    def _load_manual_template(
        self,
        descriptor: FormDescriptor
    ) -> Optional[FormTemplate]:
        """Load manual template if available."""
        if not descriptor.template_json or not descriptor.template_json.exists():
            return None

        data = load_manual_template(descriptor.template_json)
        if not data:
            return None

        fields = data.get("fields", [])
        if not fields:
            return None

        # Extract mappings
        id_to_xfa = extract_xfa_mappings(data)

        # Build questions dict
        questions = {}
        for f in fields:
            if "id" in f and ("question" in f or "q" in f):
                questions[f["id"]] = f.get("question") or f.get("q")

        return FormTemplate(
            form_id=str(descriptor.id),
            form_name=descriptor.name,
            fields=fields,
            id_to_xfa_map=id_to_xfa,
            questions=questions,
            is_manual=True
        )

    def _generate_template(self, descriptor: FormDescriptor) -> FormTemplate:
        """
        Auto-generate template from PDF.

        Note: This is a placeholder. Full implementation would use
        PDF extraction and question generation.
        """
        # For now, return empty template
        # In production, this would:
        # 1. Extract fields from PDF
        # 2. Generate questions using TemplateGenerator
        return FormTemplate(
            form_id=str(descriptor.id),
            form_name=descriptor.name,
            fields=[],
            id_to_xfa_map={},
            questions={},
            is_manual=False
        )
