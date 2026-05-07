"""Historical price and volume feature collection.

This module adds cached 5/20/60-day movement and relative-volume features used
mainly by the Hume flow layer. It is deliberately best-effort: failure should
not block the research pipeline.
"""

from __future__ import annotations

import argparse
import io
import logging
from collections import Counter
from datetime import datetime, timezone
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


FEATURE_COLUMNS = [
    "ticker",
    "history_rows",
    "history_start_date",
    "history_end_date",
    "public_age_years_proxy",
    "all_time_high",
    "all_time_drawdown",
    "return_5d",
    "return_20d",
    "return_60d",
    "avg_volume_20d",
    "avg_volume_60d",
    "relative_volume_20d",
    "relative_volume_60d",
    "dollar_volume_acceleration",
    "volume_to_float",
    "breakout_distance_60d",
    "breakout_proximity_score",
    "compression_5d_range",
    "compression_5d_score",
    "near_52w_low_score",
    "drawdown_60d",
    "explosive_behavior_score",
    "recent_dynamism_score",
    "price_history_status",
    "price_history_source",
]


def build_price_history_features(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    universe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build cached historical price/volume features for universe tickers."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))

    if not config.get("prices", {}).get("enabled", True):
        return save_features(pd.DataFrame(columns=FEATURE_COLUMNS), config, logger)

    universe = universe if universe is not None else read_universe(config)
    if universe.empty or "ticker" not in universe.columns:
        logger.warning("No universe available for price-history features")
        return existing_or_empty_features(config, logger)

    if "ten_bagger_prescreen_score" in universe.columns:
        tickers = universe["ticker"].dropna().astype(str).str.upper().drop_duplicates().tolist()
    else:
        tickers = prioritize_history_tickers(universe, config, logger)
    max_tickers = int(config["prices"].get("max_tickers_per_run", 300))
    tickers = tickers[:max_tickers]
    logger.info("Selected %s tickers for price-history refresh", len(tickers))

    if requests is None:
        logger.warning("requests is not installed; keeping existing price-history features if available")
        return existing_or_empty_features(config, logger)

    rows = []
    failed_count = 0
    source_counts: Counter[str] = Counter()
    total_tickers = len(tickers)
    for index, ticker in enumerate(tickers, start=1):
        if index == 1 or index % 10 == 0 or index == total_tickers:
            print(f"      Price history: {index}/{total_tickers} tickers checked", flush=True)
        try:
            history, source = fetch_price_history_with_source(ticker, config)
            float_shares = lookup_float_shares(universe, ticker)
            rows.append(compute_history_features(ticker, history, config, float_shares, source))
            source_counts[source] += 1
        except Exception as exc:
            failed_count += 1
            logger.debug("Price-history feature build failed for %s: %s", ticker, exc)
            rows.append(empty_feature_row(ticker, "fetch_or_parse_failed"))
            source_counts["failed"] += 1

    if failed_count:
        logger.info("Price-history skipped %s tickers because the provider returned unusable data", failed_count)
    record_source_status(
        config,
        "prices",
        "history_provider_mix",
        "ok" if source_counts.get("ok") or any(key not in {"no_history", "failed"} for key in source_counts) else "degraded",
        rows=sum(source_counts.values()),
        fallback_used=bool(source_counts.get("stooq")),
        detail=", ".join(f"{key}={value}" for key, value in sorted(source_counts.items())),
    )

    return save_features(pd.DataFrame(rows, columns=FEATURE_COLUMNS), config, logger)


def prioritize_history_tickers(
    universe: pd.DataFrame,
    config: dict[str, Any],
    logger: logging.Logger,
) -> list[str]:
    """Rank tickers so limited history-refresh slots go to higher-value candidates."""
    frame = universe.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame = frame.drop_duplicates(subset=["ticker"], keep="first")

    prior_scores_path = project_path(config["paths"].get("theory_scores_output", ""))
    if prior_scores_path.exists():
        try:
            prior_scores = pd.read_csv(prior_scores_path)
            keep_columns = [
                column
                for column in [
                    "ticker",
                    "repricing_sequence_score",
                    "asymmetry_score",
                    "relative_mispricing_score",
                    "data_confidence_score",
                ]
                if column in prior_scores.columns
            ]
            if "ticker" in keep_columns:
                prior_scores["ticker"] = prior_scores["ticker"].astype(str).str.upper().str.strip()
                frame = frame.merge(prior_scores[keep_columns], how="left", on="ticker")
        except (OSError, pd.errors.ParserError) as exc:
            logger.debug("Could not use prior theory scores for history prioritization: %s", exc)

    frame["history_priority_score"] = frame.apply(lambda row: compute_history_priority(row, config), axis=1)
    return (
        frame.sort_values("history_priority_score", ascending=False, na_position="last")["ticker"]
        .dropna()
        .astype(str)
        .tolist()
    )


def compute_history_priority(row: pd.Series, config: dict[str, Any]) -> float:
    """Score which tickers deserve scarce historical-price refresh slots first."""
    score = 0.0
    configured_tickers = {str(ticker).upper() for ticker in config["universe"].get("tickers", [])}
    ticker = str(row.get("ticker") or "").upper()
    if ticker in configured_tickers:
        score += 30

    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    volume = to_float(row.get("volume"))
    avg_volume = to_float(row.get("avg_volume"))

    if pd.notna(row.get("company_name")):
        score += 4
    if pd.notna(row.get("sector")):
        score += 4
    if pd.notna(row.get("industry")):
        score += 4
    if price is not None:
        score += 8
        if price < 1:
            score += 14
        elif price < 5:
            score += 8
    if market_cap is not None:
        score += 8
        if market_cap < config["scoring"]["thresholds"]["very_low_market_cap"]:
            score += 14
        elif market_cap < config["scoring"]["thresholds"]["small_market_cap"]:
            score += 8
    if dollar_volume is not None:
        score += 8
        if dollar_volume >= config["scoring"]["thresholds"]["low_dollar_volume"]:
            score += 12
    elif volume is not None:
        score += 4
    if avg_volume is not None:
        score += 6

    text = " ".join(
        str(row.get(column) or "")
        for column in ["company_name", "sector", "industry", "universe_reason"]
    ).lower()
    if any(term.lower() in text for term in config["scoring"].get("narrative_terms", [])):
        score += 10
    if any(term.lower() in text for term in config["scoring"].get("constraint_terms", [])):
        score += 8

    score += (to_float(row.get("repricing_sequence_score")) or 0) * 0.35
    score += (to_float(row.get("asymmetry_score")) or 0) * 0.20
    score += (to_float(row.get("relative_mispricing_score")) or 0) * 0.15
    score += (to_float(row.get("data_confidence_score")) or 0) * 0.10
    return float(score)


def fetch_price_history(ticker: str, config: dict[str, Any]) -> pd.DataFrame:
    """Fetch or load daily history, trying multiple free sources."""
    history, _source = fetch_price_history_with_source(ticker, config)
    return history


def fetch_price_history_with_source(ticker: str, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    """Fetch or load daily history and return the provider used."""
    price_config = config.get("prices", {})
    providers = [price_config.get("provider", "stooq")]
    providers.extend(price_config.get("fallback_providers", ["yahoo_chart"]))
    seen = set()
    for provider in providers:
        provider_name = str(provider or "").lower().strip()
        if not provider_name or provider_name in seen:
            continue
        seen.add(provider_name)
        if provider_name == "stooq":
            history = fetch_stooq_history(ticker, config)
        elif provider_name == "yahoo_chart":
            history = fetch_yahoo_chart_history(ticker, config)
        else:
            continue
        if not history.empty:
            return history, provider_name
    return pd.DataFrame(), "no_history"


def fetch_stooq_history(ticker: str, config: dict[str, Any]) -> pd.DataFrame:
    """Fetch or load cached daily history from Stooq."""
    cache_key = f"stooq_history_{ticker}"
    unavailable_key = f"stooq_history_unavailable_{ticker}"
    if read_json_cache(config["paths"]["cache_dir"], unavailable_key, config["refresh"]["cache_ttl_hours"]):
        return pd.DataFrame()
    cached = read_json_cache(config["paths"]["cache_dir"], cache_key, config["refresh"]["cache_ttl_hours"])
    if cached:
        return pd.DataFrame(cached)
    if requests is None:
        return pd.DataFrame()

    timeout = min(
        int(config["refresh"]["request_timeout_seconds"]),
        int(config["prices"].get("history_timeout_seconds", 6)),
    )
    try:
        response = requests.get(
            "https://stooq.com/q/d/l/",
            params={"s": f"{ticker.lower()}.us", "i": "d"},
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
    except requests.RequestException:
        # Do not cache transient network/provider failures as "unavailable".
        # A temporary timeout should get another chance on the next refresh.
        return pd.DataFrame()
    csv_text = response.text.strip()
    if not looks_like_stooq_csv(csv_text):
        write_json_cache(config["paths"]["cache_dir"], unavailable_key, {"status": "invalid_or_empty_csv"})
        return pd.DataFrame()
    try:
        frame = pd.read_csv(io.StringIO(csv_text), on_bad_lines="skip")
    except pd.errors.ParserError:
        write_json_cache(config["paths"]["cache_dir"], unavailable_key, {"status": "parse_failed"})
        return pd.DataFrame()
    if frame.empty or not {"Close", "Volume"}.issubset(frame.columns):
        write_json_cache(config["paths"]["cache_dir"], unavailable_key, {"status": "missing_required_columns"})
        return pd.DataFrame()
    write_json_cache(config["paths"]["cache_dir"], cache_key, frame.to_dict(orient="records"))
    return frame


def fetch_yahoo_chart_history(ticker: str, config: dict[str, Any]) -> pd.DataFrame:
    """Fetch or load cached daily history from Yahoo's chart endpoint."""
    cache_key = f"yahoo_chart_history_{ticker}"
    unavailable_key = f"yahoo_chart_history_unavailable_{ticker}"
    if read_json_cache(config["paths"]["cache_dir"], unavailable_key, config["refresh"]["cache_ttl_hours"]):
        return pd.DataFrame()
    cached = read_json_cache(config["paths"]["cache_dir"], cache_key, config["refresh"]["cache_ttl_hours"])
    if cached:
        return pd.DataFrame(cached)
    if requests is None:
        return pd.DataFrame()
    timeout = min(
        int(config["refresh"]["request_timeout_seconds"]),
        int(config["prices"].get("history_timeout_seconds", 6)),
    )
    try:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={
                "range": config["prices"].get("yahoo_history_range", "max"),
                "interval": "1d",
                "includePrePost": "false",
                "events": "history",
            },
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, KeyError):
        # Do not cache transient network/provider failures as "unavailable".
        # Invalid/no-data responses are cached below after parsing.
        return pd.DataFrame()
    try:
        result = payload["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result["indicators"]["quote"][0]
        frame = pd.DataFrame(
            {
                "Date": [datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() for ts in timestamps],
                "Open": quote.get("open", []),
                "High": quote.get("high", []),
                "Low": quote.get("low", []),
                "Close": quote.get("close", []),
                "Volume": quote.get("volume", []),
            }
        )
    except (KeyError, IndexError, TypeError, ValueError):
        write_json_cache(config["paths"]["cache_dir"], unavailable_key, {"status": "parse_failed"})
        return pd.DataFrame()
    frame = frame.dropna(subset=["Close"])
    if frame.empty or not {"Close", "Volume"}.issubset(frame.columns):
        write_json_cache(config["paths"]["cache_dir"], unavailable_key, {"status": "missing_required_columns"})
        return pd.DataFrame()
    write_json_cache(config["paths"]["cache_dir"], cache_key, frame.to_dict(orient="records"))
    return frame


def looks_like_stooq_csv(csv_text: str) -> bool:
    """Return True when Stooq returned the daily CSV shape we expect."""
    if not csv_text or "No data" in csv_text:
        return False
    first_line = csv_text.splitlines()[0].strip()
    required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
    return required_columns.issubset(set(first_line.split(",")))


def compute_history_features(
    ticker: str,
    history: pd.DataFrame,
    config: dict[str, Any],
    float_shares: float | None = None,
    source: str = "",
) -> dict[str, Any]:
    """Compute Hume-oriented history features from daily OHLCV rows."""
    if history.empty:
        return empty_feature_row(ticker, "no_history", source or "no_history")

    frame = history.copy()
    if "Date" in frame.columns:
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in ["Close", "High", "Low", "Volume"]:
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    full_frame = frame.dropna(subset=["Close"]).copy()
    min_rows = int(config["prices"].get("min_rows_for_features", 30))
    if len(full_frame) < min_rows:
        return empty_feature_row(ticker, "insufficient_history", source)

    full_close = full_frame["Close"]
    start_date = full_frame["Date"].dropna().iloc[0] if "Date" in full_frame.columns and not full_frame["Date"].dropna().empty else None
    end_date = full_frame["Date"].dropna().iloc[-1] if "Date" in full_frame.columns and not full_frame["Date"].dropna().empty else None
    public_age_years = safe_divide((end_date - start_date).days, 365.25) if start_date is not None and end_date is not None else None
    all_time_high = float(full_close.max())
    frame = full_frame.tail(int(config["prices"].get("history_days", 260)))
    close = frame["Close"]
    volume = frame["Volume"].fillna(0)
    latest_close = float(close.iloc[-1])
    latest_volume = float(volume.iloc[-1])
    all_time_drawdown = safe_divide(latest_close - all_time_high, all_time_high)
    avg_20 = float(volume.tail(20).mean()) if len(volume) >= 20 else None
    avg_60 = float(volume.tail(60).mean()) if len(volume) >= 60 else None
    dollar_recent = float((close.tail(5) * volume.tail(5)).mean()) if len(frame) >= 5 else None
    dollar_prior = float((close.iloc[-25:-5] * volume.iloc[-25:-5]).mean()) if len(frame) >= 25 else None
    high_252 = float(close.tail(252).max())
    low_252 = float(close.tail(252).min())
    high_60 = float(close.tail(60).max()) if len(frame) >= 60 else float(close.max())
    recent_high_60 = float(frame["High"].tail(60).max()) if "High" in frame else high_60
    recent_low_5 = float(frame["Low"].tail(5).min()) if "Low" in frame and len(frame) >= 5 else None
    recent_high_5 = float(frame["High"].tail(5).max()) if "High" in frame and len(frame) >= 5 else None
    range_252 = high_252 - low_252

    low_position = safe_divide(latest_close - low_252, range_252) if range_252 > 0 else 1
    near_low = 100 * (1 - (low_position or 0))
    drawdown_60 = safe_divide(latest_close - high_60, high_60)
    breakout_distance_60d = safe_divide(latest_close - recent_high_60, recent_high_60)
    breakout_proximity = safe_divide(latest_close, recent_high_60)
    breakout_proximity_score = 100 * max(0, min(1, breakout_proximity or 0))
    compression_5d_range = safe_divide(recent_high_5 - recent_low_5, latest_close) if recent_high_5 is not None and recent_low_5 is not None else None
    compression_5d_score = 0
    if compression_5d_range is not None:
        compression_5d_score = round(max(0, min(100, 100 * (1 - min(compression_5d_range, 0.25) / 0.25))), 1)
    volume_to_float = safe_divide(latest_volume, float_shares) if float_shares else None
    explosive = 0
    if pct_return(close, 5) and pct_return(close, 5) >= 0.5:
        explosive += 35
    if pct_return(close, 20) and pct_return(close, 20) >= 1.0:
        explosive += 35
    if safe_divide(latest_volume, avg_60) and safe_divide(latest_volume, avg_60) >= 3:
        explosive += 30
    violent_move = min(35, abs(pct_return(close, 20) or 0) * 35)
    violent_move += min(25, abs(pct_return(close, 60) or 0) * 20)
    relative_volume_pressure = min(20, (safe_divide(latest_volume, avg_60) or 0) * 5)
    dollar_flow_pressure = min(12, (safe_divide(dollar_recent, dollar_prior) or 0) * 4)
    setup_pressure = 0
    if compression_5d_score >= 70 and breakout_proximity_score >= 80:
        setup_pressure += 8
    recent_dynamism = min(100, explosive * 0.45 + violent_move + relative_volume_pressure + dollar_flow_pressure + setup_pressure)

    return {
        "ticker": ticker,
        "history_rows": len(frame),
        "history_start_date": start_date.date().isoformat() if start_date is not None else None,
        "history_end_date": end_date.date().isoformat() if end_date is not None else None,
        "public_age_years_proxy": round(public_age_years, 2) if public_age_years is not None else None,
        "all_time_high": all_time_high,
        "all_time_drawdown": all_time_drawdown,
        "return_5d": pct_return(close, 5),
        "return_20d": pct_return(close, 20),
        "return_60d": pct_return(close, 60),
        "avg_volume_20d": avg_20,
        "avg_volume_60d": avg_60,
        "relative_volume_20d": safe_divide(latest_volume, avg_20),
        "relative_volume_60d": safe_divide(latest_volume, avg_60),
        "dollar_volume_acceleration": safe_divide(dollar_recent, dollar_prior),
        "volume_to_float": volume_to_float,
        "breakout_distance_60d": breakout_distance_60d,
        "breakout_proximity_score": round(max(0, min(100, breakout_proximity_score)), 1),
        "compression_5d_range": compression_5d_range,
        "compression_5d_score": compression_5d_score,
        "near_52w_low_score": round(max(0, min(100, near_low)), 1),
        "drawdown_60d": drawdown_60,
        "explosive_behavior_score": min(100, explosive),
        "recent_dynamism_score": round(max(0, min(100, recent_dynamism)), 1),
        "price_history_status": "ok",
        "price_history_source": source or "unknown",
    }


def lookup_float_shares(universe: pd.DataFrame, ticker: str) -> float | None:
    """Find float shares for volume/float pressure when the universe has it."""
    if universe.empty or "float" not in universe.columns:
        return None
    match = universe[universe["ticker"].astype(str).str.upper() == ticker.upper()]
    if match.empty:
        return None
    return to_float(match.iloc[0].get("float"))


def pct_return(close: pd.Series, days: int) -> float | None:
    """Return percentage change over a trailing number of rows."""
    if len(close) <= days:
        return None
    start = float(close.iloc[-days - 1])
    end = float(close.iloc[-1])
    return safe_divide(end - start, start)


def empty_feature_row(ticker: str, status: str, source: str = "") -> dict[str, Any]:
    """Return a stable empty feature row for a ticker."""
    row = {column: None for column in FEATURE_COLUMNS}
    row["ticker"] = ticker
    row["price_history_status"] = status
    row["price_history_source"] = source or status
    return row


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Read the processed universe if available."""
    path = project_path(config["paths"]["universe_output"])
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def save_features(features: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Save price-history features to CSV."""
    output_path = project_path(config["paths"]["price_history_features_output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_path, index=False)
    logger.info("Price-history features saved to %s with %s rows", output_path, len(features))
    return features


def existing_or_empty_features(config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Return existing price-history features if present; otherwise write an empty stable file."""
    output_path = project_path(config["paths"]["price_history_features_output"])
    if output_path.exists():
        try:
            features = pd.read_csv(output_path)
            logger.info("Using existing price-history features from %s with %s rows", output_path, len(features))
            return features
        except (OSError, pd.errors.ParserError):
            pass
    return save_features(pd.DataFrame(columns=FEATURE_COLUMNS), config, logger)


def run() -> pd.DataFrame:
    """Run price-history feature collection independently."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    return build_price_history_features(config, logger)


def main() -> None:
    """Run this module independently from the command line."""
    parser = argparse.ArgumentParser(description="Build historical price/volume features.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    features = build_price_history_features(config, logger)
    print(features.head(25).to_string(index=False))


if __name__ == "__main__":
    main()
