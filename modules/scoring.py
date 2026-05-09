"""Economic theory scoring for Contrarian Flow Engine.

This module turns the user's Austrian/Hume/Keynes framework into explicit,
explainable ticker-level scores using currently available project data.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
from typing import Any

import pandas as pd

from utils.helpers import safe_divide, to_float
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path


SCORE_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "industry",
    "price",
    "market_cap",
    "volume",
    "avg_volume",
    "dollar_volume",
    "austrian_mispricing_score",
    "hume_flow_potential_score",
    "keynes_repricing_potential_score",
    "relative_mispricing_score",
    "asymmetry_score",
    "data_confidence_score",
    "data_confidence_label",
    "data_confidence_explanation",
    "long_term_investment_score",
    "long_term_investment_label",
    "long_term_investment_note",
    "dcf_plausibility_score",
    "expectation_gap_score",
    "time_to_viability",
    "time_to_viability_score",
    "dcf_plausibility_note",
    "dilution_pressure_score",
    "survival_risk_score",
    "catalyst_signal_score",
    "narrative_trigger_score",
    "filing_activity_score",
    "catalyst_probability_score",
    "volume_to_float",
    "breakout_distance_60d",
    "breakout_proximity_score",
    "compression_5d_range",
    "compression_5d_score",
    "public_age_years_proxy",
    "all_time_high",
    "all_time_drawdown",
    "recent_dynamism_score",
    "zombie_decay_penalty",
    "zombie_decay_label",
    "zombie_decay_note",
    "event_shock_score",
    "event_shock_suspected_score",
    "event_shock_detail_score",
    "event_shock_penalty",
    "thesis_break_risk_score",
    "event_override_note",
    "event_shock_label",
    "event_shock_reason",
    "event_shock_source_url",
    "event_shock_confidence",
    "reset_catalyst_watch",
    "pricing_gap_factor",
    "flow_factor",
    "story_attention_factor",
    "relative_value_factor",
    "convexity_factor",
    "trading_setup_factor",
    "animal_spirits_factor",
    "portfolio_viability_factor",
    "sec_risk_penalty",
    "accounting_quality_factor",
    "factor_stack_note",
    "repricing_sequence_score",
    "raw_movement_score",
    "movement_grade",
    "movement_score",
    "echo_penalty_total",
    "small_cap_echo_penalty",
    "low_price_echo_penalty",
    "liquidity_echo_penalty",
    "narrative_echo_penalty",
    "distress_echo_penalty",
    "echo_control_note",
    "what_i_think",
    "personal_signal_label",
    "label_basis",
    "setup_type",
    "risk_posture",
    "flow_state",
    "viability_window",
    "event_callouts",
    "raw_setup_interpretation",
    "raw_setup_note",
    "thesis_integrity_label",
    "thesis_integrity_note",
    "final_rank_interpretation",
    "raw_pre_flow_opportunity_score",
    "pre_flow_opportunity_score",
    "flow_confirmation_label",
    "flow_confirmation_note",
    "penalty_adjusted_score",
    "sequence_interpretation",
    "sequence_note",
    "ranking_note",
    "subsignal_tags",
    "austrian_explanation",
    "hume_explanation",
    "keynes_explanation",
    "relative_explanation",
    "asymmetry_explanation",
]


SECURITY_NOISE_TERMS = [
    "warrant",
    "rights",
    "unit",
    "acquisition corp",
    "capital corp",
    "income fund",
    "municipal",
    "preferred",
    "beneficial interest",
]


def clean_float(value: Any, default: float = 0.0) -> float:
    """Convert numeric-ish values to finite floats for scoring math."""
    converted = to_float(value)
    if converted is None:
        return default
    if isinstance(converted, float) and math.isnan(converted):
        return default
    return float(converted)


def is_noise_security(row: pd.Series) -> bool:
    """Return True for structures that are not clean common-stock research targets."""
    text = " ".join(
        str(row.get(column) or "")
        for column in ["ticker", "company_name", "sector", "industry"]
    ).lower()
    return any(term in text for term in SECURITY_NOISE_TERMS)


def text_has_term(text: str, term: str) -> bool:
    """Match narrative terms without letting short tokens hit inside ordinary words."""
    clean_text = str(text or "").lower()
    clean_term = str(term or "").lower().strip()
    if not clean_term:
        return False
    if len(clean_term) <= 3 and clean_term.isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(clean_term)}(?![a-z0-9])", clean_text) is not None
    return clean_term in clean_text


def build_theory_scores(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Compute Austrian, Hume, Keynes, and repricing sequence scores."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))

    universe = _read_csv(config["paths"]["universe_output"])
    sec_signals = _read_csv(config["paths"]["sec_signals_output"])
    price_features = _read_csv(config["paths"]["price_history_features_output"])
    fundamentals = _read_csv(config["paths"].get("fundamentals_output", ""))
    event_shocks = _read_csv(config["paths"].get("event_shocks_output", ""))
    if universe.empty:
        logger.warning("No universe data found; writing empty theory score output")
        return _save_scores(pd.DataFrame(columns=SCORE_COLUMNS), config, logger)

    frame = universe.merge(sec_signals, how="left", on="ticker", suffixes=("", "_sec"))
    if not price_features.empty and "ticker" in price_features.columns:
        frame = frame.merge(price_features, how="left", on="ticker", suffixes=("", "_history"))
    if not fundamentals.empty and "ticker" in fundamentals.columns:
        keep = [column for column in fundamentals.columns if column == "ticker" or column not in frame.columns]
        frame = frame.merge(fundamentals[keep], how="left", on="ticker", suffixes=("", "_fundamentals"))
    if not event_shocks.empty and "ticker" in event_shocks.columns:
        keep = [column for column in event_shocks.columns if column == "ticker" or column not in frame.columns]
        frame = frame.merge(event_shocks[keep], how="left", on="ticker", suffixes=("", "_event"))
    frame = prepare_scoring_frame(frame)
    sector_stats = build_sector_stats(frame)

    rows = []
    for _, row in frame.iterrows():
        sector_row = sector_stats.get(str(row.get("sector") or ""), {})
        sub = compute_subsignals(row, config)
        austrian, austrian_note = score_austrian(row, config, sub)
        hume, hume_note = score_hume(row, sector_row, config)
        keynes, keynes_note = score_keynes(row, config, sub)
        relative, relative_note = score_relative_mispricing(row, sector_row, config, sub)
        dcf = score_dcf_plausibility(row)
        asymmetry, asymmetry_note = score_asymmetry(row, config, sub, dcf)
        data_confidence, data_confidence_label, data_confidence_explanation = score_data_confidence(row)
        sequence_score = round(austrian + hume + keynes, 1)
        event_override = get_event_override(row, config)
        zombie_decay = score_zombie_decay(row, config)
        catalyst_probability = score_catalyst_probability(row, event_override)
        factors = compute_factor_stack(
            austrian,
            hume,
            keynes,
            relative,
            asymmetry,
            data_confidence,
            catalyst_probability,
            row,
            config,
        )
        long_term = score_long_term_microcap(row, factors, dcf, zombie_decay, event_override, data_confidence)
        raw_movement_score = score_movement_potential(
            austrian,
            hume,
            keynes,
            relative,
            asymmetry,
            data_confidence,
            row,
            factors,
            event_override,
            zombie_decay,
        )
        echo = compute_echo_control(row, factors)
        movement_score = apply_echo_adjustment(raw_movement_score, echo["echo_penalty_total"])
        raw_setup_interpretation = interpret_sequence(austrian, hume, keynes, config)
        thesis_integrity_label, thesis_integrity_note = interpret_thesis_integrity(
            event_override,
            row,
            movement_score=movement_score,
            hume=hume,
            keynes=keynes,
            relative=relative,
            asymmetry=asymmetry,
            dcf=dcf,
            long_term=long_term,
        )
        raw_pre_flow_opportunity = score_pre_flow_opportunity(relative, asymmetry, data_confidence, factors, row, event_override)
        raw_pre_flow_opportunity = apply_zombie_decay_to_score(raw_pre_flow_opportunity, zombie_decay, multiplier=0.5)
        pre_flow_opportunity = apply_echo_adjustment(raw_pre_flow_opportunity, echo["echo_penalty_total"] * 0.45)
        flow_confirmation_label, flow_confirmation_note = interpret_flow_confirmation(hume, factors, pre_flow_opportunity)
        final_rank_interpretation = interpret_final_rank(movement_score, pre_flow_opportunity, hume)
        sequence_interpretation = raw_setup_interpretation
        personal_label = personal_signal_label(
            movement_score,
            austrian,
            hume,
            keynes,
            relative,
            asymmetry,
            data_confidence,
            pre_flow_opportunity,
            event_override,
            row,
            zombie_decay,
            dcf,
            long_term,
        )
        setup_type = classify_setup_type(austrian, hume, keynes, movement_score, pre_flow_opportunity)
        risk_posture = classify_risk_posture(
            row,
            event_override,
            zombie_decay,
            data_confidence,
            movement_score=movement_score,
            hume=hume,
            keynes=keynes,
            relative=relative,
            asymmetry=asymmetry,
            dcf=dcf,
            long_term=long_term,
        )
        event_callouts = build_event_callouts(row, event_override)
        rows.append(
            {
                "ticker": row.get("ticker"),
                "company_name": row.get("company_name"),
                "sector": row.get("sector"),
                "industry": row.get("industry"),
                "price": row.get("price"),
                "market_cap": row.get("market_cap"),
                "volume": row.get("volume"),
                "avg_volume": row.get("avg_volume"),
                "dollar_volume": row.get("dollar_volume"),
                "austrian_mispricing_score": austrian,
                "hume_flow_potential_score": hume,
                "keynes_repricing_potential_score": keynes,
                "relative_mispricing_score": relative,
                "asymmetry_score": asymmetry,
                "data_confidence_score": data_confidence,
                "data_confidence_label": data_confidence_label,
                "data_confidence_explanation": data_confidence_explanation,
                "long_term_investment_score": long_term["long_term_investment_score"],
                "long_term_investment_label": long_term["long_term_investment_label"],
                "long_term_investment_note": long_term["long_term_investment_note"],
                "dcf_plausibility_score": dcf["dcf_plausibility_score"],
                "expectation_gap_score": dcf["expectation_gap_score"],
                "time_to_viability": dcf["time_to_viability"],
                "time_to_viability_score": dcf["time_to_viability_score"],
                "dcf_plausibility_note": dcf["dcf_plausibility_note"],
                "dilution_pressure_score": row.get("dilution_pressure_score"),
                "survival_risk_score": row.get("survival_risk_score"),
                "catalyst_signal_score": row.get("catalyst_signal_score"),
                "narrative_trigger_score": row.get("narrative_trigger_score"),
                "filing_activity_score": row.get("filing_activity_score"),
                "catalyst_probability_score": catalyst_probability,
                "volume_to_float": row.get("volume_to_float"),
                "breakout_distance_60d": row.get("breakout_distance_60d"),
                "breakout_proximity_score": row.get("breakout_proximity_score"),
                "compression_5d_range": row.get("compression_5d_range"),
                "compression_5d_score": row.get("compression_5d_score"),
                "public_age_years_proxy": row.get("public_age_years_proxy"),
                "all_time_high": row.get("all_time_high"),
                "all_time_drawdown": row.get("all_time_drawdown"),
                "recent_dynamism_score": row.get("recent_dynamism_score"),
                "zombie_decay_penalty": zombie_decay["zombie_decay_penalty"],
                "zombie_decay_label": zombie_decay["zombie_decay_label"],
                "zombie_decay_note": zombie_decay["zombie_decay_note"],
                "event_shock_score": row.get("event_shock_score"),
                "event_shock_suspected_score": row.get("event_shock_suspected_score"),
                "event_shock_detail_score": row.get("event_shock_detail_score"),
                "event_shock_penalty": event_override["event_shock_penalty"],
                "thesis_break_risk_score": event_override["thesis_break_risk_score"],
                "event_override_note": event_override["event_override_note"],
                "event_shock_label": row.get("event_shock_label"),
                "event_shock_reason": row.get("event_shock_reason"),
                "event_shock_source_url": row.get("event_shock_source_url"),
                "event_shock_confidence": row.get("event_shock_confidence"),
                "reset_catalyst_watch": has_reset_catalyst(
                    row,
                    event_override,
                    movement_score,
                    hume,
                    keynes,
                    relative,
                    asymmetry,
                    dcf,
                    long_term,
                ),
                "pricing_gap_factor": factors["pricing_gap_factor"],
                "flow_factor": factors["flow_factor"],
                "story_attention_factor": factors["story_attention_factor"],
                "relative_value_factor": factors["relative_value_factor"],
                "convexity_factor": factors["convexity_factor"],
                "trading_setup_factor": factors["trading_setup_factor"],
                "animal_spirits_factor": factors["animal_spirits_factor"],
                "portfolio_viability_factor": factors["portfolio_viability_factor"],
                "sec_risk_penalty": factors["sec_risk_penalty"],
                "accounting_quality_factor": factors["accounting_quality_factor"],
                "factor_stack_note": factors["factor_stack_note"],
                "repricing_sequence_score": sequence_score,
                "raw_movement_score": raw_movement_score,
                "movement_grade": movement_grade(movement_score),
                "movement_score": movement_score,
                "echo_penalty_total": echo["echo_penalty_total"],
                "small_cap_echo_penalty": echo["small_cap_echo_penalty"],
                "low_price_echo_penalty": echo["low_price_echo_penalty"],
                "liquidity_echo_penalty": echo["liquidity_echo_penalty"],
                "narrative_echo_penalty": echo["narrative_echo_penalty"],
                "distress_echo_penalty": echo["distress_echo_penalty"],
                "echo_control_note": echo["echo_control_note"],
                "what_i_think": personal_label,
                "personal_signal_label": personal_label,
                "label_basis": "strict model label",
                "setup_type": setup_type,
                "risk_posture": risk_posture,
                "flow_state": flow_confirmation_label,
                "viability_window": dcf["time_to_viability"],
                "event_callouts": event_callouts,
                "raw_setup_interpretation": raw_setup_interpretation,
                "raw_setup_note": explain_sequence(raw_setup_interpretation),
                "thesis_integrity_label": thesis_integrity_label,
                "thesis_integrity_note": thesis_integrity_note,
                "final_rank_interpretation": final_rank_interpretation,
                "raw_pre_flow_opportunity_score": raw_pre_flow_opportunity,
                "pre_flow_opportunity_score": pre_flow_opportunity,
                "flow_confirmation_label": flow_confirmation_label,
                "flow_confirmation_note": flow_confirmation_note,
                "penalty_adjusted_score": movement_score,
                "sequence_interpretation": sequence_interpretation,
                "sequence_note": explain_sequence(sequence_interpretation),
                "ranking_note": build_ranking_note(
                    austrian,
                    hume,
                    keynes,
                    relative,
                    asymmetry,
                    data_confidence,
                    row,
                    factors,
                    event_override,
                    zombie_decay,
                ),
                "subsignal_tags": build_subsignal_tags(sub),
                "austrian_explanation": austrian_note,
                "hume_explanation": hume_note,
                "keynes_explanation": keynes_note,
                "relative_explanation": relative_note,
                "asymmetry_explanation": asymmetry_note,
            }
        )

    scores = pd.DataFrame(rows, columns=SCORE_COLUMNS)
    scores = scores.sort_values(
        by=[
            "movement_score",
            "repricing_sequence_score",
            "relative_mispricing_score",
            "asymmetry_score",
            "data_confidence_score",
            "hume_flow_potential_score",
        ],
        ascending=[False, False, False, False, False, False],
        na_position="last",
    )
    scores = apply_best_candidate_labels(scores)
    return _save_scores(scores, config, logger)


def prepare_scoring_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize numeric scoring columns and fill missing SEC signal values."""
    output = frame.copy()
    for column in [
        "price",
        "market_cap",
        "volume",
        "avg_volume",
        "dollar_volume",
        "dilution_pressure_score",
        "survival_risk_score",
        "catalyst_signal_score",
        "narrative_trigger_score",
        "filing_activity_score",
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
        "public_age_years_proxy",
        "all_time_high",
        "all_time_drawdown",
        "recent_dynamism_score",
        "zombie_decay_penalty",
        "near_52w_low_score",
        "drawdown_60d",
        "explosive_behavior_score",
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
        "dcf_plausibility_score",
        "expectation_gap_score",
        "time_to_viability_score",
    ]:
        if column not in output.columns:
            output[column] = 0
        output[column] = pd.to_numeric(output[column], errors="coerce")
    fallback_volume_to_float = output["volume_to_float"].isna() | (output["volume_to_float"] <= 0)
    fallback_denominator = output["shares_outstanding"].where(output["shares_outstanding"] > 0)
    output.loc[fallback_volume_to_float, "volume_to_float"] = (
        output.loc[fallback_volume_to_float, "volume"] / fallback_denominator.loc[fallback_volume_to_float]
    )
    output["is_illiquid"] = output.get("is_illiquid", False).fillna(False)
    return output


def build_sector_stats(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute sector medians used as Hume flow/rotation proxies."""
    stats: dict[str, dict[str, float]] = {}
    for sector, group in frame.groupby(frame["sector"].fillna("")):
        stats[str(sector)] = {
            "median_dollar_volume": float(group["dollar_volume"].median(skipna=True) or 0),
            "median_market_cap": float(group["market_cap"].median(skipna=True) or 0),
            "median_volume": float(group["volume"].median(skipna=True) or 0),
            "median_return_20d": float(group["return_20d"].median(skipna=True) or 0),
        }
    return stats


def compute_subsignals(row: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    """Compute Ricardo/Malthus/Technology sub-signals used to adjust main scores."""
    text = " ".join(
        str(row.get(column) or "")
        for column in ["company_name", "sector", "industry", "universe_reason"]
    ).lower()
    narrative_terms = [term.lower() for term in config["scoring"].get("narrative_terms", [])]
    useful_terms = [term.lower() for term in config["scoring"].get("useful_industries", [])]
    constraint_terms = [term.lower() for term in config["scoring"].get("constraint_terms", [])]
    evolution_config = config["scoring"].get("narrative_evolution_terms", {})
    matched_evolution_clusters = [
        str(cluster)
        for cluster, terms in evolution_config.items()
        if any(text_has_term(text, term) for term in terms)
    ]
    generic_ai = any(text_has_term(text, term) for term in ["AI", "artificial intelligence"])
    has_narrative = any(text_has_term(text, term) for term in narrative_terms)
    has_useful_industry = any(text_has_term(text, term) for term in useful_terms)
    has_evolved_narrative = bool(matched_evolution_clusters)
    technology_narrative = 70 if has_narrative else 20
    if has_evolved_narrative:
        technology_narrative = max(technology_narrative, 78)
    technology_usefulness = 70 if has_useful_industry or has_evolved_narrative else 20
    narrative_evolution = 80 if len(matched_evolution_clusters) >= 2 else 68 if has_evolved_narrative else 20
    ricardo_productivity = 75 if has_useful_industry or has_evolved_narrative or any(text_has_term(text, term) for term in ["automation", "productivity", "efficiency"]) else 20
    malthus_constraint = 75 if any(text_has_term(text, term) for term in constraint_terms) else 15
    tech_hype_warning = 0
    if technology_narrative >= 70 and technology_usefulness < 50:
        tech_hype_warning = 35
    if generic_ai and not has_evolved_narrative and technology_usefulness < 70:
        tech_hype_warning = max(tech_hype_warning, 25)
    boring_beneficiary = technology_usefulness >= 70 and technology_narrative < 50
    return {
        "technology_narrative_score": technology_narrative,
        "technology_usefulness_score": technology_usefulness,
        "narrative_evolution_score": narrative_evolution,
        "narrative_evolution_clusters": ",".join(matched_evolution_clusters),
        "ricardo_productivity_score": ricardo_productivity,
        "malthus_constraint_score": malthus_constraint,
        "tech_hype_warning": tech_hype_warning,
        "boring_beneficiary_flag": boring_beneficiary,
    }


def score_austrian(row: pd.Series, config: dict[str, Any], sub: dict[str, Any]) -> tuple[float, str]:
    """Score distress, fragility, liquidation pressure, and bust conditions."""
    thresholds = config["scoring"]["thresholds"]
    score = 0.0
    reasons = []

    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    near_low = clean_float(row.get("near_52w_low_score"))
    drawdown_60d = to_float(row.get("drawdown_60d"))

    if price is not None and price < 5:
        score += max(0, min(10, (5 - price) / 5 * 10))
        reasons.append("low-price distress")
    if price is not None and price < thresholds["low_price"]:
        score += max(0, min(12, (thresholds["low_price"] - price) / thresholds["low_price"] * 12))
        reasons.append("sub-dollar distress")
    if market_cap is not None and market_cap > 0:
        small_cap = thresholds["small_market_cap"]
        cap_pressure = max(0, math.log10(max(small_cap, 1)) - math.log10(max(market_cap, 1)))
        score += min(24, cap_pressure * 9)
        if market_cap < thresholds["very_low_market_cap"]:
            reasons.append("very small capitalization")
        elif market_cap < small_cap:
            reasons.append("small capitalization")
    if bool(row.get("is_illiquid")):
        score += 8
        reasons.append("illiquidity/forced-sale risk")
    score += dilution * 0.16
    if dilution >= 70:
        reasons.append("high dilution pressure")
    elif dilution >= 35:
        reasons.append("moderate dilution pressure")
    score += survival * 0.14
    if survival >= 70:
        reasons.append("elevated survival risk")
    elif survival >= 35:
        reasons.append("survival-risk proxy")
    if dollar_volume is not None and dollar_volume < thresholds["low_dollar_volume"]:
        score += min(10, max(0, (thresholds["low_dollar_volume"] - dollar_volume) / thresholds["low_dollar_volume"] * 10))
        reasons.append("thin dollar liquidity")
    score += near_low * 0.10
    if near_low >= 75:
        reasons.append("near 52-week low")
    if drawdown_60d is not None and drawdown_60d < 0:
        score += min(12, abs(drawdown_60d) * 22)
    if drawdown_60d is not None and drawdown_60d <= -0.4:
        reasons.append("deep 60-day drawdown")
    if sub["malthus_constraint_score"] >= 70:
        score += 6
        reasons.append("Malthus constraint exposure")

    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "limited Austrian distress evidence"


def score_hume(row: pd.Series, sector_stats: dict[str, float], config: dict[str, Any]) -> tuple[float, str]:
    """Score money-flow potential, sector rotation, volume, and ticker lag."""
    score = 0.0
    reasons = []
    volume = to_float(row.get("volume"))
    avg_volume = to_float(row.get("avg_volume"))
    dollar_volume = to_float(row.get("dollar_volume"))
    market_cap = to_float(row.get("market_cap"))
    filing_activity = to_float(row.get("filing_activity_score")) or 0
    relative_volume_20d = to_float(row.get("relative_volume_20d"))
    relative_volume_60d = to_float(row.get("relative_volume_60d"))
    return_5d = to_float(row.get("return_5d"))
    return_20d = to_float(row.get("return_20d"))
    sector_return_20d = sector_stats.get("median_return_20d") or 0

    sector_dollar_volume = sector_stats.get("median_dollar_volume") or 0
    sector_market_cap = sector_stats.get("median_market_cap") or 0
    volume_ratio = safe_divide(volume, avg_volume)
    sector_flow_ratio = safe_divide(dollar_volume, sector_dollar_volume)
    lag_ratio = safe_divide(market_cap, sector_market_cap)

    if volume_ratio is not None and volume_ratio > 0:
        score += min(24, max(0, math.log1p(volume_ratio) / math.log1p(4) * 24))
    if volume_ratio is not None and volume_ratio >= 2:
        reasons.append("volume acceleration")
    elif volume_ratio is not None and volume_ratio >= 1.25:
        reasons.append("early volume pickup")
    rel_volume_best = max(
        clean_float(relative_volume_20d) if relative_volume_20d is not None else 0,
        clean_float(relative_volume_60d) if relative_volume_60d is not None else 0,
    )
    if rel_volume_best > 0:
        score += min(22, math.log1p(rel_volume_best) / math.log1p(4) * 22)
    if relative_volume_20d is not None and relative_volume_20d >= 2:
        reasons.append("20-day relative volume surge")
    elif relative_volume_60d is not None and relative_volume_60d >= 1.5:
        reasons.append("60-day relative volume pickup")
    if return_5d is not None and return_5d > 0.1:
        score += min(12, return_5d * 35)
        reasons.append("recent price response")
    if return_20d is not None and return_20d > sector_return_20d:
        score += min(14, max(0, return_20d - sector_return_20d) * 40 + 4)
        reasons.append("ticker improving versus sector median")
    if sector_flow_ratio is not None and sector_flow_ratio > 0:
        score += min(24, math.log1p(sector_flow_ratio) / math.log1p(3) * 24)
    if sector_flow_ratio is not None and sector_flow_ratio >= 1.5:
        reasons.append("strong relative dollar flow")
    elif sector_flow_ratio is not None and sector_flow_ratio >= 0.75:
        reasons.append("participating in sector flow")
    if lag_ratio is not None and lag_ratio < 0.5 and sector_flow_ratio is not None and sector_flow_ratio >= 0.75:
        score += min(16, (0.5 - lag_ratio) / 0.5 * 16)
        reasons.append("small ticker lagging active sector")
    score += min(18, filing_activity * 0.18)
    if filing_activity >= 60:
        reasons.append("filing activity spike")
    elif filing_activity >= 30:
        reasons.append("modest filing activity pickup")
    if dollar_volume and dollar_volume > config["scoring"]["thresholds"]["high_dollar_volume"]:
        score += min(10, math.log10(max(dollar_volume, 10)) - math.log10(config["scoring"]["thresholds"]["high_dollar_volume"]) + 6)
        reasons.append("enough liquidity for flow to matter")

    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "limited Hume flow evidence"


def score_keynes(row: pd.Series, config: dict[str, Any], sub: dict[str, Any]) -> tuple[float, str]:
    """Score narrative simplicity, attention potential, reflexivity, and price movability."""
    thresholds = config["scoring"]["thresholds"]
    score = 0.0
    reasons = []
    text = " ".join(
        str(row.get(column) or "")
        for column in ["company_name", "sector", "industry", "universe_reason", "signal_interpretation"]
    ).lower()
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    narrative_signal = clean_float(row.get("narrative_trigger_score"))
    catalyst_signal = clean_float(row.get("catalyst_signal_score"))
    explosive = clean_float(row.get("explosive_behavior_score"))

    if any(text_has_term(text, term) for term in config["scoring"].get("narrative_terms", [])):
        score += 14
        reasons.append("simple narrative hook")
    score += clean_float(sub.get("technology_narrative_score")) * 0.08
    if sub["technology_narrative_score"] >= 70:
        reasons.append("technology narrative sub-signal")
    score += clean_float(sub.get("narrative_evolution_score", 20)) * 0.06
    if sub.get("narrative_evolution_score", 20) >= 65:
        reasons.append("specific outcome narrative")
    if row.get("sector") in config["scoring"].get("narrative_sectors", []):
        score += 8
        reasons.append("narrative-friendly sector")
    animal_spirits, animal_reason = score_animal_spirits(row, config, sub)
    score += animal_spirits * 0.14
    if animal_spirits >= 50:
        reasons.append(f"animal spirits theme heat: {animal_reason}")
    if market_cap is not None and market_cap > 0 and market_cap < thresholds["small_market_cap"]:
        cap_pressure = max(0, math.log10(max(thresholds["small_market_cap"], 1)) - math.log10(max(market_cap, 1)))
        score += min(12, cap_pressure * 4.5)
        reasons.append("small float/market-cap reflexivity proxy")
    if dollar_volume is not None and thresholds["low_dollar_volume"] <= dollar_volume <= thresholds["high_dollar_volume"] * 5:
        score += 10 * (1 - min(1, abs(dollar_volume - thresholds["high_dollar_volume"]) / max(thresholds["high_dollar_volume"] * 5, 1)))
        reasons.append("liquidity can move price")
    score += narrative_signal * 0.18
    if narrative_signal >= 60:
        reasons.append("filing pattern may trigger narrative")
    elif narrative_signal >= 30:
        reasons.append("some narrative trigger potential")
    score += catalyst_signal * 0.14
    if catalyst_signal >= 50:
        reasons.append("event/catalyst metadata")
    score += explosive * 0.08
    if explosive >= 50:
        reasons.append("past explosive behavior")

    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "limited Keynes repricing evidence"


def score_animal_spirits(row: pd.Series, config: dict[str, Any], sub: dict[str, Any]) -> tuple[float, str]:
    """Score crowd-believability and theme heat without over-rewarding low price alone."""
    thresholds = config["scoring"]["thresholds"]
    text = " ".join(
        str(row.get(column) or "")
        for column in ["company_name", "sector", "industry", "universe_reason", "signal_interpretation"]
    ).lower()
    sector = str(row.get("sector") or "")
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    narrative = clean_float(row.get("narrative_trigger_score"))
    catalyst = clean_float(row.get("catalyst_signal_score"))
    score = 0.0
    reasons = []

    hot_terms = [term.lower() for term in config["scoring"].get("animal_spirits_terms", [])]
    matched_terms = [term for term in hot_terms if text_has_term(text, term)]
    if matched_terms:
        score += 28
        reasons.append("hot theme: " + ", ".join(matched_terms[:3]))
    if sector in config["scoring"].get("narrative_sectors", []):
        score += 16
        reasons.append("story-friendly sector")
    if sub["technology_narrative_score"] >= 70:
        score += 14
        reasons.append("technology narrative")
    if sub.get("narrative_evolution_score", 20) >= 65:
        score += 8
        reasons.append("outcome-specific tech narrative")
    if narrative >= 60 or catalyst >= 50:
        score += 16
        reasons.append("fresh filing/catalyst hook")
    if market_cap is not None and market_cap < thresholds["small_market_cap"]:
        score += 10
        reasons.append("small enough for reflexive attention")
    if dollar_volume is not None and thresholds["low_dollar_volume"] <= dollar_volume <= thresholds["high_dollar_volume"] * 5:
        score += 10
        reasons.append("liquidity can transmit story")
    if price is not None and price < 5:
        score += 4
        reasons.append("low nominal price, small modifier")
    if sub["tech_hype_warning"] > 0:
        score -= 12
        reasons.append("hype/usefulness mismatch")

    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "low theme heat"


def score_portfolio_viability(
    row: pd.Series,
    data_confidence: float,
    dollar_volume: float | None,
    market_cap: float | None,
    sec_penalty_seed: float,
) -> tuple[float, str]:
    """Score whether a speculative idea has a realistic research/position-sizing path."""
    score = 50.0
    reasons = []
    price = to_float(row.get("price"))
    volume = to_float(row.get("volume"))

    if data_confidence >= 75:
        score += 16
        reasons.append("solid evidence record")
    elif data_confidence < 50:
        score -= 18
        reasons.append("thin evidence record")
    if dollar_volume is not None and dollar_volume >= 1_000_000:
        score += 18
        reasons.append("institutionally visible dollar volume")
    elif dollar_volume is not None and dollar_volume >= 250_000:
        score += 10
        reasons.append("workable dollar volume")
    elif dollar_volume is not None and dollar_volume < 50_000:
        score -= 18
        reasons.append("hard-to-size liquidity")
    if market_cap is not None and market_cap >= 50_000_000:
        score += 10
        reasons.append("less orphaned market cap")
    elif market_cap is not None and market_cap < 10_000_000:
        score -= 10
        reasons.append("very tiny capitalization")
    if price is not None and price < 0.25:
        score -= 10
        reasons.append("extreme penny-stock execution risk")
    if volume is not None and volume <= 0:
        score -= 15
        reasons.append("no visible volume")
    if bool(row.get("is_illiquid")):
        score -= 10
        reasons.append("illiquidity flag")
    if sec_penalty_seed >= 35:
        score -= 12
        reasons.append("dilution/survival drag")
    if is_noise_security(row):
        score -= 25
        reasons.append("non-common-stock/noise security")

    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "ordinary portfolio viability"


def score_relative_mispricing(
    row: pd.Series,
    sector_stats: dict[str, float],
    config: dict[str, Any],
    sub: dict[str, Any],
) -> tuple[float, str]:
    """Score relative cheapness/usefulness versus sector and resource constraints."""
    score = 0.0
    reasons = []
    market_cap = to_float(row.get("market_cap"))
    sector_market_cap = sector_stats.get("median_market_cap") or 0
    return_20d = to_float(row.get("return_20d"))
    sector_return_20d = sector_stats.get("median_return_20d") or 0
    near_low = clean_float(row.get("near_52w_low_score"))

    cap_ratio = safe_divide(market_cap, sector_market_cap)
    if cap_ratio is not None and cap_ratio > 0:
        score += min(30, max(0, math.log1p(1 / max(cap_ratio, 0.01)) / math.log1p(10) * 30))
    if cap_ratio is not None and cap_ratio < 0.35:
        reasons.append("small versus sector median")
    if return_20d is not None and return_20d < sector_return_20d:
        score += min(18, max(0, sector_return_20d - return_20d) * 45 + 4)
        reasons.append("ticker lagging sector return")
    score += near_low * 0.16
    if near_low >= 70:
        reasons.append("near lows despite sector membership")
    score += clean_float(sub.get("technology_usefulness_score")) * 0.08
    if sub["technology_usefulness_score"] >= 70:
        reasons.append("technology usefulness adjustment")
    score += clean_float(sub.get("ricardo_productivity_score")) * 0.09
    if sub["ricardo_productivity_score"] >= 70:
        reasons.append("Ricardo productivity adjustment")
    score += clean_float(sub.get("malthus_constraint_score")) * 0.06
    if sub["malthus_constraint_score"] >= 70:
        reasons.append("Malthus constraint adjustment")
    if sub["boring_beneficiary_flag"]:
        score += 8
        reasons.append("boring beneficiary: useful but under-narrated")
    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "limited relative mispricing evidence"


def score_dcf_plausibility(row: pd.Series) -> dict[str, Any]:
    """Score whether future cash-flow belief is plausible without building a fake DCF."""
    cash = to_float(row.get("cash"))
    market_cap = to_float(row.get("market_cap"))
    revenue = to_float(row.get("revenue"))
    operating_cash_flow = to_float(row.get("operating_cash_flow"))
    net_income = to_float(row.get("net_income"))
    current_ratio = to_float(row.get("current_ratio"))
    liability_ratio = to_float(row.get("liabilities_to_assets"))
    revenue_to_market = to_float(row.get("revenue_to_market_cap"))
    cash_to_market = to_float(row.get("cash_to_market_cap"))
    ocf_to_assets = to_float(row.get("operating_cash_flow_to_assets"))
    near_low = clean_float(row.get("near_52w_low_score"))
    all_time_drawdown = clean_float(row.get("all_time_drawdown"))
    catalyst = clean_float(row.get("catalyst_signal_score"))
    narrative = clean_float(row.get("narrative_trigger_score"))
    filing_activity = clean_float(row.get("filing_activity_score"))
    survival = clean_float(row.get("survival_risk_score"))
    dilution = clean_float(row.get("dilution_pressure_score"))

    monthly_burn = None
    runway_months = None
    if operating_cash_flow is not None and operating_cash_flow < 0:
        monthly_burn = abs(operating_cash_flow) / 12
        runway_months = safe_divide(cash, monthly_burn) if cash is not None and monthly_burn else None
    elif operating_cash_flow is not None and operating_cash_flow >= 0:
        runway_months = 36

    plausibility_points = 0
    reasons = []
    if runway_months is not None:
        if runway_months >= 24:
            plausibility_points += 1.2
            reasons.append("comfortable runway proxy")
        elif runway_months >= 12:
            plausibility_points += 0.9
            reasons.append("workable runway proxy")
        elif runway_months >= 6:
            plausibility_points += 0.45
            reasons.append("short but nonzero runway proxy")
        else:
            plausibility_points -= 0.4
            reasons.append("runway proxy under 6 months")
    else:
        reasons.append("runway unknown")
    if operating_cash_flow is not None and operating_cash_flow >= 0:
        plausibility_points += 0.8
        reasons.append("operating cash flow is nonnegative")
    elif ocf_to_assets is not None and ocf_to_assets > -0.15:
        plausibility_points += 0.35
        reasons.append("burn intensity looks manageable")
    if revenue is not None and revenue > 0:
        plausibility_points += 0.35
        reasons.append("real revenue exists")
    if current_ratio is not None and current_ratio >= 1:
        plausibility_points += 0.35
        reasons.append("current ratio supports survival")
    elif current_ratio is not None and current_ratio < 0.6:
        plausibility_points -= 0.35
        reasons.append("weak current ratio")
    if liability_ratio is not None and liability_ratio <= 0.65:
        plausibility_points += 0.25
        reasons.append("liability load is manageable")
    elif liability_ratio is not None and liability_ratio > 1:
        plausibility_points -= 0.35
        reasons.append("liabilities exceed assets")
    if catalyst >= 50 or narrative >= 60 or filing_activity >= 70:
        plausibility_points += 0.25
        reasons.append("near-term belief/catalyst evidence")
    if dilution >= 70 or survival >= 70:
        plausibility_points -= 0.45
        reasons.append("SEC risk pressures viability")

    if plausibility_points >= 2.15:
        plausibility = 3
    elif plausibility_points >= 1.2:
        plausibility = 2
    elif plausibility_points >= 0.35:
        plausibility = 1
    else:
        plausibility = 0

    expectation_gap = 0.0
    if market_cap is not None and market_cap < 50_000_000:
        expectation_gap += 18
    elif market_cap is not None and market_cap < 300_000_000:
        expectation_gap += 10
    if revenue_to_market is not None:
        expectation_gap += min(28, revenue_to_market * 18)
    if cash_to_market is not None:
        expectation_gap += min(22, cash_to_market * 45)
    if near_low >= 70:
        expectation_gap += 12
    if all_time_drawdown <= -0.75:
        expectation_gap += 12
    if plausibility >= 2:
        expectation_gap += 12
    if survival >= 70 or dilution >= 70:
        expectation_gap -= 12
    expectation_gap = round(max(0, min(100, expectation_gap)), 1)

    if runway_months is not None and runway_months >= 12 and (catalyst >= 50 or operating_cash_flow is not None and operating_cash_flow >= 0):
        viability = "< 12 months"
        viability_score = 85
    elif runway_months is not None and runway_months >= 12:
        viability = "1-3 years"
        viability_score = 65
    elif runway_months is not None and runway_months >= 6 and (catalyst >= 50 or narrative >= 60):
        viability = "1-3 years"
        viability_score = 55
    elif plausibility >= 1 and (catalyst >= 50 or narrative >= 60):
        viability = "3+ years / narrative dependent"
        viability_score = 35
    else:
        viability = "unknown"
        viability_score = 15

    runway_text = f"runway proxy={round(runway_months, 1)} months" if runway_months is not None else "runway proxy unknown"
    note = (
        f"{runway_text}; DCF plausibility={plausibility}/3; expectation gap={expectation_gap}. "
        + "; ".join(reasons[:5])
    )
    return {
        "dcf_plausibility_score": plausibility,
        "expectation_gap_score": expectation_gap,
        "time_to_viability": viability,
        "time_to_viability_score": viability_score,
        "dcf_plausibility_note": note,
    }


def score_asymmetry(row: pd.Series, config: dict[str, Any], sub: dict[str, Any], dcf: dict[str, Any] | None = None) -> tuple[float, str]:
    """Score upside convexity versus fragility and hype penalties."""
    thresholds = config["scoring"]["thresholds"]
    dcf = dcf or {}
    score = 0.0
    reasons = []
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    explosive = clean_float(row.get("explosive_behavior_score"))

    if market_cap is not None and market_cap > 0:
        cap_pressure = max(0, math.log10(max(thresholds["small_market_cap"], 1)) - math.log10(max(market_cap, 1)))
        score += min(28, cap_pressure * 8)
    if market_cap is not None and market_cap < thresholds["very_low_market_cap"]:
        reasons.append("tiny capitalization")
    elif market_cap is not None and market_cap < thresholds["small_market_cap"]:
        reasons.append("small capitalization")
    if price is not None and price > 0:
        score += max(0, min(18, (5 - min(price, 5)) / 5 * 18))
    if price is not None and price < 1:
        reasons.append("sub-dollar convexity")
    elif price is not None and price < 5:
        reasons.append("low nominal price")
    if dollar_volume is not None and thresholds["low_dollar_volume"] <= dollar_volume <= thresholds["high_dollar_volume"] * 5:
        sweet_spot = 1 - min(1, abs(dollar_volume - thresholds["high_dollar_volume"]) / max(thresholds["high_dollar_volume"] * 5, 1))
        score += max(4, sweet_spot * 14)
        reasons.append("movable liquidity")
    score += max(clean_float(sub.get("technology_usefulness_score")), clean_float(sub.get("ricardo_productivity_score"))) * 0.07
    if sub["technology_usefulness_score"] >= 70 or sub["ricardo_productivity_score"] >= 70:
        reasons.append("usefulness/productivity optionality")
    if explosive >= 50:
        score += min(12, explosive * 0.12)
        reasons.append("prior explosive behavior")
    dcf_plausibility = clean_float(dcf.get("dcf_plausibility_score"))
    expectation_gap = clean_float(dcf.get("expectation_gap_score"))
    if dcf_plausibility >= 2 and expectation_gap >= 45:
        score += 12
        reasons.append("DCF plausibility plus expectation gap")
    elif dcf_plausibility >= 2:
        score += 7
        reasons.append("future cash-flow plausibility")
    elif dcf_plausibility == 0 and sub["technology_narrative_score"] >= 70:
        score -= 8
        reasons.append("story without DCF plausibility")
    if dilution >= 70:
        score -= min(15, dilution * 0.15)
        reasons.append("dilution penalty")
    if sub["tech_hype_warning"] > 0:
        score -= sub["tech_hype_warning"]
        reasons.append("tech hype warning penalty")
    return round(max(0, min(100, score)), 1), "; ".join(reasons) or "limited asymmetry evidence"


def score_data_confidence(row: pd.Series) -> tuple[float, str, str]:
    """Score the quality and completeness of the evidence record, not investment conviction."""
    score = 0.0
    present = []
    missing = []
    if pd.notna(row.get("price")):
        score += 15
        present.append("price")
    else:
        missing.append("price")
    if pd.notna(row.get("market_cap")):
        score += 15
        present.append("market cap")
    else:
        missing.append("market cap")
    if pd.notna(row.get("volume")):
        score += 10
        present.append("volume")
    else:
        missing.append("volume")
    if pd.notna(row.get("avg_volume")):
        score += 10
        present.append("average volume")
    else:
        missing.append("average volume")
    if pd.notna(row.get("dollar_volume")):
        score += 10
        present.append("dollar volume")
    else:
        missing.append("dollar volume")
    if pd.notna(row.get("company_name")):
        score += 8
        present.append("company name")
    else:
        missing.append("company name")
    if pd.notna(row.get("sector")):
        score += 8
        present.append("sector")
    else:
        missing.append("sector")
    if pd.notna(row.get("industry")):
        score += 8
        present.append("industry")
    else:
        missing.append("industry")
    if (to_float(row.get("filing_activity_score")) or 0) > 0 or (to_float(row.get("dilution_pressure_score")) or 0) > 0:
        score += 8
        present.append("SEC signal metadata")
    else:
        missing.append("SEC signal metadata")
    if str(row.get("price_history_status") or "").lower() == "ok":
        score += 8
        present.append("price history")
    else:
        missing.append("price history")

    score = round(min(100, score), 1)
    if score >= 75:
        label = "high confidence"
    elif score >= 50:
        label = "medium confidence"
    elif score >= 25:
        label = "low confidence"
    else:
        label = "data fragile"
    explanation = f"Evidence present: {', '.join(present) or 'limited'}."
    if missing:
        explanation += f" Missing/weak: {', '.join(missing)}."
    return score, label, explanation


def get_event_override(row: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    """Return manual event-shock adjustments for known thesis-changing events."""
    ticker = str(row.get("ticker") or "").upper().strip()
    override = config.get("scoring", {}).get("event_overrides", {}).get(ticker, {})
    event_config = config.get("event_shocks", {})
    computed_shock = clean_float(row.get("event_shock_score"))
    computed_thesis_break = clean_float(row.get("event_thesis_break_risk_score"))
    computed_note = str(row.get("event_shock_reason") or "")
    computed_label = str(row.get("event_shock_label") or "")
    computed_confidence = str(row.get("event_shock_confidence") or "")
    callout_only_labels = {
        str(label).strip()
        for label in event_config.get("callout_only_detail_labels", [])
    }
    if computed_confidence == "metadata_only" and computed_label.startswith("metadata_"):
        computed_penalty = clean_float(event_config.get("metadata_only_penalty", 0))
    elif computed_label.startswith("routine_"):
        computed_penalty = clean_float(event_config.get("routine_detail_penalty", 0))
    elif computed_label == "liquidation_or_dissolution":
        computed_penalty = 70
    elif computed_label in callout_only_labels:
        computed_penalty = 0
    else:
        computed_penalty = min(35, computed_shock * 0.35)
    manual_note = str(override.get("note") or "")
    notes = []
    if manual_note:
        notes.append(manual_note)
    if computed_shock > 0:
        notes.append(f"{computed_label}: {computed_note}".strip(": "))
    return {
        "event_shock_penalty": max(clean_float(override.get("event_shock_penalty")), computed_penalty),
        "thesis_break_risk_score": max(clean_float(override.get("thesis_break_risk_score")), computed_thesis_break),
        "catalyst_probability_adjustment": clean_float(override.get("catalyst_probability_adjustment")),
        "event_override_note": " | ".join(notes),
    }


def score_catalyst_probability(row: pd.Series, event_override: dict[str, Any] | None = None) -> float:
    """Estimate catalyst probability from SEC activity, narrative triggers, and fresh flow."""
    event_override = event_override or {}
    catalyst = clean_float(row.get("catalyst_signal_score"))
    narrative = clean_float(row.get("narrative_trigger_score"))
    filing_activity = clean_float(row.get("filing_activity_score"))
    return_5d = clean_float(row.get("return_5d"))
    rel_vol = max(clean_float(row.get("relative_volume_20d")), clean_float(row.get("relative_volume_60d")))
    compression = clean_float(row.get("compression_5d_score"))
    breakout = clean_float(row.get("breakout_proximity_score"))
    score = catalyst * 0.32 + narrative * 0.24 + filing_activity * 0.18
    score += min(12, rel_vol * 4)
    if return_5d > 0:
        score += min(8, return_5d * 40)
    if compression >= 70 and breakout >= 85:
        score += 8
    score += clean_float(event_override.get("catalyst_probability_adjustment"))
    return round(max(0, min(100, score)), 1)


def compute_factor_stack(
    austrian: float,
    hume: float,
    keynes: float,
    relative: float,
    asymmetry: float,
    data_confidence: float,
    catalyst_probability: float,
    row: pd.Series,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build finance/economics sub-factors from available market, SEC, and accounting data."""
    thresholds = config["scoring"]["thresholds"]
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    cash = to_float(row.get("cash"))
    current_assets = to_float(row.get("current_assets"))
    current_liabilities = to_float(row.get("current_liabilities"))
    total_assets = to_float(row.get("total_assets"))
    total_liabilities = to_float(row.get("total_liabilities"))
    revenue = to_float(row.get("revenue"))
    operating_cash_flow = to_float(row.get("operating_cash_flow"))
    net_income = to_float(row.get("net_income"))
    raw_dilution_value = to_float(row.get("dilution_pressure_score"))
    raw_survival_value = to_float(row.get("survival_risk_score"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    catalyst = clean_float(row.get("catalyst_signal_score"))
    narrative = clean_float(row.get("narrative_trigger_score"))
    filing_activity = clean_float(row.get("filing_activity_score"))
    rel_vol = max(clean_float(row.get("relative_volume_20d")), clean_float(row.get("relative_volume_60d")))
    volume_to_float = clean_float(row.get("volume_to_float"))
    breakout_proximity = clean_float(row.get("breakout_proximity_score"))
    compression = clean_float(row.get("compression_5d_score"))
    return_20d = clean_float(row.get("return_20d"))
    near_low = clean_float(row.get("near_52w_low_score"))
    explosive = clean_float(row.get("explosive_behavior_score"))
    animal_spirits, animal_spirits_note = score_animal_spirits(row, config, compute_subsignals(row, config))

    cash_to_market = to_float(row.get("cash_to_market_cap"))
    if cash_to_market is None:
        cash_to_market = safe_divide(cash, market_cap) if cash is not None and market_cap else None
    revenue_to_market = to_float(row.get("revenue_to_market_cap"))
    if revenue_to_market is None:
        revenue_to_market = safe_divide(revenue, market_cap) if revenue is not None and market_cap else None
    current_ratio = to_float(row.get("current_ratio"))
    if current_ratio is None:
        current_ratio = safe_divide(current_assets, current_liabilities) if current_assets is not None and current_liabilities else None
    liability_ratio = to_float(row.get("liabilities_to_assets"))
    if liability_ratio is None:
        liability_ratio = safe_divide(total_liabilities, total_assets) if total_liabilities is not None and total_assets else None
    ocf_to_assets = to_float(row.get("operating_cash_flow_to_assets"))
    if ocf_to_assets is None:
        ocf_to_assets = safe_divide(operating_cash_flow, total_assets) if operating_cash_flow is not None and total_assets else None
    roa = to_float(row.get("return_on_assets"))
    if roa is None:
        roa = safe_divide(net_income, total_assets) if net_income is not None and total_assets else None

    accounting_quality = 45.0
    accounting_reasons = ["fundamentals sparse"]
    if any(value is not None for value in [cash, current_assets, total_assets, revenue, net_income, operating_cash_flow]):
        accounting_quality = 50.0
        accounting_reasons = []
        if cash_to_market is not None and cash_to_market >= 0.25:
            accounting_quality += 14
            accounting_reasons.append("cash/market cap cushion")
        if current_ratio is not None and current_ratio >= 1.5:
            accounting_quality += 12
            accounting_reasons.append("current ratio support")
        elif current_ratio is not None and current_ratio < 0.8:
            accounting_quality -= 14
            accounting_reasons.append("weak current ratio")
        if liability_ratio is not None and liability_ratio <= 0.55:
            accounting_quality += 10
            accounting_reasons.append("manageable liabilities/assets")
        elif liability_ratio is not None and liability_ratio > 0.85:
            accounting_quality -= 16
            accounting_reasons.append("heavy liabilities/assets")
        if revenue_to_market is not None and revenue_to_market >= 1:
            accounting_quality += 12
            accounting_reasons.append("revenue/market cap support")
        if ocf_to_assets is not None and ocf_to_assets > 0:
            accounting_quality += 10
            accounting_reasons.append("positive operating cash flow/assets")
        if roa is not None and roa > 0:
            accounting_quality += 8
            accounting_reasons.append("positive net income/assets")

    pricing_gap = min(
        100,
        austrian * 0.45
        + relative * 0.35
        + near_low * 0.15
        + (15 if market_cap is not None and market_cap < thresholds["very_low_market_cap"] else 0),
    )
    flow_factor = min(
        100,
        hume * 0.65
        + min(20, rel_vol * 6)
        + (10 if return_20d > 0 else 0)
        + min(15, filing_activity * 0.15),
    )
    story_factor = min(100, keynes * 0.58 + narrative * 0.12 + catalyst * 0.12 + catalyst_probability * 0.18)
    relative_value = min(
        100,
        relative * 0.65
        + (min(25, revenue_to_market * 12) if revenue_to_market is not None else 0)
        + (min(20, cash_to_market * 40) if cash_to_market is not None else 0)
        + (10 if market_cap is not None and market_cap < thresholds["small_market_cap"] else 0),
    )
    convexity = min(
        100,
        asymmetry * 0.60
        + (20 if market_cap is not None and market_cap < thresholds["very_low_market_cap"] else 0)
        + (10 if price is not None and price < 5 else 0)
        + (10 if dollar_volume is not None and thresholds["low_dollar_volume"] <= dollar_volume <= thresholds["high_dollar_volume"] * 5 else 0)
        + explosive * 0.10,
    )
    trading_setup = min(
        100,
        flow_factor * 0.35
        + min(20, volume_to_float * 100)
        + breakout_proximity * 0.20
        + compression * 0.20
        + min(15, rel_vol * 4),
    )
    portfolio_viability, portfolio_note = score_portfolio_viability(
        row,
        data_confidence,
        dollar_volume,
        market_cap,
        sec_penalty_seed=dilution * 0.38 + survival * 0.25,
    )
    has_sec_risk_data = (
        (raw_dilution_value is not None and not pd.isna(raw_dilution_value))
        or (raw_survival_value is not None and not pd.isna(raw_survival_value))
        or catalyst > 0
        or narrative > 0
        or filing_activity > 0
    )
    sec_penalty = 0.0
    if has_sec_risk_data:
        sec_penalty = min(45, dilution * 0.22 + survival * 0.18)
        if dilution >= 70 and catalyst_probability < 45:
            sec_penalty += 7
        elif dilution >= 70:
            sec_penalty += 4
        if survival >= 70 and flow_factor < 45:
            sec_penalty += 6
        if dilution >= 85:
            sec_penalty += 5
        sec_penalty = min(50, sec_penalty)

    note_bits = [
        f"pricing_gap={round(pricing_gap, 1)}",
        f"flow={round(flow_factor, 1)}",
        f"story={round(story_factor, 1)}",
        f"relative_value={round(relative_value, 1)}",
        f"convexity={round(convexity, 1)}",
        f"trading_setup={round(trading_setup, 1)}",
        f"animal_spirits={round(animal_spirits, 1)}",
        f"portfolio_viability={round(portfolio_viability, 1)}",
        f"catalyst_probability={round(catalyst_probability, 1)}",
        f"sec_penalty={round(sec_penalty, 1)}",
        f"accounting={round(max(0, min(100, accounting_quality)), 1)}",
    ]
    if animal_spirits_note:
        note_bits.append("animal_spirits_note=" + animal_spirits_note)
    if portfolio_note:
        note_bits.append("portfolio_note=" + portfolio_note)
    if accounting_reasons:
        note_bits.append("accounting_note=" + ", ".join(accounting_reasons[:3]))

    return {
        "pricing_gap_factor": round(max(0, min(100, pricing_gap)), 1),
        "flow_factor": round(max(0, min(100, flow_factor)), 1),
        "story_attention_factor": round(max(0, min(100, story_factor)), 1),
        "relative_value_factor": round(max(0, min(100, relative_value)), 1),
        "convexity_factor": round(max(0, min(100, convexity)), 1),
        "trading_setup_factor": round(max(0, min(100, trading_setup)), 1),
        "animal_spirits_factor": round(max(0, min(100, animal_spirits)), 1),
        "portfolio_viability_factor": round(max(0, min(100, portfolio_viability)), 1),
        "sec_risk_penalty": round(max(0, sec_penalty), 1),
        "accounting_quality_factor": round(max(0, min(100, accounting_quality)), 1),
        "factor_stack_note": "; ".join(note_bits),
    }


def saturating_allowance(raw: float, scale: float, max_allowed: float) -> float:
    """Allow diminishing marginal value for repeated evidence-family exposure."""
    raw = max(0.0, clean_float(raw))
    if raw <= 0:
        return 0.0
    return min(max_allowed, 100 * (1 - math.exp(-raw / scale)))


def echo_family_penalty(raw: float, scale: float, max_allowed: float, penalty_rate: float = 0.18) -> float:
    """Turn repeated evidence-family exposure into a modest score penalty."""
    allowed = saturating_allowance(raw, scale, max_allowed)
    return max(0.0, clean_float(raw) - allowed) * penalty_rate


def compute_echo_control(row: pd.Series, factors: dict[str, Any]) -> dict[str, Any]:
    """Penalize repeated evidence families without erasing the philosopher lenses."""
    price = to_float(row.get("price"))
    market_cap = to_float(row.get("market_cap"))
    dollar_volume = to_float(row.get("dollar_volume"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    filing_activity = clean_float(row.get("filing_activity_score"))
    narrative = clean_float(row.get("narrative_trigger_score"))
    catalyst = clean_float(row.get("catalyst_signal_score"))

    small_cap_raw = 0.0
    if market_cap is not None and market_cap < 50_000_000:
        small_cap_raw += 20
    if market_cap is not None and market_cap < 300_000_000:
        small_cap_raw += 14
    small_cap_raw += clean_float(factors.get("pricing_gap_factor")) * 0.12
    small_cap_raw += clean_float(factors.get("convexity_factor")) * 0.18
    small_cap_raw += clean_float(factors.get("relative_value_factor")) * 0.08

    low_price_raw = 0.0
    if price is not None and price < 1:
        low_price_raw += 18
    elif price is not None and price < 5:
        low_price_raw += 10
    if price is not None and price < 5:
        low_price_raw += clean_float(factors.get("animal_spirits_factor")) * 0.04
        low_price_raw += clean_float(factors.get("convexity_factor")) * 0.08

    liquidity_raw = 0.0
    if dollar_volume is not None and dollar_volume >= 1_000_000:
        liquidity_raw += 18
    elif dollar_volume is not None and dollar_volume >= 50_000:
        liquidity_raw += 12
    liquidity_raw += clean_float(factors.get("flow_factor")) * 0.18
    liquidity_raw += clean_float(factors.get("trading_setup_factor")) * 0.22
    liquidity_raw += clean_float(factors.get("portfolio_viability_factor")) * 0.06

    narrative_raw = clean_float(factors.get("story_attention_factor")) * 0.22
    narrative_raw += clean_float(factors.get("animal_spirits_factor")) * 0.22
    narrative_raw += narrative * 0.10 + catalyst * 0.08 + filing_activity * 0.04

    distress_raw = clean_float(factors.get("pricing_gap_factor")) * 0.16
    distress_raw += clean_float(factors.get("sec_risk_penalty")) * 0.35
    distress_raw += dilution * 0.10 + survival * 0.10

    penalties = {
        "small_cap_echo_penalty": echo_family_penalty(small_cap_raw, scale=24, max_allowed=30),
        "low_price_echo_penalty": echo_family_penalty(low_price_raw, scale=16, max_allowed=18),
        "liquidity_echo_penalty": echo_family_penalty(liquidity_raw, scale=28, max_allowed=34),
        "narrative_echo_penalty": echo_family_penalty(narrative_raw, scale=30, max_allowed=36),
        "distress_echo_penalty": echo_family_penalty(distress_raw, scale=24, max_allowed=30),
    }
    total = round(min(22, sum(penalties.values())), 1)
    note = (
        "Echo control reduces repeated evidence-family exposure; it does not delete Austrian, Hume, "
        "or Keynes signals. Biggest drags: "
        + ", ".join(
            f"{name.replace('_echo_penalty', '').replace('_', ' ')}={round(value, 1)}"
            for name, value in sorted(penalties.items(), key=lambda item: item[1], reverse=True)
            if value > 0.2
        )[:220]
    )
    if total <= 0:
        note = "Echo control found little repeated evidence-family exposure."
    return {
        **{key: round(value, 1) for key, value in penalties.items()},
        "echo_penalty_total": total,
        "echo_control_note": note,
    }


def apply_echo_adjustment(raw_score: float, echo_penalty: float) -> float:
    """Use echo-adjusted scores as the main scores while preserving raw diagnostics."""
    return round(max(0, min(100, clean_float(raw_score) - clean_float(echo_penalty))), 1)


def score_zombie_decay(row: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    """Penalize stale long-lived names unless recent price/volume action is dynamic."""
    settings = config.get("scoring", {}).get("zombie_decay", {})
    if not settings.get("enabled", True):
        return {
            "zombie_decay_penalty": 0.0,
            "zombie_decay_label": "Zombie decay off",
            "zombie_decay_note": "Zombie decay is disabled in config.",
        }
    age = clean_float(row.get("public_age_years_proxy"))
    dynamism = clean_float(row.get("recent_dynamism_score"))
    explosive = clean_float(row.get("explosive_behavior_score"))
    return_20d = abs(clean_float(row.get("return_20d")))
    return_60d = abs(clean_float(row.get("return_60d")))
    rel_vol = max(clean_float(row.get("relative_volume_20d")), clean_float(row.get("relative_volume_60d")))
    if age <= 0:
        return {
            "zombie_decay_penalty": 0.0,
            "zombie_decay_label": "Age unknown",
            "zombie_decay_note": "Not enough long-horizon price history to apply zombie decay.",
        }
    start = clean_float(settings.get("age_start_years", 3), 3)
    full = max(start + 1, clean_float(settings.get("age_full_years", 10), 10))
    max_penalty = clean_float(settings.get("max_penalty", 18), 18)
    age_pressure = max(0.0, min(1.0, (age - start) / (full - start)))
    raw_penalty = max_penalty * age_pressure
    dynamic_offset = min(
        max_penalty * 0.85,
        dynamism * clean_float(settings.get("dynamism_offset_strength", 0.12), 0.12)
        + explosive * 0.04
        + min(4, rel_vol * 0.8)
        + min(4, (return_20d + return_60d) * 4),
    )
    penalty = round(max(0, raw_penalty - dynamic_offset), 1)
    high_dynamic = dynamism >= clean_float(settings.get("high_dynamism_threshold", 65), 65)
    if penalty >= max_penalty * 0.65:
        label = "Zombie drag"
    elif penalty > 0:
        label = "Some zombie drag"
    elif age >= start and high_dynamic:
        label = "Old but still violent"
    elif age >= start:
        label = "Old but not punished"
    else:
        label = "Fresh enough"
    note = (
        f"Age proxy={round(age, 2)} years; recent dynamism={round(dynamism, 1)}; "
        f"raw stale penalty={round(raw_penalty, 1)}; dynamism offset={round(dynamic_offset, 1)}."
    )
    return {
        "zombie_decay_penalty": penalty,
        "zombie_decay_label": label,
        "zombie_decay_note": note,
    }


def apply_zombie_decay_to_score(raw_score: float, zombie_decay: dict[str, Any], multiplier: float = 1.0) -> float:
    """Apply zombie decay while preserving separate diagnostic columns."""
    penalty = clean_float((zombie_decay or {}).get("zombie_decay_penalty")) * multiplier
    return round(max(0, min(100, clean_float(raw_score) - penalty)), 1)


def score_movement_potential(
    austrian: float,
    hume: float,
    keynes: float,
    relative: float,
    asymmetry: float,
    data_confidence: float,
    row: pd.Series,
    factors: dict[str, Any],
    event_override: dict[str, Any] | None = None,
    zombie_decay: dict[str, Any] | None = None,
) -> float:
    """Compute an A-to-F style movement potential score from all major signals."""
    event_override = event_override or {}
    zombie_decay = zombie_decay or {}
    pricing_gap = to_float(factors.get("pricing_gap_factor")) or 0
    flow = to_float(factors.get("flow_factor")) or 0
    story = to_float(factors.get("story_attention_factor")) or 0
    relative_value = to_float(factors.get("relative_value_factor")) or 0
    convexity = to_float(factors.get("convexity_factor")) or 0
    trading_setup = to_float(factors.get("trading_setup_factor")) or 0
    portfolio_viability = to_float(factors.get("portfolio_viability_factor")) or 50
    sec_penalty = to_float(factors.get("sec_risk_penalty")) or 0
    accounting = to_float(factors.get("accounting_quality_factor")) or 45
    catalyst_probability = score_catalyst_probability(row, event_override)
    event_shock_penalty = clean_float(event_override.get("event_shock_penalty"))
    thesis_break_risk = clean_float(event_override.get("thesis_break_risk_score"))
    score = (
        austrian * 0.15
        + hume * 0.18
        + keynes * 0.18
        + relative * 0.15
        + asymmetry * 0.14
        + pricing_gap * 0.06
        + flow * 0.05
        + story * 0.05
        + relative_value * 0.04
        + convexity * 0.04
        + trading_setup * 0.03
        + accounting * 0.02
        + data_confidence * 0.01
    )
    if pricing_gap >= 60 and flow >= 50 and story >= 65:
        score += 8
    if relative_value >= 50 and convexity >= 50:
        score += 8
    if flow >= 55 and convexity >= 50:
        score += 5
    if trading_setup >= 65 and catalyst_probability >= 55:
        score += 5
    pre_flow_probe = score_pre_flow_opportunity(relative, asymmetry, data_confidence, factors, row, event_override)
    pre_flow_gap = pre_flow_probe - hume
    if pre_flow_gap >= 12 and hume < 60 and not is_hard_stop_event(row, event_override):
        score += min(6, pre_flow_gap * 0.10)
    if austrian >= 70 and flow < 35 and story < 45:
        score -= 12
    score -= sec_penalty * 0.28
    score -= event_shock_penalty * 0.32
    score -= clean_float(zombie_decay.get("zombie_decay_penalty")) * 0.35
    if is_hard_stop_event(row, event_override):
        score = min(score, 18)
    if thesis_break_risk >= 80 and catalyst_probability < 50:
        score -= 3
    return round(max(0, min(100, score)), 1)


def score_pre_flow_opportunity(
    relative: float,
    asymmetry: float,
    data_confidence: float,
    factors: dict[str, Any],
    row: pd.Series,
    event_override: dict[str, Any] | None = None,
) -> float:
    """Score latent opportunity before requiring Hume flow confirmation."""
    event_override = event_override or {}
    pricing_gap = clean_float(factors.get("pricing_gap_factor"))
    story = clean_float(factors.get("story_attention_factor"))
    relative_value = clean_float(factors.get("relative_value_factor"))
    convexity = clean_float(factors.get("convexity_factor"))
    accounting = clean_float(factors.get("accounting_quality_factor"), 45)
    portfolio_viability = clean_float(factors.get("portfolio_viability_factor"), 50)
    sec_penalty = clean_float(factors.get("sec_risk_penalty"))
    event_shock = clean_float(event_override.get("event_shock_penalty"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    score = (
        pricing_gap * 0.22
        + story * 0.22
        + relative_value * 0.18
        + convexity * 0.18
        + relative * 0.08
        + asymmetry * 0.07
        + accounting * 0.03
        + portfolio_viability * 0.03
        + data_confidence * 0.01
    )
    if pricing_gap >= 60 and story >= 60 and (relative_value >= 50 or convexity >= 50):
        score += 6
    score -= sec_penalty * 0.20
    score -= event_shock * 0.25
    if is_hard_stop_event(row, event_override):
        score = min(score, 12)
    if thesis_break >= 80:
        score -= 3
    if is_noise_security(row):
        score -= 25
    return round(max(0, min(100, score)), 1)


def score_long_term_microcap(
    row: pd.Series,
    factors: dict[str, Any],
    dcf: dict[str, Any],
    zombie_decay: dict[str, Any],
    event_override: dict[str, Any],
    data_confidence: float,
) -> dict[str, Any]:
    """Score whether a microcap looks like a long-term research candidate."""
    accounting = clean_float(factors.get("accounting_quality_factor"), 45)
    portfolio = clean_float(factors.get("portfolio_viability_factor"), 50)
    dcf_score = clean_float(dcf.get("dcf_plausibility_score"))
    expectation_gap = clean_float(dcf.get("expectation_gap_score"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    zombie_penalty = clean_float(zombie_decay.get("zombie_decay_penalty"))
    event_penalty = clean_float(event_override.get("event_shock_penalty"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))

    current_ratio = to_float(row.get("current_ratio"))
    liabilities_to_assets = to_float(row.get("liabilities_to_assets"))
    revenue_to_market = to_float(row.get("revenue_to_market_cap"))
    cash_to_market = to_float(row.get("cash_to_market_cap"))
    operating_cash_flow = to_float(row.get("operating_cash_flow"))
    net_income = to_float(row.get("net_income"))

    score = (
        accounting * 0.25
        + portfolio * 0.18
        + min(100, dcf_score * 28) * 0.20
        + expectation_gap * 0.12
        + data_confidence * 0.10
        + clean_float(row.get("relative_mispricing_score")) * 0.08
        + clean_float(row.get("asymmetry_score")) * 0.04
    )
    reasons = []
    if operating_cash_flow is not None and operating_cash_flow >= 0:
        score += 8
        reasons.append("positive operating cash flow")
    if net_income is not None and net_income >= 0:
        score += 5
        reasons.append("positive net income")
    if current_ratio is not None and current_ratio >= 1.2:
        score += 5
        reasons.append("current ratio supports endurance")
    if liabilities_to_assets is not None and liabilities_to_assets <= 0.65:
        score += 4
        reasons.append("liabilities/assets look manageable")
    if revenue_to_market is not None and revenue_to_market >= 1:
        score += 5
        reasons.append("revenue is large versus market cap")
    if cash_to_market is not None and cash_to_market >= 0.25:
        score += 5
        reasons.append("cash cushion versus market cap")

    score -= dilution * 0.30
    score -= survival * 0.18
    score -= zombie_penalty * 1.15
    score -= event_penalty * 0.80
    if thesis_break >= 80:
        score -= 20
    if is_noise_security(row):
        score -= 30
        reasons.append("not a clean common-stock candidate")

    risk_bits = []
    cap_bits = []
    if is_hard_stop_event(row, event_override):
        score = min(score, 12)
        risk_bits.append("hard-stop event pattern")
        cap_bits.append("liquidation or severe reset/event-shock pattern blocks long-term treatment")
    if dilution >= 70:
        risk_bits.append("dilution")
    if dilution >= 85:
        score = min(score, 42)
        cap_bits.append("extreme dilution caps long-term quality")
    elif dilution >= 70:
        score = min(score, 58)
        cap_bits.append("dilution pressure caps long-term quality")
    if survival >= 70:
        risk_bits.append("survival")
        score = min(score, 45)
        cap_bits.append("survival risk caps long-term quality")
    if zombie_penalty > 0:
        risk_bits.append("stale public-company drag")
    if zombie_penalty >= 8:
        score = min(score, 58)
        cap_bits.append("zombie drag requires reacceleration proof")
    elif zombie_penalty > 0:
        score = min(score, 64)
        cap_bits.append("stale-company drag limits the label")
    if event_penalty > 0 or thesis_break >= 80:
        risk_bits.append("event shock")
    if event_penalty > 0:
        score = min(score, 58)
        cap_bits.append("event shock caps long-term quality")
    if thesis_break >= 80:
        score = min(score, 35)
        cap_bits.append("broken thesis needs reset before long-term treatment")
    if is_catastrophic_reset_cycle(row, event_override):
        score = min(score, 25)
        risk_bits.append("reverse-split/dilution-cycle pattern")
        cap_bits.append("catastrophic reset pattern blocks long-term treatment")

    score = round(max(0, min(100, score)), 1)
    if is_hard_stop_event(row, event_override) or is_catastrophic_reset_cycle(row, event_override) or dilution >= 85 or thesis_break >= 80:
        label = "Not Long-Term Material Yet"
    elif survival >= 70:
        label = "Speculative Survival Story"
    elif zombie_penalty >= 8 and score >= 45:
        label = "Old Business, Needs Reacceleration"
    elif zombie_penalty > 0 and score >= 45:
        label = "Business Looks Real, Risks Bite"
    elif score >= 75:
        label = "Long-Term Microcap Candidate"
    elif score >= 60:
        label = "Long-Term Watchlist"
    elif score >= 45:
        label = "Business Looks Real, Risks Bite"
    elif score >= 30:
        label = "Speculative Survival Story"
    else:
        label = "Not Long-Term Material Yet"
    note = (
        f"Long-term score blends accounting quality, portfolio viability, DCF plausibility, expectation gap, "
        f"and data quality, then subtracts dilution/survival/event/zombie risk. "
        f"Strengths: {', '.join(reasons[:5]) or 'none dominant'}."
    )
    if risk_bits:
        note += " Main drags: " + ", ".join(risk_bits) + "."
    if cap_bits:
        note += " Guardrails: " + ", ".join(cap_bits) + "."
    return {
        "long_term_investment_score": score,
        "long_term_investment_label": label,
        "long_term_investment_note": note,
    }


def movement_grade(score: float) -> str:
    """Convert movement score into a plain A+ to F- research grade."""
    if score >= 92:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 78:
        return "A-"
    if score >= 72:
        return "B+"
    if score >= 66:
        return "B"
    if score >= 60:
        return "B-"
    if score >= 54:
        return "C+"
    if score >= 48:
        return "C"
    if score >= 42:
        return "C-"
    if score >= 35:
        return "D"
    if score >= 25:
        return "F"
    return "F-"


def is_catastrophic_reset_cycle(row: pd.Series, event_override: dict[str, Any] | None = None) -> bool:
    """Return True for reverse-split/dilution-cycle patterns that should not get top labels."""
    event_override = event_override or {}
    all_time_drawdown = clean_float(row.get("all_time_drawdown"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    event_label = str(row.get("event_shock_label") or "").lower()
    event_reason = str(row.get("event_shock_reason") or "").lower()
    event_note = str(event_override.get("event_override_note") or "").lower()
    reverse_split_seen = (
        "reverse_split" in event_label
        or "reverse split" in event_reason
        or "reverse_split" in event_reason
        or "reverse split" in event_note
        or "reverse_split" in event_note
    )
    near_total_collapse = all_time_drawdown <= -0.97
    if near_total_collapse and (reverse_split_seen or dilution >= 60):
        return True
    if reverse_split_seen and dilution >= 60:
        return True
    return False


LIQUIDATION_TERMS = [
    "complete liquidation",
    "plan of liquidation",
    "plan of complete liquidation",
    "plan of dissolution",
    "dissolution and liquidation",
    "liquidation and dissolution",
    "orderly wind-down",
    "orderly wind down",
    "wind down of operations",
    "winddown of operations",
    "wind-down of operations",
    "certificate of dissolution",
    "delist its shares",
    "sell its technology and remaining assets",
    "sell its technology and other remaining assets",
]


def event_text_blob(row: pd.Series, event_override: dict[str, Any] | None = None) -> str:
    """Collect event text fields into one lowercase blob for hierarchy checks."""
    event_override = event_override or {}
    parts = [
        row.get("event_shock_label"),
        row.get("event_shock_reason"),
        row.get("event_callouts"),
        event_override.get("event_override_note"),
        row.get("thesis_integrity_note"),
    ]
    return " ".join(str(part).lower() for part in parts if part is not None)


def is_liquidation_event(row: pd.Series, event_override: dict[str, Any] | None = None) -> bool:
    """Return True when the event points to liquidation, dissolution, or wind-down."""
    text = event_text_blob(row, event_override)
    return "liquidation_or_dissolution" in text or any(term in text for term in LIQUIDATION_TERMS)


def is_hard_stop_event(row: pd.Series, event_override: dict[str, Any] | None = None) -> bool:
    """Return True for natural event patterns that should block candidate labels."""
    event_override = event_override or {}
    if is_liquidation_event(row, event_override):
        return True
    label = str(row.get("event_shock_label") or "").lower()
    confidence = str(row.get("event_shock_confidence") or "").lower()
    penalty = clean_float(event_override.get("event_shock_penalty"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    metadata_shock = label in {"event_shock_watch", "metadata_shock_suspected"} or confidence == "metadata_only"
    return bool(is_catastrophic_reset_cycle(row, event_override) and metadata_shock and (penalty >= 10 or thesis_break >= 70))


RESET_CATALYST_TERMS = [
    "appointed",
    "new chief executive",
    "new ceo",
    "new chief financial",
    "new cfo",
    "successor",
    "strategic alternative",
    "strategic review",
    "turnaround",
    "transformation",
    "restructuring plan",
    "cost reduction",
    "cost savings",
    "runway extension",
    "extended runway",
    "financing secured",
    "debt reduction",
    "debt exchange",
    "commercial launch",
    "commercialization",
    "contract award",
    "new contract",
    "purchase order",
    "partnership",
    "collaboration",
    "merger",
    "business combination",
    "asset sale",
    "divestiture",
]


def has_reset_catalyst(
    row: pd.Series,
    event_override: dict[str, Any] | None = None,
    movement_score: float = 0,
    hume: float = 0,
    keynes: float = 0,
    relative: float = 0,
    asymmetry: float = 0,
    dcf: dict[str, Any] | None = None,
    long_term: dict[str, Any] | None = None,
) -> bool:
    """Return True when a broken thesis has evidence of a possible new chapter."""
    event_override = event_override or {}
    dcf = dcf or {}
    long_term = long_term or {}
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    if thesis_break < 80:
        return False
    if is_liquidation_event(row, event_override):
        return False

    text = event_text_blob(row, event_override)
    text += " " + " ".join(str(row.get(field) or "").lower() for field in ["company_name", "sector", "industry"])
    forward_language = any(term in text for term in RESET_CATALYST_TERMS)
    plausible_path = clean_float(dcf.get("dcf_plausibility_score")) >= 2
    long_term_support = clean_float(long_term.get("long_term_investment_score")) >= 45
    signal_support = (
        movement_score >= 48
        and keynes >= 50
        and (hume >= 40 or relative >= 45 or asymmetry >= 45)
    )
    return bool(forward_language and (signal_support or plausible_path or long_term_support))


def personal_signal_label(
    movement_score: float,
    austrian: float,
    hume: float,
    keynes: float,
    relative: float,
    asymmetry: float,
    data_confidence: float,
    pre_flow_opportunity: float = 0,
    event_override: dict[str, Any] | None = None,
    row: pd.Series | None = None,
    zombie_decay: dict[str, Any] | None = None,
    dcf: dict[str, Any] | None = None,
    long_term: dict[str, Any] | None = None,
) -> str:
    """Return the comprehensive personal verdict after all major lenses."""
    event_override = event_override or {}
    row = row if row is not None else pd.Series(dtype=object)
    zombie_decay = zombie_decay or {}
    dcf = dcf or {}
    long_term = long_term or {}
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    zombie_penalty = clean_float(zombie_decay.get("zombie_decay_penalty"))
    dcf_plausibility = clean_float(dcf.get("dcf_plausibility_score"))
    long_term_score = clean_float(long_term.get("long_term_investment_score"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    event_penalty = clean_float(event_override.get("event_shock_penalty"))
    serious_dilution = dilution >= 85
    heavy_dilution = dilution >= 70
    serious_survival = survival >= 70
    stale_drag = zombie_penalty >= 8
    catastrophic_reset = is_catastrophic_reset_cycle(row, event_override)
    reset_catalyst = has_reset_catalyst(
        row,
        event_override,
        movement_score,
        hume,
        keynes,
        relative,
        asymmetry,
        dcf,
        long_term,
    )

    flag_haircut = min(
        12,
        dilution * 0.035
        + survival * 0.030
        + zombie_penalty * 0.20
        + event_penalty * 0.16
        + (6 if catastrophic_reset else 0),
    )
    comprehensive_score = (
        movement_score * 0.30
        + austrian * 0.13
        + hume * 0.15
        + keynes * 0.15
        + relative * 0.10
        + asymmetry * 0.10
        + pre_flow_opportunity * 0.05
        + data_confidence * 0.04
        + long_term_score * 0.03
        - flag_haircut
    )

    if is_hard_stop_event(row, event_override):
        return "This is Garbage"
    if thesis_break >= 80 and reset_catalyst and comprehensive_score >= 66 and not catastrophic_reset:
        return "SCOOBY DOOBY DOO!!"
    if thesis_break >= 80 and reset_catalyst and comprehensive_score >= 52:
        return "Scrappy Doo"
    if thesis_break >= 80:
        return "Old thesis broken, investigate"
    if data_confidence < 45 or movement_score < 25:
        return "This is Garbage"
    if serious_dilution and comprehensive_score < 40:
        return "This is Garbage"
    if serious_survival and comprehensive_score < 40:
        return "This is Garbage"
    if stale_drag and comprehensive_score < 38:
        return "This is Garbage"
    if catastrophic_reset and comprehensive_score >= 45:
        return "High Signal, Red Flags"
    if (serious_dilution or serious_survival) and comprehensive_score >= 45:
        return "High Signal, Red Flags"

    if (
        comprehensive_score >= 72
        and movement_score >= 60
        and hume >= 50
        and keynes >= 60
        and (relative >= 45 or asymmetry >= 45)
    ):
        return "SCOOBY DOOBY DOO!!"
    if (
        comprehensive_score >= 58
        and movement_score >= 48
        and keynes >= 50
        and (hume >= 40 or pre_flow_opportunity >= 55 or relative >= 45 or asymmetry >= 45)
    ):
        return "Scrappy Doo"
    if long_term_score >= 65 and movement_score < 55 and not heavy_dilution and not serious_survival and zombie_penalty <= 3:
        return "Long-Term Clue, Slow Fuse"
    if movement_score >= 55 and long_term_score >= 55 and stale_drag:
        return "Comeback Candidate, Needs Proof"
    if pre_flow_opportunity >= 55 and movement_score >= 45 and long_term_score >= 35 and hume < 45:
        return "Pricing Gap, Waiting on Volume"
    if movement_score < 42 and long_term_score < 55:
        return "This is Garbage"
    if movement_score < 42 and long_term_score >= 55 and not heavy_dilution and not serious_survival and zombie_penalty <= 3:
        return "Long-Term Clue, Slow Fuse"

    if austrian >= 70 and hume < 45 and keynes < 55:
        return "Hayek doesnt pick stocks"
    if keynes >= 75 and hume < 45 and relative < 35 and asymmetry < 35:
        return "Purely Animal Spirits"
    if hume >= 55 and austrian < 55 and keynes < 65:
        return "Adam Smith might like this"
    if movement_score >= 82 and hume >= 50 and keynes >= 70 and (relative >= 45 or asymmetry >= 45):
        return "SCOOBY DOOBY DOO!!"
    if (
        movement_score >= 68
        and keynes >= 65
        and (hume >= 45 or relative >= 45 or asymmetry >= 45)
        and zombie_penalty <= 3
        and long_term_score >= 45
        and dcf_plausibility >= 2
        and dilution < 70
        and survival < 70
    ):
        return "Scrappy Doo"
    if hume >= 55 and keynes >= 70 and relative < 35 and asymmetry < 35:
        return "Crowded Mystery Machine"
    if austrian >= 60 and keynes >= 70 and hume < 45:
        if movement_score >= 50 and data_confidence >= 50 and pre_flow_opportunity >= 55:
            return "Pricing Gap, Waiting on Volume"
        return "Paper Setup, Needs Proof"
    if relative >= 55 and asymmetry < 35:
        return "Value Clue, Tiny Engine"
    if asymmetry >= 55 and relative < 30:
        return "Rocket Shape, No Map"
    if hume >= 50 and relative >= 45 and keynes < 65:
        return "Quiet Clue, No Headline Yet"
    if comprehensive_score >= 50:
        return "Eh this is Mid"
    return "This is Garbage"


def apply_best_candidate_labels(scores: pd.DataFrame) -> pd.DataFrame:
    """Ensure the batch surfaces best-fit Scooby/Scrappy candidates without hiding caveats."""
    if scores.empty or "what_i_think" not in scores.columns:
        return scores

    output = scores.copy()
    if "label_basis" not in output.columns:
        output["label_basis"] = "strict model label"

    def number(column: str) -> pd.Series:
        return pd.to_numeric(output.get(column, pd.Series(0, index=output.index)), errors="coerce").fillna(0)

    movement = number("movement_score")
    long_term = number("long_term_investment_score")
    pre_flow = number("pre_flow_opportunity_score")
    hume = number("hume_flow_potential_score")
    keynes = number("keynes_repricing_potential_score")
    relative = number("relative_mispricing_score")
    asymmetry = number("asymmetry_score")
    data = number("data_confidence_score")
    dilution = number("dilution_pressure_score")
    survival = number("survival_risk_score")
    zombie = number("zombie_decay_penalty")
    event_penalty = number("event_shock_penalty")
    thesis_break = number("thesis_break_risk_score")
    all_time_drawdown = number("all_time_drawdown")
    event_label = output.get("event_shock_label", pd.Series("", index=output.index)).astype(str).str.lower()
    event_reason = output.get("event_shock_reason", pd.Series("", index=output.index)).astype(str).str.lower()
    event_note = output.get("event_override_note", pd.Series("", index=output.index)).astype(str).str.lower()
    reset_cycle = (
        (all_time_drawdown <= -0.97)
        & (
            event_label.str.contains("reverse_split", na=False)
            | event_reason.str.contains("reverse split|reverse_split", regex=True, na=False)
            | (dilution >= 60)
        )
    ) | (event_label.str.contains("reverse_split", na=False) & (dilution >= 60))
    liquidation_terms_pattern = "|".join(re.escape(term) for term in LIQUIDATION_TERMS)
    liquidation_event = (
        event_label.str.contains("liquidation_or_dissolution", na=False)
        | event_reason.str.contains(liquidation_terms_pattern, regex=True, na=False)
        | event_note.str.contains(liquidation_terms_pattern, regex=True, na=False)
    )
    event_confidence = output.get("event_shock_confidence", pd.Series("", index=output.index)).astype(str).str.lower()
    hard_stop_event = liquidation_event | (
        reset_cycle
        & (
            event_label.isin(["event_shock_watch", "metadata_shock_suspected"])
            | event_confidence.eq("metadata_only")
        )
        & ((event_penalty >= 10) | (thesis_break >= 70))
    )
    reset_text = event_label + " " + event_reason + " " + event_note
    reset_terms_pattern = "|".join(re.escape(term) for term in RESET_CATALYST_TERMS)
    reset_catalyst = (
        (thesis_break >= 80)
        & reset_text.str.contains(reset_terms_pattern, regex=True, na=False)
        & (movement >= 48)
        & (keynes >= 50)
        & ((hume >= 40) | (relative >= 45) | (asymmetry >= 45) | (long_term >= 45))
    )

    fit_score = (
        movement * 0.30
        + hume * 0.16
        + keynes * 0.16
        + relative * 0.12
        + asymmetry * 0.12
        + pre_flow * 0.08
        + data * 0.04
        + long_term * 0.02
        - dilution * 0.04
        - survival * 0.035
        - zombie * 0.25
        - event_penalty * 0.16
        - reset_cycle.astype(float) * 6
    )
    output["_best_fit_score"] = fit_score

    no_go = (
        (data < 60)
        | (movement < 35)
        | (dilution >= 85)
        | (survival >= 80)
        | ((thesis_break >= 80) & ~reset_catalyst)
        | reset_cycle
        | hard_stop_event
    )
    labels = output["what_i_think"].astype(str)

    if not (labels == "SCOOBY DOOBY DOO!!").any():
        scooby_pool = output[~no_go & (movement >= 50) & (hume >= 40) & (keynes >= 45)]
        if not scooby_pool.empty:
            idx = scooby_pool["_best_fit_score"].idxmax()
            output.loc[idx, "what_i_think"] = "SCOOBY DOOBY DOO!!"
            output.loc[idx, "personal_signal_label"] = "SCOOBY DOOBY DOO!!"
            output.loc[idx, "label_basis"] = "best available candidate in this batch; still verify risks"

    labels = output["what_i_think"].astype(str)
    if not (labels == "Scrappy Doo").any():
        scrappy_pool = output[
            ~no_go
            & ~output["what_i_think"].astype(str).isin(["SCOOBY DOOBY DOO!!"])
            & (movement >= 35)
        ]
        if not scrappy_pool.empty:
            idx = scrappy_pool["_best_fit_score"].idxmax()
            output.loc[idx, "what_i_think"] = "Scrappy Doo"
            output.loc[idx, "personal_signal_label"] = "Scrappy Doo"
            output.loc[idx, "label_basis"] = "best fledgling candidate in this batch; still verify risks"

    return output.drop(columns=["_best_fit_score"])


def classify_setup_type(
    austrian: float,
    hume: float,
    keynes: float,
    movement_score: float,
    pre_flow_opportunity: float,
) -> str:
    """Return a plain setup bucket separate from the user's fun label."""
    if movement_score >= 78 and hume >= 50 and keynes >= 60:
        return "Prime mover candidate"
    if pre_flow_opportunity >= 55 and hume < 40:
        return "Pricing gap waiting on volume"
    if austrian >= 70 and hume < 45 and keynes < 55:
        return "Pricing gap without confirmation"
    if hume >= 55 and keynes < 65:
        return "Flow-first mover"
    if keynes >= 70 and hume < 45:
        return "Story-first speculation"
    if movement_score >= 55:
        return "Mixed research candidate"
    if movement_score >= 35:
        return "Incomplete setup"
    return "Low-priority setup"


def classify_risk_posture(
    row: pd.Series,
    event_override: dict[str, Any],
    zombie_decay: dict[str, Any],
    data_confidence: float,
    movement_score: float = 0,
    hume: float = 0,
    keynes: float = 0,
    relative: float = 0,
    asymmetry: float = 0,
    dcf: dict[str, Any] | None = None,
    long_term: dict[str, Any] | None = None,
) -> str:
    """Return a readable risk posture without folding every flag into what_i_think."""
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    event_penalty = clean_float(event_override.get("event_shock_penalty"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    zombie_penalty = clean_float(zombie_decay.get("zombie_decay_penalty"))
    if data_confidence < 45:
        return "Data thin: verify manually"
    if is_liquidation_event(row, event_override):
        return "Liquidation / wind-down"
    if is_hard_stop_event(row, event_override):
        return "Hard stop: reset/event shock"
    if has_reset_catalyst(row, event_override, movement_score, hume, keynes, relative, asymmetry, dcf, long_term):
        return "Old thesis reset watch"
    if thesis_break >= 80:
        return "Old thesis broken: needs reset catalyst"
    if is_catastrophic_reset_cycle(row, event_override):
        return "Catastrophic reset cycle"
    if dilution >= 85:
        return "Extreme dilution watch"
    if dilution >= 70 and survival >= 70:
        return "Dilution plus survival pressure"
    if survival >= 70:
        return "Survival pressure elevated"
    if dilution >= 70:
        return "Dilution pressure elevated"
    if event_penalty > 0:
        return "Event shock active"
    if zombie_penalty > 0:
        return "Zombie drag active"
    if str(zombie_decay.get("zombie_decay_label") or "") == "Old but still violent":
        return "Old name, still moving"
    return "Clean enough to study"


def build_event_callouts(row: pd.Series, event_override: dict[str, Any]) -> str:
    """Summarize event-shock context as a callout, not always as a penalty."""
    label = str(row.get("event_shock_label") or "").strip()
    reason = str(row.get("event_shock_reason") or "").strip()
    note = str(event_override.get("event_override_note") or "").strip()
    penalty = clean_float(event_override.get("event_shock_penalty"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    if not label or label.lower() in {"nan", "none_detected", "metadata_none"}:
        return "No major event shock flagged"
    stance = "callout"
    if thesis_break >= 80:
        stance = "thesis reset"
    elif penalty > 0:
        stance = "score penalty"
    detail = note or reason or label
    return f"{stance}: {label} - {detail[:180]}"


def build_ranking_note(
    austrian: float,
    hume: float,
    keynes: float,
    relative: float,
    asymmetry: float,
    data_confidence: float,
    row: pd.Series,
    factors: dict[str, Any] | None = None,
    event_override: dict[str, Any] | None = None,
    zombie_decay: dict[str, Any] | None = None,
) -> str:
    """Explain why the movement score ranked the ticker where it did."""
    event_override = event_override or {}
    zombie_decay = zombie_decay or {}
    strengths = []
    weaknesses = []
    if austrian >= 70:
        strengths.append("Austrian signal is high, meaning the market may be pricing in a lot of damage or survival risk.")
    elif austrian < 35:
        weaknesses.append("Austrian signal is low, so the engine sees less pricing-gap pressure.")
    if hume >= 60:
        strengths.append("Hume flow is visible, so money/volume may already be moving.")
    elif hume < 30:
        weaknesses.append("Hume flow is quiet, so movement is not confirmed yet.")
    if keynes >= 60:
        strengths.append("Keynes story power is strong enough that other investors may understand the setup.")
    elif keynes < 30:
        weaknesses.append("Keynes story power is weak, so attention may be harder to attract.")
    if relative >= 50:
        strengths.append("Relative mispricing contributes to the rank.")
    else:
        weaknesses.append("Relative mispricing is weak, so the stock may not look unusually overlooked versus context.")
    if asymmetry >= 50:
        strengths.append("Asymmetry contributes to the rank.")
    else:
        weaknesses.append("Asymmetry is weak, so the setup may be less 10-bagger-shaped.")
    if data_confidence >= 75:
        strengths.append("Data quality is strong enough to take the read more seriously.")
    elif data_confidence < 50:
        weaknesses.append("Data quality is thin, so the ranking needs manual verification.")

    dilution = to_float(row.get("dilution_pressure_score")) or 0
    survival = to_float(row.get("survival_risk_score")) or 0
    if dilution >= 70:
        weaknesses.append("SEC metadata suggests high dilution pressure.")
    if dilution >= 85:
        weaknesses.append("Extreme dilution pressure is a major ranking haircut.")
    if survival >= 70:
        weaknesses.append("Survival-risk proxy is elevated.")
    event_shock = clean_float(event_override.get("event_shock_penalty"))
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    event_note = str(event_override.get("event_override_note") or "")
    if event_shock > 0:
        weaknesses.append(f"Known event shock penalty is active: {event_note}")
    if thesis_break >= 80:
        weaknesses.append("Major thesis-break risk: the old story may no longer be the right story.")
    zombie_penalty = clean_float(zombie_decay.get("zombie_decay_penalty"))
    if zombie_penalty > 0:
        weaknesses.append(f"Zombie decay is active: {zombie_decay.get('zombie_decay_note')}")
    elif str(zombie_decay.get("zombie_decay_label") or "") == "Old but still violent":
        strengths.append("The name is old, but recent violent/dynamic movement offsets zombie decay.")
    factor_note = factors.get("factor_stack_note") if factors else None
    if factor_note:
        strengths.append(f"Factor stack: {factor_note}.")

    note = " ".join(strengths[:4])
    if weaknesses:
        note += " Watch-outs: " + " ".join(weaknesses[:4])
    return note or "The ranking is mixed; no single signal dominates."


def explain_sequence(sequence_interpretation: str) -> str:
    """Explain what the sequence pattern means as a research note."""
    explanations = {
        "Prime setup: pricing gap + flow + story": (
            "Austrian, Hume, and Keynes are all high: pricing-gap pressure, flow, and story are aligned. "
            "This is the cleanest movement setup, but still needs dilution and survival checks."
        ),
        "Austrian-heavy: pricing gap without confirmation": (
            "Austrian is high by itself: the stock may look mispriced because the market is pricing in damage, "
            "but flow and story are missing. This can be a value trap."
        ),
        "Hume-heavy: money is moving, thesis is thinner": (
            "Hume is high by itself: money or volume is moving, but the engine does not see enough pricing-gap "
            "or story support yet. This may be movement without deep asymmetry."
        ),
        "Keynes-heavy: story without enough proof": (
            "Keynes is high by itself: the story is easy to care about, but flow and pricing-gap confirmation are weak. "
            "This can be narrative without proof."
        ),
        "Pricing gap + story, waiting on flow": (
            "Austrian and Keynes are high: the market may be pricing in too much damage, and the story is understandable. "
            "Hume is not high yet, so money has not clearly arrived."
        ),
        "Pricing gap + flow, story still unclear": (
            "Austrian and Hume are high: a pricing-gap setup may be attracting flow, but the public story is not obvious yet. "
            "Research should ask why money is moving."
        ),
        "Flow + story, smaller pricing gap": (
            "Hume and Keynes are high: money and story are present, but the Austrian pricing-gap signal is weaker. "
            "It may already be partly noticed."
        ),
        "Incomplete setup: needs more evidence": (
            "The three theory signals do not line up cleanly yet. Treat it as incomplete and look for the missing piece."
        ),
        "Old thesis broken, investigate": (
            "A known thesis-changing event is overriding the old bullish setup. The stock may still have speculative ingredients, "
            "but the prior story needs a fresh catalyst before the ranking should treat it as attractive."
        ),
    }
    return explanations.get(sequence_interpretation, "Sequence pattern needs manual review.")


def build_subsignal_tags(sub: dict[str, Any]) -> str:
    """Build compact advanced-detail tags for Ricardo/Malthus/Technology sub-signals."""
    tags = [
        f"tech_narrative={sub['technology_narrative_score']}",
        f"tech_usefulness={sub['technology_usefulness_score']}",
        f"narrative_evolution={sub.get('narrative_evolution_score', 20)}",
        f"ricardo_productivity={sub['ricardo_productivity_score']}",
        f"malthus_constraint={sub['malthus_constraint_score']}",
    ]
    if sub.get("narrative_evolution_clusters"):
        tags.append("outcome_clusters=" + str(sub["narrative_evolution_clusters"]))
    if sub["tech_hype_warning"]:
        tags.append(f"tech_hype_warning=-{sub['tech_hype_warning']}")
    if sub["boring_beneficiary_flag"]:
        tags.append("boring_beneficiary")
    return "; ".join(tags)


def interpret_thesis_integrity(
    event_override: dict[str, Any] | None,
    row: pd.Series,
    movement_score: float = 0,
    hume: float = 0,
    keynes: float = 0,
    relative: float = 0,
    asymmetry: float = 0,
    dcf: dict[str, Any] | None = None,
    long_term: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Explain whether known events alter the raw setup read."""
    event_override = event_override or {}
    thesis_break = clean_float(event_override.get("thesis_break_risk_score"))
    event_shock = clean_float(event_override.get("event_shock_penalty"))
    dilution = clean_float(row.get("dilution_pressure_score"))
    survival = clean_float(row.get("survival_risk_score"))
    note = str(event_override.get("event_override_note") or "")
    event_label = str(row.get("event_shock_label") or "")
    event_confidence = str(row.get("event_shock_confidence") or "")
    if is_liquidation_event(row, event_override):
        return (
            "Liquidation / Wind-Down",
            note or "The company appears to be pursuing liquidation, dissolution, or an orderly wind-down. Treat this as a hard thesis break, not a reset setup.",
        )
    if is_hard_stop_event(row, event_override):
        return (
            "Hard Stop Event Pattern",
            note or "A severe reset-cycle pattern plus fresh event-shock metadata is too dangerous to treat as a candidate without confirmed filing text review.",
        )
    if thesis_break >= 80:
        if has_reset_catalyst(row, event_override, movement_score, hume, keynes, relative, asymmetry, dcf, long_term):
            return (
                "Reset Catalyst Watch",
                note or "The old thesis was impaired, but the event language includes a possible reset catalyst. Treat as fresh-research material, not a clean bullish read.",
            )
        return (
            "Old thesis broken, investigate",
            note or "A known thesis-changing event means the old setup needs fresh proof before it deserves trust.",
        )
    if event_shock > 0 and event_confidence == "metadata_only" and event_label.startswith("metadata_"):
        return (
            "Filing Activity Watch",
            note or "Recent filing activity is unusual enough to watch, but the engine did not confirm a specific negative event in 8-K text.",
        )
    if event_shock > 0:
        return (
            "Event Shock Active",
            note or "A known event shock is reducing confidence in the raw setup.",
        )
    if dilution >= 70 or survival >= 70:
        return (
            "Risk Check Required",
            "SEC-derived dilution or survival pressure is high enough that the raw setup needs manual verification.",
        )
    return (
        "No Major Thesis Break Flagged",
        "No configured thesis-breaking event is overriding the raw setup. This does not remove ordinary dilution, liquidity, or execution risk.",
    )


def interpret_flow_confirmation(
    hume: float,
    factors: dict[str, Any],
    pre_flow_opportunity: float,
) -> tuple[str, str]:
    """Label whether money/volume has arrived or the setup is still pre-flow."""
    trading_setup = clean_float(factors.get("trading_setup_factor"))
    flow_factor = clean_float(factors.get("flow_factor"))
    if hume >= 55 or flow_factor >= 55:
        return (
            "Flow Confirmed",
            "Money, volume, filing activity, or relative-flow evidence is already visible. This is less early, but more confirmed.",
        )
    if hume >= 35 or trading_setup >= 35:
        return (
            "Early Flow Watch",
            "Some flow evidence exists, but it is not strong enough to call confirmed. Watch for volume expansion.",
        )
    if pre_flow_opportunity >= 55:
        return (
            "Pre-Flow Setup",
            "The setup has pricing/story/asymmetry ingredients, but money has not arrived yet. This can be early, stagnant, or wrong.",
        )
    return (
        "No Flow Confirmation",
        "The engine does not yet see meaningful money movement. Without flow or a catalyst, the setup may sit or fail.",
    )


def interpret_final_rank(movement_score: float, pre_flow_opportunity: float = 0, hume: float = 0) -> str:
    """Translate final movement score into a plain research-priority tier."""
    if movement_score >= 78:
        return "High-priority research candidate"
    if movement_score >= 66:
        return "Promising but verify risks"
    if pre_flow_opportunity >= 55 and hume < 35 and movement_score >= 50:
        return "Pre-flow watchlist candidate"
    if movement_score >= 55:
        return "Mixed watchlist candidate"
    if movement_score >= 35:
        return "Low-priority or incomplete setup"
    return "Do not prioritize without new proof"


def interpret_sequence(
    austrian: float,
    hume: float,
    keynes: float,
    config: dict[str, Any],
) -> str:
    """Interpret the three-score combination in the user's requested language."""
    sequence_thresholds = config["scoring"].get("sequence_thresholds", {})
    high_a = austrian >= sequence_thresholds.get("austrian_high", 70)
    high_h = hume >= sequence_thresholds.get("hume_high", 55)
    high_k = keynes >= sequence_thresholds.get("keynes_high", 70)
    if high_a and high_h and high_k:
        return "Prime setup: pricing gap + flow + story"
    if high_a and not high_h and not high_k:
        return "Austrian-heavy: pricing gap without confirmation"
    if high_h and not high_a and not high_k:
        return "Hume-heavy: money is moving, thesis is thinner"
    if high_k and not high_a and not high_h:
        return "Keynes-heavy: story without enough proof"
    if high_a and high_k and not high_h:
        return "Pricing gap + story, waiting on flow"
    if high_a and high_h and not high_k:
        return "Pricing gap + flow, story still unclear"
    if high_h and high_k and not high_a:
        return "Flow + story, smaller pricing gap"
    return "Incomplete setup: needs more evidence"


def _read_csv(relative_path: str) -> pd.DataFrame:
    """Read a project CSV, returning an empty frame if missing or invalid."""
    path = project_path(relative_path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


def _save_scores(scores: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Save theory scores and ranked watchlist outputs."""
    scores_path = project_path(config["paths"]["theory_scores_output"])
    watchlist_path = project_path(config["paths"]["ranked_watchlist_output"])
    focused_watchlist_path = watchlist_path.with_name("focused_research_watchlist.csv")
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    watchlist_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(scores_path, index=False)
    scores.to_csv(watchlist_path, index=False)
    focused = scores
    if "what_i_think" in focused.columns:
        focused = focused[focused["what_i_think"].astype(str) != "This is Garbage"]
    focused.to_csv(focused_watchlist_path, index=False)
    logger.info("Theory scores saved to %s with %s rows", scores_path, len(scores))
    logger.info("Ranked repricing watchlist saved to %s", watchlist_path)
    logger.info("Focused non-garbage watchlist saved to %s with %s rows", focused_watchlist_path, len(focused))
    return scores


def run() -> pd.DataFrame:
    """Run scoring independently from the command line."""
    config = load_config()
    logger = configure_logging(config["paths"].get("log_file"))
    return build_theory_scores(config, logger)


def main() -> None:
    """Run the economic theory scoring module independently."""
    parser = argparse.ArgumentParser(description="Compute Austrian/Hume/Keynes repricing scores.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    scores = build_theory_scores(config, logger)
    print(scores.head(25).to_string(index=False))


if __name__ == "__main__":
    main()
