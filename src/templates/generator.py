"""
Template Generator - Generates questions from PDF form fields.

Used when no manual template exists for auto-generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class FieldType(str, Enum):
    """Form field types."""
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    DATE = "date"
    NUMBER = "number"
    SIGNATURE = "signature"
    BUTTON = "button"
    UNKNOWN = "unknown"


@dataclass
class FormField:
    """Simplified form field for question generation."""
    id: str
    name: str
    field_type: FieldType
    label: Optional[str] = None
    tooltip: Optional[str] = None
    options: Optional[List[str]] = None
    read_only: bool = False
    section: Optional[str] = None
    context_text: Optional[str] = None


class TemplateGenerator:
    """
    Generates questions from form field structure.

    Used for auto-generating templates when no manual template exists.
    """

    # Question templates by field type (French)
    QUESTION_TEMPLATES = {
        FieldType.TEXT: "Quel est {article} {label} ?",
        FieldType.CHECKBOX: "{label} : est-ce que cette condition s'applique ? (oui/non)",
        FieldType.RADIO: "Quelle option sélectionner pour {label} ?",
        FieldType.SELECT: "Quelle valeur choisir pour {label} ?",
        FieldType.DATE: "Quelle est la date de {label} ? (format: JJ.MM.AAAA)",
        FieldType.NUMBER: "Quel est le nombre/numéro de {label} ?",
        FieldType.SIGNATURE: "Y a-t-il une signature pour {label} ? (oui/non)",
    }

    # French article patterns
    ARTICLE_PATTERNS = {
        'nom': 'le',
        'prenom': 'le',
        'prénom': 'le',
        'adresse': "l'",
        'email': "l'",
        'telephone': 'le',
        'téléphone': 'le',
        'date': 'la',
        'numero': 'le',
        'numéro': 'le',
        'montant': 'le',
        'code': 'le',
        'ville': 'la',
        'pays': 'le',
        'profession': 'la',
        'nationalité': 'la',
        'nationalite': 'la',
        'sexe': 'le',
        'naissance': 'la date de',
        'canton': 'le',
        'diagnostic': 'le',
        'traitement': 'le',
        'anamnèse': "l'",
        'pronostic': 'le',
    }

    # Known field name translations (English XFA names → French labels)
    KNOWN_FIELD_MAPPINGS = {
        'lastname': 'nom de famille',
        'firstname': 'prénom',
        'name': 'nom',
        'birthdate': 'date de naissance',
        'address': 'adresse',
        'phone': 'téléphone',
        'gender': 'sexe',
        'avsnr': 'numéro AVS',
        'postal': 'code postal',
        'city': 'ville/lieu',
        'street': 'rue',
        'insurance': 'assurance',
        'patient': 'patient',
        'medication': 'médication actuelle',
        'diagnosis': 'diagnostic',
        'anamnesis': 'anamnèse',
        'prognosis': 'pronostic',
        'treatment': 'traitement',
        'incapacity': 'incapacité de travail',
    }

    def generate_questions(
        self,
        fields: List[FormField]
    ) -> List[Dict[str, str]]:
        """
        Generate question list from form fields.

        Args:
            fields: List of FormField objects

        Returns:
            List of {"id": "...", "question": "..."} dicts for RAG
        """
        questions = []

        for field in fields:
            # Skip read-only and button fields
            if field.read_only or field.field_type == FieldType.BUTTON:
                continue

            # Skip fields that are not useful
            if not self._is_field_useful(field):
                continue

            question = self._generate_question(field)

            entry = {
                "id": field.id,
                "question": question,
                "type": field.field_type.value,
            }

            # Add options for select/radio
            if field.options:
                entry["options"] = self._clean_options(field.options)

            questions.append(entry)

        return questions

    def _generate_question(self, field: FormField) -> str:
        """Generate a natural question for a field."""
        # Use tooltip first if meaningful
        if field.tooltip and len(field.tooltip) > 10 and not self._is_technical_name(field.tooltip):
            return self._format_as_question(field.tooltip)

        # Try to get a good label
        label = None

        # Try translating technical name
        translated = self._translate_technical_name(field.name)
        if translated and len(translated) > 3 and not self._is_technical_name(translated):
            label = translated

        # Try using field label
        if not label and field.label:
            cleaned = self._clean_label(field.label)
            if cleaned and len(cleaned) > 4 and not self._is_technical_name(cleaned):
                label = cleaned

        # Fallback to contextual label
        if not label or len(label) < 3 or self._is_technical_name(label):
            label = self._create_contextual_label(field)

        # Get article
        article = self._get_article(label)

        # Get template
        template = self.QUESTION_TEMPLATES.get(
            field.field_type,
            "Quelle est la valeur de {label} ?"
        )

        # Format question
        question = template.format(article=article, label=label)

        # Clean up
        question = re.sub(r'\s+', ' ', question)
        question = re.sub(r"(l'|le |la |les )\1", r'\1', question)

        return question

    def _is_technical_name(self, name: str) -> bool:
        """Check if a name is technical/not meaningful."""
        if not name:
            return True

        name_lower = name.lower().strip()

        if len(name_lower) < 3:
            return True

        technical_patterns = [
            r'\[\d+\]',
            r'\.seite\d+',
            r'^(combobox|checkbox|textfield|button|input|field)$',
            r'^[a-z]{1,3}$',
        ]

        return any(re.search(p, name_lower) for p in technical_patterns)

    def _translate_technical_name(self, name: str) -> str:
        """Translate technical XFA names to meaningful labels."""
        if not name:
            return name

        # Clean XFA path notation
        cleaned = re.sub(r'\[\d+\]', '', name)
        cleaned = re.sub(r'[_\-]+', ' ', cleaned)

        # Get last component
        parts = [p.strip() for p in cleaned.split('.') if p.strip()]
        meaningful_part = parts[-1] if parts else cleaned

        # Convert camelCase
        meaningful_part = re.sub(r'([a-z])([A-Z])', r'\1 \2', meaningful_part)
        meaningful_lower = meaningful_part.lower().strip()

        # Try translation
        if meaningful_lower in self.KNOWN_FIELD_MAPPINGS:
            return self.KNOWN_FIELD_MAPPINGS[meaningful_lower]

        # Try partial match
        for eng, fra in self.KNOWN_FIELD_MAPPINGS.items():
            if eng in meaningful_lower:
                return fra

        return meaningful_lower

    def _create_contextual_label(self, field: FormField) -> str:
        """Create a generic but contextual label."""
        section = (field.section or "").lower()

        if field.field_type == FieldType.CHECKBOX:
            return "cette option"
        elif field.field_type == FieldType.DATE:
            return "la date concernée"
        elif field.field_type == FieldType.SELECT:
            return "la sélection"

        if 'personnel' in section or 'identité' in section:
            return "information personnelle"
        elif 'médical' in section:
            return "information médicale"
        elif 'profession' in section:
            return "information professionnelle"

        return "information demandée"

    def _clean_label(self, label: str) -> str:
        """Clean field label."""
        if not label:
            return ""

        label = re.sub(r'^(txt|chk|cmb|btn|rad|fld)_?', '', label, flags=re.IGNORECASE)
        label = re.sub(r'\[\d+\]', '', label)
        label = re.sub(r'[_\-\.]+', ' ', label)
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', label)
        label = re.sub(r'\s*\d+$', '', label)
        label = ' '.join(label.split())

        return label.strip().lower()

    def _clean_options(self, options: Optional[List]) -> Optional[List[str]]:
        """Clean options list."""
        if not options:
            return None

        cleaned = []
        for opt in options:
            if isinstance(opt, (tuple, list)):
                cleaned.append(str(opt[1]) if len(opt) > 1 else str(opt[0]))
            else:
                cleaned.append(str(opt))

        return cleaned if cleaned else None

    def _is_field_useful(self, field: FormField) -> bool:
        """Determine if a field should be included."""
        if field.label and not self._is_technical_name(field.label):
            return True

        if field.context_text and len(field.context_text) > 20:
            return True

        translated = self._translate_technical_name(field.name)
        if translated and not self._is_technical_name(translated):
            return True

        if self._is_technical_name(field.name) and not field.context_text:
            return False

        return True

    def _get_article(self, label: str) -> str:
        """Get appropriate French article for label."""
        label_lower = label.lower()

        for pattern, article in self.ARTICLE_PATTERNS.items():
            if pattern in label_lower:
                return article

        if label_lower and label_lower[0] in 'aeiouhéèêàâôîûù':
            return "l'"

        return "le/la"

    def _format_as_question(self, text: str) -> str:
        """Format tooltip text as a question."""
        text = text.strip()

        if text.endswith('?'):
            return text

        if text.startswith(('Quel', 'Quelle', 'Quand', 'Où', 'Comment')):
            return text + ' ?'

        return f"Quel est {text.lower()} ?"
