"""Logging setup for command-line modules and the main pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.paths import project_path


def configure_logging(log_file: str | Path | None = None) -> logging.Logger:
    """Configure console and file logging, returning the engine logger."""
    logger = logging.getLogger("contrarian_flow_engine")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        path = project_path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
