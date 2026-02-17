"""XFA PDF processing module."""

from .extract import extract_xfa_datasets
from .fill import update_datasets
from .inject import inject_datasets
from .checkbox import discover_checkbox_paths, normalize_checkboxes
