"""Universe Builder for penny-stock and microcap research candidates.

The module creates a starting US equity universe and writes:
data/processed/universe.csv

It intentionally flags illiquidity instead of deleting illiquid tickers because
extreme asymmetry often lives where liquidity is ugly. Source functions are
small and swappable so the engine is not locked to one data provider.
"""

from __future__ import annotations

import argparse
import io
import logging
from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd
try:
    import requests
except ImportError:
    requests = None

from utils.cache import read_json_cache, write_json_cache
from utils.helpers import coalesce, safe_divide, to_float
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path
from utils.source_status import record_source_status


UNIVERSE_COLUMNS = [
    "ticker",
    "company_name",
    "price",
    "market_cap",
    "volume",
    "avg_volume",
    "dollar_volume",
    "exchange",
    "sector",
    "industry",
    "float",
    "is_illiquid",
    "universe_reason",
]


@dataclass
class UniverseSourceResult:
    """Container for source output and diagnostics."""

    frame: pd.DataFrame
    source_name: str
    errors: list[str]


def build_universe(config: dict[str, Any] | None = None, logger: logging.Logger | None = None) -> pd.DataFrame:
    """Build, filter, flag, and save the penny/microcap universe."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))
    logger.info("Building starting universe")

    seed_frame = load_seed_universe(config, logger)
    source_frame = add_broad_public_universe(seed_frame, config, logger)
    normalized_source = normalize_universe(source_frame)
    prefiltered = apply_universe_filters(normalized_source, config, logger)
    enriched_frame = enrich_quotes(prefiltered, config, logger)
    normalized = normalize_universe(enriched_frame)
    filtered = apply_universe_filters(normalized, config, logger)
    flagged = flag_illiquidity(filtered, config)
    final_frame = flagged[UNIVERSE_COLUMNS].sort_values(
        by=["is_illiquid", "market_cap", "dollar_volume"],
        ascending=[True, True, False],
        na_position="last",
    )

    output_path = project_path(config["paths"]["universe_output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_frame.to_csv(output_path, index=False)
    logger.info("Universe saved to %s with %s rows", output_path, len(final_frame))
    record_source_status(
        config,
        "universe",
        "seed_nasdaq_sec_quote_sources",
        "ok" if len(final_frame) else "degraded",
        rows=len(final_frame),
        fallback_used=bool(final_frame["price"].isna().sum()),
        detail=f"Universe rows={len(final_frame)}; missing price rows={int(final_frame['price'].isna().sum())}.",
    )
    return final_frame


def add_broad_public_universe(
    seed_frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger
) -> pd.DataFrame:
    """Append broad public screener rows when enabled, preserving seed candidates."""
    if not config["refresh"].get("use_network", True) or not config["universe"].get("use_nasdaq_screener", True):
        return seed_frame
    result = fetch_nasdaq_screener_universe(config, logger)
    if result.frame.empty:
        logger.warning("Broad Nasdaq screener source returned no rows; using seed/config universe only")
        return seed_frame
    combined = pd.concat([seed_frame, result.frame], ignore_index=True, sort=False)
    combined["ticker"] = combined["ticker"].astype(str).str.upper().str.strip()
    combined = combined.drop_duplicates(subset=["ticker"], keep="first")
    logger.info("Universe after broad public screener merge has %s unique tickers", len(combined))
    return combined


def fetch_nasdaq_screener_universe(config: dict[str, Any], logger: logging.Logger) -> UniverseSourceResult:
    """Fetch a broad stock universe from Nasdaq's public screener endpoint."""
    cache_dir = config["paths"]["cache_dir"]
    ttl_hours = config["refresh"]["cache_ttl_hours"]
    cache_key = "nasdaq_screener_" + "_".join(config["universe"].get("nasdaq_exchanges", []))
    cached = read_json_cache(cache_dir, cache_key, ttl_hours)
    if cached:
        return UniverseSourceResult(parse_nasdaq_screener_payloads(cached), "nasdaq_screener_cache", [])

    if requests is None:
        stale = read_json_cache(cache_dir, cache_key, 10_000_000)
        if stale:
            return UniverseSourceResult(parse_nasdaq_screener_payloads(stale), "nasdaq_screener_stale_cache", [])
        message = "requests is not installed; skipping Nasdaq screener source"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "nasdaq_screener", [message])

    payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "Mozilla/5.0",
    }
    for exchange in config["universe"].get("nasdaq_exchanges", ["nasdaq", "nyse", "amex"]):
        try:
            response = requests.get(
                config["universe"]["nasdaq_screener_url"],
                params={"tableonly": "true", "limit": "25", "exchange": exchange, "download": "true"},
                timeout=config["refresh"]["request_timeout_seconds"],
                headers=headers,
            )
            response.raise_for_status()
            payloads.append({"exchange": exchange, "payload": response.json()})
        except (requests.RequestException, ValueError) as exc:
            message = f"Nasdaq screener fetch failed for {exchange}: {exc}"
            logger.warning(message)
            errors.append(message)
    if payloads:
        write_json_cache(cache_dir, cache_key, payloads)
    return UniverseSourceResult(parse_nasdaq_screener_payloads(payloads), "nasdaq_screener", errors)


def parse_nasdaq_screener_payloads(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse Nasdaq screener payloads into universe columns."""
    rows: list[dict[str, Any]] = []
    for wrapped in payloads:
        exchange = str(wrapped.get("exchange", "")).upper()
        payload = wrapped.get("payload", {})
        for item in payload.get("data", {}).get("rows", []) or []:
            ticker = str(item.get("symbol", "")).upper().strip()
            if not ticker:
                continue
            price = parse_market_number(item.get("lastsale"))
            volume = parse_market_number(item.get("volume"))
            market_cap = parse_market_number(item.get("marketCap"))
            rows.append(
                {
                    "ticker": ticker,
                    "company_name": item.get("name"),
                    "price": price,
                    "market_cap": market_cap,
                    "volume": volume,
                    "avg_volume": None,
                    "dollar_volume": price * volume if price is not None and volume is not None else None,
                    "exchange": exchange,
                    "sector": item.get("sector"),
                    "industry": item.get("industry"),
                    "float": None,
                    "universe_reason": "Matched broad public screener and configured penny/microcap filters.",
                }
            )
    return pd.DataFrame(rows)


def parse_market_number(value: Any) -> float | None:
    """Parse public screener number strings such as '$1.23', '1,000', or 'N/A'."""
    if value in (None, "", "N/A", "n/a"):
        return None
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    return to_float(cleaned)


def load_seed_universe(config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Load seed CSV and merge in additional tickers listed in config."""
    seed_path = project_path(config["universe"]["seed_csv"])
    frames: list[pd.DataFrame] = []
    if seed_path.exists():
        try:
            frame = pd.read_csv(seed_path)
            logger.info("Loaded seed universe from %s", seed_path)
            frames.append(frame)
        except (OSError, pd.errors.ParserError) as exc:
            logger.warning("Could not read seed universe %s: %s", seed_path, exc)

    metadata_path = project_path(config["universe"].get("metadata_csv", ""))
    if metadata_path.exists():
        try:
            metadata = pd.read_csv(metadata_path)
            logger.info("Loaded ticker metadata from %s", metadata_path)
            frames.append(metadata)
        except (OSError, pd.errors.ParserError) as exc:
            logger.warning("Could not read ticker metadata %s: %s", metadata_path, exc)

    tickers = config["universe"].get("tickers", [])
    if tickers:
        frames.append(pd.DataFrame({"ticker": tickers, "universe_reason": "Configured ticker candidate."}))
        logger.info("Loaded %s configured tickers", len(tickers))

    if not frames:
        return pd.DataFrame(columns=UNIVERSE_COLUMNS)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["ticker"] = combined["ticker"].astype(str).str.upper().str.strip()
    combined = combined.drop_duplicates(subset=["ticker"], keep="first")
    logger.info("Combined starting universe has %s unique tickers", len(combined))
    return combined


def enrich_quotes(seed_frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Enrich seed rows with public metadata and quote fields when enabled."""
    if not config["refresh"].get("use_network", True):
        logger.info("Network refresh disabled; using seed universe only")
        return seed_frame

    for column in UNIVERSE_COLUMNS:
        if column not in seed_frame.columns:
            seed_frame[column] = None

    enriched = enrich_company_names_from_sec(seed_frame, config, logger)
    missing_quote_mask = enriched["price"].isna()
    tickers = sorted({str(ticker).upper().strip() for ticker in enriched.loc[missing_quote_mask, "ticker"].dropna()})
    if not tickers:
        logger.info("No missing-price tickers require quote enrichment")
        return enriched

    try:
        quote_result = fetch_yahoo_quote_snapshot(tickers, config, logger)
        if not quote_result.frame.empty:
            enriched = merge_enrichment(
                enriched,
                quote_result.frame,
                ["company_name", "price", "market_cap", "volume", "avg_volume", "exchange", "float", "universe_reason"],
            )
        else:
            logger.warning("Yahoo quote enrichment returned no rows")
    except Exception as exc:
        logger.warning("Yahoo quote enrichment failed without blocking universe build: %s", exc)

    missing_price_tickers = enriched[enriched["price"].isna()]["ticker"].dropna().astype(str).tolist()
    if missing_price_tickers:
        max_fallback = config["universe"].get("max_stooq_fallback_tickers", 100)
        if int(max_fallback) <= 0:
            logger.info("Stooq universe fallback disabled; leaving %s missing-price rows for data-quality filters", len(missing_price_tickers))
            return enriched
        fallback_tickers = missing_price_tickers[:max_fallback]
        try:
            stooq_result = fetch_stooq_daily_snapshot(fallback_tickers, config, logger)
            if not stooq_result.frame.empty:
                enriched = merge_enrichment(
                    enriched,
                    stooq_result.frame,
                    ["price", "volume", "dollar_volume", "universe_reason"],
                )
        except Exception as exc:
            logger.warning("Stooq fallback enrichment failed without blocking universe build: %s", exc)

    return enriched


def merge_enrichment(base_frame: pd.DataFrame, enrichment_frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Merge provider columns, preferring existing non-empty values over provider blanks."""
    merged = base_frame.merge(enrichment_frame, how="left", on="ticker", suffixes=("", "_provider"))
    for column in columns:
        provider_column = f"{column}_provider"
        if provider_column in merged.columns:
            merged[column] = merged.apply(lambda row: coalesce(row.get(column), row.get(provider_column)), axis=1)
            merged = merged.drop(columns=[provider_column])
    return merged


def enrich_company_names_from_sec(
    seed_frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger
) -> pd.DataFrame:
    """Fill missing company names from SEC's public ticker directory."""
    directory = fetch_sec_company_directory(config, logger)
    if directory.frame.empty:
        return seed_frame
    return merge_enrichment(seed_frame, directory.frame, ["company_name", "universe_reason"])


def fetch_sec_company_directory(config: dict[str, Any], logger: logging.Logger) -> UniverseSourceResult:
    """Fetch or load SEC's public company ticker directory for name enrichment."""
    cache_dir = config["paths"]["cache_dir"]
    ttl_hours = config["refresh"]["cache_ttl_hours"]
    cache_key = "sec_company_tickers"
    cached = read_json_cache(cache_dir, cache_key, ttl_hours)
    if cached:
        return UniverseSourceResult(parse_sec_company_directory(cached), "sec_company_names_cache", [])
    if requests is None:
        stale = read_json_cache(cache_dir, cache_key, 10_000_000)
        if stale:
            return UniverseSourceResult(parse_sec_company_directory(stale), "sec_company_names_stale_cache", [])
        message = "requests is not installed; skipping SEC company-name enrichment"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=["ticker", "company_name"]), "sec_company_names", [message])

    try:
        response = requests.get(
            config["sec"]["company_tickers_url"],
            timeout=config["refresh"]["request_timeout_seconds"],
            headers={"User-Agent": config["sec"]["default_user_agent"]},
        )
        response.raise_for_status()
        payload = response.json()
        write_json_cache(cache_dir, cache_key, payload)
        return UniverseSourceResult(parse_sec_company_directory(payload), "sec_company_names", [])
    except (requests.RequestException, ValueError) as exc:
        message = f"SEC company-name enrichment failed: {exc}"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=["ticker", "company_name"]), "sec_company_names", [message])


def parse_sec_company_directory(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse SEC ticker directory into ticker and company-name columns."""
    rows = []
    for item in payload.values():
        ticker = str(item.get("ticker", "")).upper().strip()
        title = item.get("title")
        if ticker and title:
            rows.append(
                {
                    "ticker": ticker,
                    "company_name": title,
                    "universe_reason": "Configured candidate; company name filled from SEC directory.",
                }
            )
    return pd.DataFrame(rows)


def fetch_yahoo_quote_snapshot(
    tickers: Iterable[str], config: dict[str, Any], logger: logging.Logger
) -> UniverseSourceResult:
    """Fetch quote data from Yahoo's public quote endpoint.

    This is a no-key public source and should be considered best-effort. The
    function is intentionally isolated so it can be replaced by another provider.
    """
    ticker_list = [ticker for ticker in tickers if ticker]
    if requests is None:
        message = "requests is not installed; skipping network quote enrichment"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "yahoo_quote", [message])

    batch_size = int(config["universe"].get("quote_batch_size", 80))
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    if not config["universe"].get("use_yahoo_quotes", True):
        message = "Yahoo quote enrichment disabled in config"
        logger.info(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "yahoo_quote", [message])

    for start in range(0, len(ticker_list), batch_size):
        batch = ticker_list[start : start + batch_size]
        batch_result = fetch_yahoo_quote_batch(batch, config, logger)
        if not batch_result.frame.empty:
            frames.append(batch_result.frame)
        errors.extend(batch_result.errors)
        if any("access rejected" in error for error in batch_result.errors):
            logger.warning("Yahoo quote source unavailable this run; continuing with other data sources")
            break
    frame = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame(columns=UNIVERSE_COLUMNS)
    return UniverseSourceResult(frame, "yahoo_quote", errors)


def fetch_yahoo_quote_batch(
    tickers: list[str], config: dict[str, Any], logger: logging.Logger
) -> UniverseSourceResult:
    """Fetch one manageable Yahoo quote batch."""
    cache_dir = config["paths"]["cache_dir"]
    ttl_hours = config["refresh"]["cache_ttl_hours"]
    cache_key = "yahoo_quote_" + "_".join(tickers)
    cached = read_json_cache(cache_dir, cache_key, ttl_hours)
    if cached:
        return UniverseSourceResult(parse_yahoo_quote_payload(cached), "yahoo_quote_cache", [])

    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {"symbols": ",".join(tickers)}
    timeout = config["refresh"]["request_timeout_seconds"]
    try:
        response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        payload = response.json()
        write_json_cache(cache_dir, cache_key, payload)
        return UniverseSourceResult(parse_yahoo_quote_payload(payload), "yahoo_quote", [])
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        if status_code in (401, 403):
            message = f"Yahoo quote access rejected ({status_code}) for batch {tickers[0]}..{tickers[-1]}"
        else:
            message = f"Yahoo quote HTTP error ({status_code}) for batch {tickers[0]}..{tickers[-1]}"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "yahoo_quote", [message])
    except (requests.RequestException, ValueError) as exc:
        message = f"Yahoo quote batch failed for {tickers[0]}..{tickers[-1]}: {exc}"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "yahoo_quote", [message])


def fetch_stooq_daily_snapshot(
    tickers: Iterable[str], config: dict[str, Any], logger: logging.Logger
) -> UniverseSourceResult:
    """Fetch latest daily close and volume from Stooq as a secondary free fallback."""
    ticker_list = [ticker for ticker in tickers if ticker]
    if requests is None:
        message = "requests is not installed; skipping Stooq fallback enrichment"
        logger.warning(message)
        return UniverseSourceResult(pd.DataFrame(columns=UNIVERSE_COLUMNS), "stooq_daily", [message])

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    fallback_timeout = min(
        int(config["refresh"]["request_timeout_seconds"]),
        int(config["universe"].get("stooq_fallback_timeout_seconds", 6)),
    )
    for ticker in ticker_list:
        cache_key = f"stooq_daily_{ticker}"
        cached = read_json_cache(config["paths"]["cache_dir"], cache_key, config["refresh"]["cache_ttl_hours"])
        if cached:
            rows.extend(cached)
            continue
        try:
            url = "https://stooq.com/q/d/l/"
            response = requests.get(
                url,
                params={"s": f"{ticker.lower()}.us", "i": "d"},
                timeout=fallback_timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            parsed_rows = parse_stooq_daily_csv(ticker, response.text)
            if parsed_rows:
                write_json_cache(config["paths"]["cache_dir"], cache_key, parsed_rows)
                rows.extend(parsed_rows)
        except requests.RequestException as exc:
            message = f"Stooq fallback failed for {ticker}: {exc}"
            logger.info(message)
            errors.append(message)
    return UniverseSourceResult(pd.DataFrame(rows), "stooq_daily", errors)


def parse_stooq_daily_csv(ticker: str, csv_text: str) -> list[dict[str, Any]]:
    """Parse Stooq daily CSV and return the latest close/volume row."""
    csv_text = csv_text.strip()
    if not looks_like_stooq_csv(csv_text):
        return []
    try:
        frame = pd.read_csv(io.StringIO(csv_text), on_bad_lines="skip")
    except pd.errors.ParserError:
        return []
    if frame.empty or not {"Close", "Volume"}.issubset(frame.columns):
        return []
    latest = frame.tail(1).iloc[0]
    price = to_float(latest.get("Close"))
    volume = to_float(latest.get("Volume"))
    return [
        {
            "ticker": ticker.upper(),
            "price": price,
            "volume": volume,
            "dollar_volume": price * volume if price is not None and volume is not None else None,
            "universe_reason": "Configured candidate; latest price/volume filled from Stooq fallback.",
        }
    ]


def looks_like_stooq_csv(csv_text: str) -> bool:
    """Return True when Stooq returned the daily CSV shape we expect."""
    if not csv_text or "No data" in csv_text:
        return False
    first_line = csv_text.splitlines()[0].strip()
    required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
    return required_columns.issubset(set(first_line.split(",")))


def parse_yahoo_quote_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse Yahoo quote JSON into normalized universe-like columns."""
    rows: list[dict[str, Any]] = []
    results = payload.get("quoteResponse", {}).get("result", [])
    for item in results:
        price = to_float(item.get("regularMarketPrice"))
        volume = to_float(item.get("regularMarketVolume"))
        avg_volume = to_float(item.get("averageDailyVolume3Month") or item.get("averageDailyVolume10Day"))
        rows.append(
            {
                "ticker": str(item.get("symbol", "")).upper(),
                "company_name": item.get("longName") or item.get("shortName"),
                "price": price,
                "market_cap": to_float(item.get("marketCap")),
                "volume": volume,
                "avg_volume": avg_volume,
                "dollar_volume": safe_divide(price * volume, 1) if price is not None and volume is not None else None,
                "exchange": item.get("fullExchangeName") or item.get("exchange"),
                "sector": item.get("sector"),
                "industry": item.get("industry"),
                "float": to_float(item.get("floatShares")),
                "universe_reason": "Public quote snapshot matched configured penny/microcap filters.",
            }
        )
    return pd.DataFrame(rows)


def normalize_universe(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns, types, and calculated dollar volume."""
    normalized = frame.copy()
    for column in UNIVERSE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized["ticker"] = normalized["ticker"].astype(str).str.upper().str.strip()

    numeric_columns = ["price", "market_cap", "volume", "avg_volume", "dollar_volume", "float"]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    missing_dollar_volume = normalized["dollar_volume"].isna()
    normalized.loc[missing_dollar_volume, "dollar_volume"] = (
        normalized.loc[missing_dollar_volume, "price"] * normalized.loc[missing_dollar_volume, "volume"]
    )
    normalized["universe_reason"] = normalized["universe_reason"].fillna("Seed universe candidate.")
    return normalized


def apply_universe_filters(frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Apply hard universe filters while preserving illiquidity for flagging."""
    filters = config["universe"]["filters"]
    output = frame.copy()

    before = len(output)
    output = output[(output["price"].isna()) | (output["price"] <= filters["max_price"])]
    output = output[(output["market_cap"].isna()) | (output["market_cap"] <= filters["max_market_cap"])]
    if not filters.get("include_otc", False):
        exchange_text = output["exchange"].fillna("").str.lower()
        output = output[~exchange_text.str.contains("otc|pink|expert", regex=True)]
    logger.info("Applied hard price/market-cap/exchange filters: %s -> %s rows", before, len(output))
    return output


def flag_illiquidity(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Flag tickers below liquidity thresholds without automatically deleting them."""
    rules = config["universe"]["illiquidity"]
    output = frame.copy()
    low_avg_volume = output["avg_volume"].fillna(0) < rules["flag_below_avg_volume"]
    low_dollar_volume = output["dollar_volume"].fillna(0) < rules["flag_below_dollar_volume"]
    output["is_illiquid"] = low_avg_volume | low_dollar_volume
    return output


def main() -> None:
    """Command-line entrypoint for running only the Universe Builder."""
    parser = argparse.ArgumentParser(description="Build the starting penny/microcap equity universe.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    frame = build_universe(config, logger)
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
