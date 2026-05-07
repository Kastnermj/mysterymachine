"""Simple JSON cache helpers for public data source responses."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from utils.paths import project_path


def cache_path(cache_dir: str, key: str) -> Path:
    """Build a safe cache file path for a logical cache key."""
    safe_key = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in key)
    return project_path(cache_dir) / f"{safe_key}.json"


def read_json_cache(cache_dir: str, key: str, ttl_hours: float) -> Any | None:
    """Read cached JSON if it exists and has not expired."""
    path = cache_path(cache_dir, key)
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > ttl_hours:
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def write_json_cache(cache_dir: str, key: str, payload: Any) -> None:
    """Write JSON payload to the project cache directory."""
    path = cache_path(cache_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
