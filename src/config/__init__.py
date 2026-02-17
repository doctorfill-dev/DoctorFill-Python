"""Configuration module."""

from .settings import *
from .form_registry import (
    FormDescriptor,
    available_forms,
    get_form_descriptor,
    get_form_by_name,
    rebuild_registry,
)
