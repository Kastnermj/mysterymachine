"""Relative path helpers for the research engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(relative_path: str | Path) -> Path:
    """Return a project-relative path as an absolute Path for local file access."""
    return PROJECT_ROOT / Path(relative_path)


def load_config(config_path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load YAML config from a project-relative path."""
    path = project_path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        if yaml is not None:
            return yaml.safe_load(handle)
        return _parse_simple_yaml(handle.read())


def ensure_project_dirs(config: dict[str, Any]) -> None:
    """Create configured output and data folders when they do not exist."""
    for key in ["raw_dir", "processed_dir", "cache_dir", "watchlists_dir", "reports_dir"]:
        project_path(config["paths"][key]).mkdir(parents=True, exist_ok=True)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the project's simple YAML shape if PyYAML is unavailable."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    pending_list_key: tuple[int, str, dict[str, Any]] | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if line.startswith("- ") and pending_list_key:
            list_indent, key, parent = pending_list_key
            if indent > list_indent:
                if not isinstance(parent.get(key), list):
                    parent[key] = []
                parent[key].append(_parse_scalar(line[2:].strip()))
                continue

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
            pending_list_key = (indent, key, parent)
        else:
            parent[key] = _parse_scalar(value)
            pending_list_key = None
    return root


def _parse_scalar(value: str) -> Any:
    """Convert a basic YAML scalar to a Python value."""
    value = value.strip().strip('"').strip("'")
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
