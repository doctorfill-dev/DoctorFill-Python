"""
User Configuration - Persistent user settings stored locally.

Handles API keys and provider preferences separately from .env defaults.
Stored in a JSON file in the data directory.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .settings import DATA_DIR

logger = logging.getLogger(__name__)

CONFIG_FILE = DATA_DIR / "user_config.json"

_DEFAULTS = {
    "llm_provider": "infomaniak",
    "ifk_product_id": "",
    "ifk_api_token": "",
    "lmstudio_base_url": "http://localhost:1234/v1",
}


def load() -> Dict[str, Any]:
    """Load user configuration from disk."""
    if not CONFIG_FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load user config, using defaults: %s", e)
        return dict(_DEFAULTS)


def save(config: Dict[str, Any]) -> None:
    """Save user configuration to disk."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("User config saved to %s", CONFIG_FILE)


def is_configured() -> bool:
    """Check if user has provided required API credentials."""
    cfg = load()
    provider = cfg.get("llm_provider", "infomaniak")
    if provider == "infomaniak":
        return bool(cfg.get("ifk_product_id")) and bool(cfg.get("ifk_api_token"))
    elif provider == "local":
        return bool(cfg.get("lmstudio_base_url"))
    return False


def get(key: str, fallback: Optional[str] = None) -> Optional[str]:
    """Get a single config value."""
    return load().get(key, fallback)
