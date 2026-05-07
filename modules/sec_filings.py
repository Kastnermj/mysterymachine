"""Lightweight SEC filing metadata collection.

Stage 1 stores filing metadata only. It does not parse XBRL or full filing text.
The goal is to add SEC awareness without slowing or breaking the rest of the
pipeline.
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

from utils.cache import read_json_cache, write_json_cache
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path
from utils.source_status import record_source_status


FILING_COLUMNS = [
    "ticker",
    "cik",
    "company_name",
    "filing_type",
    "filing_date",
    "accession_number",
    "primary_document",
    "filing_url",
    "is_high_signal",
]

FLAG_COLUMNS = [
    "ticker",
    "cik",
    "company_name",
    "recent_filing_count",
    "recent_high_signal_count",
    "has_recent_10k",
    "has_recent_10q",
    "has_recent_8k",
    "has_recent_s1",
    "has_recent_s3",
    "has_recent_424b",
    "latest_filing_type",
    "latest_filing_date",
    "sec_activity_flag",
]

SIGNAL_COLUMNS = [
    "ticker",
    "cik",
    "company_name",
    "dilution_pressure_score",
    "survival_risk_score",
    "catalyst_signal_score",
    "narrative_trigger_score",
    "filing_activity_score",
    "catalyst_signal_label",
    "signal_interpretation",
]


def build_sec_filings(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    universe: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch, cache, and save lightweight SEC filing metadata and flags."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))

    if not config.get("sec", {}).get("enabled", True):
        logger.info("SEC filings stage disabled in config")
        return _empty_outputs(config, logger)
    if requests is None:
        logger.warning("requests is not installed; keeping existing SEC outputs if available")
        return _existing_or_empty_outputs(config, logger)
    if not config["refresh"].get("use_network", True):
        logger.info("Network refresh disabled; keeping existing SEC outputs if available")
        return _existing_or_empty_outputs(config, logger)

    universe = universe if universe is not None else _load_universe(config, logger)
    if universe.empty or "ticker" not in universe.columns:
        logger.warning("No universe tickers available for SEC filing metadata")
        return _existing_or_empty_outputs(config, logger)
    max_tickers = config["sec"].get("max_tickers_per_run")
    if max_tickers and len(universe) > int(max_tickers):
        logger.info("Limiting SEC metadata refresh to first %s universe tickers this run", max_tickers)
        universe = universe.head(int(max_tickers)).copy()

    try:
        cik_map = fetch_company_ticker_map(config, logger)
        filing_rows: list[dict[str, Any]] = []
        total_tickers = len(universe)
        for index, (_, row) in enumerate(universe.iterrows(), start=1):
            if index == 1 or index % 25 == 0 or index == total_tickers:
                print(f"      SEC metadata: {index}/{total_tickers} tickers checked", flush=True)
            ticker = str(row.get("ticker", "")).upper().strip()
            if not ticker:
                continue
            cik = cik_map.get(ticker)
            if not cik:
                logger.info("No SEC CIK found for %s", ticker)
                continue
            try:
                payload = fetch_company_submissions(cik, config, logger)
            except Exception as exc:
                logger.info("SEC submissions skipped for %s after provider error: %s", ticker, exc)
                continue
            filing_rows.extend(parse_recent_filings(ticker, cik, row.get("company_name"), payload, config))

        filings = pd.DataFrame(filing_rows, columns=FILING_COLUMNS)
        flags = summarize_filing_flags(filings, config)
        signals = interpret_filing_signals(filings, flags, config)
        _save_outputs(filings, flags, signals, config, logger)
        record_source_status(
            config,
            "sec",
            "sec_submissions",
            "ok" if len(flags) else "degraded",
            rows=len(flags),
            fallback_used=False,
            detail=f"{len(filings)} filing metadata rows; {len(flags)} ticker flags.",
        )
        return filings, flags
    except Exception as exc:
        if config.get("sec", {}).get("never_block_pipeline", True):
            logger.warning("SEC filings stage failed without blocking pipeline: %s", exc)
            return _existing_or_empty_outputs(config, logger)
        raise


def fetch_company_ticker_map(config: dict[str, Any], logger: logging.Logger) -> dict[str, str]:
    """Fetch or load cached SEC ticker-to-CIK mapping."""
    cache_dir = config["paths"]["cache_dir"]
    ttl_hours = config["refresh"]["cache_ttl_hours"]
    cache_key = "sec_company_tickers"
    cached = read_json_cache(cache_dir, cache_key, ttl_hours)
    payload = cached if cached else _get_json(config["sec"]["company_tickers_url"], config)
    if not cached:
        write_json_cache(cache_dir, cache_key, payload)
        logger.debug("Cached SEC company ticker mapping")

    mapping: dict[str, str] = {}
    for item in payload.values():
        ticker = str(item.get("ticker", "")).upper().strip()
        cik = str(item.get("cik_str", "")).zfill(10)
        if ticker and cik:
            mapping[ticker] = cik
    return mapping


def fetch_company_submissions(cik: str, config: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    """Fetch or load cached SEC submissions metadata for a single CIK."""
    cache_dir = config["paths"]["cache_dir"]
    ttl_hours = config["refresh"]["cache_ttl_hours"]
    cache_key = f"sec_submissions_{cik}"
    cached = read_json_cache(cache_dir, cache_key, ttl_hours)
    if cached:
        return cached

    url = config["sec"]["submissions_url"].format(cik=cik)
    try:
        payload = _get_json(url, config)
    except Exception:
        stale = read_json_cache(cache_dir, cache_key, 10_000_000)
        if stale:
            logger.debug("Using stale SEC submissions cache for CIK %s after provider error", cik)
            return stale
        raise
    write_json_cache(cache_dir, cache_key, payload)
    logger.debug("Cached SEC submissions for CIK %s", cik)
    return payload


def parse_recent_filings(
    ticker: str,
    cik: str,
    company_name: str | None,
    payload: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract filing metadata rows from SEC submissions JSON."""
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    max_rows = config["sec"]["max_recent_filings_per_ticker"]
    high_signal_forms = set(config["sec"]["high_signal_forms"])

    rows: list[dict[str, Any]] = []
    for idx, form in enumerate(forms[:max_rows]):
        filing_date = _safe_list_get(dates, idx)
        accession = _safe_list_get(accessions, idx)
        primary_doc = _safe_list_get(primary_docs, idx)
        filing_url = build_filing_url(cik, accession, primary_doc)
        rows.append(
            {
                "ticker": ticker,
                "cik": cik,
                "company_name": company_name or payload.get("name"),
                "filing_type": form,
                "filing_date": filing_date,
                "accession_number": accession,
                "primary_document": primary_doc,
                "filing_url": filing_url,
                "is_high_signal": is_high_signal_form(form, high_signal_forms),
            }
        )
    return rows


def summarize_filing_flags(filings: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create ticker-level high-signal filing activity flags."""
    if filings.empty:
        return pd.DataFrame(columns=FLAG_COLUMNS)

    frame = filings.copy()
    frame["filing_date_dt"] = pd.to_datetime(frame["filing_date"], errors="coerce", utc=True)
    cutoff = pd.Timestamp(datetime.now(timezone.utc)) - pd.Timedelta(days=config["sec"]["recent_activity_days"])
    recent = frame[frame["filing_date_dt"] >= cutoff].copy()

    rows: list[dict[str, Any]] = []
    for ticker, group in frame.groupby("ticker"):
        recent_group = recent[recent["ticker"] == ticker]
        latest = group.sort_values("filing_date_dt", ascending=False).iloc[0]
        forms = set(recent_group["filing_type"].dropna().astype(str))
        rows.append(
            {
                "ticker": ticker,
                "cik": latest["cik"],
                "company_name": latest["company_name"],
                "recent_filing_count": int(len(recent_group)),
                "recent_high_signal_count": int(recent_group["is_high_signal"].fillna(False).sum()),
                "has_recent_10k": "10-K" in forms,
                "has_recent_10q": "10-Q" in forms,
                "has_recent_8k": "8-K" in forms,
                "has_recent_s1": "S-1" in forms,
                "has_recent_s3": "S-3" in forms,
                "has_recent_424b": any(form.startswith("424B") for form in forms),
                "latest_filing_type": latest["filing_type"],
                "latest_filing_date": latest["filing_date"],
                "sec_activity_flag": classify_activity(recent_group),
            }
        )
    return pd.DataFrame(rows, columns=FLAG_COLUMNS)


def interpret_filing_signals(
    filings: pd.DataFrame,
    flags: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Convert SEC filing metadata into research signals.

    This uses only existing metadata and flags. It does not fetch or parse
    filing documents, so text-specific concepts such as going concern language,
    contracts, resignations, or bankruptcy references are represented only by
    conservative metadata proxies.
    """
    if flags.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    frame = filings.copy()
    if not frame.empty:
        frame["filing_date_dt"] = pd.to_datetime(frame["filing_date"], errors="coerce", utc=True)
    rows: list[dict[str, Any]] = []
    now = pd.Timestamp(datetime.now(timezone.utc))
    recent_cutoff = now - pd.Timedelta(days=config["sec"]["recent_activity_days"])
    spike_cutoff = now - pd.Timedelta(days=config["sec"].get("activity_spike_days", 14))
    financing_cutoff = now - pd.Timedelta(days=config["sec"].get("financing_lookback_days", 365))

    for _, flag_row in flags.iterrows():
        ticker = flag_row["ticker"]
        group = frame[frame["ticker"] == ticker].copy() if not frame.empty else pd.DataFrame(columns=FILING_COLUMNS)
        recent_group = group[group["filing_date_dt"] >= recent_cutoff] if not group.empty else group
        spike_group = group[group["filing_date_dt"] >= spike_cutoff] if not group.empty else group
        financing_watch_group = group[group["filing_date_dt"] >= financing_cutoff] if not group.empty else group
        forms_all = group["filing_type"].dropna().astype(str).str.upper().tolist() if not group.empty else []
        forms_recent = recent_group["filing_type"].dropna().astype(str).str.upper().tolist() if not recent_group.empty else []
        forms_financing_watch = financing_watch_group["filing_type"].dropna().astype(str).str.upper().tolist() if not financing_watch_group.empty else []

        financing_all = [form for form in forms_all if is_financing_form(form)]
        financing_recent = [form for form in forms_recent if is_financing_form(form)]
        financing_watch = [form for form in forms_financing_watch if is_financing_form(form)]
        eightk_recent = forms_recent.count("8-K")

        dilution_score = score_dilution_pressure(financing_all, financing_recent, financing_watch)
        survival_score = score_survival_risk(flag_row, forms_recent, financing_recent, recent_group)
        catalyst_score, catalyst_label = score_catalyst_signal(forms_recent, financing_recent)
        narrative_score = score_narrative_trigger(forms_recent, financing_recent, recent_group, spike_group)
        activity_score = score_filing_activity(recent_group, spike_group, group)

        rows.append(
            {
                "ticker": ticker,
                "cik": flag_row.get("cik"),
                "company_name": flag_row.get("company_name"),
                "dilution_pressure_score": dilution_score,
                "survival_risk_score": survival_score,
                "catalyst_signal_score": catalyst_score,
                "narrative_trigger_score": narrative_score,
                "filing_activity_score": activity_score,
                "catalyst_signal_label": catalyst_label,
                "signal_interpretation": build_signal_interpretation(
                    dilution_score,
                    survival_score,
                    catalyst_label,
                    narrative_score,
                    activity_score,
                    eightk_recent,
                    len(financing_recent),
                    len(financing_watch),
                ),
            }
        )
    return pd.DataFrame(rows, columns=SIGNAL_COLUMNS)


def is_financing_form(form: str) -> bool:
    """Return True when a form is commonly associated with financing/dilution pressure."""
    form_text = str(form or "").upper()
    base_form = form_text.replace("/A", "")
    return base_form in {"S-1", "S-3", "F-1", "F-3"} or form_text.startswith("424B")


def score_dilution_pressure(
    financing_all: list[str],
    financing_recent: list[str],
    financing_watch: list[str] | None = None,
) -> int:
    """Score dilution pressure from registration/prospectus filing metadata."""
    financing_watch = financing_watch or []
    score = 0
    recent_base = [form.replace("/A", "") for form in financing_recent]
    watch_base = [form.replace("/A", "") for form in financing_watch]
    all_base = [form.replace("/A", "") for form in financing_all]
    if any(form in {"S-1", "F-1"} for form in recent_base):
        score += 40
    if any(form in {"S-3", "F-3"} for form in recent_base):
        score += 35
    if any(form.startswith("424B") for form in financing_recent):
        score += 35
    score += min(30, len(financing_recent) * 10)
    if financing_watch and not financing_recent:
        score += 18
    if any(form in {"S-1", "F-1"} for form in watch_base):
        score += 18
    if any(form in {"S-3", "F-3"} for form in watch_base):
        score += 16
    if any(form.startswith("424B") for form in financing_watch):
        score += 16
    if len(financing_watch) >= 2:
        score += 10
    score += min(20, max(0, len(financing_all) - len(financing_recent)) * 4)
    if len(set(all_base) & {"S-1", "F-1", "S-3", "F-3"}) >= 2:
        score += 8
    if len(financing_recent) >= 2:
        score += 15
    return min(100, score)


def score_survival_risk(
    flag_row: pd.Series,
    forms_recent: list[str],
    financing_recent: list[str],
    recent_group: pd.DataFrame,
) -> int:
    """Score survival risk using metadata-only proxies."""
    recent_count = int(flag_row.get("recent_filing_count", 0) or 0)
    score = 10
    if financing_recent:
        score += 25
    if recent_count == 0:
        score += 30
    if recent_count >= 6:
        score += 20
    if "10-K" not in forms_recent and "10-Q" not in forms_recent:
        score += 15
    if "8-K" in forms_recent and financing_recent:
        score += 10
    if not recent_group.empty and recent_group["is_high_signal"].fillna(False).sum() >= 4:
        score += 10
    return min(100, score)


def score_catalyst_signal(forms_recent: list[str], financing_recent: list[str]) -> tuple[int, str]:
    """Classify 8-K catalyst signal using metadata-only evidence."""
    eightk_count = forms_recent.count("8-K")
    if eightk_count == 0:
        return 0, "none_detected"
    if financing_recent:
        return 35, "negative_or_financing_related"
    if eightk_count >= 3:
        return 60, "event_cluster_needs_review"
    return 50, "neutral_event_update"


def score_narrative_trigger(
    forms_recent: list[str],
    financing_recent: list[str],
    recent_group: pd.DataFrame,
    spike_group: pd.DataFrame,
) -> int:
    """Score potential for headline-worthy or surprising filing activity."""
    score = 0
    if forms_recent.count("8-K") >= 1:
        score += 25
    if forms_recent.count("8-K") >= 3:
        score += 20
    if financing_recent:
        score += 20
    if len(spike_group) >= 3:
        score += 25
    if not recent_group.empty and recent_group["is_high_signal"].fillna(False).sum() >= 3:
        score += 10
    return min(100, score)


def score_filing_activity(recent_group: pd.DataFrame, spike_group: pd.DataFrame, full_group: pd.DataFrame) -> int:
    """Score sudden filing activity versus available metadata history."""
    recent_count = len(recent_group)
    spike_count = len(spike_group)
    baseline_count = max(1, len(full_group))
    score = min(60, recent_count * 8) + min(40, spike_count * 15)
    if spike_count >= 3 and recent_count / baseline_count >= 0.2:
        score += 15
    return min(100, score)


def build_signal_interpretation(
    dilution_score: int,
    survival_score: int,
    catalyst_label: str,
    narrative_score: int,
    activity_score: int,
    eightk_recent: int,
    financing_recent_count: int,
    financing_watch_count: int = 0,
) -> str:
    """Create a concise human-readable explanation for the metadata signal."""
    parts = []
    if dilution_score >= 70:
        parts.append("High metadata-based dilution pressure.")
    elif dilution_score >= 35:
        parts.append("Moderate dilution pressure.")
    if survival_score >= 70:
        parts.append("Survival risk proxy is elevated.")
    if eightk_recent:
        parts.append(f"{eightk_recent} recent 8-K filing(s); catalyst label: {catalyst_label}.")
    if financing_recent_count:
        parts.append(f"{financing_recent_count} recent financing/prospectus filing(s).")
    elif financing_watch_count:
        parts.append(f"{financing_watch_count} financing/prospectus filing(s) inside the broader dilution lookback window.")
    if narrative_score >= 60 or activity_score >= 60:
        parts.append("Recent filing pattern may deserve headline/narrative review.")
    return " ".join(parts) if parts else "No strong metadata-only SEC signal detected."


def classify_activity(recent_group: pd.DataFrame) -> str:
    """Classify recent SEC activity into a simple research flag."""
    if recent_group.empty:
        return "quiet"
    forms = set(recent_group["filing_type"].dropna().astype(str))
    if any(form in forms for form in ["S-1", "S-3"]) or any(form.startswith("424B") for form in forms):
        return "financing_or_registration_activity"
    if "8-K" in forms:
        return "recent_event_activity"
    if "10-K" in forms or "10-Q" in forms:
        return "recent_periodic_reporting"
    return "recent_other_activity"


def is_high_signal_form(form: str, high_signal_forms: set[str]) -> bool:
    """Return True if a filing form is one of the configured high-signal types."""
    form_text = str(form or "").upper()
    base_form = form_text.replace("/A", "")
    return form_text in high_signal_forms or base_form in high_signal_forms or form_text.startswith("424B")


def build_filing_url(cik: str, accession: str | None, primary_doc: str | None) -> str | None:
    """Build an SEC Archives URL for a primary filing document."""
    if not accession or not primary_doc:
        return None
    cik_no_zeros = str(int(cik))
    accession_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_clean}/{primary_doc}"


def _get_json(url: str, config: dict[str, Any]) -> dict[str, Any]:
    """Fetch JSON from SEC with configured timeout and user agent."""
    if requests is None:
        raise RuntimeError("requests is required for SEC network calls")
    sec_config = config["sec"]
    user_agent = os.getenv(sec_config["user_agent_env"], sec_config["default_user_agent"])
    response = requests.get(
        url,
        timeout=config["refresh"]["request_timeout_seconds"],
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
    )
    response.raise_for_status()
    return response.json()


def _safe_list_get(values: list[Any], index: int) -> Any:
    """Return a list item or None when SEC arrays have mismatched lengths."""
    return values[index] if index < len(values) else None


def _load_universe(config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Load the processed universe CSV if available."""
    path = project_path(config["paths"]["universe_output"])
    if not path.exists():
        logger.warning("Universe file does not exist yet: %s", path)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        logger.warning("Could not read universe file %s: %s", path, exc)
        return pd.DataFrame()


def _save_outputs(
    filings: pd.DataFrame,
    flags: pd.DataFrame,
    signals: pd.DataFrame,
    config: dict[str, Any],
    logger: logging.Logger,
) -> None:
    """Save SEC metadata outputs as structured CSV files."""
    filings_path = project_path(config["paths"]["sec_filings_output"])
    flags_path = project_path(config["paths"]["sec_flags_output"])
    signals_path = project_path(config["paths"]["sec_signals_output"])
    filings_path.parent.mkdir(parents=True, exist_ok=True)
    filings.to_csv(filings_path, index=False)
    flags.to_csv(flags_path, index=False)
    signals.to_csv(signals_path, index=False)
    logger.info("SEC filing metadata saved to %s with %s rows", filings_path, len(filings))
    logger.info("SEC filing flags saved to %s with %s rows", flags_path, len(flags))
    logger.info("SEC filing signals saved to %s with %s rows", signals_path, len(signals))


def _empty_outputs(config: dict[str, Any], logger: logging.Logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write empty SEC output files so downstream stages have stable inputs."""
    filings = pd.DataFrame(columns=FILING_COLUMNS)
    flags = pd.DataFrame(columns=FLAG_COLUMNS)
    signals = pd.DataFrame(columns=SIGNAL_COLUMNS)
    _save_outputs(filings, flags, signals, config, logger)
    return filings, flags


def _existing_or_empty_outputs(config: dict[str, Any], logger: logging.Logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep existing SEC outputs on noncritical refresh failures when possible."""
    filings_path = project_path(config["paths"]["sec_filings_output"])
    flags_path = project_path(config["paths"]["sec_flags_output"])
    signals_path = project_path(config["paths"]["sec_signals_output"])
    if filings_path.exists() and flags_path.exists():
        try:
            filings = pd.read_csv(filings_path)
            flags = pd.read_csv(flags_path)
            if not signals_path.exists():
                signals = interpret_filing_signals(filings, flags, config)
                signals_path.parent.mkdir(parents=True, exist_ok=True)
                signals.to_csv(signals_path, index=False)
            logger.info("Using existing SEC outputs after noncritical SEC refresh issue")
            record_source_status(
                config,
                "sec",
                "existing_sec_outputs",
                "reused_cache",
                rows=len(flags),
                fallback_used=True,
                detail="SEC provider unavailable or skipped; reused existing SEC files.",
            )
            return filings, flags
        except (OSError, pd.errors.ParserError) as exc:
            logger.warning("Existing SEC outputs could not be reused: %s", exc)
    return _empty_outputs(config, logger)


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run SEC filing metadata collection independently."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    return build_sec_filings(config, logger)


def interpret_existing_sec_outputs(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Regenerate SEC filing signals from existing metadata CSVs without fetching."""
    config = config or load_config()
    logger = logger or configure_logging(config["paths"].get("log_file"))
    filings_path = project_path(config["paths"]["sec_filings_output"])
    flags_path = project_path(config["paths"]["sec_flags_output"])
    try:
        filings = pd.read_csv(filings_path) if filings_path.exists() else pd.DataFrame(columns=FILING_COLUMNS)
        flags = pd.read_csv(flags_path) if flags_path.exists() else pd.DataFrame(columns=FLAG_COLUMNS)
    except (OSError, pd.errors.ParserError) as exc:
        logger.warning("Could not read existing SEC outputs for interpretation: %s", exc)
        filings = pd.DataFrame(columns=FILING_COLUMNS)
        flags = pd.DataFrame(columns=FLAG_COLUMNS)
    signals = interpret_filing_signals(filings, flags, config)
    signals_path = project_path(config["paths"]["sec_signals_output"])
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(signals_path, index=False)
    logger.info("SEC filing signals regenerated from existing metadata at %s", signals_path)
    return signals


def main() -> None:
    """Run this module independently from the command line."""
    parser = argparse.ArgumentParser(description="Fetch lightweight SEC filing metadata.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    parser.add_argument(
        "--interpret-only",
        action="store_true",
        help="Use existing SEC metadata CSVs and do not fetch any SEC data.",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    if args.interpret_only:
        signals = interpret_existing_sec_outputs(config, logger)
        print(f"SEC signals: {len(signals)} rows")
        return
    filings, flags = build_sec_filings(config, logger)
    print(f"SEC filings: {len(filings)} rows")
    print(f"SEC flags: {len(flags)} rows")


if __name__ == "__main__":
    main()
