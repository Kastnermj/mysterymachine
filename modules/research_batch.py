"""Pre-screen a focused 10-bagger research batch from the broad universe."""

from __future__ import annotations

import argparse
import logging
from typing import Any

import pandas as pd

from utils.helpers import to_float
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path


BATCH_COLUMNS = [
    "ticker",
    "company_name",
    "price",
    "market_cap",
    "volume",
    "avg_volume",
    "dollar_volume",
    "sector",
    "industry",
    "ten_bagger_prescreen_score",
    "prescreen_data_quality_score",
    "prescreen_reason",
]


NOISE_TERMS = [
    "acquisition corp",
    "acquisition corporation",
    "spac",
    "blank check",
    "capital corp",
    "units",
    "unit ",
    "warrant",
    "rights",
    "preferred",
    "depositary shares",
    "municipal",
    "income fund",
    "closed-end fund",
    "trust units",
    "beneficial interest",
]


def build_research_batch(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    universe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Select the focused Top-N batch for slow SEC and price-history pulls."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))
    universe = universe if universe is not None else read_universe(config)
    if universe.empty or "ticker" not in universe.columns:
        logger.warning("No universe available for 10-bagger pre-screen")
        return save_batch(pd.DataFrame(columns=BATCH_COLUMNS), config, logger)

    frame = universe.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame = frame.drop_duplicates(subset=["ticker"], keep="first")
    frame = attach_prior_scores(frame, config, logger)
    scored_rows = []
    for _, row in frame.iterrows():
        setup_score, setup_reasons = score_ten_bagger_setup(row, config)
        quality_score, quality_reasons, missing_critical = score_prescreen_data_quality(row)
        if missing_critical and quality_score < 35:
            continue
        scored = row.to_dict()
        scored["ten_bagger_prescreen_score"] = round(setup_score + quality_score * 0.35, 1)
        scored["prescreen_data_quality_score"] = quality_score
        scored["prescreen_reason"] = "; ".join(setup_reasons + quality_reasons)
        scored_rows.append(scored)

    output = pd.DataFrame(scored_rows)
    if output.empty:
        logger.warning("Strict pre-screen found no names; falling back to broad universe ordering")
        output = frame.copy()
        output["ten_bagger_prescreen_score"] = 0
        output["prescreen_data_quality_score"] = 0
        output["prescreen_reason"] = "Fallback row; insufficient pre-screen data."

    batch_size = int(config.get("research_batch", {}).get("size", 100))
    output = output.sort_values(
        by=["ten_bagger_prescreen_score", "prescreen_data_quality_score"],
        ascending=[False, False],
        na_position="last",
    )
    output = apply_price_band_diversity(output, batch_size, config)
    output = ensure_batch_columns(output)
    logger.info("10-bagger research batch selected with %s tickers", len(output))
    print(f"      Research batch: selected {len(output)} best pre-screened 10-bagger candidates", flush=True)
    return save_batch(output, config, logger)


def apply_price_band_diversity(frame: pd.DataFrame, batch_size: int, config: dict[str, Any]) -> pd.DataFrame:
    """Reserve room for credible non-penny 10-bagger candidates when available."""
    if frame.empty or "price" not in frame.columns:
        return frame.head(batch_size)
    minimums = config.get("research_batch", {}).get("price_band_minimums", {})
    if not minimums:
        return frame.head(batch_size)
    output_parts = []
    used_tickers: set[str] = set()
    band_rules = [
        ("under_1", lambda price: price is not None and price < 1),
        ("between_1_and_5", lambda price: price is not None and 1 <= price < 5),
        ("between_5_and_20", lambda price: price is not None and 5 <= price <= config["universe"]["filters"]["max_price"]),
    ]
    for band_name, predicate in band_rules:
        target_count = int(minimums.get(band_name, 0))
        if target_count <= 0:
            continue
        band = frame[
            frame["price"].apply(lambda value: predicate(to_float(value)))
            & ~frame["ticker"].astype(str).isin(used_tickers)
        ].head(target_count)
        if not band.empty:
            output_parts.append(band)
            used_tickers.update(band["ticker"].astype(str).tolist())

    selected = pd.concat(output_parts, ignore_index=False) if output_parts else frame.iloc[0:0]
    remaining_slots = max(0, batch_size - len(selected))
    if remaining_slots:
        remaining = frame[~frame["ticker"].astype(str).isin(used_tickers)].head(remaining_slots)
        selected = pd.concat([selected, remaining], ignore_index=False)
    return selected.sort_values(
        by=["ten_bagger_prescreen_score", "prescreen_data_quality_score"],
        ascending=[False, False],
        na_position="last",
    ).head(batch_size)


def attach_prior_scores(frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Merge prior theory scores when available so the pre-screen improves over time."""
    prior_scores_path = project_path(config["paths"].get("theory_scores_output", ""))
    if not prior_scores_path.exists():
        return frame
    try:
        prior_scores = pd.read_csv(prior_scores_path)
    except (OSError, pd.errors.ParserError) as exc:
        logger.debug("Could not read prior scores for pre-screen: %s", exc)
        return frame
    keep_columns = [
        column
        for column in [
            "ticker",
            "repricing_sequence_score",
            "movement_score",
            "asymmetry_score",
            "relative_mispricing_score",
            "data_confidence_score",
        ]
        if column in prior_scores.columns
    ]
    if "ticker" not in keep_columns:
        return frame
    prior_scores["ticker"] = prior_scores["ticker"].astype(str).str.upper().str.strip()
    return frame.merge(prior_scores[keep_columns], how="left", on="ticker")


def score_ten_bagger_setup(row: pd.Series, config: dict[str, Any]) -> tuple[float, list[str]]:
    """Score fast 10-bagger setup clues before slower data pulls."""
    score = 0.0
    reasons: list[str] = []
    thresholds = config["scoring"]["thresholds"]
    configured_tickers = {str(ticker).upper() for ticker in config["universe"].get("tickers", [])}
    ticker = str(row.get("ticker") or "").upper()
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    text = " ".join(
        str(row.get(column) or "")
        for column in ["ticker", "company_name", "sector", "industry", "universe_reason"]
    ).lower()
    is_noise = any(term in text for term in NOISE_TERMS)

    if ticker in configured_tickers:
        score += 20
        reasons.append("seed ticker")
    if market_cap is not None and market_cap < thresholds["very_low_market_cap"]:
        score += 24
        reasons.append("tiny market cap")
    elif market_cap is not None and market_cap < thresholds["small_market_cap"]:
        score += 18
        reasons.append("small market cap")
    elif market_cap is not None and market_cap < thresholds.get("ten_bagger_market_cap_ceiling", 1_000_000_000):
        score += 8
        reasons.append("sub-billion market cap")
    if price is not None and price < 1:
        reasons.append("sub-dollar risk context")
    elif price is not None and price < 5:
        score += 6
        reasons.append("low nominal price")
    elif price is not None and price <= config["universe"]["filters"]["max_price"]:
        score += 6
        reasons.append("within 10-bagger price band")
    if dollar_volume is not None and dollar_volume >= thresholds["low_dollar_volume"]:
        score += 12
        reasons.append("enough dollar volume to research")

    if any(term.lower() in text for term in config["scoring"].get("narrative_terms", [])):
        score += 12
        reasons.append("narrative hook")
    if any(term.lower() in text for term in config["scoring"].get("constraint_terms", [])):
        score += 10
        reasons.append("constraint exposure")

    score += (to_float(row.get("repricing_sequence_score")) or 0) * 0.30
    score += (to_float(row.get("movement_score")) or 0) * 0.35
    score += (to_float(row.get("asymmetry_score")) or 0) * 0.25
    score += (to_float(row.get("relative_mispricing_score")) or 0) * 0.20
    if is_noise:
        score -= 35
        reasons.append("SPAC/fund/unit noise penalty")
        if not market_cap or market_cap <= 0:
            score -= 35
            reasons.append("missing market cap on noise structure")
    return score, reasons or ["basic setup candidate"]


def score_prescreen_data_quality(row: pd.Series) -> tuple[float, list[str], bool]:
    """Score fast evidence quality and flag names missing critical basics."""
    score = 0.0
    reasons: list[str] = []
    missing_critical = False
    critical_fields = ["price", "market_cap", "dollar_volume"]
    for field in critical_fields:
        if pd.notna(row.get(field)):
            score += 12
            reasons.append(f"{field} present")
        else:
            missing_critical = True
    for field in ["company_name", "sector", "industry", "volume"]:
        if pd.notna(row.get(field)):
            score += 8
            reasons.append(f"{field} present")
    if pd.notna(row.get("avg_volume")):
        score += 6
        reasons.append("avg_volume present")
    score += (to_float(row.get("data_confidence_score")) or 0) * 0.25
    return min(100, score), reasons or ["thin pre-screen evidence"], missing_critical


def ensure_batch_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a stable batch frame with expected output columns first."""
    output = frame.copy()
    for column in BATCH_COLUMNS:
        if column not in output.columns:
            output[column] = None
    return output[BATCH_COLUMNS]


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Read the processed universe if available."""
    path = project_path(config["paths"]["universe_output"])
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def save_batch(batch: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Save the research batch to CSV."""
    output_path = project_path(config["paths"]["research_batch_output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batch.to_csv(output_path, index=False)
    logger.info("10-bagger research batch saved to %s", output_path)
    return batch


def run() -> pd.DataFrame:
    """Run the research batch pre-screen independently."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    return build_research_batch(config, logger)


def main() -> None:
    """Run this module independently from the command line."""
    parser = argparse.ArgumentParser(description="Build focused 10-bagger research batch.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    batch = build_research_batch(config, logger)
    print(batch.head(25).to_string(index=False))


if __name__ == "__main__":
    main()
