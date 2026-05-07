"""General helper functions shared by research modules."""

from __future__ import annotations

import math
from typing import Any

from utils.logging_config import configure_logging
from utils.paths import load_config


def to_float(value: Any) -> float | None:
    """Convert a value to float, returning None for missing or invalid values."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Divide two numbers while protecting against missing values and zero."""
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def coalesce(*values: Any) -> Any:
    """Return the first non-empty value."""
    for value in values:
        if value in (None, ""):
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        if str(value).lower() == "nan":
            continue
        if value is not None:
            return value
    return None


def run_placeholder_module(module_name: str) -> None:
    """Log that a module is wired and ready for its future implementation."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    logger.info("%s module is wired and ready for implementation", module_name)
