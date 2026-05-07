"""Lightweight accounting fundamentals extraction from SEC Companyfacts.

This module avoids full filing-document parsing, but it does pull real
structured accounting facts where available. The output feeds finance ratios
used by the movement score.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

from utils.cache import read_json_cache, write_json_cache
from utils.helpers import safe_divide, to_float
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path
from utils.source_status import record_source_status


FUNDAMENTAL_COLUMNS = [
    "ticker",
    "cik",
    "company_name",
    "period_end",
    "cash",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "revenue",
    "operating_cash_flow",
    "net_income",
    "shares_outstanding",
    "cash_to_market_cap",
    "current_ratio",
    "liabilities_to_assets",
    "revenue_to_market_cap",
    "operating_cash_flow_to_assets",
    "return_on_assets",
    "source_filing_url",
    "extraction_status",
]


FACT_ALIASES = {
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "Cash",
    ],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "net_income": ["NetIncomeLoss"],
    "shares_outstanding": [
        "EntityCommonStockSharesOutstanding",
        "CommonStocksIncludingAdditionalPaidInCapitalMember",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
}


def build_fundamentals_stub(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Backward-compatible entrypoint for the pipeline."""
    return build_fundamentals(config, logger)


def build_fundamentals(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Build real lightweight fundamentals from SEC Companyfacts when possible."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))

    sec_flags = _load_sec_flags(config, logger)
    if sec_flags.empty:
        return save_fundamentals(pd.DataFrame(columns=FUNDAMENTAL_COLUMNS), config, logger)

    max_tickers = int(config.get("fundamentals", {}).get("max_tickers_per_run", len(sec_flags)))
    sec_flags = sec_flags.head(max_tickers).copy()
    universe = _load_universe(config)

    rows: list[dict[str, Any]] = []
    total = len(sec_flags)
    for index, (_, row) in enumerate(sec_flags.iterrows(), start=1):
        if index == 1 or index % 10 == 0 or index == total:
            print(f"      Fundamentals: {index}/{total} tickers checked", flush=True)
        ticker = str(row.get("ticker", "")).upper().strip()
        cik = str(row.get("cik", "")).zfill(10)
        if not ticker or not cik:
            continue
        try:
            payload = fetch_companyfacts(cik, config, logger)
            fundamentals = parse_companyfacts(ticker, cik, row.get("company_name"), payload)
        except Exception as exc:
            logger.debug("Fundamentals skipped for %s after provider error: %s", ticker, exc)
            fundamentals = empty_fundamental_row(ticker, cik, row.get("company_name"), "companyfacts_unavailable")
        market_cap = lookup_market_cap(universe, ticker)
        rows.append(add_fundamental_ratios(fundamentals, market_cap))

    frame = pd.DataFrame(rows, columns=FUNDAMENTAL_COLUMNS)
    return save_fundamentals(frame, config, logger)


def fetch_companyfacts(cik: str, config: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    """Fetch or load cached SEC Companyfacts for one CIK."""
    cache_dir = config["paths"]["cache_dir"]
    cache_key = f"sec_companyfacts_{cik}"
    cached = read_json_cache(cache_dir, cache_key, config["refresh"]["cache_ttl_hours"])
    if cached:
        return cached
    if requests is None:
        stale = read_json_cache(cache_dir, cache_key, 10_000_000)
        if stale:
            return stale
        raise RuntimeError("requests is required for Companyfacts fetch")

    url = config["sec"].get("companyfacts_url", "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").format(cik=cik)
    try:
        payload = _get_json(url, config)
    except Exception:
        stale = read_json_cache(cache_dir, cache_key, 10_000_000)
        if stale:
            logger.debug("Using stale SEC Companyfacts cache for CIK %s after provider error", cik)
            return stale
        raise
    write_json_cache(cache_dir, cache_key, payload)
    logger.debug("Cached SEC Companyfacts for CIK %s", cik)
    return payload


def parse_companyfacts(ticker: str, cik: str, company_name: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the latest available accounting fields from Companyfacts."""
    facts = payload.get("facts", {}).get("us-gaap", {})
    extracted: dict[str, Any] = empty_fundamental_row(
        ticker,
        cik,
        company_name or payload.get("entityName"),
        "companyfacts_partial",
    )
    periods: list[str] = []
    for output_name, aliases in FACT_ALIASES.items():
        value, end, accession = latest_fact_value(facts, aliases)
        extracted[output_name] = value
        if end:
            periods.append(str(end))
        if accession and not extracted.get("source_filing_url"):
            extracted["source_filing_url"] = build_sec_index_url(cik, accession)
    if periods:
        extracted["period_end"] = max(periods)
    found_count = sum(1 for key in FACT_ALIASES if extracted.get(key) is not None)
    extracted["extraction_status"] = "companyfacts_ok" if found_count >= 4 else "companyfacts_sparse"
    return extracted


def latest_fact_value(facts: dict[str, Any], aliases: list[str]) -> tuple[float | None, str | None, str | None]:
    """Return the latest numeric fact from any acceptable taxonomy alias."""
    candidates: list[dict[str, Any]] = []
    for alias in aliases:
        fact = facts.get(alias, {})
        for units in fact.get("units", {}).values():
            for item in units:
                value = to_float(item.get("val"))
                end = item.get("end")
                if value is None or not end:
                    continue
                form = str(item.get("form") or "")
                candidates.append(
                    {
                        "value": value,
                        "end": str(end),
                        "filed": str(item.get("filed") or ""),
                        "accn": item.get("accn"),
                        "form": form,
                    }
                )
    if not candidates:
        return None, None, None
    candidates.sort(key=lambda item: (item["end"], item["filed"]), reverse=True)
    latest = candidates[0]
    return latest["value"], latest["end"], latest.get("accn")


def add_fundamental_ratios(row: dict[str, Any], market_cap: float | None) -> dict[str, Any]:
    """Add finance/accounting ratios used by scoring."""
    total_assets = to_float(row.get("total_assets"))
    total_liabilities = to_float(row.get("total_liabilities"))
    current_assets = to_float(row.get("current_assets"))
    current_liabilities = to_float(row.get("current_liabilities"))
    row["cash_to_market_cap"] = safe_divide(to_float(row.get("cash")), market_cap)
    row["current_ratio"] = safe_divide(current_assets, current_liabilities)
    row["liabilities_to_assets"] = safe_divide(total_liabilities, total_assets)
    row["revenue_to_market_cap"] = safe_divide(to_float(row.get("revenue")), market_cap)
    row["operating_cash_flow_to_assets"] = safe_divide(to_float(row.get("operating_cash_flow")), total_assets)
    row["return_on_assets"] = safe_divide(to_float(row.get("net_income")), total_assets)
    return row


def lookup_market_cap(universe: pd.DataFrame, ticker: str) -> float | None:
    """Find market cap from the processed universe."""
    if universe.empty or "ticker" not in universe.columns:
        return None
    match = universe[universe["ticker"].astype(str).str.upper() == ticker]
    if match.empty:
        return None
    return to_float(match.iloc[0].get("market_cap"))


def empty_fundamental_row(ticker: str, cik: str, company_name: Any, status: str) -> dict[str, Any]:
    """Create a stable fundamentals row."""
    row = {column: None for column in FUNDAMENTAL_COLUMNS}
    row["ticker"] = ticker
    row["cik"] = cik
    row["company_name"] = company_name
    row["extraction_status"] = status
    return row


def build_sec_index_url(cik: str, accession: str | None) -> str | None:
    """Build an SEC filing index URL from a Companyfacts accession number."""
    if not accession:
        return None
    cik_no_zeros = str(int(cik))
    accession_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_clean}/"


def _get_json(url: str, config: dict[str, Any]) -> dict[str, Any]:
    """Fetch JSON with SEC user-agent rules."""
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


def _load_sec_flags(config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Load ticker-level SEC flags if the SEC stage has produced them."""
    path = project_path(config["paths"]["sec_flags_output"])
    if not path.exists():
        logger.info("SEC flags not found yet; writing empty fundamentals output")
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        logger.warning("Could not read SEC flags %s: %s", path, exc)
        return pd.DataFrame()


def _load_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Load universe data for market-cap denominators."""
    path = project_path(config["paths"]["universe_output"])
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


def save_fundamentals(frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Save fundamentals output."""
    output_path = project_path(config["paths"]["fundamentals_output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for column in FUNDAMENTAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame = frame[FUNDAMENTAL_COLUMNS]
    frame.to_csv(output_path, index=False)
    logger.info("Fundamentals saved to %s with %s rows", output_path, len(frame))
    status_counts = frame["extraction_status"].fillna("unknown").astype(str).value_counts().to_dict() if "extraction_status" in frame.columns else {}
    ok_rows = sum(count for status, count in status_counts.items() if status in {"companyfacts_ok", "companyfacts_partial", "companyfacts_sparse"})
    record_source_status(
        config,
        "fundamentals",
        "sec_companyfacts",
        "ok" if ok_rows else "degraded",
        rows=len(frame),
        fallback_used=bool(status_counts.get("companyfacts_unavailable")),
        detail=", ".join(f"{key}={value}" for key, value in sorted(status_counts.items())),
    )
    return frame


def extract_fundamentals_from_xbrl(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Future hook for full filing-document XBRL extraction."""
    raise NotImplementedError("Full filing-document XBRL extraction is planned for a later stage.")


def normalize_fundamentals_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Future hook for provider-agnostic fundamentals normalization."""
    raise NotImplementedError("Fundamentals normalization is planned for a later stage.")


def run() -> pd.DataFrame:
    """Run fundamentals extraction independently."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    return build_fundamentals(config, logger)


def main() -> None:
    """Run this module independently from the command line."""
    parser = argparse.ArgumentParser(description="Extract lightweight SEC Companyfacts fundamentals.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    frame = build_fundamentals(config, logger)
    print(f"Fundamentals: {len(frame)} rows")


if __name__ == "__main__":
    main()
