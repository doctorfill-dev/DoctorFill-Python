"""
Form Registry - Secure management of available PDF forms and templates.

Provides secure access to form templates with path traversal protection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .settings import TEMPLATES_DIR, FORMS_DIR

# Namespace for generating form UUIDs
FORM_NAMESPACE = UUID("f7bc1110-7f40-4b0d-9d33-7d732b4f5c2d")


@dataclass(frozen=True)
class FormDescriptor:
    """Metadata for an available form."""

    id: UUID
    name: str
    label: str
    form_pdf: Path
    template_json: Optional[Path]
    template_min_json: Optional[Path]
    has_manual_template: bool = True

    def __post_init__(self):
        # Set has_manual_template based on template existence
        object.__setattr__(
            self,
            'has_manual_template',
            self.template_json is not None and self.template_json.exists()
        )


def _resolve_within(base: Path, candidate: Path) -> Path:
    """
    Resolve a path and verify it stays within the base directory.

    Security measure to prevent path traversal attacks.
    """
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve(strict=False)

    try:
        resolved_candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(f"Path outside of {resolved_base}: {candidate}") from exc

    return resolved_candidate


def _iter_template_dirs(base: Path) -> Iterable[Path]:
    """Iterate over valid template directories."""
    if not base.exists():
        return

    for entry in base.iterdir():
        if not entry.is_dir():
            continue

        # Skip symlinks for security
        if entry.is_symlink():
            continue

        try:
            safe_entry = _resolve_within(base, entry)
        except ValueError:
            continue

        if safe_entry.is_dir():
            yield safe_entry


def _build_form_registry(
    forms_dir: Path,
    templates_dir: Path
) -> Tuple[Dict[UUID, FormDescriptor], Dict[str, FormDescriptor]]:
    """Build the form registry from available templates."""

    by_id: Dict[UUID, FormDescriptor] = {}
    by_name: Dict[str, FormDescriptor] = {}

    for template_dir in sorted(_iter_template_dirs(templates_dir)):
        template_name = template_dir.name

        # Check for form PDF
        try:
            form_pdf = _resolve_within(forms_dir, forms_dir / f"{template_name}.pdf")
        except ValueError:
            continue

        if not form_pdf.exists():
            continue

        # Check for template files (optional for auto-generated templates)
        template_json = template_dir / f"{template_name}.json"
        template_min_json = template_dir / f"{template_name}_Min.json"

        has_manual = template_json.exists()

        form_id = uuid5(FORM_NAMESPACE, template_name)
        descriptor = FormDescriptor(
            id=form_id,
            name=template_name,
            label=template_name.replace("_", " "),
            form_pdf=form_pdf,
            template_json=template_json if has_manual else None,
            template_min_json=template_min_json if template_min_json.exists() else None,
            has_manual_template=has_manual,
        )

        by_id[form_id] = descriptor
        by_name[template_name] = descriptor

    return by_id, by_name


# Build registry at module load
_FORMS_BY_ID, _FORMS_BY_NAME = _build_form_registry(FORMS_DIR, TEMPLATES_DIR)


def rebuild_registry() -> None:
    """Rebuild the form registry (useful after adding new forms)."""
    global _FORMS_BY_ID, _FORMS_BY_NAME
    _FORMS_BY_ID, _FORMS_BY_NAME = _build_form_registry(FORMS_DIR, TEMPLATES_DIR)


def available_forms() -> List[FormDescriptor]:
    """Return list of available forms."""
    return list(_FORMS_BY_ID.values())


def available_form_names() -> Set[str]:
    """Return set of available form names."""
    return set(_FORMS_BY_NAME.keys())


def get_form_descriptor(form_id: UUID | str) -> FormDescriptor:
    """
    Get form descriptor by UUID or string UUID.

    Raises ValueError if form not found.
    """
    if isinstance(form_id, str):
        try:
            form_id = UUID(form_id)
        except ValueError as exc:
            raise ValueError("Invalid form identifier") from exc

    try:
        return _FORMS_BY_ID[form_id]
    except KeyError as exc:
        raise ValueError(f"Unknown form: {form_id}") from exc


def get_form_by_name(name: str) -> FormDescriptor:
    """
    Get form descriptor by name.

    Raises ValueError if form not found.
    """
    try:
        return _FORMS_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Unknown form: {name}") from exc


def form_id_for_name(template_name: str) -> UUID:
    """Get UUID for a template name."""
    return get_form_by_name(template_name).id
