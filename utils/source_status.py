"""Lightweight source-health recording for refresh diagnostics."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.paths import project_path


STATUS_COLUMNS = [
    "timestamp_utc",
    "stage",
    "provider",
    "status",
    "rows",
    "fallback_used",
    "detail",
]


def status_path(config: dict[str, Any]) -> Path:
    """Return the project source-status CSV path."""
    return project_path(config["paths"].get("source_status_output", "data/processed/source_status.csv"))


def reset_source_status(config: dict[str, Any]) -> None:
    """Start a fresh source-health log for a new full refresh."""
    path = status_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATUS_COLUMNS)
        writer.writeheader()


def record_source_status(
    config: dict[str, Any],
    stage: str,
    provider: str,
    status: str,
    rows: int | float | None = None,
    fallback_used: bool = False,
    detail: str = "",
) -> None:
    """Append one source-health row without interrupting the pipeline."""
    path = status_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": stage,
        "provider": provider,
        "status": status,
        "rows": "" if rows is None else rows,
        "fallback_used": bool(fallback_used),
        "detail": str(detail or "")[:500],
    }
    try:
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=STATUS_COLUMNS)
            if needs_header:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        return
