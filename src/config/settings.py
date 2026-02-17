"""
Settings - Centralized configuration for DoctorFill.

All settings can be overridden via environment variables.
User-provided API keys (from the setup screen) take priority over .env values.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────

import sys

_FROZEN = getattr(sys, '_MEIPASS', None)

if _FROZEN:
    # PyInstaller bundle: read-only assets are in _MEIPASS,
    # writable dirs (data, logs) live next to the executable.
    _BUNDLE_DIR = Path(_FROZEN)
    _APP_DIR = Path(sys.executable).parent
    TEMPLATES_DIR = _BUNDLE_DIR / "templates"
    FORMS_DIR = _BUNDLE_DIR / "forms"
    DATA_DIR = _APP_DIR / "data"
    LOGS_DIR = _APP_DIR / "logs"
    PROJECT_ROOT = _APP_DIR
else:
    # Normal development mode
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    TEMPLATES_DIR = PROJECT_ROOT / "templates"
    FORMS_DIR = PROJECT_ROOT / "forms"
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = PROJECT_ROOT / "logs"

LOG_JSON_DIR = LOGS_DIR / "json"
LOG_XML_DIR = LOGS_DIR / "xml"
LOG_PDF_DIR = LOGS_DIR / "pdf"

# Ensure writable directories exist
for dir_path in [TEMPLATES_DIR, FORMS_DIR, DATA_DIR, LOGS_DIR, LOG_JSON_DIR, LOG_XML_DIR, LOG_PDF_DIR]:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Read-only dirs (in bundle) may fail, that's OK

# ──────────────────────────────────────────────────────────────
# User config (API keys from setup screen take priority)
# ──────────────────────────────────────────────────────────────

def _user_cfg(key: str, fallback: str = "") -> str:
    """Get a value from user config, falling back to env var then default."""
    from .user_config import load as _load_user_config
    cfg = _load_user_config()
    val = cfg.get(key, "")
    if val:
        return val
    return os.getenv(key.upper(), fallback)

# ──────────────────────────────────────────────────────────────
# LLM Provider
# ──────────────────────────────────────────────────────────────

LLM_PROVIDER = _user_cfg("llm_provider", os.getenv("LLM_PROVIDER", "infomaniak"))

# Local (LM Studio)
LMSTUDIO_BASE_URL = _user_cfg("lmstudio_base_url", os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"))
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen2.5-14b-instruct")
LMSTUDIO_EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "nomic-embed-text")

# Infomaniak
IFK_PRODUCT_ID = _user_cfg("ifk_product_id", os.getenv("IFK_PRODUCT_ID", ""))
IFK_API_TOKEN = _user_cfg("ifk_api_token", os.getenv("IFK_API_TOKEN", ""))
IFK_LLM_MODEL = os.getenv("IFK_LLM_MODEL", "qwen3")
IFK_EMBEDDING_MODEL = os.getenv("IFK_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
IFK_RERANKER_MODEL = os.getenv("IFK_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

# Request settings
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# ──────────────────────────────────────────────────────────────
# RAG Configuration
# ──────────────────────────────────────────────────────────────

RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "2000"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "300"))
RAG_RETRIEVAL_TOP_K = int(os.getenv("RAG_RETRIEVAL_TOP_K", "4"))
RAG_USE_RERANKING = os.getenv("RAG_USE_RERANKING", "true").lower() == "true"
RAG_MAX_CONTEXT_WINDOW = int(os.getenv("RAG_MAX_CONTEXT_WINDOW", "8192"))
RAG_SAFETY_MARGIN = int(os.getenv("RAG_SAFETY_MARGIN", "1500"))
RAG_MAX_INPUT_TOKENS = RAG_MAX_CONTEXT_WINDOW - RAG_SAFETY_MARGIN
RAG_BATCH_SIZE = int(os.getenv("RAG_BATCH_SIZE", "5"))

# ──────────────────────────────────────────────────────────────
# API Configuration
# ──────────────────────────────────────────────────────────────

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
