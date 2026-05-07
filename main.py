"""Main orchestration pipeline for Contrarian Flow Engine."""

from __future__ import annotations

import argparse

from modules.fundamentals import build_fundamentals_stub
from modules.event_shocks import build_event_shocks
from modules.prices import build_price_history_features
from modules.research_batch import build_research_batch
from modules.scoring import build_theory_scores
from modules.sec_filings import build_sec_filings
from modules.universe import build_universe
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config
from utils.paths import project_path
from utils.source_status import record_source_status, reset_source_status


def run_pipeline(config_path: str = "config.yaml", quick: bool = False) -> None:
    """Run the research pipeline in the configured refresh order."""
    config = load_config(config_path)
    ensure_project_dirs(config)
    logger = configure_logging(config["paths"].get("log_file"))
    logger.info("Starting Contrarian Flow Engine pipeline")
    show_progress(5, "Starting research engine")

    if quick and existing_research_outputs_ready(config):
        record_source_status(config, "startup", "saved_outputs", "reused", detail="Quick startup used saved research outputs.")
        show_progress(100, "Using saved research files; dashboard can open now")
        logger.info("Quick startup used existing research outputs")
        return

    reset_source_status(config)
    record_source_status(config, "startup", "pipeline", "started", detail="Full refresh started.")

    try:
        show_progress(10, "Building broad 10-bagger candidate universe")
        universe = build_universe(config, logger)
        record_source_status(config, "universe", "multi_source_universe", "ok", rows=len(universe))
    except Exception as exc:
        logger.exception("Universe stage failed")
        raise RuntimeError(f"Universe stage failed: {exc}") from exc
    logger.info("Universe stage complete with %s candidates", len(universe))
    show_progress(30, f"Universe built: {len(universe)} candidates")

    try:
        show_progress(32, "Pre-screening Top 100 10-bagger research batch")
        research_batch = build_research_batch(config, logger, universe)
        record_source_status(config, "research_batch", "prescreen", "ok", rows=len(research_batch))
        show_progress(34, f"Research batch ready: {len(research_batch)} candidates")
    except Exception as exc:
        logger.warning("Research batch pre-screen failed; using broad universe for slow stages: %s", exc)
        research_batch = universe
        show_progress(34, "Research batch pre-screen skipped; using broad universe")

    try:
        show_progress(35, "Refreshing price and volume history for Top 100 batch")
        price_features = build_price_history_features(config, logger, research_batch)
        ok_count = int((price_features.get("price_history_status", "") == "ok").sum()) if not price_features.empty else 0
        status = "ok" if ok_count else "degraded"
        record_source_status(config, "prices", "history_providers", status, rows=ok_count, detail=f"{ok_count}/{len(price_features)} tickers with usable history.")
        logger.info("Price-history stage complete with %s rows", len(price_features))
        show_progress(55, f"Price-history features ready: {len(price_features)} rows")
    except Exception as exc:
        logger.warning("Price-history stage skipped after noncritical failure: %s", exc)
        show_progress(55, "Price-history stage skipped; continuing with available data")

    try:
        show_progress(60, "Checking SEC filing metadata and signals for Top 100 batch")
        sec_filings, sec_flags = build_sec_filings(config, logger, research_batch)
        record_source_status(config, "sec", "sec_submissions", "ok" if len(sec_flags) else "degraded", rows=len(sec_flags))
        logger.info("SEC metadata stage complete with %s filings and %s ticker flags", len(sec_filings), len(sec_flags))
        show_progress(78, f"SEC metadata ready: {len(sec_filings)} filings")
    except Exception as exc:
        logger.warning("SEC metadata stage skipped after noncritical failure: %s", exc)
        show_progress(78, "SEC metadata stage skipped; continuing with available data")

    try:
        show_progress(80, "Scanning event-shock risk for Top 100 batch")
        event_shocks = build_event_shocks(config, logger, research_batch)
        record_source_status(config, "event_shocks", "sec_8k_text_or_metadata", "ok" if len(event_shocks) else "degraded", rows=len(event_shocks))
        logger.info("Event shock stage complete with %s rows", len(event_shocks))
        show_progress(81, f"Event shock scan ready: {len(event_shocks)} rows")
    except Exception as exc:
        logger.warning("Event shock stage skipped after noncritical failure: %s", exc)
        show_progress(81, "Event shock scan skipped; continuing")

    try:
        show_progress(82, "Extracting accounting fundamentals and ratios")
        fundamentals = build_fundamentals_stub(config, logger)
        record_source_status(config, "fundamentals", "sec_companyfacts", "ok" if len(fundamentals) else "degraded", rows=len(fundamentals))
        logger.info("Fundamentals stage complete with %s rows", len(fundamentals))
        show_progress(88, f"Fundamentals ready: {len(fundamentals)} rows")
    except Exception as exc:
        logger.warning("Fundamentals stage skipped after noncritical failure: %s", exc)
        show_progress(88, "Fundamentals skipped; continuing")

    try:
        show_progress(92, "Scoring Austrian, Hume, Keynes, relative mispricing, and asymmetry")
        theory_scores = build_theory_scores(config, logger)
        record_source_status(config, "scoring", "local_model", "ok" if len(theory_scores) else "degraded", rows=len(theory_scores))
        logger.info("Theory scoring stage complete with %s rows", len(theory_scores))
        show_progress(100, f"Watchlist complete: {len(theory_scores)} scored candidates")
    except Exception as exc:
        logger.warning("Theory scoring stage skipped after noncritical failure: %s", exc)
        show_progress(100, "Pipeline finished, but scoring was skipped")

    logger.info("Pipeline complete")


def show_progress(percent: int, message: str) -> None:
    """Print a human-friendly progress line for the double-click launcher."""
    print(f"[{percent:>3}%] {message}", flush=True)


def existing_research_outputs_ready(config: dict) -> bool:
    """Return True when saved outputs are enough to open the dashboard quickly."""
    required_paths = [
        config["paths"]["universe_output"],
        config["paths"]["research_batch_output"],
        config["paths"]["theory_scores_output"],
        config["paths"]["ranked_watchlist_output"],
    ]
    return all(project_path(path).exists() for path in required_paths)


def main() -> None:
    """Parse command-line arguments and run the full pipeline."""
    parser = argparse.ArgumentParser(description="Run Contrarian Flow Engine.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Open quickly using saved research outputs when they already exist.",
    )
    args = parser.parse_args()
    run_pipeline(args.config, quick=args.quick)


if __name__ == "__main__":
    main()
