"""Event-shock interpretation layer for SEC filing metadata and 8-K details."""

from __future__ import annotations

import argparse
import logging
import re
import urllib.error
import urllib.request
from urllib.parse import urljoin
from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from utils.cache import read_json_cache, write_json_cache
from utils.helpers import to_float
from utils.logging_config import configure_logging
from utils.paths import ensure_project_dirs, load_config, project_path
from utils.source_status import record_source_status


EVENT_SHOCK_COLUMNS = [
    "ticker",
    "company_name",
    "event_shock_suspected_score",
    "event_shock_detail_score",
    "event_shock_score",
    "event_shock_label",
    "event_shock_reason",
    "event_shock_source_url",
    "event_thesis_break_risk_score",
    "event_shock_confidence",
    "event_business_profile",
    "event_identity_terms",
]


DETAIL_PATTERNS = [
    (
        "liquidation_or_dissolution",
        70,
        100,
        [
            r"\bcomplete liquidation\b",
            r"\bplan of liquidation\b",
            r"\bplan of dissolution\b",
            r"\bdissolution and liquidation\b",
            r"\bliquidation and dissolution\b",
            r"\borderly wind[- ]down\b",
            r"\bwind down of operations\b",
            r"\bwinddown of operations\b",
            r"\bdelist its shares\b",
            r"\bcertificate of dissolution\b",
        ],
    ),
    ("bankruptcy_or_receivership", 50, 85, [r"\bbankruptcy\b", r"\bchapter 11\b", r"\breceivership\b"]),
    ("default_or_acceleration", 42, 75, [r"\bevent of default\b", r"\bdefault\b", r"\bacceleration\b"]),
    ("delisting_or_listing_failure", 38, 70, [r"\bdelisting\b", r"\bnasdaq.*non-compliance\b", r"\bminimum bid\b"]),
    ("going_concern_or_liquidity", 34, 65, [r"\bgoing concern\b", r"\bliquidity\b", r"\bsubstantial doubt\b"]),
    ("reverse_split", 24, 35, [r"\breverse stock split\b", r"\breverse split\b"]),
    ("major_financing_or_warrants", 32, 45, [r"\bregistered direct\b", r"\bprivate placement\b", r"\bwarrant\b", r"\bconvertible\b"]),
    ("partnership_or_customer_loss", 42, 80, [r"\bterminated.*agreement\b", r"\btermination.*agreement\b", r"\bmaterial customer\b", r"\bcollaboration.*terminated\b"]),
    ("clinical_or_regulatory_setback", 45, 80, [r"\bclinical hold\b", r"\bfda.*hold\b", r"\bfailed.*endpoint\b", r"\bcomplete response letter\b"]),
    ("restructuring_or_workforce", 30, 55, [r"\brestructuring\b", r"\bworkforce reduction\b", r"\blayoff\b", r"\breduction in force\b"]),
    ("asset_sale_or_impairment", 26, 45, [r"\bimpairment\b", r"\basset sale\b", r"\bgoing private\b"]),
    (
        "business_pivot_or_rebrand",
        14,
        10,
        [
            r"\bstrategic (?:focus|pivot|transformation)\b",
            r"\bbusiness combination\b",
            r"\brecent combination\b",
            r"\bevolved into\b",
            r"\brebrand(?:ed|ing)?\b",
            r"\boperating as\b",
            r"\bflash sports\b",
            r"\bglobal t20 cricket\b",
            r"\bt20 cricket\b",
            r"\bcricket ecosystem\b",
            r"\bsports media\b",
            r"\bsports and entertainment\b",
            r"\bmedia rights\b",
            r"\bbroadcast rights\b",
            r"\blive events\b",
        ],
    ),
]


BUSINESS_IDENTITY_PATTERNS = [
    (
        "sports_media",
        [
            r"\bflash sports\b",
            r"\bglobal t20 cricket\b",
            r"\bt20 cricket\b",
            r"\bcricket ecosystem\b",
            r"\bsports media\b",
            r"\bsports and entertainment\b",
            r"\bmedia rights\b",
            r"\bbroadcast rights\b",
            r"\blive events\b",
            r"\bbranded fan experiences\b",
        ],
        "SEC filing exhibits describe a sports/media pivot around Flash Sports & Media, T20 cricket, league rights, media distribution, sponsorships, and live-event monetization.",
    ),
    (
        "construction_services",
        [
            r"\bconstruction\b",
            r"\barchitecture\b",
            r"\bengineering\b",
            r"\bfacility design\b",
            r"\bdesign-build\b",
            r"\bcontrolled environment agriculture\b",
        ],
        "SEC filing text describes construction, design-build, engineering, or controlled-environment agriculture services.",
    ),
]


BENIGN_MANAGEMENT_PATTERNS = [
    r"\bappointed\b",
    r"\belected\b",
    r"\bsuccessor\b",
    r"\binterim\b",
    r"\bannual meeting\b",
    r"\bnot due to any disagreement\b",
    r"\bnot because of any disagreement\b",
    r"\bno disagreement\b",
    r"\bno disagreements\b",
]


MANAGEMENT_EXIT_PATTERNS = [
    r"\bchief executive officer\b.{0,120}\bresign",
    r"\bresign.{0,120}\bchief executive officer\b",
    r"\bchief financial officer\b.{0,120}\bresign",
    r"\bresign.{0,120}\bchief financial officer\b",
    r"\bprincipal executive officer\b.{0,120}\bresign",
    r"\bprincipal financial officer\b.{0,120}\bresign",
    r"\bterminated.{0,120}\bemployment\b",
    r"\btermination.{0,120}\bemployment\b",
]


AUDITOR_CHANGE_PATTERNS = [
    r"\bchange.{0,80}accountant\b",
    r"\bindependent registered public accounting firm\b.{0,120}\bdismiss",
    r"\bauditor\b.{0,120}\bresign",
    r"\baccountant\b.{0,120}\bresign",
]


AUDITOR_NEGATIVE_PATTERNS = [
    r"\bdisagreement\b",
    r"\breportable event\b",
    r"\badverse opinion\b",
    r"\bgoing concern\b",
    r"\bmaterial weakness\b",
]


THESIS_BREAK_DETAIL_LABELS = {
    "liquidation_or_dissolution",
    "bankruptcy_or_receivership",
    "default_or_acceleration",
    "delisting_or_listing_failure",
    "partnership_or_customer_loss",
    "clinical_or_regulatory_setback",
    "abrupt_management_exit",
    "auditor_change_with_warning",
}


def build_event_shocks(
    config: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    research_batch: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build event-shock scores from SEC metadata and selected 8-K text."""
    config = config or load_config()
    ensure_project_dirs(config)
    logger = logger or configure_logging(config["paths"].get("log_file"))
    if not config.get("event_shocks", {}).get("enabled", True):
        return save_event_shocks(pd.DataFrame(columns=EVENT_SHOCK_COLUMNS), config, logger)

    filings = _read_csv(config["paths"]["sec_filings_output"])
    signals = _read_csv(config["paths"]["sec_signals_output"])
    if filings.empty and signals.empty:
        logger.info("Event shock stage skipped because SEC metadata is empty")
        return save_event_shocks(pd.DataFrame(columns=EVENT_SHOCK_COLUMNS), config, logger)

    batch_tickers = set()
    if research_batch is not None and not research_batch.empty and "ticker" in research_batch.columns:
        batch_tickers = set(research_batch["ticker"].dropna().astype(str).str.upper())
    elif project_path(config["paths"].get("research_batch_output", "")).exists():
        batch = _read_csv(config["paths"]["research_batch_output"])
        batch_tickers = set(batch.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper())

    rows = []
    all_tickers = sorted(set(filings.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper()) | set(signals.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper()))
    detail_limit = int(config.get("event_shocks", {}).get("max_detail_tickers", 100))
    detail_tickers = set(list(batch_tickers)[:detail_limit])
    inspect_suspicious = bool(config.get("event_shocks", {}).get("inspect_suspicious_outside_batch", False))
    total = len(all_tickers)
    for index, ticker in enumerate(all_tickers, start=1):
        if index == 1 or index % 10 == 0 or index == total:
            print(f"      Event shock scan: {index}/{total} tickers checked", flush=True)
        filing_group = filings[filings["ticker"].astype(str).str.upper() == ticker].copy() if not filings.empty else pd.DataFrame()
        signal_row = _first_row(signals[signals["ticker"].astype(str).str.upper() == ticker]) if not signals.empty else {}
        suspicion = score_event_shock_suspicion(filing_group, signal_row, config)
        needs_detail = (
            ticker in detail_tickers
            or (inspect_suspicious and (suspicion["score"] >= 30 or suspicion["thesis_break"] > 0))
        )
        detail = score_event_shock_detail(filing_group, config, logger) if needs_detail else empty_detail()
        score = min(100, max(suspicion["score"], detail["score"], suspicion["score"] + detail["score"] * 0.35))
        thesis_break = min(100, max(suspicion["thesis_break"], detail["thesis_break"]))
        label = choose_event_label(score, detail["label"], suspicion["label"])
        rows.append(
            {
                "ticker": ticker,
                "company_name": signal_row.get("company_name") or _first_value(filing_group, "company_name"),
                "event_shock_suspected_score": round(suspicion["score"], 1),
                "event_shock_detail_score": round(detail["score"], 1),
                "event_shock_score": round(score, 1),
                "event_shock_label": label,
                "event_shock_reason": " | ".join(part for part in [suspicion["reason"], detail["reason"]] if part),
                "event_shock_source_url": detail["source_url"] or suspicion["source_url"],
                "event_thesis_break_risk_score": round(thesis_break, 1),
                "event_shock_confidence": detail["confidence"] if detail["score"] > 0 else suspicion["confidence"],
                "event_business_profile": detail.get("business_profile", ""),
                "event_identity_terms": detail.get("identity_terms", ""),
            }
        )
    return save_event_shocks(pd.DataFrame(rows, columns=EVENT_SHOCK_COLUMNS), config, logger)


def score_event_shock_suspicion(filings: pd.DataFrame, signal_row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Stage 1: metadata-only event shock suspicion."""
    if filings.empty and not signal_row:
        return {"score": 0, "label": "none_detected", "reason": "", "source_url": "", "thesis_break": 0, "confidence": "metadata_none"}
    frame = filings.copy()
    if not frame.empty:
        frame["filing_date_dt"] = pd.to_datetime(frame["filing_date"], errors="coerce", utc=True)
    now = pd.Timestamp(datetime.now(timezone.utc))
    recent_cutoff = now - pd.Timedelta(days=config["sec"]["recent_activity_days"])
    recent = frame[frame["filing_date_dt"] >= recent_cutoff] if not frame.empty else frame
    forms = recent.get("filing_type", pd.Series(dtype=str)).dropna().astype(str).str.upper().tolist()
    financing_count = sum(1 for form in forms if form in {"S-1", "S-3"} or form.startswith("424B"))
    eightk_count = forms.count("8-K")
    nt_count = sum(1 for form in forms if form.startswith("NT "))
    dilution = to_float(signal_row.get("dilution_pressure_score")) or 0
    survival = to_float(signal_row.get("survival_risk_score")) or 0
    narrative = to_float(signal_row.get("narrative_trigger_score")) or 0
    activity = to_float(signal_row.get("filing_activity_score")) or 0
    score = 0
    thesis_break = 0
    reasons = []
    if financing_count >= 2 or dilution >= 70:
        score += 30
        reasons.append("financing/prospectus burst")
    elif financing_count == 1 or dilution >= 35:
        score += 18
        reasons.append("financing/prospectus activity")
    if survival >= 70:
        score += 24
        thesis_break += 30
        reasons.append("high survival-risk metadata")
    if eightk_count >= 3:
        score += 24
        reasons.append("recent 8-K cluster")
    elif eightk_count >= 1 and activity >= 60:
        score += 16
        reasons.append("8-K plus filing activity spike")
    if nt_count:
        score += 26
        thesis_break += 20
        reasons.append("late periodic report notice")
    if narrative >= 60 and activity >= 60:
        score += 12
        reasons.append("narrative/activity spike")
    score = min(80, score)
    source_frame = recent[recent["filing_type"].astype(str).str.upper() == "8-K"] if not recent.empty and "filing_type" in recent.columns else recent
    return {
        "score": score,
        "label": "metadata_shock_suspected" if score >= 35 else "metadata_watch" if score > 0 else "none_detected",
        "reason": "; ".join(reasons),
        "source_url": (_first_value(source_frame, "filing_url") or _first_value(recent, "filing_url") or _first_value(frame, "filing_url") or "") if score > 0 else "",
        "thesis_break": min(70, thesis_break),
        "confidence": "metadata_only" if score > 0 else "metadata_none",
    }


def score_event_shock_detail(filings: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    """Stage 2: inspect recent 8-K filing text for shock language."""
    if filings.empty:
        return empty_detail()
    frame = filings.copy()
    frame["filing_date_dt"] = pd.to_datetime(frame["filing_date"], errors="coerce", utc=True)
    eightks = frame[frame["filing_type"].astype(str).str.upper() == "8-K"].sort_values("filing_date_dt", ascending=False)
    max_docs = int(config.get("event_shocks", {}).get("max_8k_documents_per_ticker", 3))
    best = empty_detail()
    for _, row in eightks.head(max_docs).iterrows():
        url = str(row.get("filing_url") or "")
        if not url:
            continue
        try:
            text = fetch_filing_text(url, config, logger)
        except Exception as exc:
            logger.debug("Event shock detail fetch skipped for %s: %s", url, exc)
            continue
        detail = classify_event_text(text)
        if detail["score"] > best["score"]:
            best = {**detail, "source_url": url, "confidence": "8k_text"}
        elif detail.get("business_profile") and not best.get("business_profile"):
            best = {
                **best,
                "source_url": best.get("source_url") or url,
                "business_profile": detail.get("business_profile", ""),
                "identity_terms": detail.get("identity_terms", ""),
            }
    return best


def fetch_filing_text(url: str, config: dict[str, Any], logger: logging.Logger) -> str:
    """Fetch and cache a filing document as plain text."""
    cache_dir = config["paths"]["cache_dir"]
    cache_key = "event_shock_doc_v2_" + re.sub(r"[^A-Za-z0-9]+", "_", url)[-140:]
    ttl = int(config.get("event_shocks", {}).get("cache_ttl_hours", config["refresh"].get("cache_ttl_hours", 24)))
    cached = read_json_cache(cache_dir, cache_key, ttl)
    if cached and isinstance(cached, dict):
        return str(cached.get("text") or "")
    headers = {"User-Agent": config["sec"].get("default_user_agent", "ContrarianFlowEngine research@example.com")}
    timeout = int(config.get("event_shocks", {}).get("detail_timeout_seconds", 8))
    if requests is not None:
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        raw_text = response.text[:350_000]
    else:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_text = response.read(350_000).decode("utf-8", errors="ignore")
    text_parts = [html_to_text(raw_text)]
    if bool(config.get("event_shocks", {}).get("scan_exhibits", True)):
        max_exhibits = int(config.get("event_shocks", {}).get("max_exhibit_documents_per_filing", 2))
        for exhibit_url in extract_exhibit_urls(raw_text, url)[:max_exhibits]:
            try:
                exhibit_raw = fetch_raw_document(exhibit_url, headers, timeout)
            except Exception as exc:
                logger.debug("Event shock exhibit fetch skipped for %s: %s", exhibit_url, exc)
                continue
            text_parts.append(html_to_text(exhibit_raw[:350_000]))
    text = "\n\n".join(text_parts)
    write_json_cache(cache_dir, cache_key, {"url": url, "text": text[:120_000]})
    logger.debug("Cached event shock filing text for %s", url)
    return text


def fetch_raw_document(url: str, headers: dict[str, str], timeout: int) -> str:
    """Fetch a single SEC document without cache orchestration."""
    if requests is not None:
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.text
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(350_000).decode("utf-8", errors="ignore")


def extract_exhibit_urls(raw_html: str, base_url: str) -> list[str]:
    """Find high-signal exhibit documents linked from a filing cover page."""
    links: list[str] = []
    seen = set()
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw_html or "", "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "")
            label = " ".join([str(anchor.get_text(" ", strip=True) or ""), href]).lower()
            if not is_detail_exhibit_link(label, href):
                continue
            absolute = urljoin(base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)
    if links:
        return links
    for match in re.finditer(r'href=["\']([^"\']+)["\']', raw_html or "", flags=re.IGNORECASE):
        href = match.group(1)
        if is_detail_exhibit_link(href.lower(), href):
            absolute = urljoin(base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)
    return links


def is_detail_exhibit_link(label: str, href: str) -> bool:
    """Keep exhibits likely to hold business-update language, not XBRL/static assets."""
    combined = f"{label} {href}".lower()
    if any(skip in combined for skip in [".xml", ".xsd", ".jpg", ".png", ".gif", "ixviewer", "xslf345"]):
        return False
    return bool(re.search(r"(?:^|[^a-z0-9])ex(?:hibit)?[-_ ]?99|ex99[-_ ]?\d|\b99\.[0-9]\b|press release|investor presentation", combined))


def html_to_text(raw_html: str) -> str:
    """Convert HTML-ish filing content into searchable text."""
    if BeautifulSoup is not None:
        return BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"<[^>]+>", " ", raw_html)


def classify_event_text(text: str) -> dict[str, Any]:
    """Classify event shock details from filing text."""
    clean = re.sub(r"\s+", " ", str(text or "").lower())
    matches = []
    best_score = 0
    best_thesis = 0
    best_label = ""
    business_identity = classify_business_identity(clean)
    management_detail = classify_management_change(clean)
    if management_detail["score"] > 0:
        matches.append(management_detail["label"])
        if management_detail["score"] > best_score:
            best_score = management_detail["score"]
            best_label = management_detail["label"]
        best_thesis = max(best_thesis, management_detail["thesis_break"])
    auditor_detail = classify_auditor_change(clean)
    if auditor_detail["score"] > 0:
        matches.append(auditor_detail["label"])
        if auditor_detail["score"] > best_score:
            best_score = auditor_detail["score"]
            best_label = auditor_detail["label"]
        best_thesis = max(best_thesis, auditor_detail["thesis_break"])
    for label, score, thesis, patterns in DETAIL_PATTERNS:
        if any(re.search(pattern, clean) for pattern in patterns):
            matches.append(label)
            if score > best_score:
                best_score = score
                best_label = label
            best_thesis = max(best_thesis, thesis)
    if not matches:
        if business_identity["identity_terms"]:
            detail = empty_detail()
            detail.update(
                {
                    "score": 0,
                    "label": "business_identity_context",
                    "reason": "SEC text identified business context: " + business_identity["identity_terms"],
                    "business_profile": business_identity["business_profile"],
                    "identity_terms": business_identity["identity_terms"],
                }
            )
            return detail
        return empty_detail()
    return {
        "score": min(100, best_score + min(20, (len(matches) - 1) * 6)),
        "label": best_label or matches[0],
        "reason": "8-K text matched: " + ", ".join(matches[:4]),
        "source_url": "",
        "thesis_break": best_thesis,
        "confidence": "8k_text",
        "business_profile": business_identity["business_profile"],
        "identity_terms": business_identity["identity_terms"],
    }


def classify_business_identity(clean_text: str) -> dict[str, str]:
    """Extract a plain-English business profile clue from SEC filing text."""
    identities = []
    profiles = []
    for label, patterns, profile in BUSINESS_IDENTITY_PATTERNS:
        if any(re.search(pattern, clean_text) for pattern in patterns):
            identities.append(label)
            profiles.append(profile)
    return {
        "identity_terms": ", ".join(identities),
        "business_profile": " ".join(profiles[:2]),
    }


def classify_management_change(clean_text: str) -> dict[str, Any]:
    """Classify management changes without treating signatures as resignations."""
    has_item_502 = "item 5.02" in clean_text
    has_exit = any(re.search(pattern, clean_text) for pattern in MANAGEMENT_EXIT_PATTERNS)
    has_benign_context = any(re.search(pattern, clean_text) for pattern in BENIGN_MANAGEMENT_PATTERNS)
    has_disagreement = bool(re.search(r"\bdisagreement\b", clean_text)) and not bool(
        re.search(r"\b(no|not due to any|not because of any)\b.{0,80}\bdisagreement", clean_text)
    )
    if has_disagreement and has_exit:
        return {
            "score": 42,
            "label": "abrupt_management_exit",
            "thesis_break": 70,
        }
    if has_item_502 and has_exit and not has_benign_context:
        return {
            "score": 30,
            "label": "management_exit_needs_review",
            "thesis_break": 50,
        }
    if has_item_502 and has_exit:
        return {
            "score": 8,
            "label": "routine_management_transition",
            "thesis_break": 5,
        }
    return {"score": 0, "label": "", "thesis_break": 0}


def classify_auditor_change(clean_text: str) -> dict[str, Any]:
    """Classify auditor changes, separating routine changes from dispute signals."""
    has_auditor_change = any(re.search(pattern, clean_text) for pattern in AUDITOR_CHANGE_PATTERNS)
    if not has_auditor_change:
        return {"score": 0, "label": "", "thesis_break": 0}
    has_negative = any(re.search(pattern, clean_text) for pattern in AUDITOR_NEGATIVE_PATTERNS) and not bool(
        re.search(r"\b(no|not due to any|not because of any)\b.{0,100}\b(disagreement|reportable event)", clean_text)
    )
    if has_negative:
        return {
            "score": 40,
            "label": "auditor_change_with_warning",
            "thesis_break": 70,
        }
    return {
        "score": 14,
        "label": "routine_auditor_change",
        "thesis_break": 15,
    }


def choose_event_label(score: float, detail_label: str, suspicion_label: str) -> str:
    """Choose the display label for event-shock output."""
    if detail_label in THESIS_BREAK_DETAIL_LABELS:
        return "Old thesis broken, investigate"
    if detail_label and detail_label != "none_detected":
        return detail_label
    if score >= 60:
        return "event_shock_likely"
    if score >= 35:
        return suspicion_label or "event_shock_watch"
    if score > 0:
        return "event_shock_watch"
    return "none_detected"


def empty_detail() -> dict[str, Any]:
    """Return an empty detail classification."""
    return {
        "score": 0,
        "label": "none_detected",
        "reason": "",
        "source_url": "",
        "thesis_break": 0,
        "confidence": "not_checked",
        "business_profile": "",
        "identity_terms": "",
    }


def save_event_shocks(frame: pd.DataFrame, config: dict[str, Any], logger: logging.Logger) -> pd.DataFrame:
    """Save event shock output."""
    path = project_path(config["paths"]["event_shocks_output"])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    logger.info("Event shock output saved to %s with %s rows", path, len(frame))
    confidence_counts = frame["event_shock_confidence"].fillna("unknown").astype(str).value_counts().to_dict() if "event_shock_confidence" in frame.columns else {}
    record_source_status(
        config,
        "event_shocks",
        "sec_8k_text_with_metadata_fallback",
        "ok" if len(frame) else "degraded",
        rows=len(frame),
        fallback_used=bool(confidence_counts.get("metadata_only") or confidence_counts.get("not_checked")),
        detail=", ".join(f"{key}={value}" for key, value in sorted(confidence_counts.items())),
    )
    return frame


def _first_row(frame: pd.DataFrame) -> dict[str, Any]:
    """Return the first row as a dict."""
    if frame.empty:
        return {}
    return frame.iloc[0].to_dict()


def _first_value(frame: pd.DataFrame, column: str) -> Any:
    """Return the first non-empty value in a column."""
    if frame.empty or column not in frame.columns:
        return None
    values = frame[column].dropna()
    return values.iloc[0] if not values.empty else None


def _read_csv(relative_path: str) -> pd.DataFrame:
    """Read a project CSV, returning an empty frame when unavailable."""
    path = project_path(relative_path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


def main() -> None:
    """Run event-shock interpretation independently."""
    parser = argparse.ArgumentParser(description="Build event shock interpretation layer.")
    parser.add_argument("--config", default="config.yaml", help="Project-relative config path.")
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config["paths"].get("log_file"))
    build_event_shocks(config, logger)


if __name__ == "__main__":
    main()
