"""Top research-batch scoring wrapper.

The core scoring module is intentionally broad and historically started from
``universe.csv``. For the hosted dashboard, we want the final scored board to
represent the post-prescreen research batch, currently Top 250.

This wrapper keeps the original scorer intact, but points its universe input to
``research_batch.csv`` for final dashboard scoring. The full ``universe.csv``
still remains available for the sidebar Full Universe Scout.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from modules.scoring import build_theory_scores as build_core_theory_scores
from utils.logging_config import configure_logging
from utils.paths import load_config


def build_theory_scores(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Score the configured post-prescreen research batch instead of all universe names."""
    config = config or load_config()
    logger = logger or configure_logging(config["paths"].get("log_file"))

    research_batch_path = config["paths"].get("research_batch_output")
    if research_batch_path:
        scoped_config = dict(config)
        scoped_paths = dict(config.get("paths", {}))
        scoped_paths["universe_output"] = research_batch_path
        scoped_config["paths"] = scoped_paths
        logger.info("Scoring final dashboard board from research batch: %s", research_batch_path)
        return build_core_theory_scores(scoped_config, logger)

    logger.warning("No research_batch_output configured; falling back to core broad-universe scoring")
    return build_core_theory_scores(config, logger)
